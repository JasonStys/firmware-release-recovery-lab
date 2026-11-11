//! Bounded editable desktop rehearsals using the original signed-package and durable A/B engines.
//!
//! File map: `execute` validates complete requests before creating owned temporary devices;
//! lifecycle records real before/after states, preflight never mutates initialized devices,
//! and campaign retains the original interruption oracle. Exact lines: docs/code-index.md.

use std::{collections::BTreeMap, collections::BTreeSet, fs, str::FromStr};

use serde::Deserialize;
use serde_json::{Value, json};

use crate::{
    BootMetadata, DeviceProfile, FaultInjector, FaultPoint, LabError, NoFault, ReleasePackage,
    SignedManifest, SingleFault, SlotId, UpdateAgent, Version,
    crypto::{demo_signing_key, sha256_hex},
    preflight::{FleetPlan, PlannedDevice, TrialOutcome},
    run_fault_campaign,
    store::LabStore,
};

const MAX_IMAGE: usize = 65_536;

/// Closed requests cannot choose device paths, host commands, signing secrets or network endpoints.
#[derive(Debug, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
enum Request {
    Lifecycle { plan: Plan },
    Preflight { fleet: Fleet },
    Campaign { iterations: u32 },
}

/// Every lifecycle input is retained for semantic rerun, including intended interruptions.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Plan {
    devices: Vec<Device>,
    release: Release,
    steps: Vec<Step>,
}

/// Preflight has no transition commands; health outcomes are supplied assumptions.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Fleet {
    devices: Vec<Device>,
    release: Release,
    cohort_size: usize,
}

/// Device labels are map keys only; fresh ordinal directories are generated independently.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Device {
    id: String,
    hardware: String,
    minimum_version: String,
    initial_version: String,
    initial_image_hex: String,
    outcome: TrialOutcome,
}

/// Packages use inert bytes and the deliberately public demo key, never an uploaded private key.
#[derive(Debug, Deserialize)]
#[serde(tag = "mode", rename_all = "snake_case", deny_unknown_fields)]
enum Release {
    Build {
        version: String,
        release_id: String,
        compatible_hardware: Vec<String>,
        max_boot_attempts: u8,
        image_hex: String,
    },
    Import {
        manifest: SignedManifest,
        image_hex: String,
    },
}

/// A selected fault is attempted only inside this step's original commit implementation.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Step {
    device: String,
    action: Action,
    fault: Option<FaultPoint>,
}

/// Actual transitions, not a second implementation of the A/B state machine.
#[derive(Debug, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
enum Action {
    Stage {},
    Activate { slot: SlotId, attempts: u8 },
    Boot {},
    Confirm {},
    Fail { reason: String },
}

/// Return a stable input error before executing any simulator filesystem operation.
fn invalid(message: &str) -> LabError {
    LabError::Validation(message.into())
}

/// Bound labels before they can enter reports, audit events or lookup maps.
fn label(value: &str) -> bool {
    !value.trim().is_empty() && value.len() <= 80 && !value.chars().any(char::is_control)
}

/// Decode inert binary contents with an explicit per-image bound before allocation.
fn image(value: &str) -> Result<Vec<u8>, LabError> {
    if value.is_empty() || value.len() > MAX_IMAGE * 2 || value.len() % 2 != 0 {
        return Err(invalid(
            "image must contain 1..65536 hexadecimal byte pairs",
        ));
    }
    hex::decode(value).map_err(|_| invalid("image contains invalid hexadecimal bytes"))
}

/// Validate every device identity/version/image before creating even the first temporary root.
fn validate_devices(devices: &[Device]) -> Result<(), LabError> {
    if !(1..=64).contains(&devices.len()) {
        return Err(invalid("a rehearsal needs 1..64 fictional devices"));
    }
    let mut ids = BTreeSet::new();
    for device in devices {
        if !label(&device.id) || !label(&device.hardware) || !ids.insert(&device.id) {
            return Err(invalid("device identifiers must be unique bounded labels"));
        }
        Version::from_str(&device.minimum_version)?;
        Version::from_str(&device.initial_version)?;
        image(&device.initial_image_hex)?;
    }
    Ok(())
}

/// Build or import the actual original signed manifest without blessing an imported signature.
fn package(input: &Release) -> Result<ReleasePackage, LabError> {
    match input {
        Release::Import {
            manifest,
            image_hex,
        } => Ok(ReleasePackage {
            manifest: manifest.clone(),
            image: image(image_hex)?,
        }),
        Release::Build {
            version,
            release_id,
            compatible_hardware,
            max_boot_attempts,
            image_hex,
        } => {
            if !label(release_id)
                || !(1..=64).contains(&compatible_hardware.len())
                || compatible_hardware.iter().any(|value| !label(value))
                || !(1..=10).contains(max_boot_attempts)
            {
                return Err(invalid(
                    "invalid release identity, hardware list or signed boot budget",
                ));
            }
            let image = image(image_hex)?;
            Ok(ReleasePackage {
                manifest: SignedManifest::create(
                    release_id.clone(),
                    Version::from_str(version)?,
                    compatible_hardware.clone(),
                    *max_boot_attempts,
                    &image,
                    &demo_signing_key(),
                )?,
                image,
            })
        }
    }
}

/// Use only fresh ordinal children; caller labels never become paths.
fn initialize(
    root: &std::path::Path,
    devices: &[Device],
) -> Result<BTreeMap<String, UpdateAgent>, LabError> {
    devices
        .iter()
        .enumerate()
        .map(|(index, device)| {
            let agent = UpdateAgent::new(
                LabStore::new(root.join(index.to_string())),
                DeviceProfile {
                    hardware_id: device.hardware.clone(),
                    minimum_version: Version::from_str(&device.minimum_version)?,
                },
                demo_signing_key().verifying_key(),
            );
            agent.initialize(
                Version::from_str(&device.initial_version)?,
                &image(&device.initial_image_hex)?,
                &mut NoFault,
            )?;
            Ok((device.id.clone(), agent))
        })
        .collect()
}

/// Snapshot actual recoverable state and independently verify its confirmed image bytes.
fn states(
    agents: &BTreeMap<String, UpdateAgent>,
    roots: &BTreeMap<String, std::path::PathBuf>,
) -> Result<Value, LabError> {
    let mut values = BTreeMap::new();
    for (id, agent) in agents {
        values.insert(id, snapshot(agent, &roots[id])?);
    }
    Ok(serde_json::to_value(values)?)
}

/// Check the one changed device per step; avoid rereading every unrelated image on every action.
fn snapshot(agent: &UpdateAgent, root: &std::path::Path) -> Result<BootMetadata, LabError> {
    let state = agent.status()?;
    state.validate_invariants()?;
    let confirmed_image = fs::read(
        root.join("slots")
            .join(state.confirmed.to_string())
            .join("image.bin"),
    )?;
    if sha256_hex(&confirmed_image) != state.slots[&state.confirmed].image_sha256 {
        return Err(invalid(
            "actual confirmed image differs from recovered metadata",
        ));
    }
    Ok(state)
}

/// Stop on the first rejection/interruption; later requested steps are explicitly unattempted.
fn lifecycle(plan: &Plan, input_sha256: &str) -> Result<Value, LabError> {
    validate_devices(&plan.devices)?;
    let package = package(&plan.release)?;
    if plan.steps.len() > 64 || plan.steps.iter().any(|step| {
        !plan.devices.iter().any(|device| device.id == step.device)
        || matches!(&step.action, Action::Fail { reason } if !label(reason))
        || matches!(step.action, Action::Activate { attempts, .. } if !(1..=10).contains(&attempts))
    }) {
        return Err(invalid("invalid step identity/action or more than64 steps"));
    }
    let directory = tempfile::tempdir()?;
    let agents = initialize(directory.path(), &plan.devices)?;
    let roots = plan
        .devices
        .iter()
        .enumerate()
        .map(|(index, device)| (device.id.clone(), directory.path().join(index.to_string())))
        .collect();
    let initial = states(&agents, &roots)?;
    let mut timeline = Vec::new();
    let mut outcome = "completed";
    for (index, step) in plan.steps.iter().enumerate() {
        let agent = &agents[&step.device];
        let before = snapshot(agent, &roots[&step.device])?;
        let mut injector: Box<dyn FaultInjector> = step.fault.map_or_else(
            || Box::new(NoFault) as Box<dyn FaultInjector>,
            |point| Box::new(SingleFault::new(point)) as Box<dyn FaultInjector>,
        );
        let result: Result<(BootMetadata, Option<SlotId>), LabError> = match &step.action {
            Action::Stage {} => agent
                .stage(&package, injector.as_mut())
                .map(|state| (state, None)),
            Action::Activate { slot, attempts } => agent
                .activate(*slot, *attempts, injector.as_mut())
                .map(|state| (state, None)),
            Action::Boot {} => agent
                .boot(injector.as_mut())
                .map(|(state, slot)| (state, Some(slot))),
            Action::Confirm {} => agent
                .confirm_health(injector.as_mut())
                .map(|state| (state, None)),
            Action::Fail { reason } => agent
                .fail_health(reason, injector.as_mut())
                .map(|state| (state, None)),
        };
        let after = snapshot(agent, &roots[&step.device])?;
        let (status, reason, selected) = match result {
            Ok((_, slot)) => ("applied", None, slot),
            Err(LabError::InjectedCrash(point)) => ("interrupted_recovered", Some(point), None),
            Err(LabError::Io(_)) => return Err(invalid("simulator filesystem operation failed")),
            Err(error) => ("rejected", Some(error.to_string()), None),
        };
        timeline.push(
            json!({"step": index + 1, "device": step.device, "status": status,
            "requested_fault":step.fault,"fault_triggered":status=="interrupted_recovered",
            "reason": reason, "selected_slot": selected, "before": before, "after": after}),
        );
        if status != "applied" {
            outcome = status;
            break;
        }
    }
    Ok(
        json!({"schemaVersion":1,"kind":"lifecycle","input_sha256":input_sha256,
        "package":{"manifest":package.manifest,"image_hex":hex::encode(&package.image)},
        "initial":initial,"timeline":timeline,"final":states(&agents,&roots)?,
        "outcome":outcome,"requested_steps":plan.steps.len(),"unattempted_steps":plan.steps.len()-timeline.len(),
        "notice":"OFFLINE REHEARSAL. Public demo signing key. Images are inert bytes, health is a supplied action, and faults model named metadata boundaries, not physical power loss or secure boot."}),
    )
}

/// Rehearse the actual read-only cohort engine and prove initialized states remain byte-equivalent.
fn preflight(fleet: &Fleet, input_sha256: &str) -> Result<Value, LabError> {
    validate_devices(&fleet.devices)?;
    if !(1..=16).contains(&fleet.cohort_size) {
        return Err(invalid("cohort_size must be1..16"));
    }
    let package = package(&fleet.release)?;
    let directory = tempfile::tempdir()?;
    let agents = initialize(directory.path(), &fleet.devices)?;
    let roots: BTreeMap<_, _> = fleet
        .devices
        .iter()
        .enumerate()
        .map(|(index, device)| (device.id.clone(), directory.path().join(index.to_string())))
        .collect();
    let before = states(&agents, &roots)?;
    let plan = FleetPlan {
        schema: 1,
        cohort_size: fleet.cohort_size,
        devices: fleet
            .devices
            .iter()
            .map(|device| {
                Ok(PlannedDevice {
                    id: device.id.clone(),
                    root: roots[&device.id].clone(),
                    profile: DeviceProfile {
                        hardware_id: device.hardware.clone(),
                        minimum_version: Version::from_str(&device.minimum_version)?,
                    },
                    outcome: device.outcome,
                })
            })
            .collect::<Result<_, LabError>>()?,
    };
    let report = crate::preflight::review(&plan, &package, &demo_signing_key().verifying_key())?;
    let after = states(&agents, &roots)?;
    if before != after {
        return Err(invalid(
            "read-only cohort rehearsal mutated initialized state",
        ));
    }
    Ok(
        json!({"schemaVersion":1,"kind":"preflight","input_sha256":input_sha256,
        "package":{"manifest":package.manifest,"image_hex":hex::encode(&package.image)},
        "report":report,"before":before,"after":after,"read_only":true,
        "notice":"Outcomes are supplied assumptions. report.plan_sha256 includes fresh physical simulator roots and is not a portable rerun hash; input_sha256 identifies the submitted JSON bytes."}),
    )
}

/// Execute a bounded request with the original engines; malformed input never creates a report.
pub fn execute(input: &str) -> Result<Value, LabError> {
    if input.len() > 262_144 {
        return Err(invalid("desktop request exceeds256KiB"));
    }
    let request: Request = serde_json::from_str(input)?;
    let input_sha256 = sha256_hex(input.as_bytes());
    match request {
        Request::Lifecycle { plan } => lifecycle(&plan, &input_sha256),
        Request::Preflight { fleet } => preflight(&fleet, &input_sha256),
        Request::Campaign { iterations } => {
            if !(1..=5).contains(&iterations) {
                return Err(invalid(
                    "desktop interruption campaign supports1..5 iterations",
                ));
            }
            Ok(
                json!({"schemaVersion":1,"kind":"campaign","input_sha256":input_sha256,
                "report":run_fault_campaign(iterations)?,
                "notice":"Original metadata-boundary simulation, not a physical power-loss or hardware reliability measurement. elapsed_milliseconds is measured wall time, not a deterministic replay field."}),
            )
        }
    }
}
