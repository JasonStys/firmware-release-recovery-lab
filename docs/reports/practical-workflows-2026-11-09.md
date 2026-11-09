# Fleet preflight validation — November 9, 2026

Created by Jason Stys. Windows x64, exact pinned Rust 1.90.0; local temporary
synthetic devices/packages only. Existing historical reports remain point-in-time
records. Hosted acceptance is recorded separately on the matching commit.

Added a complete CLI/library release-review workflow: bounded explicit inventory,
signed-package/local-policy preflight, canonical plan/manifest/state fingerprints,
ordered cohort rehearsal, confirmation/exhausted-budget assumptions, and visible
not-attempted states after a failed cohort. Every device retains a compatibility
result. Nothing writes device state; raw roots are omitted from the report.

Tests exposed and now prevent four concrete lifecycle problems: staging bytes
before rejecting an active trial; activation exceeding a manifest's signed boot
ceiling; repeated activation resetting remaining boots; and reactivation of an
older previously verified image after a newer release was confirmed. Old metadata
remains readable; legacy inactive candidates need verified restaging to acquire
the actual signed ceiling. No ceiling or version floor is guessed.

| Check | Observed result |
|---|---|
| `cargo test --all-targets --all-features --locked` | 20 passed, including 8 new real-directory and actual CLI tests; no skipped tests. |
| `cargo clippy --all-targets --all-features --locked -- -D warnings` | Passed without lint suppression. |
| `cargo fmt --all -- --check` | Passed. |
| `cargo doc --no-deps --document-private-items --locked` | Passed. |
| Release interruption campaign | 1,200/1,200 recovered and preserved the known-good invariant; all six named boundaries for stage and activation. |
| `cargo audit --deny warnings` | No findings across 85 locked dependencies and the fetched RustSec database. |
| Source index / repository contract | Regenerated and passed. |

Independent expectations cover cohorts of size one and two, same-cohort
completion, later-cohort stop, all-confirmed success, wrong hardware, version
floor, corrupt bytes/signature/state, pending trials, exact recursive filesystem
byte preservation, stable reports, duplicate IDs/resolved roots, controls, schema,
count/size limits, unknown fields, duplicate JSON keys, actual JSON CLI output,
legacy restaging and multi-update rollback-floor protection.

Read caps are 32 KiB plan, 64 KiB manifest, 16 MiB image and 128 KiB per metadata
copy. This is a directory simulator with a deliberately public signing key; the
OS/operator and explicitly selected paths remain trusted. It is not secure boot,
physical flashing, a protected ledger, measured health, a performance prediction,
or an atomic fleet snapshot. Concurrent external writers are not locked.
Docker and workstation protections were left unchanged. Native execution required
scoped permission to use the existing compiler/dependency cache; no checks were
disabled after the sandbox's DNS restriction.
