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
from hive.locking.sqlite_store import SqliteLockStore, SqliteLockStoreError
from hive.locking.store import InMemoryLockStore, JsonLockStore, LockStore
from hive.locking.sweeper import LockSweeper

__all__ = [
    "InMemoryLockStore",
    "JsonLockStore",
    "LockAcquireResult",
    "LockService",
    "LockStore",
    "LockSweeper",
    "SqliteLockStore",
    "SqliteLockStoreError",
    "acquire",
    "list_active",
    "release",
]
