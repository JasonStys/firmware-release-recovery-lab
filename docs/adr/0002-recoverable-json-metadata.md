# ADR-0002: Use complete recoverable JSON metadata records

- Status: accepted for simulator
- Date: 2026-09-17

## Context

The lab must make interrupted state changes visible and easy to inspect. Updating separate
fields in place can create combinations no transition emitted.

## Options

1. Complete JSON state with synchronized temporary file, prior copy, and generation selection.
2. Append-only journal with replay and compaction.
3. SQLite transaction.
4. Fixed binary dual-copy boot metadata.

## Decision

Serialize the complete `BootMetadata` value, synchronize it, preserve the prior primary, then
replace the primary. On load, parse and invariant-check both authoritative copies and choose the
highest valid generation.

## Consequences

Reviewers can inspect and corrupt fixtures easily, and each state is internally complete. The
format is verbose, flash-unaware, and not suitable as a production boot metadata design.

## Revisit trigger

Revisit for concurrency, large audit history, constrained storage, real flash media, or a
bootloader that requires a fixed binary ABI.
