"""Tests for artifact manifest model."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from hive.common.models.artifact import ArtifactManifest


def _valid_uuid() -> str:
    return str(uuid.uuid4())


def _valid_data() -> dict:
    return {
        "artifact_id": _valid_uuid(),
        "project": "IMP2",
        "target": "esp32s3",
        "git": {"repo": "imp2-firmware", "commit_sha": "deadbeef1234567", "dirty": False},
        "artifact": {
            "path": "artifacts/firmware.bin",
            "sha256": "a" * 64,
            "size_bytes": 1024,
            "format": "esp32-binary",
        },
        "build": {
            "built_at": "2026-07-30T04:00:00Z",
            "build_command": "idf.py build",
            "build_duration_s": 47.0,
        },
        "status": "built",
    }


def test_valid_artifact_loads() -> None:
    m = ArtifactManifest.model_validate(_valid_data())
    assert m.target == "esp32s3"
    assert m.status == "built"


def test_invalid_sha256_rejected() -> None:
    data = _valid_data()
    data["artifact"]["sha256"] = "short"
    with pytest.raises(ValidationError):
        ArtifactManifest.model_validate(data)


def test_invalid_status_rejected() -> None:
    data = _valid_data()
    data["status"] = "magic"
    with pytest.raises(ValidationError):
        ArtifactManifest.model_validate(data)


def test_artifact_id_must_be_uuid() -> None:
    data = _valid_data()
    data["artifact_id"] = "not-a-uuid"
    with pytest.raises(ValidationError):
        ArtifactManifest.model_validate(data)


def test_all_artifact_statuses_supported() -> None:
    for s in ("built", "tested", "verified", "known-good", "rejected", "superseded", "archived"):
        data = _valid_data()
        data["status"] = s
        m = ArtifactManifest.model_validate(data)
        assert m.status == s
