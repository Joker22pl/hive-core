"""SQLAlchemy ORM models for HIVE's SQLite registry.

Two tables in H1:

    devices — one row per discovered device (or claimed device_id).
              discovered_at: when we first saw it on the host.
              last_seen_at:  when we last saw it (updated on each scan).
              fingerprint:   stable join key with DiscoveredDevice.
              manifest_path: optional path to a YAML manifest that
                             fills in DeviceManifest fields (project, role, ...).
                             NULL = discovered but not registered.

    locks   — current lock per device_id. Mirrors Lock pydantic model.
              H1+ sweeper removes expired entries.

All datetimes are stored as ISO 8601 UTC strings. SQLite doesn't have
a native datetime type, and SQLAlchemy DateTime with timezone=True is
fragile on SQLite. Strings keep things simple and unambiguous.
"""

from __future__ import annotations

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy 2.x declarative base."""


class DeviceRecord(Base):
    """A device discovered on the host (USB / serial / SSH)."""

    __tablename__ = "devices"

    # Primary key
    fingerprint: Mapped[str] = mapped_column(String(64), primary_key=True)
    """Stable fingerprint (SHA-256 hex, 32 chars)."""

    # Identity
    device_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    """User-assigned ID (from manifest) once registered. NULL until then."""

    usb_vid: Mapped[str | None] = mapped_column(String(4), nullable=True)
    usb_pid: Mapped[str | None] = mapped_column(String(4), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)

    serial_port: Mapped[str | None] = mapped_column(String(256), nullable=True)
    serial_by_id: Mapped[str | None] = mapped_column(String(512), nullable=True)

    ssh_host: Mapped[str | None] = mapped_column(String(256), nullable=True)
    ssh_port: Mapped[int | None] = mapped_column(nullable=True)
    ssh_user: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Description
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(128), nullable=True)
    product: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Lifecycle
    discovered_at: Mapped[str] = mapped_column(String(32), nullable=False)
    last_seen_at: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    """Indexed for 'show recently seen devices' queries."""

    # Optional manifest reference (relative path inside the project)
    manifest_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Free-form notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_devices_usb", "usb_vid", "usb_pid", "serial_number"),
        Index("ix_devices_ssh", "ssh_host", "ssh_user"),
    )


class LockRecord(Base):
    """A lock held by an active session."""

    __tablename__ = "locks"

    device_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    owner: Mapped[str] = mapped_column(String(128), nullable=False)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    operation: Mapped[str] = mapped_column(String(128), nullable=False)
    acquired_at: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    """Indexed for the lock sweeper (WHERE expires_at < now)."""

    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)


__all__ = ["Base", "DeviceRecord", "LockRecord"]