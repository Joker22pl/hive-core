"""Unit tests for hive.discovery.fingerprint."""

from __future__ import annotations

import re

import pytest

from hive.discovery.fingerprint import compute_fingerprint


class TestComputeFingerprint:
    """compute_fingerprint() is the join key between scans."""

    def test_returns_32_lowercase_hex(self):
        fp = compute_fingerprint(source="usb", usb_vid="239a", usb_pid="811b")
        assert len(fp) == 32
        assert re.match(r"^[0-9a-f]{32}$", fp), fp

    def test_stable_across_calls(self):
        a = compute_fingerprint(source="usb", usb_vid="239a", usb_pid="811b", serial_number="ABC")
        b = compute_fingerprint(source="usb", usb_vid="239A", usb_pid="811B", serial_number="ABC")
        assert a == b, "VID/PID casing must not change fingerprint"

    def test_different_vid_different_fp(self):
        a = compute_fingerprint(source="usb", usb_vid="239a", usb_pid="811b")
        b = compute_fingerprint(source="usb", usb_vid="239b", usb_pid="811b")
        assert a != b

    def test_different_serial_different_fp(self):
        a = compute_fingerprint(source="usb", usb_vid="239a", usb_pid="811b", serial_number="ABC")
        b = compute_fingerprint(source="usb", usb_vid="239a", usb_pid="811b", serial_number="XYZ")
        assert a != b

    def test_different_source_same_fp(self):
        # Source is NOT part of fingerprint — same physical device
        # discovered by usb and serial adapters must produce the same
        # fingerprint for deduplication in DiscoveryService.
        a = compute_fingerprint(source="usb", usb_vid="239a", usb_pid="811b")
        b = compute_fingerprint(source="serial", usb_vid="239a", usb_pid="811b")
        assert a == b, "Source must NOT affect fingerprint (used for dedup)"

    def test_ssh_fingerprint(self):
        a = compute_fingerprint(source="ssh", ssh_host="192.168.1.10", ssh_port=22, ssh_user="ubuntu")
        b = compute_fingerprint(source="ssh", ssh_host="192.168.1.10", ssh_port=22, ssh_user="ubuntu")
        assert a == b

    def test_ssh_different_user(self):
        a = compute_fingerprint(source="ssh", ssh_host="192.168.1.10", ssh_user="ubuntu")
        b = compute_fingerprint(source="ssh", ssh_host="192.168.1.10", ssh_user="root")
        assert a != b

    def test_serial_by_id_alone(self):
        # Some devices have serial_by_id but no readable VID/PID
        a = compute_fingerprint(source="usb", serial_by_id="/dev/serial/by-id/usb-ESP32_ABC")
        b = compute_fingerprint(source="usb", serial_by_id="/dev/serial/by-id/usb-ESP32_ABC")
        assert a == b

    def test_serial_by_id_different(self):
        a = compute_fingerprint(source="usb", serial_by_id="/dev/serial/by-id/usb-ESP32_ABC")
        b = compute_fingerprint(source="usb", serial_by_id="/dev/serial/by-id/usb-ESP32_XYZ")
        assert a != b

    def test_no_identity_raises(self):
        with pytest.raises(ValueError, match="no identifying fields"):
            compute_fingerprint(source="usb")

    def test_serial_by_id_and_vid_combined(self):
        # Both fields together — should be stable
        a = compute_fingerprint(
            source="usb",
            usb_vid="239a",
            usb_pid="811b",
            serial_by_id="/dev/serial/by-id/usb-X",
        )
        b = compute_fingerprint(
            source="usb",
            usb_vid="239a",
            usb_pid="811b",
            serial_by_id="/dev/serial/by-id/usb-X",
        )
        assert a == b


class TestFingerprintContract:
    """Contract: same physical device → same fingerprint.

    We don't care about the exact hash, only the stability.
    """

    def test_swap_source_same_id_same_fp(self):
        a = compute_fingerprint(source="usb", serial_by_id="X")
        b = compute_fingerprint(source="serial", serial_by_id="X")
        assert a == b, "Source must not affect fingerprint"

    def test_order_independent(self):
        # python json.dumps with sort_keys=True makes the order irrelevant
        # for the SAME fields. We test by passing the same data in two ways.
        a = compute_fingerprint(source="usb", usb_vid="239a", usb_pid="811b", serial_number="ABC")
        b = compute_fingerprint(
            source="usb",
            serial_number="ABC",
            usb_pid="811b",
            usb_vid="239a",
        )
        assert a == b