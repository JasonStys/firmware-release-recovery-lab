//! Firmware release and recovery simulation library.
//!
//! File map (exact line locations are generated in `docs/code-index.md`):
//! - `agent`: orchestration and restart recovery.
//! - `crypto`: SHA-256 and Ed25519 demo signing.
//! - `fault`: deterministic interruption injection.
//! - `model`: persisted domain types and invariants.
//! - `package`: package creation, loading, and verification.
//! - `store`: bounded-path, atomic filesystem persistence.
//! - `transition`: pure A/B lifecycle state transitions.

pub mod agent;
pub mod crypto;
pub mod fault;
pub mod model;
pub mod package;
pub mod store;
pub mod transition;

pub use agent::{CampaignReport, UpdateAgent, run_fault_campaign};
pub use fault::{FaultInjector, FaultPoint, NoFault, SingleFault};
pub use model::{BootMetadata, DeviceProfile, LabError, LifecyclePhase, SlotId, Version};
pub use package::{ReleasePackage, SignedManifest};
