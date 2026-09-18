# ADR-0001: Use Rust for the state engine

- Status: accepted
- Date: 2026-09-17

## Context

The project needs explicit states, recoverable errors, binary hashing/signing, filesystem I/O,
and property tests. Invalid combinations should be difficult to express and warnings should be
enforceable in CI.

## Options

1. Rust with enums, `Result`, Cargo tests, and Clippy.
2. C++ with variants, RAII, CMake, and external test/crypto packages.
3. Python with dataclasses, exceptions, and rapid property-test iteration.

## Decision

Use Rust 2024 edition with a pinned 1.90.0 toolchain. Model slots and phases as enums, versions
as an ordered value type, and recoverable failures as one typed error taxonomy. Forbid unsafe
code and deny warnings in CI.

## Consequences

The compiler eliminates several ownership and exhaustiveness errors before tests run. Cargo
provides a cohesive build/test/documentation workflow. Contributors need a Rust toolchain, and
filesystem durability still requires platform-specific reasoning beyond memory safety.

## Revisit trigger

Revisit if the model must run in a constrained target without the Rust standard library or
interoperate directly with an existing C/C++ boot environment.

