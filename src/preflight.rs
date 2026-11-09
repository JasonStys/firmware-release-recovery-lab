//! Read-only fleet release preflight and deterministic cohort rehearsal by Jason Stys.
//!
//! File map: `FleetPlan` validates bounded explicit device roots; `review` verifies
//! one package against every recorded device and rehearses pure transitions only.
//! Public fields document inputs/results; exact declarations: docs/code-index.md.

use std::{collections::BTreeSet, fs::File, io::Read, path::PathBuf};

use ed25519_dalek::VerifyingKey;
use serde::{Deserialize, Serialize};

use crate::{
    crypto::sha256_hex,
    model::{DeviceProfile, LabError, LifecyclePhase},
    package::ReleasePackage,
    store::LabStore,
    transition,
};

/// A caller-declared synthetic health outcome, never a measured device signal.
#[derive(Debug, Clone, Copy, Deserialize, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum TrialOutcome {
    /// Confirm after the first selected trial boot.
    Confirm,
    /// Exhaust the signed boot budget without a health confirmation.
    Exhaust,
}

/// One explicitly selected local simulated device and hypothetical outcome.
#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct PlannedDevice {
    /// Unique printable identifier; no directory is inferred from this value.
    pub id: String,
    /// Operator-supplied existing simulator root, relative to the process directory.
    pub root: PathBuf,
    /// Explicit local compatibility and minimum-version policy.
    pub profile: DeviceProfile,
    /// Synthetic health outcome used only during pure rehearsal.
    pub outcome: TrialOutcome,
}

/// Closed, bounded rehearsal input. No source or device state is changed.
#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct FleetPlan {
    /// Only schema 1 is supported.
    pub schema: u8,
    /// Number of devices attempted before checking the cohort stop condition.
    pub cohort_size: usize,
    /// Explicitly ordered devices, at most 64 unique IDs and resolved roots.
    pub devices: Vec<PlannedDevice>,
}

impl FleetPlan {
    /// Read at most 32 KiB from an ordinary file, rejecting unknown/duplicate plan/device keys.
    pub fn load(path: &std::path::Path) -> Result<Self, LabError> {
        if !path.is_file() {
            return Err(LabError::Validation("ordinary fleet plan required".into()));
        }
        let mut bytes = Vec::new();
        File::open(path)?.take(32_769).read_to_end(&mut bytes)?;
        if bytes.len() > 32_768 {
            return Err(LabError::Validation("fleet plan exceeds 32 KiB".into()));
        }
        Ok(serde_json::from_slice(&bytes)?)
    }

    /// Validate all IDs/roots before examining state or producing a partial report.
    fn validate(&self) -> Result<(), LabError> {
        if self.schema != 1
            || !(1..=16).contains(&self.cohort_size)
            || !(1..=64).contains(&self.devices.len())
        {
            return Err(LabError::Validation("invalid fleet bounds/schema".into()));
        }
        let mut ids = BTreeSet::new();
        let mut roots = BTreeSet::new();
        for device in &self.devices {
            if device.id.is_empty()
                || device.id.len() > 80
                || device.id.chars().any(char::is_control)
                || !ids.insert(&device.id)
                || !roots.insert(device.root.canonicalize()?)
            {
                return Err(LabError::Validation(
                    "invalid or duplicate fleet identity/root".into(),
                ));
            }
        }
        Ok(())
    }
}

/// Per-device eligibility and explicitly hypothetical rollout result.
#[derive(Debug, Serialize)]
pub struct DeviceReview {
    /// Caller-assigned device ID; local paths are intentionally omitted.
    pub id: String,
    /// Explicit local policy used for this review.
    pub profile: DeviceProfile,
    /// Caller-declared hypothetical health outcome.
    pub assumed_outcome: TrialOutcome,
    /// Exact canonical metadata snapshot hash, absent when no valid state exists.
    pub state_sha256: Option<String>,
    /// Whether signature/image, local policy and staging transition passed.
    pub eligible: bool,
    /// Stable reviewer-facing failure category, without raw local I/O details.
    pub reason: &'static str,
    /// One-based cohort index in the explicit plan order.
    pub cohort: usize,
    /// `confirmed`, `rolled_back`, `blocked`, or `not_attempted_after_stop`.
    pub rehearsal: &'static str,
}

/// Immutable read-only report: never a rollout authorization or actual health evidence.
#[derive(Debug, Serialize)]
pub struct FleetReview {
    /// Canonical full plan hash, binding order, roots, policies and assumptions.
    pub plan_sha256: String,
    /// Exact canonical signed-manifest hash; includes the image digest and signature.
    pub manifest_sha256: String,
    /// Every requested device appears exactly once, even after a cohort stop.
    pub devices: Vec<DeviceReview>,
    /// First unsuccessful cohort, after which no later cohort is rehearsed.
    pub stopped_after_cohort: Option<usize>,
    /// Explicit simulation and concurrency boundary.
    pub notice: &'static str,
}

/// Verify recorded compatibility for all devices, then rehearse bounded pure trial transitions.
pub fn review(
    plan: &FleetPlan,
    package: &ReleasePackage,
    key: &VerifyingKey,
) -> Result<FleetReview, LabError> {
    plan.validate()?;
    let mut rows = Vec::new();
    let mut stopped = None;
    for (index, device) in plan.devices.iter().enumerate() {
        let cohort = index / plan.cohort_size + 1;
        let state = LabStore::new(&device.root).load_state();
        let state_hash = state
            .as_ref()
            .ok()
            .map(serde_json::to_vec)
            .transpose()?
            .map(|bytes| sha256_hex(&bytes));
        let result = state
            .map_err(|_| "unrecoverable_state")
            .and_then(|current| {
                let confirmed = current
                    .confirmed_version()
                    .map_err(|_| "invalid_confirmed_state")?;
                package
                    .verify(key, &device.profile, confirmed)
                    .map_err(|error| match error {
                        LabError::Signature => "signature_rejected",
                        LabError::DigestMismatch { .. } => "image_digest_rejected",
                        _ => "package_or_compatibility_policy_rejected",
                    })?;
                transition::stage(&current, &package.manifest.payload)
                    .map_err(|_| "staging_transition_rejected")
            });
        let eligible = result.is_ok();
        let reason = result.as_ref().err().copied().unwrap_or("compatible");
        let rehearsal = if stopped.is_some_and(|previous| cohort > previous) {
            "not_attempted_after_stop"
        } else if let Ok(staged) = result {
            let attempts = package.manifest.payload.max_boot_attempts;
            let mut trial = transition::activate(&staged, staged.confirmed.other(), attempts)?;
            match device.outcome {
                TrialOutcome::Confirm => {
                    trial = transition::select_boot(&trial)?.0;
                    trial = transition::confirm_health(&trial)?;
                }
                TrialOutcome::Exhaust => {
                    // One extra selection observes automatic rollback after the last unconfirmed boot.
                    for _ in 0..=attempts {
                        trial = transition::select_boot(&trial)?.0;
                    }
                }
            }
            if trial.phase == LifecyclePhase::Stable {
                "confirmed"
            } else {
                "rolled_back"
            }
        } else {
            "blocked"
        };
        if rehearsal == "blocked" || rehearsal == "rolled_back" {
            stopped.get_or_insert(cohort);
        }
        rows.push(DeviceReview {
            id: device.id.clone(),
            profile: device.profile.clone(),
            assumed_outcome: device.outcome,
            state_sha256: state_hash,
            eligible,
            reason,
            cohort,
            rehearsal,
        });
    }
    Ok(FleetReview {
        plan_sha256: sha256_hex(&serde_json::to_vec(plan)?),
        manifest_sha256: sha256_hex(&serde_json::to_vec(&package.manifest)?),
        devices: rows,
        stopped_after_cohort: stopped,
        notice: "READ-ONLY DIRECTORY SIMULATION. Outcomes are supplied assumptions, not measured health. Every device gets compatibility review; later cohorts stop after a blocked/rolled-back cohort. No image, metadata or audit file is written. Concurrent external changes are not locked; rerun before staging. Demo signing key is public; no hardware/secure-boot/production rollout claim.",
    })
}
