# Native rehearsal studio architecture

Author: Jason Stys. Status: accepted for implementation; native delivery requires actual source,
packaging and user-workflow acceptance. Date: 11 November 2026.

## Context and decision

The repository's actual Rust engine already verifies synthetic signed packages, rehearses A/B trial
boots, persists recoverable metadata and reviews read-only fleet cohorts. Its CLI is not a complete
desktop interface. Add a genuine editable rehearsal studio with a small native owner and browser
GUI. The original Rust agent, transition, store, signature and fleet-review implementations remain
the only domain engines. Python owns the fixed process, admitted local history and loopback lifetime;
TypeScript/HTML/CSS owns editing, timeline/state comparison, help and file interchange.

A user edits a reproducible plan: fictional devices and their explicit policies/initial images,
a demo-signed or imported signed package, ordered stage/activate/boot/confirm/fail operations and
optional named durable-write interruptions. Each execution uses a new owned synthetic lab and the
real durable Rust adapter. Results retain exact inputs, package/signature evidence, before/after
states, recovery outcomes and rejected transitions. A separate read-only cohort preflight uses the
same explicit device plan and records assumed health outcomes. Existing interruption campaigns
remain available through bounded native settings and the original general CLI.

The UI provides actual custom inputs and step controls, not a collection of fixed demonstrations.
Prepared examples are optional inputs inside this application. Saving a plan/result allows later
inspection and deterministic semantic replay; it does not claim to manage a persistent real fleet.
Run-specific timing and physical-root fingerprints remain distinguishable from stable logical input
identity. Imported reports are never trusted as fresh verification; their inputs are rerun.

## Alternatives and consequences

| Option | Benefit | Cost |
| --- | --- | --- |
| Preserve the Rust engines with a bounded native owner/browser editor | Retains tested domain/durability semantics and SDK-free installed use | Needs explicit lifecycle, private history and native resource/provenance acceptance |
| Reimplement lifecycle transitions in the UI/Python | Simpler display wiring | Creates a second unverified domain engine and risks diverging from the original project |
| Expose original CLI paths through a generic terminal GUI | Minimal new code | Does not give meaningful plan/state/recovery workflows and expands arbitrary filesystem input |

Choose the first option. The fixed native protocol accepts bounded structured data, not executables,
shell commands, arbitrary filesystem roots, network addresses or hardware endpoints. Source-bound
Rust/Python/UI resources must verify before the private workspace opens. The workspace retains
searchable explicit evidence with record/byte limits and no silent eviction; Exit retains ownership
until work really finishes.

## Safety and validation

The signing seed is intentionally public and must never protect a real release. Imported packages
are reviewed under the declared educational trust policy, not advertised as production secure boot.
Images are inert bytes only: nothing flashes, boots a real image, controls hardware or downloads a
device update. Simulated health signals and storage interruptions remain explicit assumptions, not
real measured device health or physical power-loss proof.

Independent tests require exact successful confirmation and exhausted-budget rollback states,
version/hardware/signature/digest rejection, preservation on rejected transitions, recovery on both
sides of a named commit boundary and cohort-stop semantics. Real native GUI journeys must edit a
plan, add/remove operations, inspect/reject state, import/export, save/search/reopen history and
normally close the actual extracted executable. Existing Rust/property/recovery/RustSec/CodeQL
gates remain; no source fallback, unreviewed exclusion or installer-transaction claim is allowed.
