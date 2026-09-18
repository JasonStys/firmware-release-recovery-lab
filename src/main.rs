//! `fwlab` command-line interface for the release and recovery simulator.
//!
//! File map: `Cli` and `Command` define arguments; `run` dispatches commands;
//! `print_state` provides human and JSON audit output. See `docs/code-index.md`.

use std::{fs, path::PathBuf, process::ExitCode};

use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use firmware_recovery::{
    DeviceProfile, NoFault, ReleasePackage, SignedManifest, SlotId, UpdateAgent, Version,
    crypto::demo_signing_key, run_fault_campaign, store::LabStore,
};

/// Educational A/B firmware lifecycle and power-loss recovery simulator.
#[derive(Debug, Parser)]
#[command(name = "fwlab", version, about)]
struct Cli {
    /// Operation to perform.
    #[command(subcommand)]
    command: Command,
}

/// Supported lifecycle, packaging, inspection, and test operations.
#[derive(Debug, Subcommand)]
enum Command {
    /// Initialize a synthetic device with a confirmed slot-A image.
    Init {
        /// Directory that represents the simulated device.
        #[arg(long)]
        root: PathBuf,
        /// Initial firmware version.
        #[arg(long, default_value = "1.0.0")]
        version: Version,
        /// Synthetic initial image contents.
        #[arg(long, default_value = "known-good-v1")]
        image: String,
    },
    /// Build a reproducible demo-signed release package.
    Package {
        /// Output directory for `manifest.json` and `image.bin`.
        #[arg(long)]
        output: PathBuf,
        /// New firmware version.
        #[arg(long)]
        version: Version,
        /// Compatible synthetic hardware identifier.
        #[arg(long, default_value = "edge-controller-v1")]
        hardware: String,
        /// Release identifier recorded in the manifest.
        #[arg(long)]
        release_id: String,
        /// Maximum unsuccessful candidate boots.
        #[arg(long, default_value_t = 3)]
        attempts: u8,
        /// Synthetic image contents.
        #[arg(long, default_value = "synthetic-firmware-image")]
        image: String,
    },
    /// Verify and stage a package in the inactive slot.
    Stage {
        /// Simulated device directory.
        #[arg(long)]
        root: PathBuf,
        /// Release package directory.
        #[arg(long)]
        package: PathBuf,
        /// Synthetic hardware identifier.
        #[arg(long, default_value = "edge-controller-v1")]
        hardware: String,
        /// Local anti-downgrade floor.
        #[arg(long, default_value = "1.0.0")]
        minimum_version: Version,
    },
    /// Select a verified inactive slot for bounded trial boots.
    Activate {
        /// Simulated device directory.
        #[arg(long)]
        root: PathBuf,
        /// Candidate slot, normally B for the first update.
        #[arg(long)]
        slot: SlotId,
        /// Maximum unsuccessful candidate boots.
        #[arg(long, default_value_t = 3)]
        attempts: u8,
    },
    /// Persist and print the next slot selected by the boot policy.
    Boot {
        /// Simulated device directory.
        #[arg(long)]
        root: PathBuf,
    },
    /// Confirm that the currently pending image passed its health check.
    Confirm {
        /// Simulated device directory.
        #[arg(long)]
        root: PathBuf,
    },
    /// Record a failed health check and roll back when attempts are exhausted.
    Fail {
        /// Simulated device directory.
        #[arg(long)]
        root: PathBuf,
        /// Audit explanation for the failed health check.
        #[arg(long, default_value = "health deadline expired")]
        reason: String,
    },
    /// Print the recovered metadata and audit history.
    Status {
        /// Simulated device directory.
        #[arg(long)]
        root: PathBuf,
        /// Emit machine-readable JSON.
        #[arg(long)]
        json: bool,
    },
    /// Exercise every metadata commit boundary and write a JSON report.
    FaultCampaign {
        /// Number of full boundary sets (12 scenarios per iteration).
        #[arg(long, default_value_t = 100)]
        iterations: u32,
        /// Destination for machine-readable campaign evidence.
        #[arg(long)]
        output: Option<PathBuf>,
    },
}

/// Parses the CLI, reports errors without panicking, and returns a process status.
fn main() -> ExitCode {
    match run(Cli::parse()) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("error: {error:#}");
            ExitCode::FAILURE
        }
    }
}

/// Dispatches one CLI operation and prints its auditable result.
// Keeping the short command arms together makes the lifecycle order easier to audit.
#[allow(clippy::too_many_lines)]
fn run(cli: Cli) -> Result<()> {
    match cli.command {
        Command::Init {
            root,
            version,
            image,
        } => {
            if root.exists() {
                anyhow::bail!(
                    "refusing to initialize an existing path: {}",
                    root.display()
                );
            }
            let agent = agent(root, "edge-controller-v1".into(), Version::new(1, 0, 0));
            let state = agent
                .initialize(version, image.as_bytes(), &mut NoFault)
                .context("initialization failed")?;
            print_state(&state, false)?;
        }
        Command::Package {
            output,
            version,
            hardware,
            release_id,
            attempts,
            image,
        } => {
            if output.exists() {
                anyhow::bail!(
                    "refusing to overwrite an existing package: {}",
                    output.display()
                );
            }
            let key = demo_signing_key();
            let image = image.into_bytes();
            let package = ReleasePackage {
                manifest: SignedManifest::create(
                    release_id,
                    version,
                    vec![hardware],
                    attempts,
                    &image,
                    &key,
                )?,
                image,
            };
            package.write(&output)?;
            println!("created signed demo package at {}", output.display());
        }
        Command::Stage {
            root,
            package,
            hardware,
            minimum_version,
        } => {
            let package = ReleasePackage::load(&package).context("package load failed")?;
            let state = agent(root, hardware, minimum_version)
                .stage(&package, &mut NoFault)
                .context("stage failed")?;
            print_state(&state, false)?;
        }
        Command::Activate {
            root,
            slot,
            attempts,
        } => {
            let state = default_agent(root)
                .activate(slot, attempts, &mut NoFault)
                .context("activation failed")?;
            print_state(&state, false)?;
        }
        Command::Boot { root } => {
            let (state, slot) = default_agent(root)
                .boot(&mut NoFault)
                .context("boot selection failed")?;
            println!("selected slot {slot}");
            print_state(&state, false)?;
        }
        Command::Confirm { root } => {
            let state = default_agent(root)
                .confirm_health(&mut NoFault)
                .context("health confirmation failed")?;
            print_state(&state, false)?;
        }
        Command::Fail { root, reason } => {
            let state = default_agent(root)
                .fail_health(&reason, &mut NoFault)
                .context("health failure update failed")?;
            print_state(&state, false)?;
        }
        Command::Status { root, json } => {
            print_state(&default_agent(root).status()?, json)?;
        }
        Command::FaultCampaign { iterations, output } => {
            let report = run_fault_campaign(iterations).context("fault campaign failed")?;
            let json = serde_json::to_string_pretty(&report)?;
            if let Some(path) = output {
                if let Some(parent) = path.parent() {
                    fs::create_dir_all(parent)?;
                }
                fs::write(&path, format!("{json}\n"))?;
                println!("wrote campaign report to {}", path.display());
            }
            println!("{json}");
        }
    }
    Ok(())
}

/// Builds an agent using the deliberately public demonstration verification key.
fn agent(root: PathBuf, hardware_id: String, minimum_version: Version) -> UpdateAgent {
    let key = demo_signing_key();
    UpdateAgent::new(
        LabStore::new(root),
        DeviceProfile {
            hardware_id,
            minimum_version,
        },
        key.verifying_key(),
    )
}

/// Builds an agent using the repository's default synthetic device profile.
fn default_agent(root: PathBuf) -> UpdateAgent {
    agent(root, "edge-controller-v1".into(), Version::new(1, 0, 0))
}

/// Renders compact human status or complete JSON for automation.
fn print_state(state: &firmware_recovery::BootMetadata, json: bool) -> Result<()> {
    if json {
        println!("{}", serde_json::to_string_pretty(state)?);
    } else {
        println!(
            "generation={} phase={:?} active={} confirmed={} pending={} attempts_remaining={}",
            state.generation,
            state.phase,
            state.active,
            state.confirmed,
            state
                .pending
                .map_or_else(|| "none".into(), |slot| slot.to_string()),
            state.attempts_remaining
        );
        if let Some(event) = state.audit.last() {
            println!("last_event={} {}", event.action, event.detail);
        }
    }
    Ok(())
}
