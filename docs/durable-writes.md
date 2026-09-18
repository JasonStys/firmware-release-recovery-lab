# Durable-write model

## Commit sequence

Each metadata commit serializes a complete state value and executes these named boundaries:

1. `before_temp_create`
2. create/truncate `state.pending.json`, write all bytes, and call `sync_all`
3. `after_temp_write`
4. `after_temp_sync`
5. replace `state.backup.json` with the prior `state.json`, when present
6. `after_backup_rename`
7. replace `state.json` with the synchronized temporary file
8. `after_primary_rename`
9. synchronize the containing directory on Unix
10. `after_directory_sync`

The campaign interrupts both stage and activation commits at all six injectable boundaries.
On restart, the loader parses primary and backup, validates invariants, then selects the
highest generation. A temporary file is never considered authoritative.

## Why a full-state record

A small, complete record avoids partial field updates that can express impossible
combinations. JSON is chosen for inspectability in this simulator, not for production flash
wear, boot-time, or corruption characteristics.

## Platform note

Rust exposes file synchronization directly. Directory synchronization is used on Unix; the
portable Windows standard-library path does not offer the same directory-handle operation in
this implementation. Therefore the campaign demonstrates application ordering, not a claim
about every filesystem, controller cache, or storage device.

## Deliberate simplifications

- Slot image replacement has synchronized temporary files but its boundaries are not modeled
  at block-device granularity.
- The simulator does not model torn sectors, NAND erase blocks, journal replay, wear leveling,
  or independent bootloader metadata.
- No durability guarantee can be inferred for a real target without platform-specific tests.

