"""USB adapter skeleton (H0) — pyudev-backed discovery (H1+)."""

from __future__ import annotations

from dataclasses import dataclass

from hive.adapters.base import Adapter
from hive.common.errors import NotImplementedInStageError


@dataclass(frozen=True)
class UsbDeviceInfo:
    """A single observed USB device."""

    vid: str
    pid: str
    serial: str | None
    port: str | None
    stable_path: str | None


class UsbAdapter(Adapter):
    """USB discovery adapter (uses pyudev in H1+)."""

    name = "usb"

    def open(self) -> None:
        raise NotImplementedInStageError("UsbAdapter.open", "H1")

    def close(self) -> None:
        raise NotImplementedInStageError("UsbAdapter.close", "H1")

    def scan(self) -> list[UsbDeviceInfo]:
        """Enumerate USB devices. H0 raises NotImplementedInStageError."""
        raise NotImplementedInStageError("UsbAdapter.scan", "H1")
