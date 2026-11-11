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
- The native application is a single OS-user, single-owner workspace; it has no authentication
  roles, multiuser hosting or at-rest encryption. Protect exports with normal OS access controls.
- Lifecycle rehearsals initialize fresh temporary fictional devices. Saved history is evidence,
  not a connection to a persistent physical fleet. Health outcomes are supplied assumptions.
- Imported evidence is rerun from its structured input. Its original signature/report claims or
  file whitespace are not certified as a faithful representation of another system.
- Portable archives are unsigned application bundles, not OS installers. Automated source/native
  journeys do not establish default-browser opening, clean-machine installation or notarization.
- The native-target Cargo notice graph conservatively includes reachable build/test dependency
  terms; that inventory is not an assertion that each crate is linked into the final executable.

These constraints are intentional. They keep the project small enough for transition and
recovery behavior to remain inspectable.

