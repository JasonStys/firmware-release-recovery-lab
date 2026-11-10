# Documentation refresh — 2026-11-09

By Jason Stys.

This documentation-only edition describes source `8a89d6fc27a9f283bc26395a91691975daf92c95`. It does not change application behavior, accounts, private data, installers or published releases.

## Published editions and completed review

| File | Bytes | SHA-256 | Reviewed scope |
| --- | ---: | --- | --- |
| [project-guide.docx](project-guide.docx) | 43667 | `6a65c614f7c8b5478f7789689ba69f4eb5923d4dc7ab9d75c340e63896b11f04` | 5 pages, each viewed individually |
| [validation-review.docx](validation-review.docx) | 43572 | `e8629f39875b97f81ccdaa2b487903f85b9c49596d30b7bfaa084d84fba0a0f3` | 4 pages, each viewed individually |
| [validation-evidence.xlsx](validation-evidence.xlsx) | 7273 | `b2cc7299ae0f5c440566c0c9a48db75f561da7ce9a6b2e369d2ce6f25169de31` | Both tab previews; two actual Excel Tables/autoFilters; four formulas; failure-change/restore recalculation and zero formula errors |

Word review checked plain black titles, readable pagination, whole table rows, source references, practical limits and absence of clipping or overflow. Render receipts were matched to the current DOCX digest before approval. Workbook review inspected both tab previews and actual exported Table/autoFilter elements; recalculated success/failure summaries were compared independently with workflow metadata. Static previews do not draw Excel dropdown arrows; the exported workbook contains the actual filters.

## Evidence and change boundary

- Functional baseline: `8a89d6fc27a9f283bc26395a91691975daf92c95`.
- Workflow observation: `2026-11-10T06:12:50.203249+00:00`; exact run URLs and source identities remain in [publications.json](publications.json).
- Local document-package validation verifies exact copied bytes, Office ZIP integrity, approved page/tab identities and internal documentation links. Repository-specific documentation and source-policy commands are run separately and recorded in the integration handoff.
- Source/index metadata is regenerated using the repository’s existing tools. Existing privacy, security, coverage and workflow gates are retained.
- PR and later main workflows must pass independently. This record does not claim future or unrun integration CI success.

## Interpretation

The Word files document the cited source; dated source reports retain their original execution scope. A passing workflow is distinct from completed analysis with zero findings, and neither establishes production suitability. The Excel source inventory is not a per-test execution report. Checksums identify exact bytes, not a signature or publisher attestation.

Use the [handbook](../handbook.md) to choose usage, design, security and test documentation. Keep editable Markdown and reviewed editions together; do not replace historical measurements with undated claims.

## Integration-local checks

Observed at `2026-11-10T07:54:22.317145+00:00` on Windows with this repository’s existing development tools. Python commands use its isolated development environment. The documentation source baseline remains the immutable revision above; these checks validate this documentation integration locally.

| Command | Observed result |
| --- | --- |
| `python scripts/generate_code_index.py` | Passed, exit 0. |
| `python scripts/verify_repo.py` | Passed, exit 0. |
| `cargo fmt --all -- --check` | Passed, exit 0. |
| `cargo test --all-targets --all-features --locked --offline` | Passed, exit 0. |

The independent publication audit also matched every copied Office file to its approved SHA-256, checked ZIP package integrity and current page/tab approvals, compared immutable workflow/source metadata, and resolved every local handbook/report link within the repository. Hosted PR/main, browser, platform and container jobs remain separate required checks; they are not inferred from these local results.



All 20 existing Rust tests passed with no ignored tests using the exact pinned Rust 1.90.0 toolchain and locked offline graph. Cargo reported a local incremental-cache hard-link warning and copied cache files instead; this was not a source diagnostic or a disabled compiler gate. The existing full hosted Clippy, release, documentation and 1,200-interruption lanes remain required. No source file, simulator state or release asset was changed.
