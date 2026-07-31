"""Unit tests for hive.database.registry.DeviceRegistry."""

from __future__ import annotations

import pytest

from hive.database.engine import HiveDatabase
from hive.database.registry import DeviceRegistry, RegistryError
from hive.discovery.fingerprint import compute_fingerprint
from hive.discovery.models import DiscoveredDevice


@pytest.fixture
def mem_db() -> HiveDatabase:
    db = HiveDatabase.from_url("sqlite:///:memory:")
    db.upgrade()
    return db


@pytest.fixture
def registry(mem_db) -> DeviceRegistry:
    return DeviceRegistry(mem_db)


def _discovered(**kwargs):
    """Helper to build a DiscoveredDevice."""
    fp_kwargs = {
        k: v
        for k, v in kwargs.items()
        if k
        in (
            "usb_vid",
            "usb_pid",
            "serial_number",
            "serial_by_id",
            "ssh_host",
            "ssh_port",
            "ssh_user",
        )
    }
    fp = compute_fingerprint(source="usb", **fp_kwargs)
    return DiscoveredDevice(source="usb", fingerprint=fp, **kwargs)


class TestRegistryUpsert:
    def test_empty_upsert(self, registry):
        assert registry.upsert([]) == 0

    def test_single_device_insert(self, registry):
        d = _discovered(usb_vid="239a", usb_pid="811b", serial_number="ABC")
        n = registry.upsert([d])
        assert n == 1
        rec = registry.get_by_fingerprint(d.fingerprint)
        assert rec is not None
        assert rec.usb_vid == "239a"
        assert rec.usb_pid == "811b"
        assert rec.serial_number == "ABC"

    def test_upsert_updates_last_seen_at(self, registry):
        d = _discovered(usb_vid="239a", usb_pid="811b", serial_number="A")
        registry.upsert([d])
        rec1 = registry.get_by_fingerprint(d.fingerprint)
        last_seen_1 = rec1.last_seen_at
        # Second upsert should update last_seen_at (timestamp changes)
        import time

        time.sleep(0.01)
        registry.upsert([d])
        rec2 = registry.get_by_fingerprint(d.fingerprint)
        assert rec2.last_seen_at >= last_seen_1

    def test_upsert_preserves_discovered_at(self, registry):
        d = _discovered(usb_vid="239a", usb_pid="811b", serial_number="A")
        registry.upsert([d])
        rec1 = registry.get_by_fingerprint(d.fingerprint)
        discovered_at_1 = rec1.discovered_at
        import time

        time.sleep(0.01)
        registry.upsert([d])
        rec2 = registry.get_by_fingerprint(d.fingerprint)
        assert rec2.discovered_at == discovered_at_1, "discovered_at must not change on re-upsert"

    def test_upsert_first_non_null_wins(self, registry):
        # First scan: serial_port only
        d1 = _discovered(
            usb_vid="239a",
            usb_pid="811b",
            serial_number="ABC",
            serial_port="/dev/ttyACM0",
        )
        registry.upsert([d1])
        # Second scan: same fp, but serial_port None — should not erase
        rec = DiscoveredDevice(
            fingerprint=d1.fingerprint,
            source="serial",
            usb_vid="239a",
            usb_pid="811b",
            serial_number="ABC",
        )
        registry.upsert([rec])
        result = registry.get_by_fingerprint(d1.fingerprint)
        assert result.serial_port == "/dev/ttyACM0"

    def test_list_devices_sorted_by_last_seen(self, registry):
        d_old = _discovered(usb_vid="1111", usb_pid="2222", serial_number="OLD")
        d_new = _discovered(usb_vid="3333", usb_pid="4444", serial_number="NEW")
        registry.upsert([d_old])
        import time

        time.sleep(0.01)
        registry.upsert([d_new])
        devices = registry.list_devices()
        assert devices[0].serial_number == "NEW"
        assert devices[1].serial_number == "OLD"


class TestRegistryClaim:
    def test_claim_assigns_device_id(self, registry):
        d = _discovered(usb_vid="239a", usb_pid="811b", serial_number="X")
        registry.upsert([d])
        rec = registry.claim(
            d.fingerprint, device_id="robot_imu", manifest_path="registry/devices/robot_imu.yaml"
        )
        assert rec.device_id == "robot_imu"
        assert rec.manifest_path == "registry/devices/robot_imu.yaml"

    def test_claim_unknown_fingerprint_raises(self, registry):
        with pytest.raises(RegistryError):
            registry.claim("nonexistent", device_id="x")

    def test_claim_without_manifest_path(self, registry):
        d = _discovered(usb_vid="239a", usb_pid="811b", serial_number="X")
        registry.upsert([d])
        rec = registry.claim(d.fingerprint, device_id="my_device")
        assert rec.device_id == "my_device"
        assert rec.manifest_path is None
