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


## Source security analysis

The supported Rust, Python, TypeScript/JavaScript and Actions [CodeQL lanes](docs/codeql-analysis.md) use security-extended queries and immutable action pins. A completed job, an available exact-source analysis and its reported findings are separate evidence. Unavailable analysis is not zero clearance, and no automated finding is dismissed or suppressed by this setup. RustSec and runtime/fault tests retain their existing scope.

## Local application boundary

The native owner admits one identified OS-user workspace, refusing existing ancestor aliases,
program roots and linked fixed profile/SQLite files before writes. It checks opened file identity;
it does not defend against a malicious concurrent OS-owner namespace mutation or encrypt data from
that owner. Do not put real signing keys or sensitive device images into this educational tool.
The service binds a preowned ephemeral loopback socket and requires its exact authority,
per-instance capability and Origin on private API requests. Static local UI resources remain
public to the local user; no capability is stored in history or browser storage. There is no CORS,
remote transport, telemetry, arbitrary child command or automatic firmware download.

Inputs have explicit JSON/body/device/image/step budgets and the child is the fixed source-bound
Rust executable with a finite deadline. Saved outcomes come from completed validated engine
reports; imported report claims are rerun. Normal Exit retains ownership and the lock until real
work has drained. Packaging tests never justify disabling these boundaries after a failure.
