"""Device registry — persist discovered devices and resolve them to manifests.

H1 introduces DeviceRegistry:
    * scan_and_persist(discovery) — runs discovery + upserts into SQLite
    * resolve(fingerprint) — returns (DeviceRecord, DeviceManifest | None)
    * list_devices() — all known devices
    * claim(fingerprint, device_id, manifest_path) — assign a logical name

A "claimed" device has both a DiscoveredDevice record (auto-populated
from scan) AND a DeviceManifest (from a YAML file in registry/).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from hive.common.errors import HiveError
from hive.database.engine import HiveDatabase
from hive.database.models import DeviceRecord
from hive.discovery.models import DiscoveredDevice


class RegistryError(HiveError):
    """Raised when a registry operation fails."""


class DeviceRegistry:
    """SQLite-backed device registry.

    Acts as the persistent bridge between DiscoveryService (transient
    scan results) and DeviceManifest (declarative metadata from YAML
    files).
    """

    def __init__(self, db: HiveDatabase) -> None:
        self._db = db
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self._db.upgrade()

    def upsert(self, devices: list[DiscoveredDevice]) -> int:
        """Insert or update device records. Returns count upserted.

        A device is matched by `fingerprint`. New devices get a fresh
        discovered_at; existing devices have last_seen_at updated.
        All other fields are updated from the scan (first non-null wins).
        """
        if not devices:
            return 0
        now = datetime.now(UTC).isoformat()
        with self._db.session() as s:
            count = 0
            for dev in devices:
                fp = dev.fingerprint
                rec = s.get(DeviceRecord, fp)
                if rec is None:
                    rec = DeviceRecord(
                        fingerprint=fp,
                        discovered_at=now,
                        last_seen_at=now,
                    )
                    s.add(rec)
                rec.last_seen_at = now
                # Update identity fields (first non-null wins from scan)
                if dev.usb_vid is not None:
                    rec.usb_vid = dev.usb_vid
                if dev.usb_pid is not None:
                    rec.usb_pid = dev.usb_pid
                if dev.serial_number is not None:
                    rec.serial_number = dev.serial_number
                if dev.serial_port is not None:
                    rec.serial_port = dev.serial_port
                if dev.serial_by_id is not None:
                    rec.serial_by_id = dev.serial_by_id
                if dev.ssh_host is not None:
                    rec.ssh_host = dev.ssh_host
                if dev.ssh_port is not None:
                    rec.ssh_port = dev.ssh_port
                if dev.ssh_user is not None:
                    rec.ssh_user = dev.ssh_user
                if dev.description is not None:
                    rec.description = dev.description
                if dev.manufacturer is not None:
                    rec.manufacturer = dev.manufacturer
                if dev.product is not None:
                    rec.product = dev.product
                count += 1
        return count

    def list_devices(self) -> list[DeviceRecord]:
        """Return all known devices (sorted by last_seen_at desc)."""
        with self._db.session() as s:
            from sqlalchemy import select

            rows = (
                s.execute(select(DeviceRecord).order_by(DeviceRecord.last_seen_at.desc()))
                .scalars()
                .all()
            )
            return list(rows)

    def get_by_fingerprint(self, fingerprint: str) -> DeviceRecord | None:
        with self._db.session() as s:
            return s.get(DeviceRecord, fingerprint)

    def claim(
        self,
        fingerprint: str,
        *,
        device_id: str,
        manifest_path: str | Path | None = None,
    ) -> DeviceRecord:
        """Claim a discovered device — assign it a logical device_id.

        Args:
            fingerprint: the discovered device's fingerprint
            device_id: the logical name (from a DeviceManifest)
            manifest_path: optional path to the manifest YAML

        Raises:
            RegistryError: fingerprint not found.
        """
        with self._db.session() as s:
            rec = s.get(DeviceRecord, fingerprint)
            if rec is None:
                raise RegistryError(
                    f"No device with fingerprint {fingerprint!r}. Run `hive device scan` first.",
                    details={"fingerprint": fingerprint},
                )
            rec.device_id = device_id
            if manifest_path is not None:
                rec.manifest_path = str(manifest_path)
            return rec
