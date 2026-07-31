"""Tests for device manifest model + JSON schema validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from hive.common.errors import SchemaValidationError
from hive.common.models.device import DeviceManifest
from hive.registry.loader import load_all_device_manifests, load_device_manifest
from hive.registry.validator import validate_manifest_against_schema

# ---------- Pydantic model ----------


def test_minimal_valid_device_manifest() -> None:
    data = {
        "device_id": "test-device",
        "type": "microcontroller",
        "project": "TEST",
        "role": "test",
        "identity": {"usb_vid": "303A", "usb_pid": "1001"},
    }
    manifest = DeviceManifest.model_validate(data)
    assert manifest.device_id == "test-device"
    assert manifest.identity.usb_vid == "303A"
    assert manifest.has_strong_identity is False  # no serial


def test_strong_identity_requires_serial() -> None:
    data = {
        "device_id": "test-device",
        "type": "microcontroller",
        "project": "TEST",
        "role": "test",
        "identity": {"usb_vid": "303A", "usb_pid": "1001", "serial_number": "SN1"},
    }
    manifest = DeviceManifest.model_validate(data)
    assert manifest.has_serial is True
    assert manifest.has_strong_identity is True


def test_invalid_device_id_pattern_rejected() -> None:
    data = {
        "device_id": "Invalid ID With Spaces",
        "type": "microcontroller",
        "project": "TEST",
        "role": "test",
        "identity": {"usb_vid": "303A", "usb_pid": "1001"},
    }
    with pytest.raises(ValidationError):  # ValidationError
        DeviceManifest.model_validate(data)


def test_invalid_vid_rejected() -> None:
    data = {
        "device_id": "test-device",
        "type": "microcontroller",
        "project": "TEST",
        "role": "test",
        "identity": {"usb_vid": "ZZZZ", "usb_pid": "1001"},  # non-hex
    }
    with pytest.raises(ValidationError):
        DeviceManifest.model_validate(data)


def test_unknown_capability_rejected() -> None:
    data = {
        "device_id": "test-device",
        "type": "microcontroller",
        "project": "TEST",
        "role": "test",
        "identity": {"usb_vid": "303A", "usb_pid": "1001"},
        "capabilities": ["unicorn-power"],  # not allowed
    }
    with pytest.raises(ValidationError):
        DeviceManifest.model_validate(data)


def test_ssh_fingerprint_format_enforced() -> None:
    data = {
        "device_id": "host-01",
        "type": "linux_host",
        "project": "TEST",
        "role": "host",
        "identity": {
            "usb_vid": None,
            "usb_pid": None,
            "ssh": {
                "host": "10.0.0.1",
                "user": "tester",
                "host_key_fingerprint": "MD5:abcdef",  # wrong format
            },
        },
    }
    with pytest.raises(ValidationError):
        DeviceManifest.model_validate(data)


# ---------- JSON Schema validation ----------


def test_validate_manifest_against_schema_passes_for_real_manifest(registry_dir: Path) -> None:
    """Bundled manifests must validate against schemas/device.schema.json."""
    for path in sorted(registry_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        validate_manifest_against_schema(data, "device.schema.json")


def test_validate_manifest_against_schema_fails_on_missing_required() -> None:
    bad = {"device_id": "x"}  # missing type, project, role, identity
    with pytest.raises(SchemaValidationError):
        validate_manifest_against_schema(bad, "device.schema.json")


# ---------- Loader ----------


def test_load_all_device_manifests_skips_readme(registry_dir: Path) -> None:
    manifests = list(load_all_device_manifests(registry_dir))
    assert len(manifests) == 1
    assert manifests[0].device_id == "esp32s3-test-01"


def test_load_device_manifest_round_trip(registry_dir: Path) -> None:
    path = registry_dir / "esp32s3-test-01.yaml"
    manifest = load_device_manifest(path)
    assert manifest.identity.serial_number == "TEST-SN-001"


def test_load_bundled_manifests() -> None:
    """All manifests shipped in hive-core/registry/devices/ must load cleanly."""
    repo_root = Path(__file__).resolve().parents[2]
    dev_dir = repo_root / "registry" / "devices"
    assert dev_dir.exists(), f"missing {dev_dir}"
    manifests = list(load_all_device_manifests(dev_dir))
    assert len(manifests) >= 4, "expected at least 4 bundled device manifests"

    ids = {m.device_id for m in manifests}
    assert "esp32s3-imp2-motor-01" in ids
    assert "esp32s3-imp2-sensor-01" in ids
    assert "pico-test-01" in ids
    assert "hive-io-controller" in ids
