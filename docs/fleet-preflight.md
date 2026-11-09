# Read-only fleet preflight

Created by Jason Stys. A release engineer can review one demo-signed package
against up to 64 explicitly selected local simulated devices, then rehearse
ordered cohorts of 1–16 devices. This is a CLI/library workflow; it never flashes
hardware or writes device images, metadata, or audit records.

```text
cargo run -- init --root demo/device-a
cargo run -- init --root demo/device-b
cargo run -- package --output demo/candidate --version 2.0.0 --release-id sample-2
cargo run -- fleet-preflight --inventory demo/fleet.json --package demo/candidate
```

Save this as `demo/fleet.json`. Paths are relative to the **process working
directory**, not to the JSON file. All roots must already exist. Use temporary
synthetic roots for demonstrations.

```json
{
  "schema": 1,
  "cohort_size": 1,
  "devices": [
    {
      "id": "canary-a",
      "root": "demo/device-a",
      "profile": {
        "hardware_id": "edge-controller-v1",
        "minimum_version": {"major": 1, "minor": 0, "patch": 0}
      },
      "outcome": "exhaust"
    },
    {
      "id": "cohort-b",
      "root": "demo/device-b",
      "profile": {
        "hardware_id": "edge-controller-v1",
        "minimum_version": {"major": 1, "minor": 0, "patch": 0}
      },
      "outcome": "confirm"
    }
  ]
}
```

The first device exhausts its signed trial-boot allowance and rolls back **in
memory**. The second remains compatibility-reviewed but is
`not_attempted_after_stop`. Devices in the same cohort finish before the stop
condition applies. A rejected compatibility/staging check also stops later
cohorts. Changing `exhaust` to `confirm` demonstrates an all-confirmed rehearsal.
These outcomes are supplied assumptions, never measurements or forecasts.

Reports bind the canonical complete plan, signed manifest and each successfully
loaded metadata snapshot with SHA-256. All requested devices appear exactly
once. Explicit policy, outcome, cohort, eligibility, reason and rehearsal state
remain separate. Source paths are omitted from output; the plan hash still binds
them. Hashes identify content, not authenticity or a locked concurrent snapshot.

Invalid/duplicate device IDs or resolved roots, unsupported schema, empty or
oversized fleets, unknown/duplicate plan/device fields and files over 32 KiB are
rejected. Package reads are capped at 64 KiB for a manifest and 16 MiB for an image;
metadata recovery reads at most 128 KiB per copy. The local operator and OS remain
trusted; this is not a sandbox for hostile filesystem writers or linked paths.

The CLI returns zero for a valid report even when devices are blocked: inspect
`eligible`, `rehearsal`, and `stopped_after_cohort`. Invalid inputs return nonzero.
Use shell redirection to save the JSON; choose a new destination to preserve prior
evidence. Review never stages, retries, activates or authorizes a real rollout.

Lifecycle defects are also corrected: a pending trial is rejected **before**
any slot write, activation cannot exceed the signed manifest's attempt
ceiling, reactivation cannot reset an in-flight budget, and previously verified
older inactive images cannot downgrade the confirmed release.
Existing confirmed metadata remains readable. Legacy inactive candidates
without that ceiling must be restaged from their verified package before
activation; a ceiling is never invented. Directory state is not tamper-resistant,
and the deliberately public demonstration key is unsuitable for real releases.

Complexity is O(d × (n + m)) for d devices, n image bytes and m bounded metadata
bytes; verification intentionally rechecks the package per device. At most 64
devices, 10 trial selections plus one rollback observation per device and bounded
files prevent unbounded rehearsal. No external service, device or network call
is made.
