"""End-to-end integration tests for the discovery → registry → lock pipeline.

These tests don't require real USB hardware. They use fake adapters to
simulate a scan, then exercise the full flow:

    DiscoveryService.scan()
        → DeviceRegistry.upsert() → SQLite
        → registry.claim() → SQLite
        → SqliteLockStore.acquire/release/sweep → SQLite

The point is to verify that all the modules wire together correctly,
not to verify individual behaviors (those live in tests/unit/).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from hive.common.models.lock import Lock
from hive.database.engine import HiveDatabase
from hive.database.registry import DeviceRegistry
from hive.discovery.fingerprint import compute_fingerprint
from hive.discovery.models import DiscoveredDevice
from hive.discovery.service import DiscoveryService
from hive.locking import LockService, LockSweeper, SqliteLockStore


class FakeAdapter:
    """In-memory discovery adapter."""

    def __init__(self, source: str, records: list[dict[str, Any]]) -> None:
        self.source = source
        self._records = records

    def list_devices(self) -> list[dict[str, Any]]:
        return list(self._records)


@pytest.fixture
def mem_db() -> HiveDatabase:
    db = HiveDatabase.from_url("sqlite:///:memory:")
    db.upgrade()
    return db


def _discovered(usb_vid: str, usb_pid: str, serial: str, port: str) -> DiscoveredDevice:
    fp = compute_fingerprint(source="usb", usb_vid=usb_vid, usb_pid=usb_pid, serial_number=serial)
    return DiscoveredDevice(
        source="usb",
        usb_vid=usb_vid,
        usb_pid=usb_pid,
        serial_number=serial,
        serial_port=port,
        fingerprint=fp,
    )


class TestDiscoveryToRegistryFlow:
    def test_scan_upserts_persists(self, mem_db):
        """End-to-end: scan → upsert → list_devices."""
        devices = [
            _discovered("303a", "1001", "ESP32-001", "/dev/ttyACM0"),
            _discovered("239a", "811b", "FEATHER-001", "/dev/ttyACM1"),
            _discovered("1a86", "55d3", "CH9102-001", "/dev/ttyUSB0"),
        ]

        reg = DeviceRegistry(mem_db)
        count = reg.upsert(devices)
        assert count == 3

        stored = reg.list_devices()
        assert len(stored) == 3
        serials = {r.serial_number for r in stored}
        assert serials == {"ESP32-001", "FEATHER-001", "CH9102-001"}

    def test_scan_claim_lock_acquire_release(self, mem_db):
        """Full flow: scan → upsert → claim → lock acquire → release."""
        d = _discovered("303a", "1001", "ESP32-001", "/dev/ttyACM0")

        reg = DeviceRegistry(mem_db)
        reg.upsert([d])
        reg.claim(
            d.fingerprint, device_id="robot_imu", manifest_path="registry/devices/robot_imu.yaml"
        )

        lock_store = SqliteLockStore(mem_db)
        lock_svc = LockService(lock_store)
        result = lock_svc.acquire("robot_imu", owner="alice", operation="flash", ttl_seconds=60)
        assert result.created is True
        sid = result.lock.session_id

        # Try to acquire again from a different session — should fail (busy)
        from hive.common.errors import DeviceBusyError

        with pytest.raises(DeviceBusyError):
            lock_svc.acquire("robot_imu", owner="bob", operation="reset", ttl_seconds=60)

        # Release and re-acquire from a different session
        assert lock_svc.release("robot_imu", sid) is True
        result2 = lock_svc.acquire("robot_imu", owner="bob", operation="reset", ttl_seconds=60)
        assert result2.created is True

    def test_scan_sweeper_removes_abandoned_locks(self, mem_db):
        """End-to-end: expired locks are removed by the sweeper."""
        d = _discovered("303a", "1001", "X", "/dev/ttyACM0")
        reg = DeviceRegistry(mem_db)
        reg.upsert([d])

        lock_store = SqliteLockStore(mem_db)
        lock = Lock.new(device_id="robot_imu", owner="alice", operation="flash", ttl_seconds=60)
        # Force expiry
        lock.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        lock_store.put(lock)

        sweeper = LockSweeper(lock_store)
        removed = sweeper.sweep()
        assert removed == 1
        # Verify lock is gone
        assert lock_store.get("robot_imu") is None


class TestDiscoveryServiceWithRealDatabase:
    """DiscoveryService → DeviceRegistry without using a fake adapter.

    Uses real DiscoveryService construction; only the underlying
    adapters are mocked.
    """

    def test_service_with_fake_adapters_and_real_registry(self, mem_db):
        svc = DiscoveryService(
            usb_adapter=FakeAdapter(
                "usb",
                [
                    {
                        "source": "usb",
                        "usb_vid": "303a",
                        "usb_pid": "1001",
                        "serial_number": "REAL-001",
                        "serial_port": "/dev/ttyACM0",
                    },
                ],
            ),
            serial_adapter=FakeAdapter("serial", []),
        )

        devices = svc.scan()
        assert len(devices) == 1

        reg = DeviceRegistry(mem_db)
        reg.upsert(devices)
        stored = reg.list_devices()
        assert len(stored) == 1
        assert stored[0].device_id is None  # not claimed yet
        assert stored[0].serial_number == "REAL-001"

    def test_dedup_across_adapters_keeps_one_registry_row(self, mem_db):
        """Same device via USB and serial adapters → one DB row."""
        common = {
            "usb_vid": "303a",
            "usb_pid": "1001",
            "serial_number": "DEDUP-001",
            "serial_port": "/dev/ttyACM0",
        }
        svc = DiscoveryService(
            usb_adapter=FakeAdapter("usb", [{"source": "usb", **common}]),
            serial_adapter=FakeAdapter("serial", [{"source": "serial", **common}]),
        )
        devices = svc.scan()
        assert len(devices) == 1
        assert devices[0].source == "usb+serial"

        reg = DeviceRegistry(mem_db)
        count = reg.upsert(devices)
        assert count == 1
        stored = reg.list_devices()
        assert len(stored) == 1


class TestRegistryReScan:
    """Re-scanning updates last_seen_at but not discovered_at."""

    def test_rescan_updates_last_seen_keeps_discovered(self, mem_db):
        d = _discovered("303a", "1001", "X", "/dev/ttyACM0")
        reg = DeviceRegistry(mem_db)

        reg.upsert([d])
        rec1 = reg.get_by_fingerprint(d.fingerprint)
        discovered_at_1 = rec1.discovered_at

        import time

        time.sleep(0.05)
        reg.upsert([d])
        rec2 = reg.get_by_fingerprint(d.fingerprint)

        assert rec2.discovered_at == discovered_at_1
        assert rec2.last_seen_at >= discovered_at_1
