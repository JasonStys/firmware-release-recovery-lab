//! Independent real-engine desktop rehearsals, package refusals and interruption/cohort oracles.
//!
//! File map: independent fixture requests use the actual original UpdateAgent/LabStore through
//! the bounded protocol; expected generations/slots/cohort decisions are hand-derived.

use firmware_recovery::studio::execute;
use serde_json::{Value, json};

fn device(id: &str) -> Value {
    json!({"id":id,"hardware":"fictional-controller","minimum_version":"1.0.0",
        "initial_version":"1.0.0","initial_image_hex":"7631","outcome":"confirm"})
}

fn release() -> Value {
    json!({"mode":"build","version":"2.0.0","release_id":"training-release",
        "compatible_hardware":["fictional-controller"],"max_boot_attempts":1,"image_hex":"7632"})
}

fn request(actions: &[&str]) -> Value {
    let steps: Vec<_> = actions
        .iter()
        .map(|kind| {
            let action = match *kind {
                "activate" => json!({"kind":kind,"slot":"B","attempts":1}),
                "fail" => json!({"kind":kind,"reason":"supplied failed health assumption"}),
                _ => json!({"kind":kind}),
            };
            json!({"device":"alpha","action":action,"fault":null})
        })
        .collect();
    json!({"kind":"lifecycle","plan":{"devices":[device("alpha")],"release":release(),"steps":steps}})
}

fn run(value: &Value) -> Value {
    execute(&serde_json::to_string(value).expect("fixture JSON")).expect("actual rehearsal")
}

#[test]
fn original_engine_promotes_only_after_selected_boot_and_explicit_health() {
    let report = run(&request(&["stage", "activate", "boot", "confirm"]));
    assert_eq!(report["outcome"], "completed");
    assert_eq!(report["requested_steps"], 4);
    assert_eq!(report["unattempted_steps"], 0);
    assert_eq!(report["initial"]["alpha"]["generation"], 0);
    assert_eq!(report["timeline"][0]["after"]["phase"], "staged");
    assert_eq!(report["timeline"][1]["after"]["confirmed"], "A");
    assert_eq!(report["timeline"][2]["selected_slot"], "B");
    assert_eq!(report["timeline"][2]["after"]["attempts_remaining"], 0);
    assert_eq!(report["final"]["alpha"]["generation"], 4);
    assert_eq!(report["final"]["alpha"]["confirmed"], "B");
    assert_eq!(report["final"]["alpha"]["phase"], "stable");
    assert_eq!(
        report["final"]["alpha"]["slots"]["B"]["version"],
        json!({"major":2,"minor":0,"patch":0})
    );
}

#[test]
fn failed_last_trial_preserves_actual_original_confirmed_image() {
    let report = run(&request(&["stage", "activate", "boot", "fail"]));
    assert_eq!(report["outcome"], "completed");
    assert_eq!(report["final"]["alpha"]["phase"], "rolled_back");
    assert_eq!(report["final"]["alpha"]["generation"], 4);
    assert_eq!(report["final"]["alpha"]["active"], "A");
    assert_eq!(report["final"]["alpha"]["confirmed"], "A");
    assert_eq!(
        report["final"]["alpha"]["slots"]["A"],
        report["initial"]["alpha"]["slots"]["A"]
    );
}

#[test]
fn incompatible_signature_digest_and_downgrade_are_negative_evidence_not_success() {
    let package = run(&request(&[]))["package"].clone();
    for change in ["hardware", "signature", "digest", "downgrade"] {
        let mut value = request(&["stage", "activate"]);
        if change == "hardware" {
            value["plan"]["devices"][0]["hardware"] = json!("different-fictional-family");
        } else if change == "downgrade" {
            value["plan"]["release"]["version"] = json!("0.9.0");
        } else {
            value["plan"]["release"] = json!({"mode":"import","manifest":package["manifest"],"image_hex":package["image_hex"]});
            if change == "signature" {
                value["plan"]["release"]["manifest"]["signature_ed25519"] = json!("00".repeat(64));
            } else {
                value["plan"]["release"]["image_hex"] = json!("0000");
            }
        }
        let report = run(&value);
        assert_eq!(report["outcome"], "rejected", "{change}");
        assert_eq!(report["unattempted_steps"], 1, "{change}");
        assert_eq!(report["initial"], report["final"], "{change}");
        assert_eq!(report["timeline"][0]["status"], "rejected", "{change}");
        assert!(
            report["timeline"][0]["reason"]
                .as_str()
                .is_some_and(|reason| !reason.is_empty())
        );
    }
}

#[test]
fn actual_metadata_boundaries_recover_prior_or_new_state_without_claiming_applied() {
    for (fault, generation, phase) in [
        ("after_temp_write", 0, "stable"),
        ("after_primary_rename", 1, "staged"),
    ] {
        let mut value = request(&["stage", "activate"]);
        value["plan"]["steps"][0]["fault"] = json!(fault);
        let report = run(&value);
        assert_eq!(report["outcome"], "interrupted_recovered");
        assert_eq!(report["timeline"][0]["status"], "interrupted_recovered");
        assert_eq!(report["final"]["alpha"]["generation"], generation);
        assert_eq!(report["final"]["alpha"]["phase"], phase);
        assert_eq!(report["final"]["alpha"]["confirmed"], "A");
        assert_eq!(report["unattempted_steps"], 1);
    }
}

#[test]
fn read_only_cohort_rehearsal_reviews_all_devices_and_preserves_each_state() {
    let mut middle = device("beta");
    middle["outcome"] = json!("exhaust");
    let value = json!({"kind":"preflight","fleet":{"devices":[device("alpha"),middle,device("gamma")],"release":release(),"cohort_size":1}});
    let report = run(&value);
    assert_eq!(report["before"], report["after"]);
    assert_eq!(report["read_only"], true);
    assert_eq!(report["report"]["stopped_after_cohort"], 2);
    let rows = report["report"]["devices"].as_array().expect("all rows");
    assert_eq!(rows.len(), 3);
    assert_eq!(
        rows.iter()
            .map(|row| row["id"].as_str().expect("ID"))
            .collect::<Vec<_>>(),
        vec!["alpha", "beta", "gamma"]
    );
    assert_eq!(
        rows.iter()
            .map(|row| row["rehearsal"].as_str().expect("outcome"))
            .collect::<Vec<_>>(),
        vec!["confirmed", "rolled_back", "not_attempted_after_stop"]
    );
    assert!(rows.iter().all(|row| row["eligible"] == true));
}

#[test]
fn original_campaign_checks_every_boundary_and_measured_counts_remain_consistent() {
    let report = run(&json!({"kind":"campaign","iterations":1}));
    assert_eq!(report["report"]["scenarios"], 12);
    assert_eq!(report["report"]["recovered"], 12);
    assert_eq!(report["report"]["safety_invariants_preserved"], 12);
    // Four stage boundaries recover stable; two recover staged. All six activation
    // boundaries recover staged or awaiting-health, hence4stable/8forward.
    assert_eq!(report["report"]["stable_recoveries"], 4);
    assert_eq!(report["report"]["forward_progress_recoveries"], 8);
    assert!(report["report"]["elapsed_milliseconds"].is_u64());
}

#[test]
fn malformed_host_paths_duplicate_keys_unsigned_fields_and_oversized_requests_fail() {
    let mut value = request(&["stage"]);
    value["plan"]["devices"][0]["root"] = json!("C:/outside");
    assert!(execute(&value.to_string()).is_err());
    let duplicate = r#"{"kind":"campaign","iterations":1,"iterations":2}"#;
    assert!(execute(duplicate).is_err());
    assert!(execute(&json!({"kind":"campaign","iterations":6}).to_string()).is_err());
    let mut value = request(&[]);
    let package = run(&value)["package"].clone();
    value["plan"]["release"] =
        json!({"mode":"import","manifest":package["manifest"],"image_hex":package["image_hex"]});
    value["plan"]["release"]["manifest"]["unsigned_notes"] = json!("not signed or accepted");
    assert!(execute(&value.to_string()).is_err());
    assert!(execute(&" ".repeat(262_145)).is_err());
    let mut duplicate = request(&[]);
    duplicate["plan"]["devices"] = json!([device("same"), device("same")]);
    assert!(execute(&duplicate.to_string()).is_err());
}

#[test]
fn selected_fault_is_not_reported_fired_when_no_commit_checkpoint_was_reached() {
    let mut value = request(&["boot"]);
    value["plan"]["steps"][0]["fault"] = json!("after_temp_write");
    let report = run(&value);
    assert_eq!(report["timeline"][0]["requested_fault"], "after_temp_write");
    assert_eq!(report["timeline"][0]["fault_triggered"], false);
    assert_eq!(report["timeline"][0]["status"], "applied");
    assert_eq!(report["final"]["alpha"]["generation"], 0);
}

#[test]
fn no_argument_actions_still_refuse_ignored_or_unsigned_configuration_fields() {
    for kind in ["stage", "boot", "confirm"] {
        let mut value = request(&[kind]);
        value["plan"]["steps"][0]["action"]["host_command"] = json!("never accepted or executed");
        assert!(execute(&value.to_string()).is_err(), "{kind}");
    }
}

#[test]
fn interleaved_devices_keep_independent_confirmed_state_and_stop_at_first_blocked_step() {
    let mut value = request(&["stage", "activate", "boot", "confirm"]);
    let mut beta = device("beta");
    beta["initial_version"] = json!("2.1.0");
    value["plan"]["devices"]
        .as_array_mut()
        .expect("devices")
        .push(beta);
    let steps = value["plan"]["steps"].as_array_mut().expect("steps");
    steps.push(json!({"device":"beta","action":{"kind":"stage"},"fault":null}));
    steps.push(json!({"device":"beta","action":{"kind":"boot"},"fault":null}));
    let report = run(&value);
    assert_eq!(report["outcome"], "rejected");
    assert_eq!(report["timeline"].as_array().expect("timeline").len(), 5);
    assert_eq!(report["unattempted_steps"], 1);
    assert_eq!(report["final"]["alpha"]["confirmed"], "B");
    assert_eq!(report["final"]["alpha"]["generation"], 4);
    assert_eq!(report["final"]["beta"], report["initial"]["beta"]);
}
