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
        import serial.tools.list_ports

        return serial.tools.list_ports
    except ImportError as e:
        from hive.common.errors import HiveError

        raise HiveError(
            "pyserial is required for serial port enumeration. Install with: pip install pyserial",
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
        """Enumerate all serial ports visible to pyserial.

        Filters out ports that are clearly not USB-attached (no VID/PID
        AND not in the typical USB-serial naming patterns /dev/ttyUSB*
        or /dev/ttyACM*). This avoids surfacing kernel-internal UARTs
        (e.g. /dev/ttyS*) which have no discoverable identity.
        """
        results: list[dict[str, Any]] = []
        for port in self._list_ports.comports():
            vid_int = getattr(port, "vid", None)
            pid_int = getattr(port, "pid", None)
            device_path = port.device or ""

            # Filter: must have VID/PID OR be in a USB-serial naming pattern
            has_vid_pid = vid_int is not None and pid_int is not None
            looks_like_usb_serial = (
                "/dev/ttyUSB" in device_path
                or "/dev/ttyACM" in device_path
                or "/dev/bus/usb" in device_path
            )
            if not has_vid_pid and not looks_like_usb_serial:
                # Kernel UART or other non-USB serial — skip silently.
                continue

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
