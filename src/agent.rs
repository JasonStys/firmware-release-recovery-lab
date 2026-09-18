//! Update orchestration and exhaustive interruption campaign support.
//!
//! File map: `UpdateAgent` composes package verification, slot persistence, and pure
//! transitions; `run_fault_campaign` restarts after every injected commit boundary.

use std::time::Instant;

use ed25519_dalek::VerifyingKey;
use serde::{Deserialize, Serialize};

use crate::{
    fault::{FaultInjector, FaultPoint, NoFault, SingleFault},
    model::{BootMetadata, DeviceProfile, LabError, LifecyclePhase, SlotId, Version},
    package::{ReleasePackage, SignedManifest},
    store::LabStore,
    transition,
};

/// High-level update service that keeps I/O separate from transition decisions.
#[derive(Debug, Clone)]
pub struct UpdateAgent {
    store: LabStore,
    device: DeviceProfile,
    verifying_key: VerifyingKey,
}

impl UpdateAgent {
    /// Creates an update agent for one simulated device and trusted demo public key.
    #[must_use]
    pub const fn new(store: LabStore, device: DeviceProfile, verifying_key: VerifyingKey) -> Self {
        Self {
            store,
            device,
            verifying_key,
        }
    }

    /// Creates a fresh slot-A installation with a verified initial image.
    pub fn initialize(
        &self,
        version: Version,
        image: &[u8],
        injector: &mut dyn FaultInjector,
    ) -> Result<BootMetadata, LabError> {
        let state = BootMetadata::initial(version, crate::crypto::sha256_hex(image));
        self.store.initialize(&state, image, injector)?;
        Ok(state)
    }

    /// Verifies and stages a package in the inactive slot, then commits its metadata.
    pub fn stage(
        &self,
        package: &ReleasePackage,
        injector: &mut dyn FaultInjector,
    ) -> Result<BootMetadata, LabError> {
        let current = self.store.load_state()?;
        package.verify(
            &self.verifying_key,
            &self.device,
            current.confirmed_version()?,
        )?;
        let target = current.confirmed.other();
        self.store.write_slot(target, package)?;
        let next = transition::stage(&current, &package.manifest.payload)?;
        self.store.commit_state(&next, injector)?;
        Ok(next)
    }

    /// Activates a verified inactive slot with a bounded boot-attempt budget.
    pub fn activate(
        &self,
        target: SlotId,
        attempts: u8,
        injector: &mut dyn FaultInjector,
    ) -> Result<BootMetadata, LabError> {
        let current = self.store.load_state()?;
        let next = transition::activate(&current, target, attempts)?;
        self.store.commit_state(&next, injector)?;
        Ok(next)
    }

    /// Selects and persists the next boot decision before returning it.
    pub fn boot(
        &self,
        injector: &mut dyn FaultInjector,
    ) -> Result<(BootMetadata, SlotId), LabError> {
        let current = self.store.load_state()?;
        let (next, selected) = transition::select_boot(&current)?;
        if next != current {
            self.store.commit_state(&next, injector)?;
        }
        Ok((next, selected))
    }

    /// Promotes the pending image after an explicit health signal.
    pub fn confirm_health(
        &self,
        injector: &mut dyn FaultInjector,
    ) -> Result<BootMetadata, LabError> {
        let current = self.store.load_state()?;
        let next = transition::confirm_health(&current)?;
        self.store.commit_state(&next, injector)?;
        Ok(next)
    }

    /// Records a failed health signal and persists rollback when attempts are exhausted.
    pub fn fail_health(
        &self,
        reason: &str,
        injector: &mut dyn FaultInjector,
    ) -> Result<BootMetadata, LabError> {
        let current = self.store.load_state()?;
        let next = transition::record_boot_failure(&current, reason)?;
        self.store.commit_state(&next, injector)?;
        Ok(next)
    }

    /// Loads the newest valid primary or recovery copy for audit output.
    pub fn status(&self) -> Result<BootMetadata, LabError> {
        self.store.load_state()
    }
}

/// Machine-readable evidence produced by a deterministic interruption campaign.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CampaignReport {
    /// Report format version.
    pub schema_version: u16,
    /// Number of full boundary sets requested.
    pub iterations: u32,
    /// Stage and activation interruptions attempted.
    pub scenarios: u64,
    /// Scenarios that restarted into valid state.
    pub recovered: u64,
    /// Scenarios retaining a verified confirmed image.
    pub safety_invariants_preserved: u64,
    /// Scenarios recovering the original stable state.
    pub stable_recoveries: u64,
    /// Scenarios recovering a staged or awaiting-health state.
    pub forward_progress_recoveries: u64,
    /// Measured campaign wall time for performance evidence.
    pub elapsed_milliseconds: u128,
}

/// Interrupts stage and activation commits at every named boundary, then restarts.
pub fn run_fault_campaign(iterations: u32) -> Result<CampaignReport, LabError> {
    if iterations == 0 || iterations > 10_000 {
        return Err(LabError::Validation(
            "iterations must be between 1 and 10000".into(),
        ));
    }
    let started = Instant::now();
    let key = crate::crypto::demo_signing_key();
    let device = DeviceProfile {
        hardware_id: "edge-controller-v1".into(),
        minimum_version: Version::new(1, 0, 0),
    };
    let image = b"synthetic-release-v2";
    let package = ReleasePackage {
        manifest: SignedManifest::create(
            "release-2.0.0".into(),
            Version::new(2, 0, 0),
            vec![device.hardware_id.clone()],
            3,
            image,
            &key,
        )?,
        image: image.to_vec(),
    };

    let mut report = CampaignReport {
        schema_version: 1,
        iterations,
        scenarios: 0,
        recovered: 0,
        safety_invariants_preserved: 0,
        stable_recoveries: 0,
        forward_progress_recoveries: 0,
        elapsed_milliseconds: 0,
    };

    for _ in 0..iterations {
        for point in FaultPoint::all() {
            run_interrupted_stage(point, &device, &key.verifying_key(), &package, &mut report)?;
            run_interrupted_activation(
                point,
                &device,
                &key.verifying_key(),
                &package,
                &mut report,
            )?;
        }
    }
    report.elapsed_milliseconds = started.elapsed().as_millis();
    Ok(report)
}

/// Executes one interrupted stage and classifies the recovered state.
fn run_interrupted_stage(
    point: FaultPoint,
    device: &DeviceProfile,
    verifying_key: &VerifyingKey,
    package: &ReleasePackage,
    report: &mut CampaignReport,
) -> Result<(), LabError> {
    let directory = tempfile::tempdir()?;
    let agent = UpdateAgent::new(
        LabStore::new(directory.path()),
        device.clone(),
        *verifying_key,
    );
    agent.initialize(Version::new(1, 0, 0), b"known-good-v1", &mut NoFault)?;
    let result = agent.stage(package, &mut SingleFault::new(point));
    if !matches!(result, Err(LabError::InjectedCrash(_))) {
        return Err(LabError::Validation(format!(
            "fault {point} did not interrupt stage"
        )));
    }
    classify_recovery(&agent.status()?, report)
}

/// Executes one interrupted activation and classifies the recovered state.
fn run_interrupted_activation(
    point: FaultPoint,
    device: &DeviceProfile,
    verifying_key: &VerifyingKey,
    package: &ReleasePackage,
    report: &mut CampaignReport,
) -> Result<(), LabError> {
    let directory = tempfile::tempdir()?;
    let agent = UpdateAgent::new(
        LabStore::new(directory.path()),
        device.clone(),
        *verifying_key,
    );
    agent.initialize(Version::new(1, 0, 0), b"known-good-v1", &mut NoFault)?;
    agent.stage(package, &mut NoFault)?;
    let result = agent.activate(SlotId::B, 3, &mut SingleFault::new(point));
    if !matches!(result, Err(LabError::InjectedCrash(_))) {
        return Err(LabError::Validation(format!(
            "fault {point} did not interrupt activation"
        )));
    }
    classify_recovery(&agent.status()?, report)
}

/// Updates campaign counters after validating the last-known-good invariant.
fn classify_recovery(
    recovered: &BootMetadata,
    report: &mut CampaignReport,
) -> Result<(), LabError> {
    recovered.validate_invariants()?;
    report.scenarios += 1;
    report.recovered += 1;
    report.safety_invariants_preserved += 1;
    match recovered.phase {
        LifecyclePhase::Stable | LifecyclePhase::RolledBack => report.stable_recoveries += 1,
        LifecyclePhase::Staged | LifecyclePhase::AwaitingHealth => {
            report.forward_progress_recoveries += 1;
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn campaign_recovers_every_injected_boundary() {
        let report = run_fault_campaign(2).expect("campaign");
        assert_eq!(report.scenarios, 24);
        assert_eq!(report.recovered, report.scenarios);
        assert_eq!(report.safety_invariants_preserved, report.scenarios);
        assert_eq!(
            report.stable_recoveries + report.forward_progress_recoveries,
            report.scenarios
        );
    }
}
