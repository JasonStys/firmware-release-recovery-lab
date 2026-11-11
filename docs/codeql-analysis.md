# CodeQL analysis and findings review

By Jason Stys. This is source analysis for an educational repository, not security certification or permission to connect to equipment.

## Setup diagnosis

The authenticated current-main findings/analyses API previously returned HTTP404 with `no analysis found`. Inspection of the public repository and its active workflow list confirmed there was no CodeQL workflow or uploaded analysis. Existing CI and dependency/security jobs were real, separate gates; their success did not establish CodeQL coverage. GitHub supports code scanning for public repositories without purchasing a private-organization feature. No broader account permission, default-setup toggle or alert suppression was required to add advanced setup.

## Supported language and build inventory

| Language lane | Extraction and actual scope |
| --- | --- |
| `rust` / none | Pinned Rust1.98.1 and `cargo fetch --locked` provide the reviewed Cargo graph. CodeQL uses rust-analyzer to process build scripts/macros and authored Rust, without pretending to trace a full Cargo build. The existing CI still compiles and tests all targets/features independently. |
| `python` / none | Actual `firmware_studio` owner, profile, service, subprocess/resource boundary, packaging/acceptance tools and repository scripts. |
| `javascript-typescript` / none | Authored browser editor, input/model code, native browser acceptance and local asset build scripts. |
| `actions` / none | Repository workflow YAML and expression/security patterns. |


The language choices follow the official [supported languages](https://docs.github.com/en/code-security/concepts/code-scanning/codeql/codeql-code-scanning), [compiled-language modes](https://docs.github.com/en/code-security/reference/code-scanning/codeql/build-options-for-compiled-languages), and [query suites](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/manage-your-configuration/customizing-your-advanced-setup-for-code-scanning).

## Workflow security contract

`.github/workflows/codeql.yml` runs on main pushes, pull requests targeting main, an explicit weekly schedule and manual dispatch. It uses no `pull_request_target`, secrets, deployment, hardware access or mutation of old releases. Top-level contents permission is read-only; only the analysis job additionally requests `security-events: write` to upload its genuine SARIF. Checkout does not persist credentials. Public dependencies/query packs require no package-write or identity token.

All action references use full40-character source commits. The reviewed CodeQL action is4.39.3 at `33d7b85da1a04171e211befe2c739303b9a4c066`, independently resolved from GitHub's annotated release tag. Init and analyze use the same pin and `security-extended`; no query exclusions, blanket path ignores, advisory ignores, suppression baseline or `continue-on-error` is added. Each lane has a25-minute timeout and separate language category. Trap/dependency caches are disabled for this new workflow rather than adding storage or changing existing cache/retention policies.

## Reading results correctly

A successful job means the scanner completed; it does not imply no alerts. After merge, verify the actual main ref SHA, the complete open-alert listing filtered to `refs/heads/main`, and an error-free rule-bearing CodeQL analysis at that same SHA. Separate language categories make extraction coverage visible. An HTTP403/404, incomplete listing, missing category or older analysis is unavailable/incomplete evidence, never zero clearance. A PR analysis belongs to the PR/merge ref and must not be represented as a completed main analysis.

Investigate a reported path and line in the real input-to-sink flow, reproduce a reachable issue with an independent negative test, fix the boundary, then rerun its existing tests and actual CodeQL. This project does not automatically dismiss findings or require a false zero result. Preserve every existing compiler, runtime, sanitizer, browser and dependency gate.

## Reproduction and limits

Run the existing commands in [testing](testing.md). Validate workflow syntax with a reviewed actionlint release. Genuine CodeQL extraction/query execution occurs in the hosted workflow; local YAML parsing, successful builds and zero known dependency advisories are separate observations. GitHub's language/framework models can miss custom boundaries; none of these checks proves absence of vulnerabilities or operational safety. See [the setup validation report](reports/codeql-setup-2026-11-09.md).
