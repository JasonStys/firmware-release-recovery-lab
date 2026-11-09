//! Jason Stys: real-directory read-only rollout and rejected-stage preservation oracles.
//!
//! File map: helpers create synthetic fixtures; tests assert cohort semantics,
//! exact byte preservation, bounds, cryptographic rejection and the actual CLI.
//! All roots and packages are temporary; declarations: docs/code-index.md.

use std::{collections::BTreeMap, fs, path::Path, process::Command};

use firmware_recovery::{
    DeviceProfile, NoFault, ReleasePackage, SignedManifest, SlotId, UpdateAgent, Version,
    crypto::demo_signing_key,
    preflight::{FleetPlan, review},
    store::LabStore,
};
use serde_json::{Value, json};

fn profile() -> DeviceProfile {
    DeviceProfile {
        hardware_id: "edge-controller-v1".into(),
        minimum_version: Version::new(1, 0, 0),
    }
}

fn package(image: &[u8]) -> ReleasePackage {
    ReleasePackage {
        manifest: SignedManifest::create(
            "release-2".into(),
            Version::new(2, 0, 0),
            vec![profile().hardware_id],
            2,
            image,
            &demo_signing_key(),
        )
        .unwrap(),
        image: image.to_vec(),
    }
}

fn agent(root: &Path) -> UpdateAgent {
    UpdateAgent::new(
        LabStore::new(root),
        profile(),
        demo_signing_key().verifying_key(),
    )
}

fn setup(root: &Path, count: usize, cohort_size: usize) -> Value {
    let devices: Vec<_> = (0..count).map(|index| {
        let directory = root.join(format!("device-{index}"));
        agent(&directory).initialize(Version::new(1, 0, 0), b"known-good", &mut NoFault).unwrap();
        json!({"id":format!("device-{index}"), "root":directory, "profile":profile(), "outcome":"confirm"})
    }).collect();
    json!({"schema":1,"cohort_size":cohort_size,"devices":devices})
}

fn bytes(root: &Path) -> BTreeMap<std::path::PathBuf, Vec<u8>> {
    let mut result = BTreeMap::new();
    for entry in fs::read_dir(root).unwrap() {
        let path = entry.unwrap().path();
        if path.is_dir() {
            result.extend(bytes(&path));
        } else {
            result.insert(path.clone(), fs::read(path).unwrap());
        }
    }
    result
}

#[test]
fn cohorts_stop_after_failure_but_preserve_all_compatibility_rows_and_bytes() {
    let root = tempfile::tempdir().unwrap();
    let mut value = setup(root.path(), 4, 2);
    value["devices"][0]["outcome"] = json!("exhaust");
    let plan: FleetPlan = serde_json::from_value(value).unwrap();
    let before = bytes(root.path());
    let report = review(
        &plan,
        &package(b"new-v2"),
        &demo_signing_key().verifying_key(),
    )
    .unwrap();
    assert_eq!(report.stopped_after_cohort, Some(1));
    assert_eq!(
        report
            .devices
            .iter()
            .map(|row| row.rehearsal)
            .collect::<Vec<_>>(),
        [
            "rolled_back",
            "confirmed",
            "not_attempted_after_stop",
            "not_attempted_after_stop"
        ]
    );
    assert!(
        report
            .devices
            .iter()
            .all(|row| row.eligible && row.state_sha256.as_ref().unwrap().len() == 64)
    );
    assert_eq!(bytes(root.path()), before);
    assert_eq!(
        serde_json::to_value(&report).unwrap(),
        serde_json::to_value(
            review(
                &plan,
                &package(b"new-v2"),
                &demo_signing_key().verifying_key()
            )
            .unwrap()
        )
        .unwrap()
    );
}

#[test]
fn compatible_fleet_completes_and_wrong_hardware_or_floor_is_not_ready() {
    let root = tempfile::tempdir().unwrap();
    let mut value = setup(root.path(), 3, 1);
    let plan: FleetPlan = serde_json::from_value(value.clone()).unwrap();
    assert!(
        review(&plan, &package(b"v2"), &demo_signing_key().verifying_key())
            .unwrap()
            .devices
            .iter()
            .all(|row| row.rehearsal == "confirmed")
    );
    value["devices"][0]["profile"]["hardware_id"] = json!("wrong-board");
    value["devices"][1]["profile"]["minimum_version"]["major"] = json!(3);
    let plan = serde_json::from_value(value).unwrap();
    let report = review(&plan, &package(b"v2"), &demo_signing_key().verifying_key()).unwrap();
    assert!(!report.devices[0].eligible && !report.devices[1].eligible);
    assert_eq!(report.devices[0].rehearsal, "blocked");
    assert_eq!(report.devices[1].rehearsal, "not_attempted_after_stop");
    assert!(report.devices[2].eligible);
}

#[test]
fn active_trial_rejected_before_any_slot_or_metadata_write() {
    let root = tempfile::tempdir().unwrap();
    let value = setup(root.path(), 1, 1);
    let device = root.path().join("device-0");
    let updater = agent(&device);
    updater
        .stage(&package(b"candidate-original"), &mut NoFault)
        .unwrap();
    updater.activate(SlotId::B, 2, &mut NoFault).unwrap();
    let before = bytes(root.path());
    assert!(
        updater
            .stage(&package(b"candidate-replacement"), &mut NoFault)
            .is_err()
    );
    let plan = serde_json::from_value(value).unwrap();
    assert!(
        !review(
            &plan,
            &package(b"candidate-replacement"),
            &demo_signing_key().verifying_key()
        )
        .unwrap()
        .devices[0]
            .eligible
    );
    assert_eq!(bytes(root.path()), before);
}

#[test]
fn corrupt_package_or_state_never_becomes_eligible() {
    let root = tempfile::tempdir().unwrap();
    let plan: FleetPlan = serde_json::from_value(setup(root.path(), 1, 1)).unwrap();
    let mut candidate = package(b"v2");
    candidate.image[0] ^= 1;
    assert!(
        !review(&plan, &candidate, &demo_signing_key().verifying_key())
            .unwrap()
            .devices[0]
            .eligible
    );
    candidate = package(b"v2");
    candidate.manifest.signature_ed25519 = "00".repeat(64);
    assert!(
        !review(&plan, &candidate, &demo_signing_key().verifying_key())
            .unwrap()
            .devices[0]
            .eligible
    );
    fs::write(root.path().join("device-0/state.json"), b"{}").unwrap();
    let report = review(&plan, &package(b"v2"), &demo_signing_key().verifying_key()).unwrap();
    assert!(!report.devices[0].eligible);
    assert!(report.devices[0].state_sha256.is_none());
}

#[test]
fn duplicate_ids_resolved_roots_and_closed_bounds_rejected() {
    let root = tempfile::tempdir().unwrap();
    let value = setup(root.path(), 2, 1);
    for changed in [
        {
            let mut v = value.clone();
            v["devices"][1]["id"] = v["devices"][0]["id"].clone();
            v
        },
        {
            let mut v = value.clone();
            v["devices"][1]["root"] = v["devices"][0]["root"].clone();
            v
        },
        {
            let mut v = value.clone();
            v["cohort_size"] = json!(0);
            v
        },
        {
            let mut v = value.clone();
            v["cohort_size"] = json!(17);
            v
        },
        {
            let mut v = value.clone();
            v["schema"] = json!(2);
            v
        },
        {
            let mut v = value.clone();
            v["devices"] = json!([]);
            v
        },
        {
            let mut v = value.clone();
            v["devices"][0]["id"] = json!("bad\nID");
            v
        },
    ] {
        let plan: FleetPlan = serde_json::from_value(changed).unwrap();
        assert!(review(&plan, &package(b"v2"), &demo_signing_key().verifying_key()).is_err());
    }
    let mut extra = value;
    extra["execute"] = json!("untrusted-command");
    assert!(serde_json::from_value::<FleetPlan>(extra).is_err());
}

#[test]
fn bounded_input_and_actual_cli_preserve_sources() {
    let root = tempfile::tempdir().unwrap();
    let value = setup(root.path(), 2, 1);
    let input = root.path().join("plan.json");
    fs::write(&input, serde_json::to_vec(&value).unwrap()).unwrap();
    package(b"v2").write(&root.path().join("package")).unwrap();
    let before = bytes(root.path());
    let output = Command::new(env!("CARGO_BIN_EXE_fwlab"))
        .args(["fleet-preflight", "--inventory"])
        .arg(&input)
        .arg("--package")
        .arg(root.path().join("package"))
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(report["devices"][0]["rehearsal"], "confirmed");
    assert!(report["stopped_after_cohort"].is_null());
    assert_eq!(bytes(root.path()), before);
    fs::write(&input, vec![b' '; 32_769]).unwrap();
    assert!(FleetPlan::load(&input).is_err());
    fs::write(&input, b"{\"schema\":1,\"schema\":1}").unwrap();
    assert!(FleetPlan::load(&input).is_err());
    fs::write(
        root.path().join("package/manifest.json"),
        vec![b' '; 65_537],
    )
    .unwrap();
    assert!(ReleasePackage::load(&root.path().join("package")).is_err());
}

#[test]
fn signed_attempt_ceiling_and_legacy_restage_boundary() {
    let root = tempfile::tempdir().unwrap();
    setup(root.path(), 1, 1);
    let device = root.path().join("device-0");
    let updater = agent(&device);
    updater.stage(&package(b"v2"), &mut NoFault).unwrap();
    let before = bytes(root.path());
    assert!(updater.activate(SlotId::B, 3, &mut NoFault).is_err());
    assert_eq!(bytes(root.path()), before);
    let mut legacy = serde_json::to_value(updater.status().unwrap()).unwrap();
    legacy["slots"]["B"]
        .as_object_mut()
        .unwrap()
        .remove("max_boot_attempts");
    let primary = device.join("state.json");
    fs::write(&primary, serde_json::to_vec(&legacy).unwrap()).unwrap();
    assert!(
        updater.status().is_ok(),
        "old confirmed states remain readable"
    );
    assert!(updater.activate(SlotId::B, 1, &mut NoFault).is_err());
    updater.stage(&package(b"v2"), &mut NoFault).unwrap();
    assert!(updater.activate(SlotId::B, 2, &mut NoFault).is_ok());
    updater.boot(&mut NoFault).unwrap();
    let before = bytes(root.path());
    assert!(updater.activate(SlotId::B, 2, &mut NoFault).is_err());
    assert_eq!(
        bytes(root.path()),
        before,
        "reactivation must not reset remaining boots"
    );
}

#[test]
fn previously_verified_inactive_image_cannot_downgrade_new_confirmed_release() {
    let root = tempfile::tempdir().unwrap();
    setup(root.path(), 1, 1);
    let updater = agent(&root.path().join("device-0"));
    updater.stage(&package(b"v2"), &mut NoFault).unwrap();
    updater.activate(SlotId::B, 2, &mut NoFault).unwrap();
    updater.boot(&mut NoFault).unwrap();
    updater.confirm_health(&mut NoFault).unwrap();
    let mut v3 = package(b"v3");
    v3.manifest = SignedManifest::create(
        "release-3".into(),
        Version::new(3, 0, 0),
        vec![profile().hardware_id],
        2,
        &v3.image,
        &demo_signing_key(),
    )
    .unwrap();
    updater.stage(&v3, &mut NoFault).unwrap();
    updater.activate(SlotId::A, 2, &mut NoFault).unwrap();
    updater.boot(&mut NoFault).unwrap();
    updater.confirm_health(&mut NoFault).unwrap();
    let before = bytes(root.path());
    assert!(updater.activate(SlotId::B, 2, &mut NoFault).is_err());
    assert_eq!(bytes(root.path()), before);
}
