"""Tests for SerialHiveIOClient retry behaviour."""

from __future__ import annotations

import time
from collections import deque

import pytest

from hive.io_controller.protocol import Request, Response
from hive.io_controller.serial_client import (
    HiveIOError,
    SerialHiveIOClient,
)
from hive.io_controller.transport import HiveIOTransport


class _ScriptedTransport(HiveIOTransport):
    """Programmable transport that returns canned replies and records writes."""

    def __init__(self) -> None:
        self._inbox: deque[bytes] = deque()
        self._outbox: deque[bytes] = deque()
        self.writes: list[bytes] = []
        self._open = True

    def push_response(self, raw: bytes) -> None:
        self._inbox.append(raw if raw.endswith(b"\n") else raw + b"\n")

    def push_timeout(self) -> None:
        self._inbox.append(b"")

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    @property
    def is_open(self) -> bool:
        return self._open

    def write_line(self, line: bytes) -> None:
        self.writes.append(line if line.endswith(b"\n") else line + b"\n")

    def read_line(self, timeout_s: float) -> bytes | None:
        if not self._inbox:
            time.sleep(min(timeout_s, 0.05))
            return None
        data = self._inbox.popleft()
        if data == b"":
            return None
        while data.endswith((b"\n", b"\r")):
            data = data[:-1]
        return data


def _ok_response(request_id: str) -> bytes:
    import json

    return json.dumps(
        {
            "protocol_version": "0.1.0",
            "request_id": request_id,
            "result": "ok",
            "observed_state": True,
        }
    ).encode("utf-8")


def test_retry_recovers_from_transient_transport_timeout() -> None:
    """First attempt raises HiveIOError (transient); second attempt succeeds."""
    t = _ScriptedTransport()
    t.push_response(_ok_response("req-recover"))

    client = SerialHiveIOClient(t, request_timeout_s=1.0, retry_attempts=3, retry_backoff_s=0.0)

    # Force the first two attempts to look like transient timeouts.
    # The third attempt sees the staged reply and succeeds.
    original = client._send_once
    call_state = {"n": 0}

    def flaky_once(request: Request) -> Response:
        call_state["n"] += 1
        if call_state["n"] < 3:
            raise HiveIOError(
                f"Timeout waiting for response (request_id={request.request_id})",
                details={"request_id": request.request_id, "command": request.command},
            )
        return original(request)

    client._send_once = flaky_once  # type: ignore[method-assign]

    resp = client.power_set("power_esp32_1", True)
    assert resp.result == "ok"
    assert resp.observed_state is True
    assert call_state["n"] == 3  # 2 timeouts + 1 success


def test_retry_gives_up_after_attempts() -> None:
    """When all attempts time out, retry surfaces HiveIOError."""
    t = _ScriptedTransport()
    client = SerialHiveIOClient(t, request_timeout_s=0.05, retry_attempts=3, retry_backoff_s=0.0)

    with pytest.raises(HiveIOError):
        client.heartbeat()
    assert len(t.writes) == 3


def test_retry_disabled_by_default() -> None:
    """Default behaviour must remain single-shot (no surprise latency)."""
    t = _ScriptedTransport()
    client = SerialHiveIOClient(t, request_timeout_s=0.05)

    with pytest.raises(HiveIOError):
        client.get_status()
    assert len(t.writes) == 1


def test_retry_does_not_swallow_protocol_errors() -> None:
    """A genuine protocol error response must not be retried."""
    import json

    t = _ScriptedTransport()
    payload = json.dumps(
        {
            "protocol_version": "0.1.0",
            "request_id": "any",
            "result": "error",
            "error_class": "UNKNOWN_COMMAND",
            "message": "nope",
        }
    ).encode("utf-8")
    t.push_response(payload)
    client = SerialHiveIOClient(t, request_timeout_s=0.5, retry_attempts=3, retry_backoff_s=0.0)

    resp = client.send_request(Request(command="mystery"))
    assert resp.result == "error"
    assert resp.error_class == "UNKNOWN_COMMAND"
    assert len(t.writes) == 1
