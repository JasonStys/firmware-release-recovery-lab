//! Pure transition functions for the A/B release lifecycle.
//!
//! File map: `stage`, `activate`, `select_boot`, `confirm_health`, and
//! `record_boot_failure` are deterministic and perform no I/O.

use crate::{
    model::{AuditEvent, BootMetadata, LabError, LifecyclePhase, SlotId, SlotRecord},
    package::ManifestPayload,
};

const AUDIT_LIMIT: usize = 128;

/// Appends a bounded deterministic audit event and advances the generation.
fn commit_event(state: &mut BootMetadata, action: &str, detail: String) {
    state.generation = state.generation.saturating_add(1);
    state.audit.push(AuditEvent {
        sequence: state.generation,
        action: action.into(),
        detail,
    });
    if state.audit.len() > AUDIT_LIMIT {
        let excess = state.audit.len() - AUDIT_LIMIT;
        state.audit.drain(0..excess);
    }
}

/// Records a fully verified package in the inactive slot.
pub fn stage(current: &BootMetadata, manifest: &ManifestPayload) -> Result<BootMetadata, LabError> {
    current.validate_invariants()?;
    if current.pending.is_some() {
        return Err(LabError::Validation(
            "cannot stage while a candidate is awaiting health confirmation".into(),
        ));
    }

    let target = current.confirmed.other();
    let mut next = current.clone();
    next.slots.insert(
        target,
        SlotRecord {
            version: manifest.version,
            image_sha256: manifest.image_sha256.clone(),
            verified: true,
        },
    );
    next.phase = LifecyclePhase::Staged;
    commit_event(
        &mut next,
        "stage",
        format!("verified release {} in slot {target}", manifest.version),
    );
    next.validate_invariants()?;
    Ok(next)
}

/// Selects the staged inactive image for a bounded number of boot attempts.
pub fn activate(
    current: &BootMetadata,
    target: SlotId,
    max_boot_attempts: u8,
) -> Result<BootMetadata, LabError> {
    current.validate_invariants()?;
    if target == current.confirmed {
        return Err(LabError::Validation(
            "activation target must be the inactive slot".into(),
        ));
    }
    let record = current
        .slots
        .get(&target)
        .ok_or_else(|| LabError::Validation("activation target is empty".into()))?;
    if !record.verified {
        return Err(LabError::Validation(
            "activation target has not been verified".into(),
        ));
    }
    if !(1..=10).contains(&max_boot_attempts) {
        return Err(LabError::Validation(
            "activation attempts must be between 1 and 10".into(),
        ));
    }

    let mut next = current.clone();
    next.active = target;
    next.pending = Some(target);
    next.attempts_remaining = max_boot_attempts;
    next.phase = LifecyclePhase::AwaitingHealth;
    commit_event(
        &mut next,
        "activate",
        format!("slot {target} selected with {max_boot_attempts} attempts"),
    );
    next.validate_invariants()?;
    Ok(next)
}

/// Accounts for one pending-image boot and returns the slot to execute.
pub fn select_boot(current: &BootMetadata) -> Result<(BootMetadata, SlotId), LabError> {
    current.validate_invariants()?;
    let Some(candidate) = current.pending else {
        return Ok((current.clone(), current.active));
    };

    if current.attempts_remaining == 0 {
        let rolled_back = rollback(current, "attempt budget exhausted before boot")?;
        return Ok((rolled_back.clone(), rolled_back.active));
    }

    let mut next = current.clone();
    next.attempts_remaining -= 1;
    let attempts_remaining = next.attempts_remaining;
    commit_event(
        &mut next,
        "boot_select",
        format!("slot {candidate} selected; {attempts_remaining} attempts remain"),
    );
    next.validate_invariants()?;
    Ok((next, candidate))
}

/// Confirms the pending image as the new known-good image.
pub fn confirm_health(current: &BootMetadata) -> Result<BootMetadata, LabError> {
    current.validate_invariants()?;
    let candidate = current
        .pending
        .ok_or_else(|| LabError::Validation("no pending image to confirm".into()))?;
    let mut next = current.clone();
    next.confirmed = candidate;
    next.active = candidate;
    next.pending = None;
    next.attempts_remaining = 0;
    next.phase = LifecyclePhase::Stable;
    commit_event(
        &mut next,
        "confirm_health",
        format!("slot {candidate} is now the confirmed image"),
    );
    next.validate_invariants()?;
    Ok(next)
}

/// Records a failed health check and rolls back when the attempt budget reaches zero.
pub fn record_boot_failure(current: &BootMetadata, reason: &str) -> Result<BootMetadata, LabError> {
    current.validate_invariants()?;
    let candidate = current
        .pending
        .ok_or_else(|| LabError::Validation("no pending image can fail health".into()))?;
    if current.attempts_remaining == 0 {
        return rollback(current, reason);
    }

    let mut next = current.clone();
    let attempts_remaining = next.attempts_remaining;
    commit_event(
        &mut next,
        "health_failure",
        format!("slot {candidate} failed health: {reason}; {attempts_remaining} attempts remain"),
    );
    next.validate_invariants()?;
    Ok(next)
}

/// Restores the previously confirmed slot while retaining candidate evidence for audit.
fn rollback(current: &BootMetadata, reason: &str) -> Result<BootMetadata, LabError> {
    let failed = current
        .pending
        .ok_or_else(|| LabError::Validation("rollback requires an unconfirmed candidate".into()))?;
    let mut next = current.clone();
    next.active = current.confirmed;
    next.pending = None;
    next.attempts_remaining = 0;
    next.phase = LifecyclePhase::RolledBack;
    commit_event(
        &mut next,
        "rollback",
        format!(
            "slot {failed} rejected ({reason}); restored slot {}",
            current.confirmed
        ),
    );
    next.validate_invariants()?;
    Ok(next)
}

#[cfg(test)]
mod tests {
    use crate::{crypto::sha256_hex, model::Version, package::ManifestPayload};

    use super::*;

    fn initial() -> BootMetadata {
        BootMetadata::initial(Version::new(1, 0, 0), sha256_hex(b"v1"))
    }

    fn candidate() -> ManifestPayload {
        ManifestPayload {
            schema_version: 1,
            release_id: "v2".into(),
            version: Version::new(2, 0, 0),
            compatible_hardware: vec!["edge-controller-v1".into()],
            image_size: 2,
            image_sha256: sha256_hex(b"v2"),
            max_boot_attempts: 2,
        }
    }

    #[test]
    fn happy_path_promotes_only_after_health_confirmation() {
        let staged = stage(&initial(), &candidate()).expect("stage");
        let activated = activate(&staged, SlotId::B, 2).expect("activate");
        assert_eq!(activated.confirmed, SlotId::A);
        let (booted, selected) = select_boot(&activated).expect("select");
        assert_eq!(selected, SlotId::B);
        let confirmed = confirm_health(&booted).expect("confirm");
        assert_eq!(confirmed.confirmed, SlotId::B);
        assert_eq!(confirmed.phase, LifecyclePhase::Stable);
    }

    #[test]
    fn exhausted_attempt_budget_rolls_back_deterministically() {
        let staged = stage(&initial(), &candidate()).expect("stage");
        let activated = activate(&staged, SlotId::B, 1).expect("activate");
        let (booted, _) = select_boot(&activated).expect("first boot");
        let rolled_back = record_boot_failure(&booted, "watchdog").expect("rollback");
        assert_eq!(rolled_back.active, SlotId::A);
        assert_eq!(rolled_back.phase, LifecyclePhase::RolledBack);
        assert!(rolled_back.pending.is_none());
    }
}
