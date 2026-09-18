# Security policy

## Supported versions

Only the latest release on `main` receives security fixes while the project remains pre-1.0.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub's private vulnerability
reporting feature for this repository. Include the affected revision, reproduction steps,
impact, and any suggested mitigation. Expect acknowledgement within seven days.

## Secret handling

The signing seed in `crypto.rs` is deliberately public demo material. Never replace it with a
real private key or store credentials in this repository, examples, Actions variables,
artifacts, or issue content. Real signing should occur in an isolated service or hardware-backed
system outside a source checkout.

## Safe-use boundary

This project does not implement secure boot, production firmware delivery, device flashing, or
hardware access. Do not connect it to equipment or treat its filesystem behavior as evidence
for a specific target platform. Review [the threat model](docs/threat-model.md) and
[limitations](docs/limitations.md).

## Dependency response

The scheduled RustSec workflow checks `Cargo.lock`. A relevant advisory should be reproduced,
triaged for reachability and impact, fixed or mitigated, and documented in the changelog. CI
actions are pinned to immutable commits and updated through reviewed Dependabot proposals.

