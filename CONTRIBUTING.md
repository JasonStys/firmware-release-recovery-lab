# Contributing

## Development environment

Install Git, Python 3.11 or newer, and Rust through rustup. The repository pins Rust 1.90.0
with `rustfmt` and Clippy components. Fork or branch from `main`; never commit real firmware,
device credentials, signing keys, customer data, or proprietary specifications.

## Change workflow

1. Open an issue describing the invariant, failure mode, or usability problem.
2. Add or update a test that demonstrates the expected behavior.
3. Keep transition decisions pure; isolate filesystem behavior in `store.rs`.
4. Document new states, fault points, trust assumptions, and operational consequences.
5. Run `bash scripts/validate.sh` before opening a pull request.

## Style

- Prefer domain types and exhaustive matches over string flags.
- Return typed errors for recoverable failures; do not panic on operator/package input.
- Document public items and begin every code file with a purpose/content/variable header.
- Keep state changes deterministic and independent of wall clocks or global state.
- Explain complexity when a collection or algorithm is not obviously bounded.
- Avoid `unsafe`; the crate forbids it.

## Tests

Each transition change needs table-driven or property coverage. Persistence changes need an
interruption test before and after the affected durable boundary. Security changes need a
negative test (tampered, malformed, incompatible, or unauthorized input).

## Commits and pull requests

Use focused imperative commits such as `test: cover activation interruption`. Pull requests
must describe motivation, safety impact, evidence, limitations, and documentation changes.
All CI and security checks must pass before merge.

## Releases

Update `CHANGELOG.md`, run the full 1,200-scenario campaign, review the dependency audit, and
build from a clean checkout with `--locked`. Tag releases using semantic versioning.

