# Validation report

- Date: 2026-09-17
- Platform: Windows x86_64
- Rust: 1.90.0 (`1159e78c4`, 2025-09-14)
- Cargo: 1.90.0 (`840b83a10`, 2025-07-30)
- Repository version: 0.1.0

## Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Formatting | PASS | `cargo fmt --all -- --check` produced no diff |
| Static analysis | PASS | Clippy `all`, `pedantic`, and `nursery`; warnings denied |
| Unit tests | PASS | 9 passed, 0 failed |
| Integration tests | PASS | 1 passed, 0 failed |
| Property tests | PASS | 2 properties passed, 0 failed |
| Release build | PASS | Optimized `fwlab` binary built from locked dependencies |
| Fault campaign | PASS | 1,200/1,200 recovered; 1,200/1,200 preserved invariants |
| Rustdoc | PASS | Library and private-item documentation generated |
| Repository contract | PASS | Required artifacts, code headers, and neutral wording checked |

## Fault campaign summary

The standard campaign repeated six commit boundaries for stage and activation across 100
iterations. It completed 1,200 restart scenarios in 12,962 ms on the validation machine.

- Stable recoveries: 400
- Safe forward-progress recoveries: 800
- Unrecoverable states: 0
- Safety-invariant violations: 0

The machine-readable report is [fault-campaign.json](fault-campaign.json). Timing is diagnostic,
not a real-time or production-storage guarantee.

## Test inventory

- Version parser rejects missing components and suffixes.
- Initial state has a verified confirmed image.
- Modified signed payload is rejected.
- Modified image bytes cause a digest mismatch.
- Hardware incompatibility is rejected before staging.
- Successful health confirmation promotes only the selected candidate.
- Exhausted attempt budget restores the confirmed slot.
- Every metadata boundary recovers old or new invariant-valid state.
- Public agent operations persist across reconstructed agent instances.
- Generated versions/attempt counts preserve confirmation and rollback properties.

## Residual risk

Tests simulate process interruption around filesystem calls, not physical power removal or torn
storage writes. Cryptographic key management, secure boot, concurrent writers, protected
counters, network delivery, and hardware-in-the-loop validation remain out of scope.

