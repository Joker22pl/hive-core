"""Unit tests for hive.discovery.serial — pyserial adapter with filter logic."""

from __future__ import annotations

from typing import Any

import pytest

from hive.discovery.serial import SerialAdapter


class FakePortInfo:
    """Mimics serial.tools.list_ports.ListPortInfo for testing."""

    def __init__(
        self,
        device: str,
        *,
        vid: int | None = None,
        pid: int | None = None,
        serial_number: str | None = None,
        location: str | None = None,
        description: str | None = None,
        manufacturer: str | None = None,
        product: str | None = None,
        interface: str | None = None,
    ) -> None:
        self.device = device
        self.vid = vid
        self.pid = pid
        self.serial_number = serial_number
        self.location = location
        self.description = description
        self.manufacturer = manufacturer
        self.product = product
        self.interface = interface
        # pyserial populates .serial_by_id lazily — keep None for tests.


class FakeListPorts:
    """In-memory replacement for pyserial.tools.list_ports."""

    def __init__(self, ports: list[FakePortInfo]) -> None:
        self._ports = ports

    def comports(self) -> list[FakePortInfo]:
        return list(self._ports)


@pytest.fixture
def adapter_with():
    """Factory that returns a SerialAdapter pre-loaded with fake ports."""

    def _factory(ports: list[FakePortInfo]) -> SerialAdapter:
        adp = SerialAdapter.__new__(SerialAdapter)
        adp._list_ports = FakeListPorts(ports)  # type: ignore[attr-defined]
        return adp

    return _factory


class TestSerialAdapterFilter:
    def test_includes_port_with_vid_pid(self, adapter_with):
        # ESP32 with VID/PID — always included
        port = FakePortInfo(
            "/dev/ttyACM0",
            vid=0x303A,
            pid=0x1001,
            serial_number="ABC123",
            description="ESP32-S3",
            manufacturer="Espressif",
        )
        adp = adapter_with([port])
        results = adp.list_devices()
        assert len(results) == 1
        assert results[0]["usb_vid"] == "303a"
        assert results[0]["usb_pid"] == "1001"
        assert results[0]["serial_port"] == "/dev/ttyACM0"

    def test_includes_ttyusb_even_without_vid(self, adapter_with):
        # /dev/ttyUSB* without VID/PID — included (likely a CH340 clone)
        port = FakePortInfo("/dev/ttyUSB0")
        adp = adapter_with([port])
        results = adp.list_devices()
        assert len(results) == 1
        assert results[0]["serial_port"] == "/dev/ttyUSB0"

    def test_includes_ttyacm_even_without_vid(self, adapter_with):
        port = FakePortInfo("/dev/ttyACM3")
        adp = adapter_with([port])
        results = adp.list_devices()
        assert len(results) == 1

    def test_excludes_kernel_uart(self, adapter_with):
        # /dev/ttyS* without VID/PID — kernel internal UART, skip
        port = FakePortInfo("/dev/ttyS4")
        adp = adapter_with([port])
        results = adp.list_devices()
        assert results == []

    def test_excludes_ttyprintk(self, adapter_with):
        port = FakePortInfo("/dev/ttyprintk")
        adp = adapter_with([port])
        results = adp.list_devices()
        assert results == []

    def test_mixed_ports(self, adapter_with):
        ports = [
            FakePortInfo("/dev/ttyACM0", vid=0x303A, pid=0x1001),  # included
            FakePortInfo("/dev/ttyUSB0"),  # included (no VID)
            FakePortInfo("/dev/ttyS0"),  # excluded
            FakePortInfo("/dev/ttyS4"),  # excluded
            FakePortInfo("/dev/ttyACM1"),  # included
        ]
        adp = adapter_with(ports)
        results = adp.list_devices()
        assert len(results) == 3
        devices = [r["serial_port"] for r in results]
        assert "/dev/ttyACM0" in devices
        assert "/dev/ttyUSB0" in devices
        assert "/dev/ttyACM1" in devices
        assert "/dev/ttyS0" not in devices

    def test_empty_list(self, adapter_with):
        adp = adapter_with([])
        assert adp.list_devices() == []

    def test_serial_by_id_passed_through(self, adapter_with):
        port = FakePortInfo("/dev/ttyACM0", vid=0x303A, pid=0x1001)
        # Manually set serial_by_id (pyserial populates it lazily)
        port.serial_by_id = "/dev/serial/by-id/usb-Espressif_USB_JTAG_ABC-if00"  # type: ignore[attr-defined]
        adp = adapter_with([port])
        results = adp.list_devices()
        assert results[0]["serial_by_id"] == "/dev/serial/by-id/usb-Espressif_USB_JTAG_ABC-if00"


class TestSerialAdapterImportGuard:
    def test_import_failure_raises_hive_error(self, monkeypatch):
        # Force pyserial import to fail
        import sys

        monkeypatch.delitem(sys.modules, "serial.tools.list_ports", raising=False)

        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if name == "serial.tools.list_ports" or name.startswith("serial."):
                raise ImportError("simulated pyserial missing")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)
        with pytest.raises(Exception):  # HiveError
            SerialAdapter()