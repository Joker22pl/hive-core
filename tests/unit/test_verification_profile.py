"""Tests for verification profile model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hive.common.models.verification_profile import VerificationProfile


def _minimal_profile() -> dict:
    return {
        "profile_id": "test-profile",
        "target_type": "esp32-s3-pico",
        "preconditions": ["device_match_confirmed", "motor_enable_off"],
        "steps": [
            {"id": "s1", "type": "delay", "params": {"duration_s": 1.0}},
        ],
        "success": {"all_steps_passed": True},
        "failure": {"collect_evidence": True},
    }


def test_minimal_profile_validates() -> None:
    p = VerificationProfile.model_validate(_minimal_profile())
    assert p.profile_id == "test-profile"
    assert len(p.steps) == 1


def test_unknown_precondition_rejected() -> None:
    data = _minimal_profile()
    data["preconditions"] = ["definitely-not-real"]
    with pytest.raises(ValidationError):
        VerificationProfile.model_validate(data)


def test_unknown_step_type_rejected() -> None:
    data = _minimal_profile()
    data["steps"] = [{"id": "s1", "type": "unicorn-dance"}]
    with pytest.raises(ValidationError):
        VerificationProfile.model_validate(data)


def test_empty_steps_rejected() -> None:
    data = _minimal_profile()
    data["steps"] = []
    with pytest.raises(ValidationError):
        VerificationProfile.model_validate(data)


def test_step_on_failure_default() -> None:
    data = _minimal_profile()
    p = VerificationProfile.model_validate(data)
    assert p.steps[0].on_failure == "abort"
