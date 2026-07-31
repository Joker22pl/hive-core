"""Fingerprint computation for DiscoveredDevice.

The fingerprint is a SHA-256 hex of the canonical tuple of identifying
fields. It MUST be stable across scans of the same physical device.

Algorithm:
1. Build a canonical tuple from the relevant identifying fields.
2. Sort and serialize as JSON.
3. SHA-256 hash, lowercase hex, first 32 chars.

We deliberately exclude fields that can change between scans:
  * serial_port (kernel-assigned, can change across reboots)
  * usb_bus, usb_device (kernel-assigned)
  * description, manufacturer, product (free-form)
  * stable_path (this IS the udev alias — circular if we hash it)
  * serial_baud (depends on user init)

Included in the fingerprint:
  * source (transport class — USB vs serial vs SSH)
  * usb_vid, usb_pid, serial_number (USB identity)
  * serial_by_id (kernel-stable identifier for USB serial)
  * ssh_host, ssh_port, ssh_user (for SSH hosts)

The fingerprint is the join key between scan results and registry entries.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def compute_fingerprint(
    *,
    source: str,
    usb_vid: str | None = None,
    usb_pid: str | None = None,
    serial_number: str | None = None,
    serial_by_id: str | None = None,
    ssh_host: str | None = None,
    ssh_port: int | None = None,
    ssh_user: str | None = None,
) -> str:
    """Compute the canonical fingerprint for a device.

    Returns 32 lowercase hex characters (first 128 bits of SHA-256).

    The fingerprint is INDEPENDENT of `source` — the same physical
    device discovered via pyudev and pyserial must produce the same
    fingerprint so the discovery service can deduplicate them. The
    `source` field is still recorded on the DiscoveredDevice (and
    merged as "usb+serial" when found by both).

    Raises ValueError if no identifying field is provided (cannot
    fingerprint a device with no identity).
    """
    parts: dict[str, Any] = {}

    if usb_vid is not None:
        parts["usb_vid"] = usb_vid.lower()
    if usb_pid is not None:
        parts["usb_pid"] = usb_pid.lower()
    if serial_number is not None:
        parts["serial_number"] = serial_number
    if serial_by_id is not None:
        parts["serial_by_id"] = serial_by_id
    if ssh_host is not None:
        parts["ssh_host"] = ssh_host
    if ssh_port is not None:
        parts["ssh_port"] = ssh_port
    if ssh_user is not None:
        parts["ssh_user"] = ssh_user

    if not parts:
        raise ValueError(
            "Cannot fingerprint a device with no identifying fields "
            "(need at least one of: usb_vid+usb_pid, serial_number, "
            "serial_by_id, ssh_host)."
        )

    # sort_keys=True ensures canonical serialization
    canonical = json.dumps(parts, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]
