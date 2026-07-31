"""HIVE enums for identification, artifact, and operation status."""

from __future__ import annotations

from enum import Enum


class IdentificationStatus(str, Enum):
    """Status of device identification.

    Only MATCH_CONFIRMED allows autonomous flashing.
    See docs/safety-model.md for full semantics.
    """

    MATCH_CONFIRMED = "MATCH_CONFIRMED"
    MATCH_AMBIGUOUS = "MATCH_AMBIGUOUS"
    DEVICE_UNKNOWN = "DEVICE_UNKNOWN"
    DEVICE_OFFLINE = "DEVICE_OFFLINE"
    DEVICE_BUSY = "DEVICE_BUSY"
    PROJECT_MISMATCH = "PROJECT_MISMATCH"
    ROLE_MISMATCH = "ROLE_MISMATCH"
    FIRMWARE_INCOMPATIBLE = "FIRMWARE_INCOMPATIBLE"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    SAFETY_INTERLOCK_OPEN = "SAFETY_INTERLOCK_OPEN"
    ESTOP_ACTIVE = "ESTOP_ACTIVE"

    @property
    def allows_flash(self) -> bool:
        """Whether this status permits autonomous flashing."""
        return self is IdentificationStatus.MATCH_CONFIRMED


class ArtifactStatus(str, Enum):
    """Status of a build artifact.

    See docs/artifact-lifecycle.md for transitions.
    """

    BUILT = "built"
    TESTED = "tested"
    VERIFIED = "verified"
    KNOWN_GOOD = "known-good"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"

    @property
    def is_runnable(self) -> bool:
        """Whether this status allows the artifact to be flashed/deployed."""
        return self in (
            ArtifactStatus.TESTED,
            ArtifactStatus.VERIFIED,
            ArtifactStatus.KNOWN_GOOD,
        )


class OperationStatus(str, Enum):
    """Final status of an operation (verification, recovery, flash)."""

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    ABORTED = "aborted"
    ESCALATED = "escalated"
