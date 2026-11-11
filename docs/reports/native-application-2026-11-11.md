# Native application implementation validation — 2026-11-11

By Jason Stys. This report records local source and first compiled-candidate observations.
Hosted CI, processed CodeQL, release publication and independent installation are separate gates.
The version 0.2.0 application candidate remains an offline educational simulation.

## What changed and why

The existing Rust signed-package, A/B state machine, read-only fleet review and metadata fault
campaign now have a genuine editable application. Users can supply supported custom devices,
image bytes and packages; reorder lifecycle operations and named interruptions; inspect actual
before/after decisions; save, find and export evidence; and reopen their workspace. This makes
the original reliability work usable without replacing it with a second implementation or a
fixed demonstration executable. The native owner keeps the listener and workspace lock until
owned work has finished, including a held request during repeated close attempts.

Actual additional defects caught during implementation:

- Serde's internally tagged unit action variants did not enforce the expected unknown-field
  refusal. Structured empty variants now reject unsigned host-command fields; original package
  structs also reject undeclared fields rather than silently dropping imported metadata.
- Python 3.14 accepted JSON nesting deeper than a previous implicit recursion assumption.
  Admission now uses an explicit iterative maximum depth 64; the actual HTTP regression uses 400.
- The unchanged RustSec deny-warnings gate detected `RUSTSEC-2026-0486` in locked `rustix 1.1.5`.
  Only that compatible lock entry was moved to patched 1.1.6. No ignore was added; affected xattr
  reachability in the app was not asserted solely from the advisory's presence.
- Opening-purpose labels copied from prior packaging infrastructure contained mojibake separators.
  New packaging labels use ASCII; actual verbatim upstream license bytes are preserved.

## Observed local gates

| Gate | Observation and denominator |
| --- | --- |
| Rust unit/integration/property/domain |30 tests:9 library,1 persisted lifecycle,2 property,8 original preflight and10 new studio cases |
| Original recovery campaign |1,200 scenarios,1,200 recovered/safety checks,400 prior-state and 800 forward recoveries; original oracle unchanged |
| Strict compiler tooling | rustfmt, all-target/all-feature Clippy with warnings denied, locked tests and private-item Rustdoc |
| Python application/source/package |161 parent tests plus13 actual Tcl notice cases in a fresh bounded child interpreter; no retries/skips |
| Whole application coverage |93.91% combined statement/branch over 646 statements and 208 branches; unchanged 90% floor, owner UI included |
| TypeScript/model/build |5 actual input/binary/UTF-8/closed-schema tests;4 production assets,39,296 bytes against90,000-byte cap after the mobile-wrap repair |
| Source browser |7 saved actual workflows, fresh source owner, real Chromium edits/imports/downloads and normal exit0 |
| First compiled Windows candidate | Actual extracted executable, the same7 browser/domain workflows, normal 0/0 and7 records after restart; explicitly dirty local candidate |
| Dependency review | Exact Python hash locks and npm lock installation/advisory gates; RustSec rerun after the narrow patched-lock update |
| Repository documentation | Original artifact/neutral-wording contracts retained, expanded authored-language headers, generated source file guide/index |

These are local denominators, not a claim that every supported OS has already passed. A source
run is labelled development and never used as native acceptance. The first compiled candidate's
`RELEASE.json` explicitly records its dirty-source status; it is not a release artifact. Final
clean-source package acceptance is mandatory in the three-OS desktop workflow before a checksum
is written. Exact accepted build identities belong to their own metadata/validation receipts.

The subsequent clean-source Windows build at
[`1db8c52628c1c4be6159e82aa96e8726001cbc08`](https://github.com/JasonStys/firmware-release-recovery-lab/tree/1db8c52628c1c4be6159e82aa96e8726001cbc08)
also passed the complete extracted executable consumer: seven actual saved rehearsals,
normal exits 0/0 and retained history after restart. Its ZIP SHA-256 was
`58c04e7ca42339bd58dcdec3926ce9a0b25c0d3d6dfa5a8f43ba79c1347efc17`.
This is a source-bound local portable-package observation, not a published release, independent
installation or a result from macOS/Linux. Later source/CI review retains its own exact revision.

The first hosted quality job then exposed a workflow tooling mismatch: it used Ubuntu's system
Python3.12 to AST-parse actual Python3.14 source, while all three native-source jobs used the
declared patched interpreter and passed. The quality job now explicitly installs Python3.14.10;
an independent negative test proves the indexer refuses an old parser before overwriting its
previous output. This preserves the source/index gate rather than excluding newer source.
The original failed run43047553027 remains evidence; the corrected head needs fresh hosted checks.

At corrected source `b5080df4d9d052f19dc5f09aa4d318739229e034`, all original CI/source/dependency
checks and Windows/macOS native consumers passed. Linux native run43049227199 failed in browser
OS-dependency setup before compiling or testing the application: APT repeatedly reported
`Temporary failure resolving 'archive.ubuntu.com'` and exited100. The earlier run43047553393
reported the same setup failure. These logs do not establish the DNS root cause or a product defect.
They explicitly showed all required Chromium runtime libraries, Xvfb and existing basic fonts
installed; the nine proposed additions were extra font/X-font packages.

The native job now downloads only the exact locked Chromium and runs an actual mandatory host
probe before the unchanged full compiled consumer. This reuses the reviewed source-bound approach
from [the image application's host probe](https://github.com/JasonStys/personal-image-model-studio/blob/6f0a2536dd6e6a9b481a3f74b31388dda74e976c/scripts/check_browser_host.mjs):
normal browser launch/page input must pass, a missing executable must fail, the installed version
must match the npm lock and `PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS` is refused. No host
validation bypass, browser flag, test assertion, native journey, Xvfb requirement, job deadline or
application timeout is relaxed. This does not claim coverage of optional writing-system font sets.

The subsequent Linux native consumer reached the real compiled app and caught horizontal overflow
at390px. A preserved clean Windows compiled build independently reproduced the defect at320px:
the document measured347px because the header's real40-character Rust source identity did not wrap
(333px text width). The selected evidence and history already wrapped their identifiers; the
header now does too. No overflow hiding or clipped identity is used. The original390px assertion
remains and the native consumer additionally checks320px, full source-identity presence and
recorded geometry. The Linux failure and original Windows diagnostic are retained rather than
being relabelled as passes; the fix needs fresh exact-head compiled acceptance.

## Independent user journeys and refusal oracles

The real browser enters a custom hardware ID and binary image containing 0,1,127,128,255. A healthy
stage/activate/boot/confirm sequence reaches confirmed B at generation 4; the exact downloaded
image SHA-256 is independently computed. The four recorded step generations are 1,2,3,4.
A changed signed image is blocked at generation 0 with the remaining 3 steps explicitly unattempted.
Unsigned imported manifest fields and an excessive campaign budget are HTTP 400 refusals and do
not create a record or replace the selected evidence.

An exhausted single trial returns to confirmed A at generation 4. Fleet review retains all 3 device
rows and stops at cohort 2 while full initial/final state is equal. A one-iteration original campaign
produces 12 scenarios with 4 stable and 8 forward recoveries. A named post-write metadata interruption
recovers generation 0 and records3 unattempted steps. Importing a report with forged result claims
reexecutes its input and yields the actual independently checked outcome and a new record ID.

Actual selected input/package/evidence downloads, literal `%_` history filtering, 390px layout,
keyboard focus, zero page errors, retained selected evidence on invalid input and second-launch
history are part of the consumer. Profile tests use real temporary files, held locks and actual
junction/hardlink cases rather than weakening normal admission. Engine negative tests cover real
nonzero/timeout boundaries and malformed response contracts; inert fake children exercise refusal
only, never substitute for accepted Rust results.

## Packaging and distribution review

The builder requires coherent 0.2.0 Cargo/Python/npm/UI versions and a final patched3.14 runtime
(minimum 3.14.10). A clean exact Git checkout is mandatory; the local dirty override is forbidden
in CI. It compiles the actual Rust engine and UI, binds their bytes and source, and refuses to
overwrite output. Windows ZIP and POSIX tar.gz are safely extracted with root/member/link/size
guards before executing the actual packaged app. No downloaded Actions archive is executed.

Actual pinned Rust 1.98.1 standard-library copyright and all 12 referenced license files are
retained and reverified after extraction. Target-resolved Cargo terms are bound to Cargo.lock
crate checksums and actual registry archive/source notice bytes, then matched to the collected
source manifest after extraction. The first Windows candidate collected 74 source packages and 146
notice files; this is a conservative native-target dependency graph, not a count of linked crates.
Python, Tcl/Tk and PyInstaller notices come from actual installed distributions/runtime resources.
There is no all-MIT or legal-certification claim.

CI retains all original Cargo/Clippy/Rustdoc/RustSec and 1,200-campaign gates, adds three-OS source
and actual extracted native acceptance, and adds the supported JavaScript/TypeScript CodeQL lane.
Action pins, read-only permissions, finite jobs and original coverage/asset caps remain. No
application binary or private profile is uploaded automatically; there is no release or install
permission in the packaging workflow.

## Remaining limits

- Public demo signing material, inert images and supplied health assumptions only; no secure boot,
  device flashing, real firmware delivery or physical power-loss guarantee.
- Single OS-user profile, no login roles or encryption from the PC owner; hostile concurrent
  namespace replacement by that owner is outside the admission contract.
- Automated native launches use explicit no-window/no-browser mode; real Tk source controls are
  tested separately. Default-browser integration and normal OS installer transactions are unclaimed.
- Imported JSON is validated structured data, not arbitrary document conversion or original file
  whitespace certification. Nested preflight plan fingerprints include temporary physical paths.
- An error-free scanner/job and zero known dependency advisories are distinct from proving absence
  of defects. Exact hosted source analyses and main checks must be reviewed before publication.
