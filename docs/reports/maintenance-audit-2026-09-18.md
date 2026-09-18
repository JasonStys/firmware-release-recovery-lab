# Maintenance audit — 2026-09-18

## Result

The validated source baseline was `59211f4`. Hosted [CI](https://github.com/JasonStys/firmware-release-recovery-lab/actions/runs/35387023286) and the [RustSec audit](https://github.com/JasonStys/firmware-release-recovery-lab/actions/runs/35387023330) passed.

## Corrective work

- Ed25519, SHA-2, and the pinned Rust cache action were reviewed and merged.
- The combined cryptography lockfile was regenerated after the two dependency branches conflicted.
- Format, clippy, unit/property tests, documentation, 1,200 interruption scenarios, and RustSec all passed with the final lockfile.
- No open pull request or non-default maintenance branch remained when this report was prepared.

Historical failed branch runs remain visible for traceability and are superseded by the successful default-branch runs above.
