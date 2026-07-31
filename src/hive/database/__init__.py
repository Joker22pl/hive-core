"""Database layer — SQLite via SQLAlchemy 2.x with hand-rolled migrations.

H1 introduces:
    * HiveDatabase     — engine + session factory + initialization
    * Base             — SQLAlchemy declarative base
    * DeviceRecord     — a discovered device persisted in SQLite
    * LockRecord       — a lock persisted in SQLite
    * upgrade_to_head  — applies pending migrations (H1: single revision)
    * DeviceRegistry   — bridge between DiscoveredDevice and the DB

The DB file defaults to ~/.local/share/hive/hive.db (XDG).
Override via env HIVE_DB_URL (e.g. 'sqlite:///:memory:' for tests).
"""

from __future__ import annotations

from hive.database.engine import DatabaseError, HiveDatabase
from hive.database.migrations import CURRENT_REVISION, upgrade_to_head
from hive.database.models import Base, DeviceRecord, LockRecord
from hive.database.registry import DeviceRegistry, RegistryError

__all__ = [
    "CURRENT_REVISION",
    "Base",
    "DatabaseError",
    "DeviceRecord",
    "DeviceRegistry",
    "HiveDatabase",
    "LockRecord",
    "RegistryError",
    "upgrade_to_head",
]
