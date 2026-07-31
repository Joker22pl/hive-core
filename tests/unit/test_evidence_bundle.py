"""Tests for evidence bundle model."""

from __future__ import annotations

from hive.common.models.evidence_bundle import EvidenceBundle


def _minimal_bundle() -> dict:
    return {
        "bundle_id": "eb-test-001",
        "operation": "verify",
        "started_at": "2026-07-30T04:00:00Z",
        "ended_at": "2026-07-30T04:01:00Z",
        "final_status": "passed",
    }


def test_minimal_bundle_validates() -> None:
    b = EvidenceBundle.model_validate(_minimal_bundle())
    assert b.bundle_id == "eb-test-001"
    assert b.final_status == "passed"


def test_bundle_duration_computed() -> None:
    b = EvidenceBundle.model_validate(_minimal_bundle())
    assert b.duration_s() == 60.0


def test_invalid_operation_rejected() -> None:
    data = _minimal_bundle()
    data["operation"] = "resurrect"
    from pydantic import ValidationError

    try:
        EvidenceBundle.model_validate(data)
    except ValidationError:
        return
    raise AssertionError("expected ValidationError")


def test_invalid_final_status_rejected() -> None:
    data = _minimal_bundle()
    data["final_status"] = "maybe"
    from pydantic import ValidationError

    try:
        EvidenceBundle.model_validate(data)
    except ValidationError:
        return
    raise AssertionError("expected ValidationError")
