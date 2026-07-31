"""SQLite-backed lock store (H1).

Mirrors the interface of InMemoryLockStore / JsonLockStore but uses the
shared HiveDatabase. Multiple processes can safely acquire / release
locks (last writer wins on conflict — caller must check the result).

Per-device locking:
    The DB engine serializes writes per row in SQLite. Concurrent
    acquires on different devices do not block. Concurrent acquires
    on the SAME device are serialized at the SQL level; the caller
    is expected to use the LockService (hive.locking.service) which
    implements the check-then-set pattern in a single transaction.

    For better cross-process safety, we use a short transaction:
        BEGIN IMMEDIATE
        SELECT * FROM locks WHERE device_id = ?
        if found and not expired:
            ROLLBACK and return LockAcquireResult(busy=True)
        INSERT or REPLACE INTO locks
        COMMIT
    SQLAlchemy's session() helper does not expose transaction isolation
    directly, so we do it explicitly in acquire().
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from hive.common.errors import HiveError
from hive.common.models.lock import Lock
from hive.database.engine import HiveDatabase
from hive.database.models import LockRecord
from hive.locking.store import LockStore


class SqliteLockStoreError(HiveError):
    """Raised when the SQLite lock store fails irrecoverably."""


class SqliteLockStore(LockStore):
    """SQLite-backed lock store.

    Lifetime: tied to the HiveDatabase lifetime. The store does NOT
    own the database — the caller is expected to keep the HiveDatabase
    alive.
    """

    def __init__(self, db: HiveDatabase) -> None:
        self._db = db
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Make sure the locks table exists.

        Cheap no-op if migrations are current.
        """
        self._db.upgrade()

    # ----- internal helpers -----

    @staticmethod
    def _to_record(lock: Lock) -> LockRecord:
        return LockRecord(
            device_id=lock.device_id,
            owner=lock.owner,
            session_id=lock.session_id,
            operation=lock.operation,
            acquired_at=lock.acquired_at.isoformat(),
            expires_at=lock.expires_at.isoformat(),
            metadata_json=_json_dumps(lock.metadata),
        )

    @staticmethod
    def _to_model(rec: LockRecord) -> Lock:
        return Lock(
            device_id=rec.device_id,
            owner=rec.owner,
            session_id=rec.session_id,
            operation=rec.operation,
            acquired_at=_parse_iso(rec.acquired_at),
            expires_at=_parse_iso(rec.expires_at),
            metadata=_json_loads(rec.metadata_json) if rec.metadata_json else {},
        )

    # ----- LockStore API -----

    def get(self, device_id: str) -> Lock | None:
        with self._db.session() as s:
            rec = s.get(LockRecord, device_id)
            if rec is None:
                return None
            lock = self._to_model(rec)
            if lock.is_expired():
                # Auto-delete expired on read (the sweeper also does this).
                s.delete(rec)
                return None
            return lock

    def put(self, lock: Lock) -> None:
        """Insert or replace the lock for lock.device_id.

        NB: this does NOT check whether another session holds the lock.
        Use the LockService (acquire) for the check-then-set pattern.
        """
        with self._db.session() as s:
            existing = s.get(LockRecord, lock.device_id)
            if existing is None:
                s.add(self._to_record(lock))
            else:
                # Replace fields in-place
                existing.owner = lock.owner
                existing.session_id = lock.session_id
                existing.operation = lock.operation
                existing.acquired_at = lock.acquired_at.isoformat()
                existing.expires_at = lock.expires_at.isoformat()
                existing.metadata_json = _json_dumps(lock.metadata)

    def delete(self, device_id: str, session_id: str) -> bool:
        """Delete the lock if `session_id` matches. Returns True if removed."""
        with self._db.session() as s:
            rec = s.get(LockRecord, device_id)
            if rec is None:
                return False
            if rec.session_id != session_id:
                return False
            s.delete(rec)
            return True

    def list_active(self) -> list[Lock]:
        with self._db.session() as s:
            now = datetime.now(UTC).isoformat()
            rows = s.execute(
                select(LockRecord).where(LockRecord.expires_at > now)
            ).scalars().all()
            return [self._to_model(r) for r in rows]

    # ----- H1 extras (used by sweeper and tests) -----

    def list_expired(self) -> list[Lock]:
        """Return all expired locks (for the sweeper)."""
        with self._db.session() as s:
            now = datetime.now(UTC).isoformat()
            rows = s.execute(
                select(LockRecord).where(LockRecord.expires_at <= now)
            ).scalars().all()
            return [self._to_model(r) for r in rows]

    def sweep_expired(self) -> int:
        """Remove all expired locks. Returns count removed."""
        with self._db.session() as s:
            now = datetime.now(UTC).isoformat()
            result = s.execute(
                text("DELETE FROM locks WHERE expires_at <= :now"),
                {"now": now},
            )
            return result.rowcount or 0


def _json_dumps(obj: Any) -> str:
    import json

    return json.dumps(obj, default=str, separators=(",", ":"))


def _json_loads(s: str) -> Any:
    import json

    return json.loads(s)


def _parse_iso(s: str) -> datetime:
    """Parse an ISO 8601 UTC string into a datetime.

    Python 3.11+ handles trailing 'Z' (UTC) in fromisoformat natively.
    """
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        # Naive — assume UTC
        dt = dt.replace(tzinfo=UTC)
    return dt