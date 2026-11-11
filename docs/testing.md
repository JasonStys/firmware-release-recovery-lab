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
| Desktop ownership | Actual temporary profiles, lock/SQLite, held requests and Tk controls | No early lock release, alias/unsupported-schema refusal |
| Application protocol | Actual fixed Rust child and real local HTTP | Canonical input binding, closed schema, malformed engine refusals, bounded framing |
| Browser workflows | Actual editable UI/import/review/download/history | Independent generation/cohort/campaign oracles; mobile/keyboard; selected evidence preserved on refusal |
| Portable packaging | Actual extracted application and second launch | Exact source/runtime/assets/notices, seven recorded workflows, normal 0/0 and retained history |

The 0.2.1 browser consumer also pauses a real selected evidence file read and the delivery of an
actual completed Rust/API response independently. It requires an explicit busy refusal instead of
a rerun claim, releases the unchanged response, then explicitly deletes only that temporary eighth
run. The original seven retained-workflow, exact-download and second-launch oracles still apply.
The [dated correction record](reports/async-evidence-import-2026-11-11.md) distinguishes the actual
installed 0.2.0 reproduction from later source/package and hosted checks.

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

## CodeQL source-security evidence

The separate [CodeQL workflow](../.github/workflows/codeql.yml) creates genuine supported-language databases and uses security-extended queries. Read [the analysis contract](codeql-analysis.md) for each extraction mode and [the setup report](reports/codeql-setup-2026-11-09.md) for observations. Existing runtime/property/fault/browser/sanitizer and dependency gates remain unchanged. Syntax validation is not an executed scan; uploaded analyses and open findings must be inspected at the exact current-main SHA. Missing or unauthorized analysis is reported as unavailable rather than passing. Real findings require source-level triage and a regression reproducing the actual boundary.

## Application source and native gates

Use an isolated Python environment from a final patched3.14 SDK (minimum 3.14.10), Node 24 and
Rust 1.98.1. Install exact hash-locked Python graphs and the web lockfile; do not alter a shared environment.

```bash
python -m pip install --require-hashes -r requirements-dev.lock -r requirements-package.lock
cargo build --locked
npm --prefix web ci --ignore-scripts
npm --prefix web test
npm --prefix web run smoke
npm --prefix web audit --audit-level=high
python -m ruff check firmware_studio tests tools scripts launcher.py
python -m ruff format --check firmware_studio tests tools scripts launcher.py
python -m pytest --cov --cov-report=term-missing
python -m pip_audit --require-hashes -r requirements-dev.lock -r requirements-package.lock
python scripts/generate_code_index.py
python scripts/generate_file_guide.py
python scripts/verify_repo.py
```

The coverage floor is 90 combined statement/branch for the entire `firmware_studio` package;
native-owner code is included. It complements the domain oracles and is not a Rust coverage claim.
The parent pytest suite explicitly launches13 actual Tcl/Tk notice cases in one fresh bounded
interpreter; it propagates nonzero failure and records every case without retries or skips.
Report parent and isolated case counts separately. Real Tk source tests require a display;
Linux CI uses `xvfb-run` rather than skipping them.

Install the exact locked Chromium using `npm --prefix web exec -- playwright install chromium`
(and Linux OS dependencies). `python tools/smoke_source.py --output .runtime/source-browser-new`
uses a fresh source owner and the same GUI/domain consumer. It explicitly records development
mode. `python -m tools.package_app --output-root .runtime/native-new` requires clean Git source,
builds the actual executable, writes platform-appropriate ZIP/tar.gz, safely extracts it and runs
`tools/smoke_app.py` with no source fallback. The output path must not exist.

The native consumer verifies product/runtime/source/static assets, actual Rust identity, Rust std
and source-collected Cargo notice inventories before launching. It edits a custom leading-zero/
high-byte image, tests healthy promotion, mismatched-image blocking, exhausted-trial rollback,
all-row cohort stop, a real12-scenario campaign, named interruption and forged-result rerun.
It checks exact generation 0/4, cohort 2 and stable4/forward8 expectations, real downloads, literal
search, mobile overflow, page errors, normal Quit and all seven saved records after a second launch.
Actual archive extraction/launch is distinct from an OS installer transaction or default-browser claim.

The separate three-OS desktop workflow runs this full acceptance before any checksum sidecar is
created. It has no release permissions and uploads no application binaries or private profiles.
All original Cargo/Clippy/Rustdoc/RustSec and 1,200-scenario CI gates remain separate. Hosted results
are pending until the exact source revision and processed CodeQL categories have actually completed.
