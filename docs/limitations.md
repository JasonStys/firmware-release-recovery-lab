# Known limitations

- This is an educational filesystem simulator, not a bootloader, updater, or flashing tool.
- The fixed signing seed is public and provides reproducibility, not secrecy.
- Canonical JSON depends on the declared Rust struct field order and schema version; a
  production format needs a formally specified canonicalization standard.
- Slot payload interruption points are coarser than metadata commit points.
- Windows directory synchronization is not modeled with platform-specific handle APIs.
- Concurrent writers are outside scope; the CLI assumes one operator process per lab root.
- Audit history is bounded to 128 entries and is not an append-only security log.
- No configuration/data migration accompanies firmware versions.
- No network download, resume, bandwidth limit, or transport authentication is modeled.
- No real-time deadlines, watchdog hardware, protected counters, or secure elements exist.

These constraints are intentional. They keep the project small enough for transition and
recovery behavior to remain inspectable.

