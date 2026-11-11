# Asynchronous evidence-import correction — 2026-11-11

By Jason Stys. This is a narrowly scoped 0.2.1 source correction. Hosted checks, publication and
same-workspace installed upgrade acceptance are distinct gates and are not implied by local tests.

## Confirmed defect and correction

The actual installed, unpublished 0.2.0 candidate at source
`2ba4c369d135201f1d96d9ced2aae883e8d2cf50` reproduced a misleading rerun message. A selected file's
real read was held while another actual rehearsal response was pending delivery. Releasing the
file read made `run()` return silently from its busy guard, after which the importer said that
the imported input had been rerun. No second imported-input execution had occurred.

The actual installed probe used a new synthetic workspace, verified all 242 installed file hashes
before and after, forwarded the unchanged actual API response, and exited its owned process with
code 0. The existing visible application, ordinary workspaces, icons and old draft were untouched.

The guard now throws an explicit refusal before changing run state. The file-import error handler
shows that the loaded input has not run and asks the user to wait, then Run. The actual active
rehearsal still completes; its saved evidence remains available in history.

## Regression and independent expectations

The same compiled/source browser consumer controls only delivery of real selected file bytes and
one real completed engine/API response. It requires the refusal while Run is still disabled,
releases the original response, checks its completed outcome and source identity, then explicitly
deletes only that temporary eighth record. The seven original rehearsal records remain exact,
including promotion generation 4, rollback generation 4, blocked generation 0, cohort stop 2,
12 campaign scenarios split into 4 stable and 8 forward recoveries, and interrupted generation 0.

The existing second launch still checks all seven persisted records. No dummy API answer, extra
retry, relaxed deadline, history reset, shutdown alteration or production input is introduced.

## Observed local validation

| Gate | Actual result |
| --- | --- |
| Original Rust suites | 30 passed across library, persistence, property, preflight and studio cases |
| Original deterministic campaign | 1,200 scenarios; 1,200 recovered and safe; 400 stable and 800 forward recoveries |
| Python owner/store/engine/HTTP/alias tests | 161 passed; 93.91% combined line/branch coverage, unchanged 90% floor |
| Native Tcl notice contract | 13 mandatory cases in the existing isolated interpreter wrapper; no skips |
| TypeScript | 5 passed; production UI 4 assets, 39,967 bytes, unchanged 90,000-byte cap |
| Actual source browser | New busy refusal, all original seven records, exact downloads and mobile 390/320 checks passed; owner exit 0 |
| Regression sensitivity | The exact old silent-return guard failed the same browser regression with the actual misleading rerun message; corrected bytes restored |
| Local dirty native preflight | Safely extracted Windows portable application, actual compiled GUI, new refusal, seven retained records and second launch passed; normal exits 0/0 |
| Quality and security | Rust formatting, Clippy warnings denied, rustdoc warnings denied, Ruff, repository contract, actionlint and locked npm/pip/RustSec audits passed |

The initial restricted-shell attempts could not access loopback or actual Windows link fixtures;
those failures were preserved. The complete tests passed under a normal token without skips or
changed assertions. The native preflight explicitly reported `sourceDirty: true` and the existing
base SHA; it is an implementation check, not evidence of a clean release source.

A separate clean committed-source package is required before review handoff. Its exact SHA,
archive digest and native receipt are retained with the source-review handoff rather than
self-referentially inserting a commit hash into this file. Hosted checks and independent installed
0.2.0-to-0.2.1 same-workspace acceptance remain pending until performed on their actual bytes.

## Limits

This remains an offline educational simulation with supplied fictional health assumptions and
public demonstration signing material. It does not flash equipment, execute uploaded images,
measure physical device health or provide real release-signing security. Workspace schema and
engine algorithms are unchanged; no published old asset or normal user profile is migrated here.
