"""Serial port enumeration via pyserial.

pyserial.tools.list_ports.comports() returns a list of ListPortInfo
objects. We convert each to a dict compatible with DiscoveredDevice.

pyserial tries multiple backends:
  1. serial.tools.list_ports.grep() / comports() — uses pyudev on Linux
  2. Falls back to /dev scan on Linux
  3. Registry scan on Windows
  4. IOKit on macOS

We use pyserial's automatic detection. It is the same back-end that
most embedded tooling (esptool, mpremote, picotool) uses.

Why pyserial in addition to pyudev?
  * pyserial resolves VID/PID on macOS (where pyudev is unavailable)
  * pyserial resolves descriptions on Windows (for dev on that OS)
  * pyserial's list_ports is reliable even when pyudev is misconfigured
  * Redundancy is cheap and helps catch kernel driver bugs

Note: on Linux, pyserial uses pyudev under the hood. So the USB
adapters will see the same devices. We deduplicate in
DiscoveryService.scan() by fingerprint.
"""

from __future__ import annotations

from typing import Any


def _require_pyserial():
    try:
        import serial.tools.list_ports  # noqa: F401

        return serial.tools.list_ports
    except ImportError as e:
        from hive.common.errors import HiveError

        raise HiveError(
            "pyserial is required for serial port enumeration. "
            "Install with: pip install pyserial",
            details={"missing_module": "pyserial"},
        ) from e


class SerialAdapter:
    """Serial port enumeration via pyserial."""

    source = "serial"

    def __init__(self) -> None:
        """Create a SerialAdapter.

        pyserial.tools.list_ports.comports() is the workhorse. It uses
        pyudev internally on Linux when available, so the SerialAdapter
        and UsbAdapter will see the same set of tty devices.
        """
        self._list_ports = _require_pyserial()

    def list_devices(self) -> list[dict[str, Any]]:
        """Enumerate all serial ports visible to pyserial."""
        results: list[dict[str, Any]] = []
        for port in self._list_ports.comports():
            # ListPortInfo fields:
            #   device: str (e.g. "/dev/ttyACM0")
            #   name:   str (e.g. "ttyACM0")
            #   description: str (e.g. "Adafruit Feather ESP32-S3")
            #   hwid:   str (e.g. "USB VID:PID=239a:811b SER=ABC123 LOCATION=1-2.3")
            #   vid:    int | None
            #   pid:    int | None
            #   serial_number: str | None
            #   location: str | None  (e.g. "1-2.3")
            #   manufacturer: str | None
            #   product: str | None
            #   interface: str | None

            vid_int = getattr(port, "vid", None)
            pid_int = getattr(port, "pid", None)
            usb_vid = f"{vid_int:04x}" if vid_int is not None else None
            usb_pid = f"{pid_int:04x}" if pid_int is not None else None

            serial_number = getattr(port, "serial_number", None) or None
            serial_by_id = None
            # pyserial exposes serial_by_id only on POSIX
            serial_by_id_attr = getattr(port, "serial_by_id", None)
            if serial_by_id_attr:
                serial_by_id = serial_by_id_attr

            results.append(
                {
                    "source": self.source,
                    "usb_vid": usb_vid,
                    "usb_pid": usb_pid,
                    "serial_number": serial_number,
                    "usb_bus": None,
                    "usb_device": None,
                    "usb_port_path": getattr(port, "location", None) or None,
                    "serial_port": port.device,
                    "serial_by_id": serial_by_id,
                    "description": port.description or None,
                    "manufacturer": getattr(port, "manufacturer", None) or None,
                    "product": getattr(port, "product", None) or None,
                }
            )
        return results