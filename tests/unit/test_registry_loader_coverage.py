"""Coverage tests for ``hive.registry.loader``.

The main coverage gap is the per-file failure paths. Each ``load_*``
function wraps its own try/except, so the ``except SchemaValidationError``
re-raise paths are not exercised by the main flow tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hive.common.errors import SchemaValidationError
from hive.registry import (
    load_artifact_manifest,
    load_device_manifest,
    load_profile,
)


def test_load_device_manifest_raises_schema_validation_error_on_missing(
    tmp_path: Path,
) -> None:
    """load_device_manifest re-raises as SchemaValidationError on missing key."""
    p = tmp_path / "missing.yaml"
    p.write_text("device_id: x\nproject: x\nrole: y\nidentity: {}\n", encoding="utf-8")
    # Missing type → ValidationError → SchemaValidationError wrapper.
    with pytest.raises(SchemaValidationError) as exc_info:
        load_device_manifest(p)
    assert "Failed to load device manifest" in str(exc_info.value)


def test_load_artifact_manifest_raises_schema_validation_error(tmp_path: Path) -> None:
    """load_artifact_manifest wraps ValidationError as SchemaValidationError."""
    p = tmp_path / "bad-artifact.yaml"
    p.write_text("not: a valid artifact\n", encoding="utf-8")
    with pytest.raises(SchemaValidationError) as exc_info:
        load_artifact_manifest(p)
    assert "Failed to load artifact manifest" in str(exc_info.value)


def test_load_profile_raises_schema_validation_error(tmp_path: Path) -> None:
    """load_profile wraps ValidationError as SchemaValidationError."""
    p = tmp_path / "bad-profile.yaml"
    p.write_text("profile_id: x\ntarget_type: x\nsteps: []\n", encoding="utf-8")
    with pytest.raises(SchemaValidationError) as exc_info:
        load_profile(p)
    assert "Failed to load verification profile" in str(exc_info.value)


def test_load_device_manifest_raises_on_yaml_missing(
    tmp_path: Path,
) -> None:
    """YAML parse error → SchemaValidationError wrapper."""
    p = tmp_path / "broken.yaml"
    p.write_text(":\n  :\n  bad: [yaml: error\n", encoding="utf-8")
    with pytest.raises(SchemaValidationError) as exc_info:
        load_device_manifest(p)
    assert "Failed to load device manifest" in str(exc_info.value)


def test_load_device_manifest_file_not_found(tmp_path: Path) -> None:
    """Missing file → SchemaValidationError (FileNotFoundError is wrapped)."""
    p = tmp_path / "no-such.yaml"
    with pytest.raises(SchemaValidationError):
        load_device_manifest(p)


def test_load_artifact_manifest_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(SchemaValidationError):
        load_artifact_manifest(tmp_path / "no-such.yaml")


def test_load_profile_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(SchemaValidationError):
        load_profile(tmp_path / "no-such.yaml")
