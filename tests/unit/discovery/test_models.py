"""Unit tests for hive.discovery.models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hive.discovery.fingerprint import compute_fingerprint
from hive.discovery.models import DiscoveredDevice


class TestDiscoveredDeviceValidation:
    def test_minimal_construction(self):
        d = DiscoveredDevice(source="usb", fingerprint="0" * 32)
        assert d.source == "usb"
        assert d.usb_vid is None
        assert d.usb_pid is None

    def test_empty_source_rejected(self):
        with pytest.raises(ValidationError):
            DiscoveredDevice(source="", fingerprint="0" * 32)

    def test_invalid_vid(self):
        with pytest.raises(ValidationError):
            DiscoveredDevice(source="usb", usb_vid="ZZZZ", usb_pid="811b", fingerprint="0" * 32)

    def test_invalid_pid(self):
        with pytest.raises(ValidationError):
            DiscoveredDevice(source="usb", usb_vid="239a", usb_pid="XYZ", fingerprint="0" * 32)

    def test_vid_normalized_to_lowercase(self):
        d = DiscoveredDevice(source="usb", usb_vid="239A", usb_pid="811B", fingerprint="0" * 32)
        assert d.usb_vid == "239a"
        assert d.usb_pid == "811b"

    def test_invalid_fingerprint_too_short(self):
        with pytest.raises(ValidationError):
            DiscoveredDevice(source="usb", fingerprint="abc")

    def test_invalid_fingerprint_not_hex(self):
        with pytest.raises(ValidationError):
            DiscoveredDevice(source="usb", fingerprint="Z" * 32)

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            DiscoveredDevice(
                source="usb",
                fingerprint="0" * 32,
                unknown_field="bogus",  # type: ignore[call-arg]
            )


class TestDiscoveredDeviceProperties:
    def test_multi_source_accepted(self):
        d = DiscoveredDevice(source="usb+serial", fingerprint="0" * 32)
        assert d.source == "usb+serial"

    def test_strong_identity_true(self):
        d = DiscoveredDevice(
            source="usb",
            usb_vid="239a",
            usb_pid="811b",
            serial_number="ABC123",
            fingerprint="0" * 32,
        )
        assert d.has_strong_identity is True

    def test_strong_identity_false_no_serial(self):
        d = DiscoveredDevice(source="usb", usb_vid="239a", usb_pid="811b", fingerprint="0" * 32)
        assert d.has_strong_identity is False

    def test_strong_identity_false_no_vid(self):
        d = DiscoveredDevice(
            source="usb",
            usb_pid="811b",
            serial_number="ABC",
            fingerprint="0" * 32,
        )
        assert d.has_strong_identity is False

    def test_display_id_stable_path(self):
        d = DiscoveredDevice(
            source="usb",
            stable_path="/dev/hive/robot_imu",
            fingerprint="0" * 32,
        )
        assert d.display_id == "/dev/hive/robot_imu"

    def test_display_id_by_id(self):
        d = DiscoveredDevice(
            source="usb",
            serial_by_id="/dev/serial/by-id/usb-ESP32_ABC-if00",
            fingerprint="0" * 32,
        )
        assert d.display_id == "/dev/serial/by-id/usb-ESP32_ABC-if00"

    def test_display_id_serial_port(self):
        d = DiscoveredDevice(source="usb", serial_port="/dev/ttyACM0", fingerprint="0" * 32)
        assert d.display_id == "/dev/ttyACM0"

    def test_display_id_ssh(self):
        d = DiscoveredDevice(
            source="ssh",
            ssh_host="192.168.1.10",
            ssh_user="ubuntu",
            ssh_port=2222,
            fingerprint="0" * 32,
        )
        assert d.display_id == "ubuntu@192.168.1.10:2222"

    def test_display_id_fingerprint_fallback(self):
        d = DiscoveredDevice(source="usb", fingerprint="0123456789abcdef0123456789abcdef")
        assert d.display_id == "0123456789abcdef"


class TestFingerprintIntegration:
    """DiscoveredDevice accepts fingerprints from compute_fingerprint()."""

    def test_realistic_esp32(self):
        fp = compute_fingerprint(source="usb", usb_vid="303a", usb_pid="1001", serial_number="ABCD")
        d = DiscoveredDevice(
            source="usb",
            usb_vid="303a",
            usb_pid="1001",
            serial_number="ABCD",
            serial_port="/dev/ttyACM0",
            fingerprint=fp,
        )
        assert d.has_strong_identity
        assert d.display_id == "/dev/ttyACM0"
