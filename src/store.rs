//! Filesystem-backed slot and metadata persistence.
//!
//! File map: `LabStore` bounds all paths beneath one root; `commit_state` performs
//! synchronized temp-write and rename; `load_state` selects the newest valid copy.

use std::{
    fs::{self, OpenOptions},
    io::Write,
    path::{Path, PathBuf},
};

#[cfg(unix)]
use std::fs::File;

use crate::{
    fault::{FaultInjector, FaultPoint},
    model::{BootMetadata, LabError, SlotId},
    package::ReleasePackage,
};

const STATE_FILE: &str = "state.json";
const BACKUP_FILE: &str = "state.backup.json";
const TEMP_FILE: &str = "state.pending.json";

/// Owns the directory tree that represents simulated slots and boot metadata.
#[derive(Debug, Clone)]
pub struct LabStore {
    root: PathBuf,
}

impl LabStore {
    /// Creates a store handle. Files are not created until initialization or staging.
    #[must_use]
    pub fn new(root: impl Into<PathBuf>) -> Self {
        Self { root: root.into() }
    }

    /// Returns the simulator root for diagnostics and reports.
    #[must_use]
    pub fn root(&self) -> &Path {
        &self.root
    }

    /// Creates slot directories and persists initial boot metadata.
    pub fn initialize(
        &self,
        state: &BootMetadata,
        initial_image: &[u8],
        injector: &mut dyn FaultInjector,
    ) -> Result<(), LabError> {
        fs::create_dir_all(self.slot_dir(SlotId::A))?;
        fs::create_dir_all(self.slot_dir(SlotId::B))?;
        fs::write(self.slot_dir(SlotId::A).join("image.bin"), initial_image)?;
        self.commit_state(state, injector)
    }

    /// Writes a verified package into a target slot before state references it.
    pub fn write_slot(&self, slot: SlotId, package: &ReleasePackage) -> Result<(), LabError> {
        let directory = self.slot_dir(slot);
        fs::create_dir_all(&directory)?;
        let image_path = directory.join("image.bin.pending");
        write_and_sync(&image_path, &package.image)?;
        replace_file(&image_path, &directory.join("image.bin"))?;

        let manifest_path = directory.join("manifest.json.pending");
        let manifest = serde_json::to_vec_pretty(&package.manifest)?;
        write_and_sync(&manifest_path, &manifest)?;
        replace_file(&manifest_path, &directory.join("manifest.json"))?;
        sync_directory(&directory)?;
        Ok(())
    }

    /// Loads and validates the newest recoverable primary or backup metadata copy.
    pub fn load_state(&self) -> Result<BootMetadata, LabError> {
        let candidates = [self.root.join(STATE_FILE), self.root.join(BACKUP_FILE)];
        let mut valid = candidates
            .iter()
            .filter_map(|path| {
                let bytes = fs::read(path).ok()?;
                let state: BootMetadata = serde_json::from_slice(&bytes).ok()?;
                state.validate_invariants().ok()?;
                Some(state)
            })
            .collect::<Vec<_>>();
        valid.sort_by_key(|state| state.generation);
        valid.pop().ok_or(LabError::NoRecoverableState)
    }

    /// Atomically commits synchronized metadata while retaining one prior valid copy.
    pub fn commit_state(
        &self,
        state: &BootMetadata,
        injector: &mut dyn FaultInjector,
    ) -> Result<(), LabError> {
        state.validate_invariants()?;
        fs::create_dir_all(&self.root)?;
        let bytes = serde_json::to_vec_pretty(state)?;
        let temporary = self.root.join(TEMP_FILE);
        let primary = self.root.join(STATE_FILE);
        let backup = self.root.join(BACKUP_FILE);

        injector.checkpoint(FaultPoint::BeforeTempCreate)?;
        let mut temporary_file = OpenOptions::new()
            .create(true)
            .truncate(true)
            .write(true)
            .open(&temporary)?;
        temporary_file.write_all(&bytes)?;
        injector.checkpoint(FaultPoint::AfterTempWrite)?;
        temporary_file.sync_all()?;
        injector.checkpoint(FaultPoint::AfterTempSync)?;

        if primary.exists() {
            replace_file(&primary, &backup)?;
        }
        injector.checkpoint(FaultPoint::AfterBackupRename)?;
        replace_file(&temporary, &primary)?;
        injector.checkpoint(FaultPoint::AfterPrimaryRename)?;
        sync_directory(&self.root)?;
        injector.checkpoint(FaultPoint::AfterDirectorySync)?;
        Ok(())
    }

    /// Returns the owned directory for a slot without accepting caller-controlled paths.
    fn slot_dir(&self, slot: SlotId) -> PathBuf {
        self.root.join("slots").join(slot.to_string())
    }
}

/// Writes all bytes and asks the operating system to synchronize file data and metadata.
fn write_and_sync(path: &Path, bytes: &[u8]) -> Result<(), LabError> {
    let mut file = OpenOptions::new()
        .create(true)
        .truncate(true)
        .write(true)
        .open(path)?;
    file.write_all(bytes)?;
    file.sync_all()?;
    Ok(())
}

/// Replaces a destination on Windows and Unix without following caller-supplied paths.
fn replace_file(source: &Path, destination: &Path) -> Result<(), LabError> {
    if destination.exists() {
        fs::remove_file(destination)?;
    }
    fs::rename(source, destination)?;
    Ok(())
}

/// Synchronizes a directory on platforms that permit opening directories as files.
fn sync_directory(directory: &Path) -> Result<(), LabError> {
    #[cfg(unix)]
    File::open(directory)?.sync_all()?;
    #[cfg(not(unix))]
    let _ = directory;
    Ok(())
}

#[cfg(test)]
mod tests {
    use tempfile::tempdir;

    use crate::{
        crypto::sha256_hex,
        fault::{FaultPoint, NoFault, SingleFault},
        model::Version,
    };

    use super::*;

    #[test]
    fn interruption_recovers_old_or_new_valid_generation() {
        for point in FaultPoint::all() {
            let directory = tempdir().expect("temp directory");
            let store = LabStore::new(directory.path());
            let original = BootMetadata::initial(Version::new(1, 0, 0), sha256_hex(b"v1"));
            store
                .initialize(&original, b"v1", &mut NoFault)
                .expect("initialize");
            let mut updated = original.clone();
            updated.generation = 1;
            let _ = store.commit_state(&updated, &mut SingleFault::new(point));
            let recovered = store.load_state().expect("recover state");
            assert!(recovered.generation <= 1);
            recovered
                .validate_invariants()
                .expect("valid recovered state");
        }
    }
}
