# Repository map

Every authored or generated repository file has one primary responsibility.

| File | Responsibility |
| --- | --- |
| `.github/dependabot.yml` | Proposes reviewed Cargo and Actions dependency updates weekly |
| `.github/workflows/ci.yml` | Runs format, lint, tests, release build, docs, contracts, and fault campaign |
| `.github/workflows/security.yml` | Audits the lockfile against RustSec advisories |
| `.gitignore` | Excludes compiler output, local labs, evidence artifacts, and editor state |
| `Cargo.lock` | Locks exact direct and transitive crate versions for reproducible builds |
| `Cargo.toml` | Declares package metadata, binaries, dependencies, profiles, and lint policy |
| `CHANGELOG.md` | Records notable versioned changes |
| `CODE_OF_CONDUCT.md` | Defines respectful participation expectations |
| `CONTRIBUTING.md` | Defines environment, code, test, review, and release practices |
| `LICENSE` | Grants the MIT license |
| `README.md` | Explains purpose, quickstart, features, evidence, safety, and file guide |
| `SECURITY.md` | Defines private reporting, supported version, secrets, and safe-use policy |
| `rust-toolchain.toml` | Pins compiler, profile, formatter, and linter |
| `rustfmt.toml` | Normalizes Rust formatting and newlines |
| `docs/architecture.md` | Describes components, data flow, trust boundaries, and failure behavior |
| `docs/code-index.md` | Generated exact line locations for source declarations |
| `docs/durable-writes.md` | Documents state commit ordering and durability limitations |
| `docs/limitations.md` | Lists deliberate exclusions and non-production constraints |
| `docs/operations.md` | Documents configuration, inspection, recovery, and troubleshooting |
| `docs/release-checklist.md` | Provides a repeatable release gate list |
| `docs/repository-map.md` | Summarizes every file |
| `docs/research-notes.md` | Connects implementation choices to current primary documentation |
| `docs/state-machine.md` | Defines lifecycle states, transitions, preconditions, and invariants |
| `docs/testing.md` | Defines risks, test layers, campaign math, commands, and exit criteria |
| `docs/threat-model.md` | Enumerates assets, entry points, addressed threats, and exclusions |
| `docs/adr/0001-rust-state-engine.md` | Records the Rust language decision and tradeoffs |
| `docs/adr/0002-recoverable-json-metadata.md` | Records the complete-state persistence decision and tradeoffs |
| `docs/reports/fault-campaign.json` | Captures local machine-readable interruption results |
| `docs/reports/validation.md` | Summarizes local tools, gates, counts, timing, and residual risk |
| `examples/packages/release-2/image.bin` | Contains harmless synthetic bytes for the checked-in sample release |
| `examples/packages/release-2/manifest.json` | Contains the sample canonical payload and demo signature |
| `scripts/generate_code_index.py` | Regenerates declaration line locations deterministically |
| `scripts/validate.sh` | Runs the complete local/CI validation sequence |
| `scripts/verify_repo.py` | Checks artifacts, code headers, and neutral public wording |
| `src/agent.rs` | Orchestrates verification, storage, transitions, and campaigns |
| `src/crypto.rs` | Provides hashing, signing, verification, and isolated demo key material |
| `src/fault.rs` | Defines durable boundaries and one-shot interruption injection |
| `src/lib.rs` | Documents and exports the library modules and public API |
| `src/main.rs` | Defines `fwlab` commands, safe path checks, dispatch, and output |
| `src/model.rs` | Defines versions, slots, phases, records, audit events, errors, and invariants |
| `src/package.rs` | Creates, loads, writes, validates, and verifies release packages |
| `src/store.rs` | Owns slot files plus primary/backup metadata persistence and recovery |
| `src/transition.rs` | Implements pure stage, activation, boot, confirmation, failure, and rollback |
| `tests/end_to_end.rs` | Exercises persisted rollback through reconstructed public agents |
| `tests/lifecycle_properties.rs` | Generates bounded versions/attempt budgets to test lifecycle properties |

