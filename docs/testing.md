# Testing strategy

## Quality risks

The protected risks are accidental activation of unverified content, loss of the last
known-good image, non-deterministic rollback, accepting an incompatible release, and loading
partially committed metadata.

## Test layers

| Layer | Scope | Representative evidence |
| --- | --- | --- |
| Unit | Parsers, crypto helpers, policies, transitions | Strict version parse, signature mutation, hash mismatch |
| Integration | Public agent plus filesystem store | Stage/activate/boot/fail across fresh agent instances |
| Property | Generated versions and attempt budgets | Confirmation promotes exactly; exhaustion returns to A |
| Fault | Every state commit boundary for stage and activation | 12 scenarios per campaign iteration |
| Static | Formatting, Clippy pedantic/nursery, compiler warnings | CI denies warnings |
| Supply chain | Locked dependencies and RustSec advisories | Version-locked scheduled security workflow |
| Documentation | Rustdoc build, generated code index, required artifact/header scan | CI contract checks |

## Determinism

Transition functions use no clock, randomness, network, or global state. Audit sequence values
come from committed generations. The demo signing key and synthetic images are fixed. Property
tests use generated inputs but assert invariant behavior independent of the particular sample.

## Campaign math

There are six metadata commit fault points and two operations under interruption, so each
iteration runs 12 scenarios. The standard 100-iteration job runs 1,200 restarts. Every
recovered state must parse, satisfy all invariants, retain a verified confirmed slot, and be
classifiable as prior stable state or safe forward progress.

## Commands

```bash
cargo test --all-targets --all-features --locked
cargo clippy --all-targets --all-features -- -D warnings
cargo run --release --locked -- fault-campaign --iterations 100 --output artifacts/fault-campaign.json
```

## Exit criteria

- All tests and documentation builds pass.
- Clippy and compiler warnings are zero.
- Recovered count equals campaign scenario count.
- Safety-invariant count equals campaign scenario count.
- Repository contract and neutral-wording scan pass.

## Exclusions

The campaign is not hardware-in-the-loop, a real power-cut test, or evidence of atomicity on a
specific filesystem. Coverage percentage is intentionally not used as a substitute for
invariant and failure-mode coverage.
