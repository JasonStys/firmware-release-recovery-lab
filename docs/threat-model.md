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
| Cross-origin local API calls or a forged listener | Prebound loopback socket, exact authority/Origin and per-instance capability | Actual HTTP negative and native restart tests |
| Unsafe private-directory initialization | Existing-ancestor/reparse/program-root admission; ordinary single-link fixed members and opened identity | Actual junction/hardlink/frozen-root sentinel tests |
| Imported report presented as measured evidence | Discard supplied report and rerun its closed structured input through fixed Rust executable | Actual forged-report browser import oracle |
| Malformed/unbounded input or child response | Explicit body/nesting/device/image/step/output/deadline limits; refusal before saving | Parser/framing/engine negatives and independent domain checks |
| Workspace released while work continues | Actual handler completion and owned child shutdown before lock release | Held-request/repeated-close/second-owner tests |
| Mismatched native resources or omitted notices | Exact source/runtime/engine/UI digests plus actual Rust/Cargo/runtime notice inventories | Safe archive extraction and full compiled consumer |

## Not addressed

- Confidentiality, encrypted transport, key provisioning, or key rotation
- Compromised signing infrastructure or stolen production keys
- Physical access, fault injection against silicon, side channels, or rollback fuses
- Filesystem adversaries, privileged local users, or malicious kernels
- Production secure/measured boot or hardware root of trust
- Time-based certificate validation and revocation

The embedded signing seed is public by design. Substituting a private key does not transform
this simulator into a secure updater; the omitted system controls remain essential.


## Code scanning and its limits

[CodeQL](codeql-analysis.md) now has explicit supported-language lanes and immutable Actions pins. It complements dependency advisories and independent runtime tests; a green workflow is not a zero-findings assertion. Review actual main-branch alerts and analysis source/categories, and keep403/404/no-analysis states distinct. No blanket query/path exclusions or alert suppression is introduced. CI scanning does not authorize real-device access, production signing material, external services or an expanded application trust boundary.
