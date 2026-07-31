"""Tests for HIVE error hierarchy."""

from __future__ import annotations

import pytest

from hive.common.errors import (
    DeviceBusyError,
    DeviceNotIdentifiedError,
    HiveError,
    NotImplementedInStageError,
    SafetyInterlockError,
    SchemaValidationError,
)


def test_all_errors_inherit_from_hive_error() -> None:
    for cls in (
        DeviceBusyError,
        DeviceNotIdentifiedError,
        SafetyInterlockError,
        SchemaValidationError,
    ):
        assert issubclass(cls, HiveError)
        assert issubclass(cls, Exception)


def test_not_implemented_in_stage_error_carries_metadata() -> None:
    err = NotImplementedInStageError("feature X", "H3")
    assert err.feature == "feature X"
    assert err.planned_stage == "H3"
    assert "feature X" in str(err)
    assert "H3" in str(err)
    assert err.details == {"feature": "feature X", "planned_stage": "H3"}


def test_error_details_default_to_empty_dict() -> None:
    err = HiveError("boom")
    assert err.details == {}


def test_error_details_passed_in() -> None:
    err = HiveError("boom", details={"x": 1})
    assert err.details == {"x": 1}


def test_can_raise_and_catch_as_hive_error() -> None:
    with pytest.raises(HiveError):
        raise DeviceBusyError("device X busy")
