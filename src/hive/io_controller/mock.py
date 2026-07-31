"""In-process mock for HIVE-IO.

Useful for:
- unit tests of HIVE Core without hardware,
- local development when HIVE-IO is not yet flashed.

The mock tracks channel state in memory and validates basic safety
constraints (e.g. refuses motor_enable=true while ESTOP is ACTIVE).

Test-only helpers (``inject_estop``, ``poll_events``) are NOT part of
the public surface. They are exposed via :class:`MockHiveIOTestHooks`
(``hive.io_controller.mock_hooks``) which tests obtain explicitly.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime

from hive.io_controller.client import HiveIOClient
from hive.io_controller.protocol import (
    POWER_CHANNELS,
    PROTOCOL_VERSION,
    AsyncEvent,
    Request,
    Response,
)


class MockHiveIOClient(HiveIOClient):
    """Thread-safe in-process mock of HIVE-IO."""

    protocol_version: str = PROTOCOL_VERSION

    def __init__(self, firmware_version: str = "0.1.0-mock") -> None:
        self._lock = threading.Lock()
        self._power: dict[str, bool] = {ch: False for ch in POWER_CHANNELS}
        self._boot: dict[str, bool] = {
            ch: False
            for ch in (
                "boot_esp32_1",
                "boot_esp32_2",
                "boot_pico_1",
            )
        }
        self._reset: dict[str, bool] = {
            ch: True
            for ch in (
                "reset_esp32_1",
                "reset_esp32_2",
                "reset_pico_1",
            )
        }
        self._motor_enable: bool = False
        self._estop_active: bool = False
        self._firmware_version = firmware_version
        self._connected: bool = False
        self._events: list[AsyncEvent] = []
        self._next_id = 0

    # ---- lifecycle ----

    def connect(self) -> None:
        with self._lock:
            self._connected = True

    def close(self) -> None:
        with self._lock:
            self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    # ---- request/response plumbing ----

    def send_request(self, request: Request) -> Response:
        cmd = request.command
        params = request.params
        with self._lock:
            if cmd == "get_status":
                return self._ok(request.request_id, self._status_snapshot())
            if cmd == "get_capabilities":
                return self._ok(
                    request.request_id,
                    {
                        "protocol_version": self.protocol_version,
                        "firmware_version": self._firmware_version,
                        "power_channels": list(POWER_CHANNELS),
                        "boot_channels": list(self._boot.keys()),
                        "reset_channels": list(self._reset.keys()),
                    },
                )
            if cmd == "heartbeat":
                return self._ok(request.request_id, "ack")
            if cmd == "firmware_version":
                return self._ok(request.request_id, self._firmware_version)
            if cmd == "estop_status":
                return self._ok(
                    request.request_id,
                    "ACTIVE" if self._estop_active else "INACTIVE",
                )
            if cmd == "safe_state":
                return self._do_safe_state(request.request_id)
            if cmd == "motor_enable_set":
                return self._do_motor_enable(request.request_id, bool(params.get("state")))
            if cmd == "power_set":
                ch = str(params.get("channel", ""))
                state = bool(params.get("state", False))
                if ch not in self._power:
                    return self._err(
                        request.request_id, "UNKNOWN_CHANNEL", f"Unknown power channel: {ch!r}"
                    )
                return self._do_power_set(request.request_id, ch, state)
            if cmd == "boot_set":
                ch = str(params.get("channel", ""))
                state = bool(params.get("state", False))
                if ch not in self._boot:
                    return self._err(
                        request.request_id, "UNKNOWN_CHANNEL", f"Unknown boot channel: {ch!r}"
                    )
                self._boot[ch] = state
                return self._ok(request.request_id, state)
            if cmd == "reset_pulse":
                # In mock, we don't actually pulse; we just report.
                return self._ok(request.request_id, True)
            if cmd == "power_cycle":
                ch = str(params.get("channel", ""))
                if ch not in self._power:
                    return self._err(
                        request.request_id, "UNKNOWN_CHANNEL", f"Unknown power channel: {ch!r}"
                    )
                self._power[ch] = False
                self._power[ch] = True
                return self._ok(request.request_id, True)
            if cmd == "reset_io_controller":
                return self._ok(request.request_id, True)
            return self._err(request.request_id, "UNKNOWN_COMMAND", f"Unknown command: {cmd!r}")

    # ---- high-level helpers ----

    def get_status(self) -> Response:
        return self.send_request(Request(command="get_status"))

    def get_capabilities(self) -> Response:
        return self.send_request(Request(command="get_capabilities"))

    def heartbeat(self) -> Response:
        return self.send_request(Request(command="heartbeat"))

    def safe_state(self) -> Response:
        return self.send_request(Request(command="safe_state"))

    def power_set(self, channel: str, state: bool) -> Response:
        return self.send_request(
            Request(
                command="power_set",
                params={
                    "channel": channel,
                    "state": state,
                },
            )
        )

    def power_cycle(self, channel: str, off_duration_ms: int = 500) -> Response:
        return self.send_request(
            Request(
                command="power_cycle",
                params={
                    "channel": channel,
                    "off_duration_ms": off_duration_ms,
                },
            )
        )

    def reset_pulse(self, channel: str, duration_ms: int = 100) -> Response:
        return self.send_request(
            Request(
                command="reset_pulse",
                params={
                    "channel": channel,
                    "duration_ms": duration_ms,
                },
            )
        )

    def boot_set(self, channel: str, state: bool) -> Response:
        return self.send_request(
            Request(
                command="boot_set",
                params={
                    "channel": channel,
                    "state": state,
                },
            )
        )

    def motor_enable_set(self, state: bool) -> Response:
        return self.send_request(
            Request(
                command="motor_enable_set",
                params={
                    "state": state,
                },
            )
        )

    def estop_status(self) -> Response:
        return self.send_request(Request(command="estop_status"))

    def firmware_version(self) -> Response:
        return self.send_request(Request(command="firmware_version"))

    # ---- mock-only helpers (test/dev) — PRIVATE —-

    # These are intentionally private (single underscore) so they are
    # not part of the public HiveIOClient surface. Production code MUST
    # NOT use them. Tests should obtain injection hooks via
    # ``MockHiveIOTestHooks`` (see ``mock_hooks.py``).

    def _inject_estop(self, active: bool) -> None:
        """Inject an ESTOP state change (test helper, private)."""
        with self._lock:
            previous = self._estop_active
            self._estop_active = active
            event_name = "ESTOP_PRESSED" if active else "ESTOP_RELEASED"
        if previous != active:
            self._events.append(
                AsyncEvent(
                    event=event_name,
                    timestamp=datetime.now(UTC),
                    details={"source": "mock-injection"},
                )
            )

    def _poll_events(self) -> list[AsyncEvent]:
        with self._lock:
            events = list(self._events)
            self._events.clear()
            return events

    def snapshot(self) -> dict:
        """Read-only snapshot of all channel states (test helper)."""
        with self._lock:
            return self._status_snapshot()

    # ---- internal ----

    def _status_snapshot(self) -> dict:
        return {
            "power": dict(self._power),
            "boot": dict(self._boot),
            "reset": dict(self._reset),
            "motor_enable": self._motor_enable,
            "estop_active": self._estop_active,
            "firmware_version": self._firmware_version,
        }

    def _ok(self, request_id: str, observed_state: object) -> Response:
        return Response(
            request_id=request_id,
            result="ok",
            observed_state=observed_state,
        )

    def _err(self, request_id: str, error_class: str, message: str) -> Response:
        return Response(
            request_id=request_id,
            result="error",
            error_class=error_class,
            message=message,
        )

    def _do_safe_state(self, request_id: str) -> Response:
        self._motor_enable = False
        for ch in self._power:
            # keep power on logic rails; only motor-related goes off
            if ch.startswith("power_host") or ch.startswith("power_aux"):
                continue
            self._power[ch] = False
        for ch in self._boot:
            self._boot[ch] = False
        for ch in self._reset:
            self._reset[ch] = True  # released
        return self._ok(request_id, "safe_state")

    def _do_power_set(self, request_id: str, channel: str, state: bool) -> Response:
        if state and self._estop_active:
            return self._err(
                request_id,
                "SAFETY_INTERLOCK_OPEN",
                f"Cannot power on {channel} while ESTOP active",
            )
        self._power[channel] = state
        return self._ok(request_id, state)

    def _do_motor_enable(self, request_id: str, state: bool) -> Response:
        if state and self._estop_active:
            return self._err(
                request_id,
                "SAFETY_INTERLOCK_OPEN",
                "Cannot enable motors while ESTOP active",
            )
        self._motor_enable = state
        return self._ok(request_id, state)
