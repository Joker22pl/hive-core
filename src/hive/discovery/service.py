"""DiscoveryService — orchestrates USB / serial / SSH adapters."""

from __future__ import annotations

import logging
from typing import Any

from hive.common.errors import HiveError
from hive.discovery.fingerprint import compute_fingerprint
from hive.discovery.models import DiscoveredDevice
from hive.discovery.serial import SerialAdapter
from hive.discovery.usb import UsbAdapter

logger = logging.getLogger(__name__)


class DiscoveryError(HiveError):
    """Raised when discovery fails irrecoverably."""


class DiscoveryService:
    """Discovers USB / serial / SSH devices on the local host.

    H1: USB via pyudev, serial via pyserial.
    H4+: SSH via paramiko (SshAdapter).

    Usage:
        svc = DiscoveryService()
        devices = svc.scan()  # list[DiscoveredDevice]
    """

    def __init__(
        self,
        *,
        usb_adapter: UsbAdapter | None = None,
        serial_adapter: SerialAdapter | None = None,
        ssh_adapter: Any | None = None,
        include_usb: bool = True,
        include_serial: bool = True,
        include_ssh: bool = False,
    ) -> None:
        """Create a DiscoveryService.

        Args:
            usb_adapter: override for the default UsbAdapter (useful for tests).
            serial_adapter: override for the default SerialAdapter.
            ssh_adapter: H4+ SshAdapter.
            include_usb: include pyudev enumeration.
            include_serial: include pyserial enumeration.
            include_ssh: include SSH enumeration (off by default in H1).
        """
        self._usb = usb_adapter if usb_adapter is not None else (UsbAdapter() if include_usb else None)
        self._serial = (
            serial_adapter
            if serial_adapter is not None
            else (SerialAdapter() if include_serial else None)
        )
        self._ssh = ssh_adapter if ssh_adapter is not None else (ssh_adapter if include_ssh else None)

    def scan(self) -> list[DiscoveredDevice]:
        """Scan all enabled adapters and return deduplicated devices.

        Deduplication: two records with the same fingerprint are
        merged — the union of fields is taken (first non-null wins).
        """
        records: list[dict[str, Any]] = []
        errors: list[Exception] = []

        for name, adapter in (("usb", self._usb), ("serial", self._serial), ("ssh", self._ssh)):
            if adapter is None:
                continue
            try:
                records.extend(adapter.list_devices())
            except Exception as e:  # noqa: BLE001  — adapter failure is not fatal
                logger.warning("Adapter %s failed: %s", name, e)
                errors.append(e)

        # Build DiscoveredDevice objects with fingerprint
        devices_by_fp: dict[str, DiscoveredDevice] = {}
        for rec in records:
            try:
                fp = compute_fingerprint(
                    source=rec["source"],
                    usb_vid=rec.get("usb_vid"),
                    usb_pid=rec.get("usb_pid"),
                    serial_number=rec.get("serial_number"),
                    serial_by_id=rec.get("serial_by_id"),
                    ssh_host=rec.get("ssh_host"),
                    ssh_port=rec.get("ssh_port"),
                    ssh_user=rec.get("ssh_user"),
                )
            except ValueError as e:
                # Record has no identifying fields — skip with warning.
                logger.warning(
                    "Skipping device record with no identity: %s (error: %s)",
                    {k: v for k, v in rec.items() if k != "description"},
                    e,
                )
                continue

            existing = devices_by_fp.get(fp)
            if existing is None:
                devices_by_fp[fp] = DiscoveredDevice(fingerprint=fp, **rec)
            else:
                # Merge: first non-null wins for each field.
                merged = _merge(existing.model_dump(), rec)
                # Remove fingerprint from the merged dict — it's a
                # computed field, not a record field, and we pass it
                # explicitly to the constructor.
                merged.pop("fingerprint", None)
                devices_by_fp[fp] = DiscoveredDevice(fingerprint=fp, **merged)

        devices = sorted(devices_by_fp.values(), key=lambda d: d.display_id)

        if errors and not devices:
            # All adapters failed AND we got nothing
            raise DiscoveryError(
                "All discovery adapters failed",
                details={"errors": [str(e) for e in errors]},
            )

        return devices


def _merge(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Merge two device record dicts (first non-null wins per field).

    The 'source' field is merged specially: both sources are concatenated
    with a '+' separator, e.g. 'usb+serial'.

    The 'fingerprint' is taken from the caller (computed from the
    canonical tuple of identifying fields) — this function does not
    touch it.
    """
    out = dict(a)
    for k, v in b.items():
        if k in ("source", "fingerprint"):
            continue  # handled separately or by the caller
        cur = out.get(k)
        if cur in (None, "", 0) and v not in (None, ""):
            out[k] = v
        elif cur not in (None, "") and v not in (None, "") and cur != v:
            # Conflict — prefer the more specific (non-zero, non-empty) value.
            # If both are set and different, prefer the first one (deterministic).
            pass
    src_a = a.get("source")
    src_b = b.get("source")
    if src_a and src_b and src_a != src_b:
        out["source"] = f"{src_a}+{src_b}"
    elif src_b and not src_a:
        out["source"] = src_b
    return out