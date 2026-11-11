# Native release and recovery application

By Jason Stys. This is an offline educational application around the existing Rust agent,
transition, package and durable-store implementations. No image is executed or sent to equipment.

## Launch and workspace

Extract a reviewed complete portable package before launching the application. A source build uses
`python launcher.py` after compiling `fwlab` and the web assets. The owner window starts closed:
choosing a folder alone creates no workspace. **Open workspace** admits an empty folder or this
application's schema-1 profile, starts an ephemeral loopback listener, then opens its actual URL.
**Open browser** reopens the same owned service. **Help** explains controls and limits.

The default is the current OS user's application-data directory under
`JasonStysPortfolio/firmware-release-recovery-lab/profile`, independent of extraction or current
working directory. A selected workspace contains `profile.json`, `owner.lock` and
`workspace.sqlite3` (plus SQLite recovery files when present). It is not an account service.
Existing ancestor aliases, install-root locations, multi-link fixed files, unknown folders and
unsupported database schemas are refused before mutation. Concurrent hostile namespace changes
by the same OS user are outside this local admission contract.

Only one owner may use a workspace. A second instance refuses it rather than adopting a listener
or deleting a lock. Closing the browser leaves the owner running. Use **Exit** or **Quit application**;
closing stays pending until actual handlers and engine work finish and the lock can be released.
An error is reported as a failed close, never converted to success by a timer. Do not reset the
workspace to work around a busy or failed owner. Stop it normally, then copy the entire workspace
while closed for backup; preserve exported files separately.

## Edit a lifecycle rehearsal

1. Set a title and choose lifecycle. Edit the JSON device list: each device has an ID, hardware,
   minimum and initial versions, initial inert image hex and an assumed `confirm` or `exhaust` outcome.
2. Build a demonstration package using version, release ID, compatible hardware, signed trial ceiling
   and image hex. **Image file** preserves actual bytes, including leading zero and bytes above 127.
   Alternatively import supported JSON containing `manifest` and `image_hex`; extra unsigned fields
   are rejected. The public demonstration key provides repeatability, not real signing security.
3. Append or directly edit ordered steps. Actions are stage, activate, boot, confirm and fail.
   Activation supplies a slot and attempt budget; failure includes a reason. Any applicable step
   can select a named metadata-write interruption. Device labels never choose filesystem paths.
4. Run and inspect initial, per-step before/after and final snapshots. The first rejection or
   interruption stops later steps; both the reason and unattempted count remain explicit.

A new healthy custom device at 1.0.0, followed by stage, activate B with one attempt, boot and
confirm, reaches active/confirmed B at generation 4. The same sequence with fail after the final
attempt recovers confirmed A at generation 4. A signed package with changed image bytes is blocked
at generation 0 and leaves the other three planned steps unattempted. These are executable test
oracles, not asserted real-device outcomes.

The request is closed structured JSON, at most 256 KiB, with1–64 devices,1–64 steps and inert image
payloads of1–65,536 bytes. Unknown fields, nonfinite numbers, duplicate HTTP JSON keys, excessive
nesting and malformed framing fail before a run is saved. File imports are parsed as JSON, then
validated semantically; the input hash describes canonical submitted protocol bytes rather than
the original file's whitespace. Binary image import is separate from JSON documentation import.

If an evidence file finishes loading while another rehearsal is still running, version 0.2.1
reports that the loaded input has not been run. Wait for completion, then choose **Run** explicitly.
The active rehearsal retains its actual saved evidence; an imported result is never treated as
fresh engine output. This corrects a misleading success message in the unpublished 0.2.0 candidate.

## Review fleet cohorts and interruption campaigns

Fleet review uses custom devices, the same release and a cohort size of1–16. It evaluates the
original signed-package policy and ordered cohorts with explicitly supplied health assumptions.
All compatibility rows remain visible; the first blocked or exhausted cohort prevents later
cohorts being rehearsed. The adapter compares complete device state before and after review.
This is read-only simulation, not deployment or health measurement. The original preflight report
contains temporary physical paths in its plan fingerprint, so that nested fingerprint is not a
portable rerun identifier. The outer input SHA-256 binds the exact submitted structured request.

Desktop campaigns accept1–5 iterations, or12–60 original fault scenarios. Each iteration covers six
metadata boundaries during stage and activation. The original CLI/CI standard remains100 iterations
and 1,200 scenarios. Actual local elapsed time is reported without a cross-machine performance claim.

## Save, find and exchange evidence

Every completed engine run stores its title, creation time, kind, honest outcome, exact canonical
input, report, Rust source commit and binary digest. A blocked rehearsal is saved as blocked; an
invalid request or failed/malformed engine process is not saved as a successful run. History is
limited to1,000 records and100 MiB and refuses a full workspace rather than silently pruning it.
Search is literal title text with an optional kind filter,25 rows per page. Select a row to view
its complete evidence. Export the input for another run, the actual signed demonstration package
when present, or the full evidence JSON. An imported evidence report supplies input only: the
application executes it again and ignores supplied result claims. Deleting a selected record is
explicit and does not change already exported files.

## Native provenance and test boundaries

`RELEASE.json` binds product/version, exact source, patched Python identity, Rust executable digest
and the exact four UI assets. Runtime admission refuses mismatched assets or an older Python.
Builds require a clean checkout; the explicit local dirty-build option is forbidden in CI and is
not a release claim. Separate manifests retain actual Rust standard terms and the native-target
Cargo graph's checksum-bound license files. The build collects and verifies them again after safe
extraction. ZIP is used on Windows; tar.gz preserves POSIX modes and internal links on other OSes.

Automated native acceptance uses the actual extracted executable with no source fallback, a fresh
temporary workspace and clean loader environment. It drives real browser edits/imports/reviews/
downloads, tests refusals, quits normally and restarts to verify history. `--no-window --no-browser`
is an explicit test mode; actual Tk source tests separately exercise owner controls and minimum
window size. These are portable launch/extraction checks, not signed-installer transactions,
clean-machine certification or proof of a user's default-browser configuration. See the dated
[validation report](reports/native-application-2026-11-11.md) for observed local versus pending hosted results.
