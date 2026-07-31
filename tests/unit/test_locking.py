"""Tests for lock model + service."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from hive.common.errors import DeviceBusyError
from hive.common.models.lock import Lock
from hive.locking.service import LockAcquireResult, LockService
from hive.locking.store import InMemoryLockStore, JsonLockStore

# ---------- Lock model ----------


def test_lock_new_has_ttl() -> None:
    lock = Lock.new(device_id="d1", owner="hare", ttl_seconds=60)
    delta = lock.expires_at - lock.acquired_at
    assert 55 <= delta.total_seconds() <= 65


def test_lock_is_expired() -> None:
    lock = Lock.new(device_id="d1", owner="hare", ttl_seconds=1)
    assert lock.is_expired() is False
    future = datetime.now(UTC) + timedelta(seconds=10)
    assert lock.is_expired(future) is True


def test_lock_renew_extends_ttl() -> None:
    lock = Lock.new(device_id="d1", owner="hare", ttl_seconds=10)
    old_expires = lock.expires_at
    lock.renew(ttl_seconds=120)
    assert lock.expires_at > old_expires


def test_lock_session_id_auto() -> None:
    lock = Lock.new(device_id="d1", owner="hare")
    assert lock.session_id.startswith("sess-")


def test_lock_session_id_explicit() -> None:
    lock = Lock.new(device_id="d1", owner="hare", session_id="my-sess")
    assert lock.session_id == "my-sess"


# ---------- InMemoryLockStore ----------


def test_inmemory_store_put_get_delete() -> None:
    store = InMemoryLockStore()
    lock = Lock.new(device_id="d1", owner="hare")
    store.put(lock)
    got = store.get("d1")
    assert got is not None
    assert got.session_id == lock.session_id
    assert store.delete("d1", lock.session_id) is True
    assert store.get("d1") is None


def test_inmemory_store_delete_wrong_session_fails() -> None:
    store = InMemoryLockStore()
    lock = Lock.new(device_id="d1", owner="hare", session_id="sess-A")
    store.put(lock)
    assert store.delete("d1", "sess-B") is False
    assert store.get("d1") is not None


def test_inmemory_store_expired_lock_returned_as_none() -> None:
    store = InMemoryLockStore()
    lock = Lock.new(device_id="d1", owner="hare", ttl_seconds=1)
    lock.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    store.put(lock)
    assert store.get("d1") is None


def test_inmemory_store_list_active_excludes_expired() -> None:
    store = InMemoryLockStore()
    fresh = Lock.new(device_id="d1", owner="hare", ttl_seconds=60)
    expired = Lock.new(device_id="d2", owner="hare", ttl_seconds=1)
    expired.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    store.put(fresh)
    store.put(expired)
    active = store.list_active()
    assert len(active) == 1
    assert active[0].device_id == "d1"


# ---------- JsonLockStore ----------


def test_json_store_persists_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "locks.json"
    s1 = JsonLockStore(path)
    lock = Lock.new(device_id="d1", owner="hare", session_id="sess-X")
    s1.put(lock)

    s2 = JsonLockStore(path)
    got = s2.get("d1")
    assert got is not None
    assert got.session_id == "sess-X"


def test_json_store_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "locks.json"
    store = JsonLockStore(path)
    lock = Lock.new(device_id="d1", owner="hare", session_id="sess-Y")
    store.put(lock)

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert "d1" in raw
    assert raw["d1"]["session_id"] == "sess-Y"


# ---------- LockService ----------


def test_service_acquire_returns_created_result() -> None:
    """First acquire returns a LockAcquireResult with created=True."""
    svc = LockService(InMemoryLockStore())
    result = svc.acquire("d1", owner="hare", session_id="sess-1", operation="flash")
    assert isinstance(result, LockAcquireResult)
    assert result.created is True
    assert result.renewed is False
    assert result.lock.device_id == "d1"
    assert result.lock.operation == "flash"


def test_service_acquire_blocks_when_busy() -> None:
    svc = LockService(InMemoryLockStore())
    svc.acquire("d1", owner="hare", session_id="sess-1", operation="flash")
    with pytest.raises(DeviceBusyError):
        svc.acquire("d1", owner="hare", session_id="sess-2", operation="flash")


def test_service_re_acquire_by_same_session_returns_renewed() -> None:
    """Same-session re-acquire returns LockAcquireResult with renewed=True."""
    svc = LockService(InMemoryLockStore())
    before = datetime.now(UTC)
    r1 = svc.acquire("d1", owner="hare", session_id="sess-1", ttl_seconds=10)
    r2 = svc.acquire("d1", owner="hare", session_id="sess-1", ttl_seconds=600)

    assert r1.created is True and r1.renewed is False
    assert r2.created is False and r2.renewed is True
    # Renew extends from max(now, current expiry) + ttl. The second ttl (600s)
    # is longer than the first (10s), so the expiry must move forward.
    assert r2.lock.expires_at > r1.lock.expires_at
    # The renewed expiry must be at least ~600s after the call.
    assert r2.lock.expires_at >= before + timedelta(seconds=600)
    # Same session id preserved.
    assert r2.lock.session_id == r1.lock.session_id


def test_service_acquire_with_auto_session_id() -> None:
    """Acquiring without an explicit session_id auto-generates one."""
    svc = LockService(InMemoryLockStore())
    result = svc.acquire("d1", owner="hare")
    assert result.lock.session_id.startswith("sess-")


def test_service_acquire_with_explicit_session_id() -> None:
    """Caller-supplied session_id is preserved."""
    svc = LockService(InMemoryLockStore())
    result = svc.acquire("d1", owner="hare", session_id="my-sess")
    assert result.lock.session_id == "my-sess"


def test_service_acquire_blocks_other_session_renews_own() -> None:
    """Same session can renew; different session raises DeviceBusyError."""
    svc = LockService(InMemoryLockStore())
    svc.acquire("d1", owner="hare", session_id="sess-1")
    # Same session → renew (ok).
    again = svc.acquire("d1", owner="hare", session_id="sess-1")
    assert again.renewed is True
    # Different session → busy.
    with pytest.raises(DeviceBusyError):
        svc.acquire("d1", owner="hare", session_id="sess-2")


def test_service_release() -> None:
    svc = LockService(InMemoryLockStore())
    svc.acquire("d1", owner="hare", session_id="sess-1")
    assert svc.release("d1", "sess-1") is True
    assert svc.release("d1", "sess-1") is False  # already released


def test_service_release_wrong_session_fails() -> None:
    svc = LockService(InMemoryLockStore())
    svc.acquire("d1", owner="hare", session_id="sess-1")
    assert svc.release("d1", "sess-2") is False
    assert svc.get("d1") is not None  # still locked


def test_service_release_after_expiry() -> None:
    """Releasing an expired lock still removes it (delete is unconditional).

    The in-memory store evicts expired locks on ``get()`` but ``delete()``
    bypasses that check and removes the entry directly. This is fine
    because the lock is already non-functional; cleaning it up is the
    idempotent contract.
    """
    svc = LockService(InMemoryLockStore())
    svc.acquire("d1", owner="hare", session_id="sess-1", ttl_seconds=1)
    # Force expiry.
    store_lock = svc.get("d1")
    assert store_lock is not None
    store_lock.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    # The store still has the lock; release removes it.
    assert svc.release("d1", "sess-1") is True


def test_service_list_active() -> None:
    svc = LockService(InMemoryLockStore())
    svc.acquire("d1", owner="hare", session_id="sess-1")
    svc.acquire("d2", owner="hare", session_id="sess-2")
    locks = svc.list_active()
    assert {lock.device_id for lock in locks} == {"d1", "d2"}


# ---------- LockAcquireResult ----------


def test_lock_acquire_result_mutually_exclusive() -> None:
    """created and renewed flags are mutually exclusive."""
    a = LockAcquireResult._created(Lock.new("d1", owner="hare"))
    b = LockAcquireResult._renewed(Lock.new("d1", owner="hare"))
    assert a.created is True and a.renewed is False
    assert b.created is False and b.renewed is True


def test_lock_acquire_result_is_frozen() -> None:
    """LockAcquireResult is immutable (frozen dataclass)."""
    result = LockAcquireResult._created(Lock.new("d1", owner="hare"))
    import dataclasses

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.created = False  # type: ignore[misc]
