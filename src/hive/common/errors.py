"""HIVE error hierarchy.

All errors raised by HIVE modules inherit from HiveError, so callers can
catch broadly (HiveError) or narrowly (specific subclass).
"""

from __future__ import annotations


class HiveError(Exception):
    """Base class for all HIVE errors."""

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DeviceNotIdentifiedError(HiveError):
    """Raised when an operation requires MATCH_CONFIRMED but device is in another state."""


class DeviceBusyError(HiveError):
    """Raised when the device is locked by another owner/session."""


class SafetyInterlockError(HiveError):
    """Raised when a safety interlock blocks the operation (e.g. ESTOP_ACTIVE)."""


class LockAcquireError(HiveError):
    """Raised when a lock could not be acquired (busy, expired, invalid)."""


class SchemaValidationError(HiveError):
    """Raised when a manifest fails JSON Schema validation."""


class NotImplementedInStageError(HiveError):
    """Raised when a feature is not yet implemented in the current stage.

    H0 raises this for real I/O operations (USB, serial, SSH, flashing).
    The error includes the stage in which the operation is planned.
    """

    def __init__(self, feature: str, planned_stage: str) -> None:
        super().__init__(
            f"Feature '{feature}' is not implemented in the current stage. "
            f"Planned for stage {planned_stage}.",
            details={"feature": feature, "planned_stage": planned_stage},
        )
        self.feature = feature
        self.planned_stage = planned_stage


class RegistryNotFoundError(HiveError):
    """Raised when a registry directory does not exist or is not a directory."""


class RegistryAccessError(HiveError):
    """Raised when a registry directory cannot be read (permissions, I/O error)."""
