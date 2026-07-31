"""Example: lock service usage.

Run from the hive-core root::

    python examples/lock_service.py

Shows a complete acquire / release round-trip with both the in-memory
and JSON-file stores, plus a same-session renewal.
"""

from __future__ import annotations

import json
import sys

from hive.locking import (
    InMemoryLockStore,
    JsonLockStore,
    LockService,
)


def demo_in_memory() -> None:
    print("=== In-memory store ===")
    svc = LockService(InMemoryLockStore())
    r1 = svc.acquire("demo-device", owner="audit", operation="demo")
    print(f"acquire 1: created={r1.created} renewed={r1.renewed} "
          f"session_id={r1.lock.session_id}")
    r2 = svc.acquire("demo-device", owner="audit", session_id=r1.lock.session_id)
    print(f"acquire 2 (same session): created={r2.created} renewed={r2.renewed}")
    released = svc.release("demo-device", r1.lock.session_id)
    print(f"release: {released}")


def demo_json_store(path: str) -> None:
    print(f"\n=== JSON store at {path} ===")
    svc = LockService(JsonLockStore(path))
    r1 = svc.acquire("demo-device", owner="audit", operation="demo")
    print(f"acquire: created={r1.created} session_id={r1.lock.session_id}")
    print("(state is now persisted on disk)")
    svc.release("demo-device", r1.lock.session_id)
    print("release: True")


def main() -> int:
    demo_in_memory()
    demo_json_store("/tmp/hive-example-locks.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
