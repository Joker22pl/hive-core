"""CLI helpers for the lock subsystem.

This module extracts the lock CLI logic so it can be tested independently
of Typer (see ``tests/unit/test_cli_lock.py``).

The key design choice: every CLI command that uses locks builds an
**explicit** ``LockService`` instance per invocation. There is no
module-level singleton — that makes the CLI safe to use with a JSON
store, SQLite store, or any future backend without process-wide state
leakage.
"""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from hive.common.errors import HiveError
from hive.locking import InMemoryLockStore, JsonLockStore, LockService


def build_default_service(json_path: str | None = None) -> LockService:
    """Construct a LockService for the CLI.

    ``json_path`` is optional; if provided, a ``JsonLockStore`` is used
    so state survives across CLI invocations. Otherwise an in-memory
    store is used (per-process, lost on exit).

    H1 will add a ``--sqlite-path`` option and an ``SqliteLockStore``.
    """
    if json_path is not None:
        return LockService(JsonLockStore(json_path))
    return LockService(InMemoryLockStore())


def serialize_acquire(result: Any) -> dict[str, Any]:
    """Serialize a LockAcquireResult to a JSON-friendly dict."""
    lock = result.lock
    return {
        "created": result.created,
        "renewed": result.renewed,
        "lock": lock.model_dump(mode="json"),
    }


def serialize_release(released: bool, device_id: str, session_id: str) -> dict[str, Any]:
    """Serialize a release result to a JSON-friendly dict."""
    return {
        "released": released,
        "device_id": device_id,
        "session_id": session_id,
    }


def serialize_error(err: BaseException) -> dict[str, Any]:
    """Serialize a HIVE error to a JSON-friendly dict (for --json output).

    Accepts BaseException so non-HiveError exceptions also serialize
    cleanly; ``message`` and ``details`` are omitted if absent.
    """
    out: dict[str, Any] = {"error": type(err).__name__}
    out["message"] = getattr(err, "message", str(err))
    if isinstance(err, HiveError) and err.details:
        out["details"] = err.details
    return out


def format_json(data: dict[str, Any]) -> str:
    """Return a single-line JSON string suitable for CLI output."""
    return json.dumps(data, default=str, separators=(",", ":"))


def emit_json(data: dict[str, Any], stream: TextIO | None = None) -> None:
    """Write a single-line JSON object to ``stream`` (default: stdout).

    This bypasses Rich so the output is parseable by ``json.loads()``
    without stripping ANSI color codes.
    """
    stream = stream or sys.stdout
    stream.write(format_json(data) + "\n")
    stream.flush()
