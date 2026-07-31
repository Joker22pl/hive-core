"""Lock store interfaces and in-memory / JSON implementations."""

from __future__ import annotations

import json
import threading
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path

from hive.common.models.lock import Lock


class LockStore(ABC):
    """Abstract lock store."""

    @abstractmethod
    def get(self, device_id: str) -> Lock | None:
        """Return the active lock for `device_id`, or None."""

    @abstractmethod
    def put(self, lock: Lock) -> None:
        """Insert or replace the lock for `lock.device_id`."""

    @abstractmethod
    def delete(self, device_id: str, session_id: str) -> bool:
        """Delete the lock if `session_id` matches. Returns True if removed."""

    @abstractmethod
    def list_active(self) -> list[Lock]:
        """Return all non-expired locks."""


class InMemoryLockStore(LockStore):
    """Thread-safe in-memory lock store. Loses state on restart."""

    def __init__(self) -> None:
        self._locks: dict[str, Lock] = {}
        self._lock = threading.Lock()

    def get(self, device_id: str) -> Lock | None:
        with self._lock:
            lock = self._locks.get(device_id)
            if lock and lock.is_expired():
                self._locks.pop(device_id, None)
                return None
            return lock

    def put(self, lock: Lock) -> None:
        with self._lock:
            self._locks[lock.device_id] = lock

    def delete(self, device_id: str, session_id: str) -> bool:
        with self._lock:
            existing = self._locks.get(device_id)
            if existing is None:
                return False
            if existing.session_id != session_id:
                return False
            self._locks.pop(device_id, None)
            return True

    def list_active(self) -> list[Lock]:
        with self._lock:
            now = datetime.now(UTC)
            return [lock for lock in self._locks.values() if not lock.is_expired(now)]


class JsonLockStore(LockStore):
    """JSON-file backed lock store. Single-process only (H0).

    Suitable for single-user, single-process operation. Concurrent access
    from multiple processes is NOT safe (H1+ will move to SQLite).
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("{}", encoding="utf-8")

    def _read(self) -> dict[str, dict]:
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _write(self, data: dict[str, dict]) -> None:
        self._path.write_text(
            json.dumps(data, indent=2, default=str),
            encoding="utf-8",
        )

    def get(self, device_id: str) -> Lock | None:
        data = self._read()
        raw = data.get(device_id)
        if raw is None:
            return None
        lock = Lock.model_validate(raw)
        if lock.is_expired():
            self.delete(device_id, lock.session_id)
            return None
        return lock

    def put(self, lock: Lock) -> None:
        data = self._read()
        data[lock.device_id] = lock.model_dump(mode="json")
        self._write(data)

    def delete(self, device_id: str, session_id: str) -> bool:
        data = self._read()
        existing = data.get(device_id)
        if existing is None:
            return False
        if existing.get("session_id") != session_id:
            return False
        data.pop(device_id, None)
        self._write(data)
        return True

    def list_active(self) -> list[Lock]:
        data = self._read()
        now = datetime.now(UTC)
        result = []
        for raw in data.values():
            lock = Lock.model_validate(raw)
            if not lock.is_expired(now):
                result.append(lock)
        return result
