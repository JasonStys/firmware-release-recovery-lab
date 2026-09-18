//! End-to-end persistence test for package verification, activation, and rollback.
//!
//! File map: the single test exercises the public agent API across filesystem-backed
//! restart boundaries and verifies the JSON-serializable audit state.

use firmware_recovery::{
    DeviceProfile, LifecyclePhase, NoFault, ReleasePackage, SignedManifest, SlotId, UpdateAgent,
    Version, crypto::demo_signing_key, store::LabStore,
};

#[test]
fn failed_candidate_rolls_back_across_persisted_restarts() {
    let directory = tempfile::tempdir().expect("temporary lab");
    let key = demo_signing_key();
    let profile = DeviceProfile {
        hardware_id: "edge-controller-v1".into(),
        minimum_version: Version::new(1, 0, 0),
    };
    let make_agent = || {
        UpdateAgent::new(
            LabStore::new(directory.path()),
            profile.clone(),
            key.verifying_key(),
        )
    };

    make_agent()
        .initialize(Version::new(1, 0, 0), b"known-good", &mut NoFault)
        .expect("initialize");
    let image = b"candidate-v2".to_vec();
    let package = ReleasePackage {
        manifest: SignedManifest::create(
            "release-2.0.0".into(),
            Version::new(2, 0, 0),
            vec![profile.hardware_id.clone()],
            1,
            &image,
            &key,
        )
        .expect("manifest"),
        image,
    };
    make_agent().stage(&package, &mut NoFault).expect("stage");
    make_agent()
        .activate(SlotId::B, 1, &mut NoFault)
        .expect("activate");
    let (_, selected) = make_agent().boot(&mut NoFault).expect("boot");
    assert_eq!(selected, SlotId::B);

    let rolled_back = make_agent()
        .fail_health("watchdog timeout", &mut NoFault)
        .expect("rollback");
    assert_eq!(rolled_back.phase, LifecyclePhase::RolledBack);
    assert_eq!(rolled_back.active, SlotId::A);
    assert!(
        rolled_back
            .audit
            .last()
            .expect("audit event")
            .detail
            .contains("watchdog timeout")
    );
}
