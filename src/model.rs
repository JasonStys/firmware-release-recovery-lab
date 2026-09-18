//! Persisted domain types and recovery invariants.
//!
//! File map: `Version` models ordered semantic versions; `BootMetadata` owns slot state;
//! `validate_invariants` protects the last-known-good image. Exact locations are indexed
//! in `docs/code-index.md`.

use std::{collections::BTreeMap, fmt, str::FromStr};

use serde::{Deserialize, Serialize};
use thiserror::Error;

/// Errors produced by validation, persistence, package verification, and injected crashes.
#[derive(Debug, Error)]
pub enum LabError {
    /// A caller supplied a value that violates a domain rule.
    #[error("validation failed: {0}")]
    Validation(String),
    /// Persisted or packaged JSON could not be decoded.
    #[error("serialization failed: {0}")]
    Serialization(#[from] serde_json::Error),
    /// A filesystem operation failed.
    #[error("I/O failed: {0}")]
    Io(#[from] std::io::Error),
    /// Cryptographic verification rejected a package.
    #[error("signature verification failed")]
    Signature,
    /// A digest did not match the signed manifest.
    #[error("image digest mismatch: expected {expected}, calculated {actual}")]
    DigestMismatch {
        /// Digest recorded in the manifest.
        expected: String,
        /// Digest calculated from the package image.
        actual: String,
    },
    /// A simulated power interruption occurred at a durable-write boundary.
    #[error("simulated interruption at {0}")]
    InjectedCrash(String),
    /// Neither the primary nor recovery metadata copy was valid.
    #[error("no valid persisted boot metadata was found")]
    NoRecoverableState,
}

/// A strictly ordered `major.minor.patch` firmware version.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub struct Version {
    /// Breaking release number.
    pub major: u16,
    /// Compatible feature release number.
    pub minor: u16,
    /// Compatible corrective release number.
    pub patch: u16,
}

impl Version {
    /// Constructs a version without parsing text.
    #[must_use]
    pub const fn new(major: u16, minor: u16, patch: u16) -> Self {
        Self {
            major,
            minor,
            patch,
        }
    }
}

impl fmt::Display for Version {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{}.{}.{}", self.major, self.minor, self.patch)
    }
}

impl FromStr for Version {
    type Err = LabError;

    /// Parses exactly three decimal components and rejects suffixes or missing values.
    fn from_str(value: &str) -> Result<Self, Self::Err> {
        let components = value
            .split('.')
            .map(|part| {
                part.parse::<u16>().map_err(|_| {
                    LabError::Validation(format!("invalid version component in '{value}'"))
                })
            })
            .collect::<Result<Vec<_>, _>>()?;

        match components.as_slice() {
            [major, minor, patch] => Ok(Self::new(*major, *minor, *patch)),
            _ => Err(LabError::Validation(format!(
                "version '{value}' must use major.minor.patch"
            ))),
        }
    }
}

/// Identifies one of the two simulated firmware slots.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum SlotId {
    /// Primary slot.
    A,
    /// Secondary slot.
    B,
}

impl SlotId {
    /// Returns the opposite A/B slot.
    #[must_use]
    pub const fn other(self) -> Self {
        match self {
            Self::A => Self::B,
            Self::B => Self::A,
        }
    }
}

impl fmt::Display for SlotId {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::A => "A",
            Self::B => "B",
        })
    }
}

impl FromStr for SlotId {
    type Err = LabError;

    /// Parses a case-insensitive A/B slot identifier.
    fn from_str(value: &str) -> Result<Self, Self::Err> {
        match value.to_ascii_uppercase().as_str() {
            "A" => Ok(Self::A),
            "B" => Ok(Self::B),
            _ => Err(LabError::Validation(format!("unknown slot '{value}'"))),
        }
    }
}

/// Persistent lifecycle phase displayed by the audit CLI.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LifecyclePhase {
    /// Only the confirmed image is selected.
    Stable,
    /// A verified image is present in the inactive slot.
    Staged,
    /// A new image is selected and waiting for bounded health confirmation.
    AwaitingHealth,
    /// A failed candidate was replaced by the previous confirmed image.
    RolledBack,
}

/// Device attributes used for pre-activation compatibility and anti-downgrade checks.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DeviceProfile {
    /// Synthetic hardware family identifier.
    pub hardware_id: String,
    /// Lowest release permitted by local policy.
    pub minimum_version: Version,
}

/// Verified image metadata stored independently from the package contents.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SlotRecord {
    /// Release version in this slot.
    pub version: Version,
    /// SHA-256 image digest.
    pub image_sha256: String,
    /// True only after size, hash, signature, and compatibility checks pass.
    pub verified: bool,
}

/// Deterministic audit entry persisted in the same transaction as lifecycle state.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AuditEvent {
    /// Monotonic event number.
    pub sequence: u64,
    /// Stable machine-readable action label.
    pub action: String,
    /// Human-readable transition explanation.
    pub detail: String,
}

/// Durable A/B boot metadata and bounded audit history.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct BootMetadata {
    /// Monotonic committed-state generation.
    pub generation: u64,
    /// Slot selected for the next boot.
    pub active: SlotId,
    /// Last health-confirmed slot.
    pub confirmed: SlotId,
    /// Candidate slot awaiting health confirmation, when present.
    pub pending: Option<SlotId>,
    /// Boot attempts remaining for the pending image.
    pub attempts_remaining: u8,
    /// Current lifecycle phase.
    pub phase: LifecyclePhase,
    /// Known verified/unverified image metadata by slot.
    pub slots: BTreeMap<SlotId, SlotRecord>,
    /// Most recent audit events, capped by transition logic.
    pub audit: Vec<AuditEvent>,
}

impl BootMetadata {
    /// Creates initial metadata with a verified, confirmed slot A image.
    #[must_use]
    pub fn initial(version: Version, image_sha256: String) -> Self {
        let mut slots = BTreeMap::new();
        slots.insert(
            SlotId::A,
            SlotRecord {
                version,
                image_sha256,
                verified: true,
            },
        );
        Self {
            generation: 0,
            active: SlotId::A,
            confirmed: SlotId::A,
            pending: None,
            attempts_remaining: 0,
            phase: LifecyclePhase::Stable,
            slots,
            audit: vec![AuditEvent {
                sequence: 0,
                action: "initialize".into(),
                detail: format!("slot A confirmed at version {version}"),
            }],
        }
    }

    /// Returns the confirmed release version.
    pub fn confirmed_version(&self) -> Result<Version, LabError> {
        self.slots
            .get(&self.confirmed)
            .map(|record| record.version)
            .ok_or_else(|| LabError::Validation("confirmed slot has no image record".into()))
    }

    /// Enforces safety invariants after every transition and recovered load.
    pub fn validate_invariants(&self) -> Result<(), LabError> {
        let confirmed = self.slots.get(&self.confirmed).ok_or_else(|| {
            LabError::Validation("confirmed slot must have an image record".into())
        })?;
        if !confirmed.verified {
            return Err(LabError::Validation(
                "confirmed slot must contain a verified image".into(),
            ));
        }
        let active = self
            .slots
            .get(&self.active)
            .ok_or_else(|| LabError::Validation("active slot must have an image record".into()))?;
        if !active.verified {
            return Err(LabError::Validation(
                "active slot must contain a verified image".into(),
            ));
        }
        if self.pending.is_none() && self.attempts_remaining != 0 {
            return Err(LabError::Validation(
                "stable state cannot retain candidate boot attempts".into(),
            ));
        }
        if self.pending.is_some() && self.phase != LifecyclePhase::AwaitingHealth {
            return Err(LabError::Validation(
                "pending slot requires awaiting_health phase".into(),
            ));
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn version_parsing_is_strict_and_ordered() {
        let older: Version = "1.9.9".parse().expect("valid version");
        let newer: Version = "2.0.0".parse().expect("valid version");
        assert!(older < newer);
        assert!("1.2".parse::<Version>().is_err());
        assert!("1.2.3-beta".parse::<Version>().is_err());
    }

    #[test]
    fn initial_state_preserves_a_verified_image() {
        let state = BootMetadata::initial(Version::new(1, 0, 0), "00".repeat(32));
        assert_eq!(state.confirmed, SlotId::A);
        state.validate_invariants().expect("valid initial state");
    }
}
