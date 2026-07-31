"""Resource locking for HIVE.

H0: in-memory store + optional JSON-file persistence.
H1+: SQLite lock store with sweeper for abandoned locks.
"""

from hive.locking.service import (
    LockAcquireResult,
    LockService,
    acquire,
    list_active,
    release,
)
from hive.locking.store import InMemoryLockStore, JsonLockStore, LockStore

__all__ = [
    "InMemoryLockStore",
    "JsonLockStore",
    "LockAcquireResult",
    "LockService",
    "LockStore",
    "acquire",
    "list_active",
    "release",
]
