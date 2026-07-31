"""USB device enumeration via pyudev.

Adapter contract (see hive.discovery.base.Adapter):
    list_devices() -> list[dict]
        Return raw device records from the underlying transport.

    Each record is a flat dict that the DiscoveredDevice model
    can be built from. Keys:
        source: 'usb'
        usb_vid, usb_pid: 4-char hex (lowercase)
        serial_number: str | None
        usb_bus, usb_device: int
        usb_port_path: str  (e.g. "1-2.3")
        serial_port: str    (e.g. /dev/ttyACM0)
        serial_by_id: str | None  (e.g. /dev/serial/by-id/...)
        description, manufacturer, product: str | None

    The adapter does NOT construct DiscoveredDevice — that is the
    DiscoveryService's responsibility. This keeps the adapter pure
    data in / data out.

pyudev import strategy:
    Lazy import inside the class. If pyudev is not installed (e.g.
    on macOS or a minimal Linux container), the adapter raises a
    ImportError-like AdapterError at instantiation, not at module
    import time. This keeps `hive --version` working without pyudev.
"""

from __future__ import annotations

from typing import Any, Protocol

from hive.common.errors import HiveError


class AdapterError(HiveError):
    """Raised when an adapter cannot enumerate (missing dep, no permission, ...)."""


class Adapter(Protocol):
    """Protocol for discovery adapters.

    Implementations: UsbAdapter, SerialAdapter, SshAdapter.
    """

    source: str

    def list_devices(self) -> list[dict[str, Any]]:
        """Return raw device records. Empty list if none found."""
        ...


def _require_pyudev():
    try:
        import pyudev  # noqa: F401

        return pyudev
    except ImportError as e:
        raise AdapterError(
            "pyudev is required for USB discovery. "
            "Install with: pip install pyudev "
            "(also needs libudev-dev system package).",
            details={"missing_module": "pyudev"},
        ) from e


class UsbAdapter:
    """USB device enumeration via pyudev."""

    source = "usb"

    def __init__(self, context: Any | None = None) -> None:
        """Create a UsbAdapter.

        Args:
            context: optional pyudev.Context (useful for testing).
                     If None, a fresh Context is created.
        """
        pyudev = _require_pyudev()
        self._ctx = context if context is not None else pyudev.Context()

    def list_devices(self) -> list[dict[str, Any]]:
        """Enumerate all USB devices with a tty subsystem.

        We filter to SUBSYSTEM=="tty" because that gives us the
        device nodes (/dev/ttyACM*, /dev/ttyUSB*) plus the parent
        USB device attributes (VID, PID, serial).

        Non-serial USB devices (e.g. USB storage, USB HID) are out
        of scope for H1.
        """
        results: list[dict[str, Any]] = []
        for device in self._ctx.list_devices(subsystem="tty"):
            parent = device.find_parent("usb", "usb_device")
            if parent is None:
                # No USB parent — not a USB serial device (e.g. PCI tty)
                continue

            usb_vid = parent.attributes.get("idVendor")
            usb_pid = parent.attributes.get("idProduct")
            serial_number = parent.attributes.get("serial")

            # Normalize VID/PID: pyudev returns bytes
            vid_str = usb_vid.decode("utf-8", errors="replace").lower() if usb_vid else None
            pid_str = usb_pid.decode("utf-8", errors="replace").lower() if usb_pid else None
            serial_str = (
                serial_number.decode("utf-8", errors="replace").strip() if serial_number else None
            )
            if serial_str == "":
                serial_str = None

            # Bus / device numbers
            bus_str = parent.attributes.get("busnum")
            dev_str = parent.attributes.get("devnum")
            try:
                usb_bus = int(bus_str) if bus_str else None
            except (TypeError, ValueError):
                usb_bus = None
            try:
                usb_device = int(dev_str) if dev_str else None
            except (TypeError, ValueError):
                usb_device = None

            # Port path (e.g. "1-2.3") — useful for stable aliases
            try:
                usb_port_path = parent.device_path
            except AttributeError:
                usb_port_path = None

            # tty device node (e.g. /dev/ttyACM0)
            serial_port = device.device_node

            # /dev/serial/by-id/ symlink (very stable)
            serial_by_id = None
            try:
                for child in device.children:
                    if "by-id" in (child.device_path or ""):
                        serial_by_id = child.device_node
                        break
            except Exception:  # noqa: BLE001  — best-effort, never fail
                pass

            description = parent.attributes.get("product")
            manufacturer = parent.attributes.get("manufacturer")
            desc_str = description.decode("utf-8", errors="replace").strip() if description else None
            mfg_str = manufacturer.decode("utf-8", errors="replace").strip() if manufacturer else None
            if desc_str == "":
                desc_str = None
            if mfg_str == "":
                mfg_str = None

            results.append(
                {
                    "source": self.source,
                    "usb_vid": vid_str,
                    "usb_pid": pid_str,
                    "serial_number": serial_str,
                    "usb_bus": usb_bus,
                    "usb_device": usb_device,
                    "usb_port_path": usb_port_path,
                    "serial_port": serial_port,
                    "serial_by_id": serial_by_id,
                    "description": desc_str,
                    "manufacturer": mfg_str,
                    "product": desc_str,
                }
            )
        return results