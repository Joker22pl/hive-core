"""Unit tests for hive.locking.sqlite_store + sweeper."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from hive.common.models.lock import Lock
from hive.database.engine import HiveDatabase
from hive.locking.sqlite_store import SqliteLockStore
from hive.locking.store import InMemoryLockStore
from hive.locking.sweeper import LockSweeper


@pytest.fixture
def mem_db() -> HiveDatabase:
    db = HiveDatabase.from_url("sqlite:///:memory:")
    db.upgrade()
    return db


@pytest.fixture
def store(mem_db) -> SqliteLockStore:
    return SqliteLockStore(mem_db)


class TestSqliteLockStore:
    def test_put_and_get(self, store):
        lock = Lock.new(device_id="d1", owner="alice", operation="flash", ttl_seconds=60)
        store.put(lock)
        got = store.get("d1")
        assert got is not None
        assert got.session_id == lock.session_id
        assert got.owner == "alice"

    def test_get_missing(self, store):
        assert store.get("nonexistent") is None

    def test_put_replaces_existing(self, store):
        l1 = Lock.new(device_id="d1", owner="alice", operation="flash")
        l2 = Lock.new(device_id="d1", owner="bob", operation="reset")
        store.put(l1)
        store.put(l2)
        got = store.get("d1")
        assert got.owner == "bob"

    def test_delete_matching_session(self, store):
        lock = Lock.new(device_id="d1", owner="alice", operation="flash")
        store.put(lock)
        assert store.delete("d1", lock.session_id) is True
        assert store.get("d1") is None

    def test_delete_wrong_session(self, store):
        lock = Lock.new(device_id="d1", owner="alice", operation="flash")
        store.put(lock)
        assert store.delete("d1", "wrong-session-id") is False
        # Lock should still be there
        assert store.get("d1") is not None

    def test_delete_missing(self, store):
        assert store.delete("nonexistent", "any") is False

    def test_get_returns_none_for_expired_and_deletes(self, store):
        # Create a lock that's already expired
        lock = Lock.new(device_id="d1", owner="alice", operation="flash")
        lock.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        store.put(lock)
        # get() should auto-delete and return None
        assert store.get("d1") is None
        # And subsequent get() should also be None
        assert store.get("d1") is None

    def test_list_active_excludes_expired(self, store):
        active = Lock.new(device_id="d1", owner="alice", operation="flash", ttl_seconds=60)
        expired = Lock.new(device_id="d2", owner="bob", operation="reset")
        expired.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        store.put(active)
        store.put(expired)
        result = store.list_active()
        assert len(result) == 1
        assert result[0].device_id == "d1"

    def test_list_expired(self, store):
        active = Lock.new(device_id="d1", owner="alice", operation="flash", ttl_seconds=60)
        expired = Lock.new(device_id="d2", owner="bob", operation="reset")
        expired.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        store.put(active)
        store.put(expired)
        expired_list = store.list_expired()
        assert len(expired_list) == 1
        assert expired_list[0].device_id == "d2"

    def test_sweep_expired_removes_only_expired(self, store):
        active = Lock.new(device_id="d1", owner="alice", operation="flash", ttl_seconds=60)
        expired = Lock.new(device_id="d2", owner="bob", operation="reset")
        expired.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        store.put(active)
        store.put(expired)
        removed = store.sweep_expired()
        assert removed == 1
        # Active lock should still be there
        assert store.get("d1") is not None
        # Expired lock should be gone
        assert store.get("d2") is None

    def test_metadata_roundtrip(self, store):
        lock = Lock.new(
            device_id="d1",
            owner="alice",
            operation="flash",
            metadata={"key": "value", "count": 42},
        )
        store.put(lock)
        got = store.get("d1")
        assert got.metadata == {"key": "value", "count": 42}


class TestLockSweeper:
    def test_sweeper_calls_store(self, store):
        expired = Lock.new(device_id="d1", owner="alice", operation="flash")
        expired.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        store.put(expired)
        sweeper = LockSweeper(store)
        assert sweeper.sweep() == 1

    def test_sweeper_no_expired_returns_zero(self, store):
        lock = Lock.new(device_id="d1", owner="alice", operation="flash", ttl_seconds=60)
        store.put(lock)
        sweeper = LockSweeper(store)
        assert sweeper.sweep() == 0

    def test_sweeper_rejects_in_memory_store(self):
        with pytest.raises(TypeError):
            LockSweeper(InMemoryLockStore())  # type: ignore[arg-type]

    def test_sweeper_list_expired(self, store):
        expired = Lock.new(device_id="d1", owner="alice", operation="flash")
        expired.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        store.put(expired)
        sweeper = LockSweeper(store)
        # list_expired returns without removing
        expired_locks = sweeper.list_expired()
        assert len(expired_locks) == 1
        # Lock should still be in DB
        assert store.get("d1") is None  # but get() auto-deletes expired