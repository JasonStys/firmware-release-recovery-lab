//! Integration and property tests for public lifecycle behavior.
//!
//! File map: generators produce bounded versions/attempts; properties prove that
//! confirmation and exhaustion preserve the verified last-known-good invariant.

use firmware_recovery::{
    BootMetadata, LifecyclePhase, SlotId, Version,
    crypto::sha256_hex,
    package::ManifestPayload,
    transition::{activate, confirm_health, record_boot_failure, select_boot, stage},
};
use proptest::prelude::*;

/// Builds a valid initial state for public-API integration tests.
fn initial(version: Version) -> BootMetadata {
    BootMetadata::initial(version, sha256_hex(b"known-good"))
}

/// Builds a verified candidate manifest above the supplied confirmed version.
fn candidate(version: Version, attempts: u8) -> ManifestPayload {
    ManifestPayload {
        schema_version: 1,
        release_id: format!("release-{version}"),
        version,
        compatible_hardware: vec!["edge-controller-v1".into()],
        image_size: 9,
        image_sha256: sha256_hex(b"candidate"),
        max_boot_attempts: attempts,
    }
}

proptest! {
    #[test]
    fn successful_health_confirmation_promotes_exact_candidate(
        major in 1_u16..100,
        minor in 0_u16..100,
        patch in 0_u16..100,
        attempts in 1_u8..=10,
    ) {
        let old = Version::new(major, minor, patch);
        let new = Version::new(major + 1, minor, patch);
        let staged = stage(&initial(old), &candidate(new, attempts))?;
        let active = activate(&staged, SlotId::B, attempts)?;
        let (booted, selected) = select_boot(&active)?;
        prop_assert_eq!(selected, SlotId::B);
        let confirmed = confirm_health(&booted)?;
        prop_assert_eq!(confirmed.confirmed, SlotId::B);
        prop_assert_eq!(confirmed.confirmed_version()?, new);
        prop_assert_eq!(confirmed.phase, LifecyclePhase::Stable);
        confirmed.validate_invariants()?;
    }

    #[test]
    fn exhausted_candidate_always_returns_to_known_good(
        major in 1_u16..100,
        attempts in 1_u8..=10,
    ) {
        let old = Version::new(major, 0, 0);
        let new = Version::new(major + 1, 0, 0);
        let staged = stage(&initial(old), &candidate(new, attempts))?;
        let mut state = activate(&staged, SlotId::B, attempts)?;
        for _ in 0..attempts {
            (state, _) = select_boot(&state)?;
            state = record_boot_failure(&state, "property test failure")?;
            if state.phase == LifecyclePhase::RolledBack {
                break;
            }
        }
        prop_assert_eq!(state.active, SlotId::A);
        prop_assert_eq!(state.confirmed, SlotId::A);
        prop_assert_eq!(state.confirmed_version()?, old);
        state.validate_invariants()?;
    }
}
