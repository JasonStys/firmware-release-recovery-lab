//! Signed release package creation, serialization, and verification.
//!
//! File map: `ManifestPayload` is the canonical signed contract; `SignedManifest`
//! carries the signature; `ReleasePackage` binds the manifest to image bytes.

use std::{fs, path::Path};

use ed25519_dalek::{SigningKey, VerifyingKey};
use serde::{Deserialize, Serialize};

use crate::{
    crypto::{sha256_hex, sign_bytes, verify_bytes},
    model::{DeviceProfile, LabError, Version},
};

/// Canonical fields covered by the Ed25519 signature.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ManifestPayload {
    /// Schema version for forward-compatible parsing.
    pub schema_version: u16,
    /// Human-readable release identifier.
    pub release_id: String,
    /// Firmware version used by monotonic-version policy.
    pub version: Version,
    /// Allowlisted synthetic hardware families.
    pub compatible_hardware: Vec<String>,
    /// Exact image byte length.
    pub image_size: u64,
    /// SHA-256 digest of the image bytes.
    pub image_sha256: String,
    /// Maximum boots permitted before automatic rollback.
    pub max_boot_attempts: u8,
}

impl ManifestPayload {
    /// Serializes fields in declared order to produce deterministic signed bytes.
    pub fn canonical_bytes(&self) -> Result<Vec<u8>, LabError> {
        Ok(serde_json::to_vec(self)?)
    }

    /// Checks schema, hardware, version, size, and bounded-attempt policy before staging.
    pub fn validate_policy(
        &self,
        device: &DeviceProfile,
        confirmed_version: Version,
    ) -> Result<(), LabError> {
        if self.schema_version != 1 {
            return Err(LabError::Validation(format!(
                "unsupported manifest schema {}",
                self.schema_version
            )));
        }
        if !self
            .compatible_hardware
            .iter()
            .any(|hardware| hardware == &device.hardware_id)
        {
            return Err(LabError::Validation(format!(
                "release is incompatible with hardware '{}'",
                device.hardware_id
            )));
        }
        if self.version < device.minimum_version || self.version < confirmed_version {
            return Err(LabError::Validation(format!(
                "release {} violates monotonic version policy (confirmed {}, minimum {})",
                self.version, confirmed_version, device.minimum_version
            )));
        }
        if self.image_size == 0 {
            return Err(LabError::Validation(
                "empty firmware images are rejected".into(),
            ));
        }
        if !(1..=10).contains(&self.max_boot_attempts) {
            return Err(LabError::Validation(
                "max_boot_attempts must be between 1 and 10".into(),
            ));
        }
        Ok(())
    }
}

/// A manifest payload plus its detached hexadecimal Ed25519 signature.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SignedManifest {
    /// Signed release fields.
    pub payload: ManifestPayload,
    /// Detached signature over `payload.canonical_bytes()`.
    pub signature_ed25519: String,
}

impl SignedManifest {
    /// Creates a signed manifest for image bytes using a supplied key.
    pub fn create(
        release_id: String,
        version: Version,
        compatible_hardware: Vec<String>,
        max_boot_attempts: u8,
        image: &[u8],
        signing_key: &SigningKey,
    ) -> Result<Self, LabError> {
        let payload = ManifestPayload {
            schema_version: 1,
            release_id,
            version,
            compatible_hardware,
            image_size: image.len() as u64,
            image_sha256: sha256_hex(image),
            max_boot_attempts,
        };
        let signature_ed25519 = sign_bytes(&payload.canonical_bytes()?, signing_key);
        Ok(Self {
            payload,
            signature_ed25519,
        })
    }
}

/// In-memory package containing signed metadata and the exact image bytes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReleasePackage {
    /// Signed manifest.
    pub manifest: SignedManifest,
    /// Firmware image bytes.
    pub image: Vec<u8>,
}

impl ReleasePackage {
    /// Loads `manifest.json` and `image.bin` from a package directory.
    pub fn load(directory: &Path) -> Result<Self, LabError> {
        let manifest = serde_json::from_slice(&fs::read(directory.join("manifest.json"))?)?;
        let image = fs::read(directory.join("image.bin"))?;
        Ok(Self { manifest, image })
    }

    /// Writes a deterministic package directory, replacing only its two owned files.
    pub fn write(&self, directory: &Path) -> Result<(), LabError> {
        fs::create_dir_all(directory)?;
        let manifest = serde_json::to_vec_pretty(&self.manifest)?;
        fs::write(directory.join("manifest.json"), manifest)?;
        fs::write(directory.join("image.bin"), &self.image)?;
        Ok(())
    }

    /// Verifies signature, digest, size, hardware, and monotonic-version policy.
    pub fn verify(
        &self,
        verifying_key: &VerifyingKey,
        device: &DeviceProfile,
        confirmed_version: Version,
    ) -> Result<(), LabError> {
        let payload = &self.manifest.payload;
        verify_bytes(
            &payload.canonical_bytes()?,
            &self.manifest.signature_ed25519,
            verifying_key,
        )?;
        payload.validate_policy(device, confirmed_version)?;

        let actual_hash = sha256_hex(&self.image);
        if actual_hash != payload.image_sha256 {
            return Err(LabError::DigestMismatch {
                expected: payload.image_sha256.clone(),
                actual: actual_hash,
            });
        }
        if self.image.len() as u64 != payload.image_size {
            return Err(LabError::Validation(format!(
                "image size mismatch: expected {}, read {}",
                payload.image_size,
                self.image.len()
            )));
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use crate::crypto::demo_signing_key;

    use super::*;

    fn device() -> DeviceProfile {
        DeviceProfile {
            hardware_id: "edge-controller-v1".into(),
            minimum_version: Version::new(1, 0, 0),
        }
    }

    #[test]
    fn package_detects_image_tampering() {
        let key = demo_signing_key();
        let manifest = SignedManifest::create(
            "release-2".into(),
            Version::new(2, 0, 0),
            vec![device().hardware_id],
            3,
            b"image-v2",
            &key,
        )
        .expect("manifest");
        let package = ReleasePackage {
            manifest,
            image: b"tampered".to_vec(),
        };
        assert!(matches!(
            package.verify(&key.verifying_key(), &device(), Version::new(1, 0, 0)),
            Err(LabError::DigestMismatch { .. })
        ));
    }

    #[test]
    fn policy_rejects_wrong_hardware_before_staging() {
        let key = demo_signing_key();
        let manifest = SignedManifest::create(
            "release-2".into(),
            Version::new(2, 0, 0),
            vec!["different-device".into()],
            3,
            b"image-v2",
            &key,
        )
        .expect("manifest");
        let package = ReleasePackage {
            manifest,
            image: b"image-v2".to_vec(),
        };
        assert!(
            package
                .verify(&key.verifying_key(), &device(), Version::new(1, 0, 0))
                .is_err()
        );
    }
}
