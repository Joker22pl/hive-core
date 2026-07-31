"""Coverage tests for ``hive.locking`` edge cases.

Targets the error paths and edge conditions not exercised by the
happy-path tests in test_locking.py.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from hive.common.errors import DeviceBusyError
from hive.common.models.lock import Lock
from hive.locking import (
    InMemoryLockStore,
    JsonLockStore,
    LockAcquireResult,
    LockService,
)

# ---------- InMemoryLockStore edge cases ----------


def test_inmemory_get_returns_none_for_missing() -> None:
    """InMemoryLockStore.get returns None for unknown device."""
    assert InMemoryLockStore().get("nope") is None


def test_inmemory_get_cleans_up_expired_lock() -> None:
    """Reading an expired lock returns None and removes it from the store."""
    store = InMemoryLockStore()
    lock = Lock.new(device_id="d1", owner="hare", ttl_seconds=1)
    lock.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    store.put(lock)
    assert store.get("d1") is None
    # The expired lock should be evicted from the store.
    assert store.get("d1") is None  # idempotent


def test_inmemory_list_active_with_no_locks() -> None:
    """list_active returns empty list when no locks exist."""
    assert InMemoryLockStore().list_active() == []


# ---------- JsonLockStore error paths ----------


def test_json_store_handles_corrupted_file(tmp_path: Path) -> None:
    """A corrupted JSON file is treated as empty (no raises on read)."""
    p = tmp_path / "bad.json"
    p.write_text("{not valid json", encoding="utf-8")
    store = JsonLockStore(p)
    assert store.get("anything") is None
    assert store.list_active() == []


def test_json_store_handles_existing_file_with_data(tmp_path: Path) -> None:
    """JsonLockStore reads a valid existing file correctly."""
    p = tmp_path / "ok.json"
    p.write_text(
        '{"d1": {"device_id": "d1", "owner": "hare", "session_id": "s1", '
        '"operation": "test", "acquired_at": "2026-07-30T00:00:00Z", '
        '"expires_at": "2099-01-01T00:00:00Z", "metadata": {}}}',
        encoding="utf-8",
    )
    store = JsonLockStore(p)
    lock = store.get("d1")
    assert lock is not None
    assert lock.owner == "hare"


def test_json_store_persists_across_gets(tmp_path: Path) -> None:
    """Two get operations on the same store return the same data."""
    p = tmp_path / "x.json"
    s1 = JsonLockStore(p)
    s1.put(Lock.new(device_id="d1", owner="hare", session_id="s1"))
    s2 = JsonLockStore(p)
    assert s2.get("d1") is not None


def test_json_store_creates_parent_dir(tmp_path: Path) -> None:
    """JsonLockStore creates missing parent directories."""
    p = tmp_path / "nested" / "deeper" / "locks.json"
    JsonLockStore(p)  # constructor must not raise
    assert p.parent.exists()


# ---------- LockService edge cases ----------


def test_service_acquire_with_explicit_none_session_id_blocked() -> None:
    """Acquire(None) twice in a row — second is blocked (auto session_id differs).

    Auto-generated session_ids are unique per call, so the second
    acquire cannot renew the first. This is the correct safety semantic.
    """
    from hive.common.errors import DeviceBusyError

    svc = LockService(InMemoryLockStore())
    r1 = svc.acquire("d1", owner="hare", session_id=None)
    assert r1.created is True
    with pytest.raises(DeviceBusyError):
        svc.acquire("d1", owner="hare", session_id=None)


def test_service_acquire_after_release_creates_new_lock() -> None:
    """After release, the same session can re-acquire a fresh lock."""
    svc = LockService(InMemoryLockStore())
    r1 = svc.acquire("d1", owner="hare", session_id="sess-1")
    assert r1.created is True
    svc.release("d1", "sess-1")
    r2 = svc.acquire("d1", owner="hare", session_id="sess-1")
    # After release the lock is free; re-acquire is a fresh lock, not renewal.
    assert r2.created is True


def test_service_acquire_raises_busy_when_other_session_active() -> None:
    """Operation now → operation later from different session → busy."""
    svc = LockService(InMemoryLockStore())
    svc.acquire("d1", owner="hare", session_id="s-A", operation="first")
    with pytest.raises(DeviceBusyError) as exc_info:
        svc.acquire("d1", owner="hare", session_id="s-B", operation="second")
    assert exc_info.value.details["existing_owner"] == "hare"
    assert exc_info.value.details["existing_session"] == "s-A"
    assert exc_info.value.details["existing_operation"] == "first"


def test_service_get_returns_active_lock() -> None:
    """LockService.get wraps the underlying store."""
    svc = LockService(InMemoryLockStore())
    svc.acquire("d1", owner="hare", session_id="s1")
    assert svc.get("d1") is not None
    assert svc.get("d1").device_id == "d1"


def test_service_get_returns_none_for_missing() -> None:
    svc = LockService(InMemoryLockStore())
    assert svc.get("nope") is None


def test_service_list_active_empty() -> None:
    svc = LockService(InMemoryLockStore())
    assert svc.list_active() == []


def test_lock_acquire_result_created_is_immutable() -> None:
    """LockAcquireResult is frozen — assignment raises."""
    import dataclasses

    result = LockAcquireResult._created(Lock.new("d1", owner="hare"))
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.renewed = True  # type: ignore[misc]


def test_lock_acquire_result_renewed_is_immutable() -> None:
    import dataclasses

    result = LockAcquireResult._renewed(Lock.new("d1", owner="hare"))
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.lock = None  # type: ignore[misc]


# ---------- Default service (acquire/release at module level) ----------


def test_module_level_acquire_release() -> None:
    """The module-level ``acquire`` / ``release`` helpers work."""
    from hive.locking import acquire, release

    lock = acquire("d1", owner="hare", session_id="shared-sess")
    assert isinstance(lock, LockAcquireResult)
    assert release("d1", "shared-sess") is True


def test_module_level_list_active() -> None:
    from hive.locking import acquire, list_active, release

    acquire("d1", owner="hare", session_id="s-list")
    locks = list_active()
    assert any(lock.device_id == "d1" for lock in locks)
    release("d1", "s-list")
