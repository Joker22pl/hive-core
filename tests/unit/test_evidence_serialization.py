"""Tests for evidence bundle (de)serialization."""

from __future__ import annotations

from pathlib import Path

from hive.common.models.evidence_bundle import EvidenceBundle
from hive.evidence import read_bundle, write_bundle


def test_bundle_round_trip(tmp_path: Path) -> None:
    bundle = EvidenceBundle.model_validate(
        {
            "bundle_id": "eb-roundtrip-001",
            "operation": "verify",
            "started_at": "2026-07-30T04:00:00Z",
            "ended_at": "2026-07-30T04:01:30Z",
            "final_status": "passed",
            "device": {"device_id": "d1", "identification_status": "MATCH_CONFIRMED"},
        }
    )
    path = write_bundle(bundle, tmp_path / "bundle.json")
    loaded = read_bundle(path)
    assert loaded.bundle_id == "eb-roundtrip-001"
    assert loaded.device is not None
    assert loaded.device.device_id == "d1"
    assert loaded.duration_s() == 90.0
