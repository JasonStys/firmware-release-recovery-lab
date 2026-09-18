//! Cryptographic helpers for package integrity and authenticity.
//!
//! File map: `sha256_hex` hashes image bytes; `sign_bytes` and `verify_bytes`
//! use Ed25519. Demo key material is intentionally isolated in `demo_signing_key`.

use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use sha2::{Digest, Sha256};

use crate::model::LabError;

/// Computes a lowercase SHA-256 digest for image integrity checks.
#[must_use]
pub fn sha256_hex(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}

/// Signs canonical manifest bytes and returns a lowercase hexadecimal signature.
#[must_use]
pub fn sign_bytes(bytes: &[u8], signing_key: &SigningKey) -> String {
    hex::encode(signing_key.sign(bytes).to_bytes())
}

/// Verifies a hexadecimal Ed25519 signature over canonical manifest bytes.
pub fn verify_bytes(
    bytes: &[u8],
    signature_hex: &str,
    verifying_key: &VerifyingKey,
) -> Result<(), LabError> {
    let signature_bytes = hex::decode(signature_hex).map_err(|_| LabError::Signature)?;
    let signature = Signature::from_slice(&signature_bytes).map_err(|_| LabError::Signature)?;
    verifying_key
        .verify(bytes, &signature)
        .map_err(|_| LabError::Signature)
}

/// Returns the fixed signing key used only by examples and tests.
///
/// This key is public, offers no production security, and exists solely so demonstrations
/// are reproducible. Real signing keys must live outside source control and build agents.
#[must_use]
pub fn demo_signing_key() -> SigningKey {
    SigningKey::from_bytes(&[
        0x46, 0x57, 0x4c, 0x41, 0x42, 0x2d, 0x44, 0x45, 0x4d, 0x4f, 0x2d, 0x4b, 0x45, 0x59, 0x2d,
        0x4e, 0x4f, 0x54, 0x2d, 0x53, 0x45, 0x43, 0x52, 0x45, 0x54, 0x2d, 0x30, 0x30, 0x30, 0x30,
        0x30, 0x31,
    ])
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn signature_rejects_modified_payload() {
        let key = demo_signing_key();
        let signature = sign_bytes(b"manifest", &key);
        verify_bytes(b"manifest", &signature, &key.verifying_key()).expect("valid signature");
        assert!(verify_bytes(b"modified", &signature, &key.verifying_key()).is_err());
    }
}
