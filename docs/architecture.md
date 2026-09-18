# Architecture

## Context

The lab explores one question: after an update is interrupted or a candidate image fails,
what exact state does the system recover and why? The implementation separates transition
policy from persistence so each can be tested independently.

## Components

| Component | Responsibility | Boundary |
| --- | --- | --- |
| CLI | Parse explicit operator intent and render human/JSON results | No networking or hardware access |
| Update agent | Order verify → write inactive slot → transition → commit | Does not decide transition validity itself |
| Package verifier | Authenticate canonical manifest and bind it to image bytes | Demo public key only |
| Transition engine | Enforce lifecycle preconditions and invariants | Pure functions; no I/O or clocks |
| Store | Own internal paths, slot files, primary/backup metadata | Local directory only |
| Fault injector | Interrupt named metadata commit boundaries once | Simulated process failure, not physical power analysis |
| Campaign runner | Restart after each interruption and classify recovered state | Temporary directories are deleted automatically |

## Data flow

1. The agent loads the newest valid metadata copy.
2. The verifier checks signature, image hash/size, schema, hardware, version floor, and attempt
   bounds before any state refers to the package.
3. Image and manifest are synchronized into the inactive slot.
4. A pure transition creates the next complete metadata value.
5. The store writes and synchronizes a temporary file, preserves the previous primary, then
   replaces the primary and synchronizes the directory on Unix.
6. After restart, primary and backup are parsed, invariant-checked, and compared by generation.

## Trust boundaries

Package directories and their contents are untrusted. The selected lab root is trusted
operator configuration. Internal filenames and slot names are not derived from package input.
The fixed demo verification key is trusted only for repeatable tests.

## Deployment model

This is a local command-line simulator. A release build produces one `fwlab` executable plus
its documentation and test evidence. It has no daemon, database, listening socket, or cloud
deployment.

## Failure modes

| Failure | Expected behavior |
| --- | --- |
| Invalid signature/hash/size | Reject before slot metadata is staged |
| Wrong hardware or downgrade | Reject before activation |
| Interruption before primary replacement | Recover prior primary or backup |
| Interruption after primary replacement | Recover new primary, with old backup still valid |
| Candidate health failure with attempts left | Retain candidate and audit the failure |
| Candidate health failure at zero attempts | Select confirmed slot and persist rollback |
| Both metadata copies invalid | Fail closed with `NoRecoverableState` |

## Decisions

- [ADR-0001: Rust for the state engine](adr/0001-rust-state-engine.md)
- [ADR-0002: Recoverable JSON metadata](adr/0002-recoverable-json-metadata.md)

