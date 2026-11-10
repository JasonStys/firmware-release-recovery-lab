# CodeQL setup validation — 2026-11-09

By Jason Stys. This report records a source-analysis setup change, not a claim that absent analysis was clean.

## Baseline and configuration

Before this change the repository had no active CodeQL workflow; authenticated alerts and analyses returned404/no analysis found. The repository is public and its authored languages are supported. The new advanced workflow follows the [documented language/build contract](../codeql-analysis.md), uses the official full-SHA4.39.3 action pin, security-extended queries and only SARIF-upload permission in addition to source read. Existing CI/dependency tests remain separate and unchanged. No application behavior, device access, signing material, release bytes or private local configuration is changed.

## Observed local checks

Windows with the repository-pinned Rust1.90.0: `cargo fmt --all -- --check`, locked Clippy for all targets/features with warnings denied,20 unit/integration/property/fleet tests with no ignored cases, locked release build and private-item Rustdoc all passed. The real release executable completed all1200 interruption scenarios:1200 recoveries/invariants preserved,400stable and800forward outcomes,29332ms under the recorded local conditions. `cargo audit --deny warnings` scanned85 locked crate dependencies with1430 RustSec advisories and no finding. Repository/header/neutral-wording checks and regenerated declaration-index freshness passed. Official checksum-verified actionlint1.7.12 accepted the new workflow. These observations are not a local CodeQL execution claim.

## Observed first hosted analysis

The real [PR13 CodeQL workflow](https://github.com/JasonStys/firmware-release-recovery-lab/actions/runs/42764641313) completed all three lanes with CodeQL2.27.4. This observation belongs to source head `623fab84ac4983d0b901a3474c8d9e801dc19961` and GitHub's analyzed PR-merge commit `5c78d48e63317d8551f0821ca4c506df1a574499` at `refs/pull/13/merge`, before this report-only follow-up. It is not a main-branch analysis assertion.

| Category | Actual analysis ID | Rules executed | Results |
| --- | --- | --- | --- |
| `rust` | `2132788335` | 28 | 0 |
| `python` | `2132781988` | 50 | 0 |
| `actions` | `2132781454` | 23 | 0 |

The API returned an empty analysis error for every category and a complete empty open-alert listing for that PR ref. No finding was dismissed, suppressed, excluded or relabeled to reach that result. Current main must be scanned and its actual alerts inspected separately after merge; a report-only commit also requires its own fresh PR checks. Zero results are time/tool/language-specific observations, not proof of no vulnerabilities.

## Validation scope

Local compiler/runtime tests, repository docs/index checks and workflow syntax are separate from genuine hosted extraction/query analysis. The workflow itself and its actual language categories must run successfully; reported issues then require source-level triage. A first PR scan cannot establish current-main coverage before merge. The [CodeQL workflow history](https://github.com/JasonStys/firmware-release-recovery-lab/actions/workflows/codeql.yml) identifies the runnable contract; current hosted runs and Security findings remain the authoritative dynamic records.

The acceptance handoff records exact local commands and hosted source/run results. No CodeQL pass, rule count, zero-alert claim or operational-security guarantee is inferred solely from syntax checks or the prior404 response. The fixed public demo data and all original safety/authorization limits are preserved.
