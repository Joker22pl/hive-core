"""Lock sweeper — removes abandoned locks (H1).

The sweeper finds locks whose expires_at < now and removes them.
Call `sweep()` periodically (e.g. every 60s from a background thread
or before each acquire).

Why a sweeper is needed:
    Locks have a TTL (default 900s). A session that crashes or
    hangs may leave its lock past TTL. Without a sweeper, the lock
    would block further acquires until the next session restart.

    In-memory and JSON stores auto-expire on read. The SQLite store
    also auto-expires on read (in SqliteLockStore.get) but the sweeper
    ensures that list_active() and list_expired() are consistent
    with reality without paying the read-time check cost.
"""

from __future__ import annotations

import logging

from hive.locking.sqlite_store import SqliteLockStore

logger = logging.getLogger(__name__)


class LockSweeper:
    """Sweeper for expired locks in the SQLite store."""

    def __init__(self, store: SqliteLockStore) -> None:
        if not isinstance(store, SqliteLockStore):
            # Sweeper is meaningful only for the SQLite store — in-memory
            # and JSON stores auto-expire on read.
            raise TypeError(f"LockSweeper requires SqliteLockStore, got {type(store).__name__}")
        self._store = store

    def sweep(self) -> int:
        """Remove all expired locks. Returns count removed."""
        removed = self._store.sweep_expired()
        if removed:
            logger.info("LockSweeper removed %d expired lock(s)", removed)
        return removed

    def list_expired(self) -> list:
        """Return expired locks without removing them (for diagnostics)."""
        return self._store.list_expired()
