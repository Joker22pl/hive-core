"""Tests for HIVE common status enums."""

from __future__ import annotations

from hive.common.status import ArtifactStatus, IdentificationStatus, OperationStatus


def test_only_match_confirmed_allows_flash() -> None:
    """Hard rule: only MATCH_CONFIRMED allows autonomous flashing."""
    for status in IdentificationStatus:
        if status is IdentificationStatus.MATCH_CONFIRMED:
            assert status.allows_flash is True
        else:
            assert status.allows_flash is False, f"Status {status.value} must NOT allow flash"


def test_identification_status_count() -> None:
    """Sanity: we have exactly 11 identification statuses (per vision.md)."""
    assert len(IdentificationStatus) == 11


def test_artifact_runnable_states() -> None:
    """tested, verified, known-good are runnable."""
    for status in ArtifactStatus:
        if status in (
            ArtifactStatus.TESTED,
            ArtifactStatus.VERIFIED,
            ArtifactStatus.KNOWN_GOOD,
        ):
            assert status.is_runnable is True
        else:
            assert status.is_runnable is False


def test_operation_status_values() -> None:
    expected = {"passed", "failed", "error", "aborted", "escalated"}
    assert {s.value for s in OperationStatus} == expected
