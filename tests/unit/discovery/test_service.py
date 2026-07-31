"""Unit tests for hive.discovery.service.

These tests use mock adapters — no real USB/serial hardware required.
"""

from __future__ import annotations

from typing import Any

import pytest

from hive.discovery.service import DiscoveryService


class FakeAdapter:
    """In-memory adapter for tests."""

    def __init__(self, source: str, records: list[dict[str, Any]] | Exception) -> None:
        self.source = source
        self._records = records
        self._is_exception = isinstance(records, Exception)

    def list_devices(self) -> list[dict[str, Any]]:
        if self._is_exception:
            raise self._records  # type: ignore[misc]
        return list(self._records)  # type: ignore[arg-type]


def _record(source: str, **kwargs) -> dict[str, Any]:
    base = {"source": source}
    base.update(kwargs)
    return base


class TestDiscoveryServiceScan:
    def test_empty_scan(self):
        svc = DiscoveryService(
            usb_adapter=FakeAdapter("usb", []),
            serial_adapter=FakeAdapter("serial", []),
        )
        assert svc.scan() == []

    def test_usb_only(self):
        records = [
            _record(
                "usb",
                usb_vid="239a",
                usb_pid="811b",
                serial_number="ABC123",
                serial_port="/dev/ttyACM0",
            )
        ]
        svc = DiscoveryService(
            usb_adapter=FakeAdapter("usb", records),
            serial_adapter=FakeAdapter("serial", []),
        )
        devices = svc.scan()
        assert len(devices) == 1
        d = devices[0]
        assert d.source == "usb"
        assert d.usb_vid == "239a"
        assert d.has_strong_identity

    def test_serial_only(self):
        records = [
            _record(
                "serial",
                usb_vid="1a86",
                usb_pid="55d3",
                serial_number="CH9102",
                serial_port="/dev/ttyUSB0",
            )
        ]
        svc = DiscoveryService(
            usb_adapter=FakeAdapter("usb", []),
            serial_adapter=FakeAdapter("serial", records),
        )
        devices = svc.scan()
        assert len(devices) == 1
        d = devices[0]
        assert d.source == "serial"
        assert d.serial_port == "/dev/ttyUSB0"

    def test_dedup_same_device_usb_serial(self):
        """USB adapter and serial adapter both find the same device.

        They should be merged into one DiscoveredDevice.
        """
        rec_usb = _record(
            "usb",
            usb_vid="239a",
            usb_pid="811b",
            serial_number="ABC",
            serial_port="/dev/ttyACM0",
        )
        rec_serial = _record(
            "serial",
            usb_vid="239a",
            usb_pid="811b",
            serial_number="ABC",
            serial_port="/dev/ttyACM0",
        )
        svc = DiscoveryService(
            usb_adapter=FakeAdapter("usb", [rec_usb]),
            serial_adapter=FakeAdapter("serial", [rec_serial]),
        )
        devices = svc.scan()
        assert len(devices) == 1
        # source should be merged to "usb+serial"
        assert devices[0].source in ("usb+serial", "serial+usb")

    def test_dedup_two_different_devices(self):
        rec1 = _record("usb", usb_vid="239a", usb_pid="811b", serial_number="AAA")
        rec2 = _record("usb", usb_vid="239a", usb_pid="811b", serial_number="BBB")
        svc = DiscoveryService(
            usb_adapter=FakeAdapter("usb", [rec1, rec2]),
            serial_adapter=FakeAdapter("serial", []),
        )
        devices = svc.scan()
        assert len(devices) == 2

    def test_skips_records_without_identity(self):
        # A record with no VID/PID/serial/by_id/host is unidentifiable
        rec = _record("usb", serial_port="/dev/ttyACM0")  # only port
        svc = DiscoveryService(
            usb_adapter=FakeAdapter("usb", [rec]),
            serial_adapter=FakeAdapter("serial", []),
        )
        devices = svc.scan()
        assert devices == []  # skipped, not crashing

    def test_adapter_failure_continues(self):
        # Serial adapter raises, USB adapter returns a device.
        # Service should still return the USB device.
        rec = _record("usb", usb_vid="239a", usb_pid="811b", serial_number="X")
        svc = DiscoveryService(
            usb_adapter=FakeAdapter("usb", [rec]),
            serial_adapter=FakeAdapter("serial", RuntimeError("oops")),
        )
        devices = svc.scan()
        assert len(devices) == 1

    def test_all_adapters_fail_raises(self):
        svc = DiscoveryService(
            usb_adapter=FakeAdapter("usb", RuntimeError("usb broken")),
            serial_adapter=FakeAdapter("serial", RuntimeError("serial broken")),
        )
        from hive.discovery.service import DiscoveryError

        with pytest.raises(DiscoveryError):
            svc.scan()

    def test_devices_sorted_by_display_id(self):
        records = [
            _record("usb", usb_vid="239a", usb_pid="811b", serial_number="Z"),
            _record("usb", usb_vid="239a", usb_pid="811b", serial_number="A"),
        ]
        svc = DiscoveryService(
            usb_adapter=FakeAdapter("usb", records),
            serial_adapter=FakeAdapter("serial", []),
        )
        devices = svc.scan()
        # Display IDs depend on what's filled in; we just verify
        # the result is sorted somehow deterministically.
        ids = [d.display_id for d in devices]
        assert ids == sorted(ids)

    def test_include_serial_false(self):
        svc = DiscoveryService(
            include_usb=False,
            include_serial=False,
        )
        assert svc.scan() == []

    def test_include_usb_false(self):
        svc = DiscoveryService(
            include_usb=False,
            include_serial=False,
        )
        assert svc.scan() == []
