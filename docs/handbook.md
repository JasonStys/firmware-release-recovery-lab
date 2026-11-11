# Firmware Release & Recovery Lab handbook

By Jason Stys.

Rehearse signed A/B firmware-update decisions, bounded trial boots, rollback and interrupted local metadata writes. Fleet preflight compares declared policies and assumptions without flashing devices or measuring physical device health.

Rehearse bounded fleet cohorts with package/state fingerprints, compatibility and trial outcomes; fix unconfirmed-stage overwrite, attempt-budget reset and rollback-version checks.

Shows rollout readiness and recovery consequences before touching devices, while enforcing the underlying lifecycle invariants.

## Read the documentation

| Edition | Audience and contents |
| --- | --- |
| [project-guide.docx](reports/project-guide.docx) | User and developer guide: purpose, current usage, design, boundaries and source references. |
| [validation-review.docx](reports/validation-review.docx) | Reviewer edition: exact tested baseline, observed workflows, dated local results and remaining limits. |
| [validation-evidence.xlsx](reports/validation-evidence.xlsx) | Two filterable Excel Tables for observed workflows and test-source inventory, with recalculating outcome formulas. |

The editable Markdown remains the maintenance source. The Word files are readable editions. The workbook is an evidence index rather than a test runner. See [publication identities and review](reports/publications.json) and the [documentation refresh record](reports/documentation-refresh-2026-11-09.md).

## Current usage and help

[README quick start](../README.md) is the entry point. Use the project-specific guides below before changing inputs, operating modes or deployment assumptions.

### Usage and operations

- [native application: workspace, custom inputs, review, history and exports](native-application.md)
- [fleet preflight](fleet-preflight.md)
- [operations](operations.md)
- [release checklist](release-checklist.md)

### Design and contracts

- [adr/0001 rust state engine](adr/0001-rust-state-engine.md)
- [adr/0002 recoverable json metadata](adr/0002-recoverable-json-metadata.md)
- [architecture](architecture.md)
- [research notes](research-notes.md)
- [threat model](threat-model.md)

### Security and validation

- [testing](testing.md)
- [native application implementation observations](reports/native-application-2026-11-11.md)
- [0.2.1 asynchronous import correction](reports/async-evidence-import-2026-11-11.md)
- [source file responsibilities](source-file-guide.md)

The existing Word/workbook editions below retain their historical source and date. The newer
Markdown application guide and dated validation report describe the 0.2.1 candidate; a new reviewed
Office edition or published application must retain its own exact source/byte acceptance.

## Historical results and reproduction

The reviewed source is [`8a89d6fc27a9f283bc26395a91691975daf92c95`](https://github.com/JasonStys/firmware-release-recovery-lab/tree/8a89d6fc27a9f283bc26395a91691975daf92c95). The observed functional workflow baseline is `8a89d6fc27a9f283bc26395a91691975daf92c95`; those observations are recorded at `2026-11-10T06:12:50.203249+00:00`. They do not certify an unrun later revision.

- [Detailed recorded validation](reports/practical-workflows-2026-11-09.md)
- [Current Actions](https://github.com/JasonStys/firmware-release-recovery-lab/actions) records later integration checks separately.
- Preserve dated measurements and follow the existing testing guide to reproduce them; a test-source inventory alone does not establish execution.

## Practical boundaries

- Directory-only simulation with a public demo key, not real hardware secure boot or an operational rollout.
- Trial outcomes are supplied assumptions, not measured or predicted device health.
- The OS/operator is trusted; external concurrent writers are not locked by the rehearsal workflow.

## Maintaining these editions

Update the editable usage/design/test documents first. Rebuild and visually review every Word page and workbook tab before replacing an edition; verify the exact binary digests and evidence source in publications.json. Keep account data, logs with secrets, installed-app state and private test stores out of documentation. Source and release assets retain their existing security and licensing boundaries.
