# Threat model

## Assets

- Last health-confirmed image availability
- Authenticity and integrity of candidate metadata and bytes
- Monotonic release policy
- Explainable recovery state and audit history

## Actors and entry points

The operator supplies a package directory, lab root, hardware identifier, version floor,
attempt budget, and health result. Package files may be malformed or malicious. The local
user and operating system are trusted for this educational model.

## Addressed threats

| Threat | Control | Evidence |
| --- | --- | --- |
| Modified manifest | Ed25519 verification over canonical payload | Signature unit test |
| Modified/truncated image | SHA-256 plus exact byte length | Tamper unit test |
| Wrong hardware | Pre-stage allowlist check | Policy unit test |
| Downgrade | Confirmed-version and local minimum floor | Transition/policy tests |
| Unbounded failed boots | Attempt count persisted before boot selection | Rollback unit/property tests |
| Interrupted metadata commit | Synchronized temporary file and valid prior copy | Boundary campaign |
| Invalid recovered state | Parse plus invariant validation before selection | Store tests |
| Workflow dependency drift | Immutable action SHAs and Dependabot proposals | Workflow review |

## Not addressed

- Confidentiality, encrypted transport, key provisioning, or key rotation
- Compromised signing infrastructure or stolen production keys
- Physical access, fault injection against silicon, side channels, or rollback fuses
- Filesystem adversaries, privileged local users, or malicious kernels
- Production secure/measured boot or hardware root of trust
- Time-based certificate validation and revocation

The embedded signing seed is public by design. Substituting a private key does not transform
this simulator into a secure updater; the omitted system controls remain essential.

