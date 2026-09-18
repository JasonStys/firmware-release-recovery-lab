//! Deterministic interruption injection at durable-write boundaries.
//!
//! File map: `FaultPoint` names persistence boundaries; `FaultInjector` abstracts
//! injection; `NoFault` and `SingleFault` implement production-like and campaign modes.

use serde::{Deserialize, Serialize};

use crate::model::LabError;

/// Named boundaries surrounding a state-file commit.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum FaultPoint {
    /// Immediately before opening the temporary file.
    BeforeTempCreate,
    /// After all bytes reach the operating-system file buffer.
    AfterTempWrite,
    /// After the temporary file is synchronized to storage.
    AfterTempSync,
    /// After the prior primary copy has been moved to the recovery path.
    AfterBackupRename,
    /// After the synchronized temporary file replaces the primary path.
    AfterPrimaryRename,
    /// After the containing directory is synchronized where supported.
    AfterDirectorySync,
}

impl FaultPoint {
    /// Returns every injectable boundary in commit order.
    #[must_use]
    pub const fn all() -> [Self; 6] {
        [
            Self::BeforeTempCreate,
            Self::AfterTempWrite,
            Self::AfterTempSync,
            Self::AfterBackupRename,
            Self::AfterPrimaryRename,
            Self::AfterDirectorySync,
        ]
    }
}

impl std::fmt::Display for FaultPoint {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(match self {
            Self::BeforeTempCreate => "before_temp_create",
            Self::AfterTempWrite => "after_temp_write",
            Self::AfterTempSync => "after_temp_sync",
            Self::AfterBackupRename => "after_backup_rename",
            Self::AfterPrimaryRename => "after_primary_rename",
            Self::AfterDirectorySync => "after_directory_sync",
        })
    }
}

/// Receives durable-write checkpoints and optionally simulates a process interruption.
pub trait FaultInjector {
    /// Returns `InjectedCrash` when the selected boundary is reached.
    fn checkpoint(&mut self, point: FaultPoint) -> Result<(), LabError>;
}

/// Injector used during ordinary operation.
#[derive(Debug, Default)]
pub struct NoFault;

impl FaultInjector for NoFault {
    fn checkpoint(&mut self, _point: FaultPoint) -> Result<(), LabError> {
        Ok(())
    }
}

/// Injector that fails exactly once at one selected boundary.
#[derive(Debug)]
pub struct SingleFault {
    selected: FaultPoint,
    fired: bool,
}

impl SingleFault {
    /// Constructs an armed, one-shot injector.
    #[must_use]
    pub const fn new(selected: FaultPoint) -> Self {
        Self {
            selected,
            fired: false,
        }
    }
}

impl FaultInjector for SingleFault {
    fn checkpoint(&mut self, point: FaultPoint) -> Result<(), LabError> {
        if !self.fired && point == self.selected {
            self.fired = true;
            return Err(LabError::InjectedCrash(point.to_string()));
        }
        Ok(())
    }
}
