"""Lock service — high-level acquire / release / list operations.

This module provides the canonical lock semantics for HIVE.

Semantics:

* ``acquire`` (new): device was free; a brand-new Lock was created.
* ``acquire`` (renewal): device was locked by the **same session_id**; the
  existing lock's TTL was extended and its parent updated in place; the
  returned ``Lock`` is a fresh copy so callers cannot mutate the stored
  instance.
* ``acquire`` (conflict): device was locked by a **different session_id**;
  ``DeviceBusyError`` is raised. The error carries the conflicting owner,
  session id, operation, and expiry so callers can render a useful message.

To preserve API symmetry while exposing the renewal distinction, ``acquire``
returns a :class:`LockAcquireResult` rather than a bare ``Lock``. The
``created`` and ``renewed`` boolean flags are mutually exclusive::

    result = svc.acquire(...)
    if result.created:
        ...  # fresh lock
    elif result.renewed:
        ...  # TTL extended

``release`` deletes the lock only when the ``session_id`` matches;
mismatched session ids are silently ignored (returns ``False``). This is
the "safe" semantic — it prevents operator A from accidentally releasing
operator B's lock.

Force release (administrative override) is **not** provided by the public
API. It is intentionally absent in H0; if H1+ needs administrative
release, it will live on a separate service class so the safe path
cannot be bypassed by accident.
"""

from __future__ import annotations

from dataclasses import dataclass

from hive.common.errors import DeviceBusyError
from hive.common.models.lock import Lock
from hive.locking.store import InMemoryLockStore, LockStore


@dataclass(frozen=True)
class LockAcquireResult:
    """Result of a successful :meth:`LockService.acquire` call.

    ``created`` and ``renewed`` are mutually exclusive; exactly one is
    ``True`` on a successful call. ``acquire`` raises ``DeviceBusyError``
    on conflict, so this object is only returned for the success path.
    """

    lock: Lock
    created: bool
    renewed: bool

    @classmethod
    def _created(cls, lock: Lock) -> LockAcquireResult:
        return cls(lock=lock, created=True, renewed=False)

    @classmethod
    def _renewed(cls, lock: Lock) -> LockAcquireResult:
        return cls(lock=lock, created=False, renewed=True)


class LockService:
    """High-level lock operations.

    Wraps a :class:`LockStore` with policy:

    * refuse to overwrite active locks held by another session,
    * silently renew when the same ``session_id`` re-acquires,
    * only delete on ``release`` when the ``session_id`` matches.
    """

    def __init__(self, store: LockStore) -> None:
        self._store = store

    def acquire(
        self,
        device_id: str,
        owner: str,
        session_id: str | None = None,
        operation: str = "unspecified",
        ttl_seconds: int = 900,
    ) -> LockAcquireResult:
        """Acquire (or renew) a lock for ``device_id``.

        Returns a :class:`LockAcquireResult` indicating whether the lock
        was newly created or its TTL was extended (renewed).

        Raises:
            DeviceBusyError: when the device is locked by a different
                ``session_id``.
        """
        existing = self._store.get(device_id)
        if existing is not None:
            if existing.session_id == session_id:
                # Same session re-acquire → renew TTL.
                renewed = existing.model_copy(deep=True)
                renewed.renew(ttl_seconds)
                self._store.put(renewed)
                return LockAcquireResult._renewed(renewed)
            raise DeviceBusyError(
                f"Device {device_id!r} is locked by session {existing.session_id!r}",
                details={
                    "device_id": device_id,
                    "existing_owner": existing.owner,
                    "existing_session": existing.session_id,
                    "existing_operation": existing.operation,
                    "existing_expires_at": str(existing.expires_at),
                },
            )
        lock = Lock.new(
            device_id=device_id,
            owner=owner,
            session_id=session_id,
            operation=operation,
            ttl_seconds=ttl_seconds,
        )
        # Re-check after creating to avoid TOCTOU between get and put.
        existing_after = self._store.get(device_id)
        if existing_after is not None:
            raise DeviceBusyError(
                f"Device {device_id!r} is locked by session {existing_after.session_id!r}",
                details={
                    "device_id": device_id,
                    "existing_owner": existing_after.owner,
                },
            )
        self._store.put(lock)
        return LockAcquireResult._created(lock)

    def release(self, device_id: str, session_id: str) -> bool:
        """Release the lock on ``device_id`` if owned by ``session_id``.

        Returns ``True`` if released, ``False`` if no matching lock was
        found. Mismatched ``session_id`` is **not** an error — it returns
        ``False`` so callers can treat it as a no-op without an exception.
        """
        return self._store.delete(device_id, session_id)

    def list_active(self) -> list[Lock]:
        """Return all non-expired locks in the store."""
        return self._store.list_active()

    def get(self, device_id: str) -> Lock | None:
        """Return the active lock for ``device_id``, or ``None``."""
        return self._store.get(device_id)


# Convenience functions (default to InMemoryLockStore).
# These are retained for backward compatibility and tests; production code
# (CLI) should construct a LockService explicitly per process.
_default_service: LockService | None = None


def _get_default_service() -> LockService:
    global _default_service
    if _default_service is None:
        _default_service = LockService(InMemoryLockStore())
    return _default_service


def acquire(
    device_id: str,
    owner: str,
    session_id: str | None = None,
    operation: str = "unspecified",
    ttl_seconds: int = 900,
) -> LockAcquireResult:
    return _get_default_service().acquire(device_id, owner, session_id, operation, ttl_seconds)


def release(device_id: str, session_id: str) -> bool:
    return _get_default_service().release(device_id, session_id)


def list_active() -> list[Lock]:
    return _get_default_service().list_active()


__all__ = [
    "LockAcquireResult",
    "LockService",
    "acquire",
    "list_active",
    "release",
]
