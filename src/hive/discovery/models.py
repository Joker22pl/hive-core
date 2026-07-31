"""Pydantic model for a discovered device (USB or serial transport)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# VID/PID / serial validation patterns (mirrored from DeviceManifest)
# ---------------------------------------------------------------------------

import re as _re

_VID_PID_RE = _re.compile(r"^[0-9A-Fa-f]{4}$")


def _normalize_vid_pid(v: str | None) -> str | None:
    """Normalize VID/PID to lowercase 4-char hex."""
    if v is None:
        return None
    s = v.lower().lstrip("0x")
    if not _VID_PID_RE.match(s):
        raise ValueError(f"Invalid VID/PID: {v!r} (must be 4 hex chars)")
    return s


class DiscoveredDevice(BaseModel):
    """A device discovered on the local host (USB / serial / network).

    Fields are intentionally narrow: only what scan() can determine
    empirically without any external manifest. Manifest-derived fields
    (project, role, capabilities, ...) are filled in later by
    `DeviceRegistry.resolve()`.

    The `fingerprint` is a stable hash of the identifying tuple. Two
    scans of the same physical device always produce the same fingerprint
    (assuming the serial number is stable).
    """

    model_config = ConfigDict(extra="forbid")

    # Source
    source: str = Field(min_length=1)
    """How the device was found.

    Standard values: 'usb', 'serial', 'ssh'.

    Multi-source: when the same device is found by multiple adapters
    (e.g. pyudev AND pyserial both see the same USB serial port), the
    sources are concatenated with '+', e.g. 'usb+serial'. The '+'
    separator lets the CLI display 'seen by USB + Serial'.
    """

    # Identity (USB)
    usb_vid: str | None = None
    usb_pid: str | None = None
    serial_number: str | None = None

    # Identity (serial transport only)
    serial_port: str | None = None  # e.g. /dev/ttyACM0
    serial_baud: int | None = None
    serial_by_id: str | None = None  # e.g. /dev/serial/by-id/usb-...

    # Identity (USB)
    usb_bus: int | None = None
    usb_device: int | None = None
    usb_port_path: str | None = None  # e.g. "1-2.3"

    # Optional stable alias assigned via udev rule
    stable_path: str | None = None

    # Identity (SSH)
    ssh_host: str | None = None
    ssh_port: int | None = None
    ssh_user: str | None = None
    ssh_host_key_fingerprint: str | None = None

    # Description (free-form, from kernel / udev)
    description: str | None = None
    manufacturer: str | None = None
    product: str | None = None

    # Computed
    fingerprint: str = Field(min_length=8, max_length=128)
    """Stable identifier across scans. SHA-256 hex of the canonical tuple."""

    # Validation
    @field_validator("usb_vid", "usb_pid")
    @classmethod
    def _validate_vid_pid(cls, v: str | None) -> str | None:
        return _normalize_vid_pid(v)

    @field_validator("fingerprint")
    @classmethod
    def _validate_fp(cls, v: str) -> str:
        if not _re.match(r"^[0-9a-f]{16,128}$", v):
            raise ValueError("fingerprint must be lowercase hex (16-128 chars)")
        return v

    @property
    def has_strong_identity(self) -> bool:
        """Strong identification requires (VID + PID) + serial.

        Per ADR-0003, strong identity is required for autonomous flashing.
        """
        return bool(self.usb_vid and self.usb_pid and self.serial_number)

    @property
    def display_id(self) -> str:
        """Human-friendly identifier for CLI tables."""
        if self.stable_path:
            return self.stable_path
        if self.serial_by_id:
            return self.serial_by_id
        if self.serial_port:
            return self.serial_port
        if self.ssh_host:
            return f"{self.ssh_user}@{self.ssh_host}:{self.ssh_port or 22}"
        return self.fingerprint[:16]