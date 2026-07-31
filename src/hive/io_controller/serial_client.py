"""Real SerialHiveIOClient — implements the full client API over a transport.

Provides timeout + retry for get_status / heartbeat / safe_state
(per H2 roadmap: "klient z timeoutami i retry").

Heartbeat semantics (H2):
* Caller invokes `start_heartbeat()` once; the client spawns a
  background thread that sends `heartbeat` every `interval_ms`.
* The thread stops when `stop_heartbeat()` is called or `close()`
  is invoked.
* On heartbeat failure (timeout or transport error), the client
  raises `HeartbeatLostError`. The caller is expected to invoke
  `safe_state()` on its own E-stop logic.

For tests, swap `transport` with `LoopbackTransport` and pair it
with a fake firmware.
"""

from __future__ import annotations

import json
import threading
import time

from hive.common.errors import HiveError
from hive.io_controller.client import HiveIOClient
from hive.io_controller.protocol import (
    PROTOCOL_VERSION,
    ErrorResponse,
    Request,
    Response,
)
from hive.io_controller.transport import HiveIOTransport, SerialTransport, TransportError


class HiveIOError(HiveError):
    """Raised when the HIVE-IO client or firmware returns an error."""


class HeartbeatLostError(HiveIOError):
    """Raised when the heartbeat thread fails to reach HIVE-IO."""


class SerialHiveIOClient(HiveIOClient):
    """JSON Lines client over an arbitrary HiveIOTransport.

    Args:
        transport: a HiveIOTransport (SerialTransport for real HW,
                   LoopbackTransport for tests).
        request_timeout_s: per-request timeout in seconds.
        heartbeat_interval_ms: background heartbeat interval.
    """

    protocol_version: str = PROTOCOL_VERSION

    def __init__(
        self,
        transport: HiveIOTransport,
        *,
        request_timeout_s: float = 2.0,
        heartbeat_interval_ms: int = 200,
    ) -> None:
        self._transport = transport
        self._request_timeout_s = request_timeout_s
        self._heartbeat_interval_ms = heartbeat_interval_ms

        # Heartbeat thread state
        self._hb_thread: threading.Thread | None = None
        self._hb_stop = threading.Event()
        self._hb_lost_event = threading.Event()
        self._hb_lost_error: Exception | None = None

    # ---- transport lifecycle ----

    def connect(self) -> None:
        self._transport.open()
        # Verify the firmware is alive by asking for status. If this
        # fails, the firmware isn't flashed or the wrong port is open.
        resp = self.get_status()
        if isinstance(resp, ErrorResponse):
            raise HiveIOError(
                f"HIVE-IO get_status returned error: {resp.error_class} — {resp.message}"
            )

    def close(self) -> None:
        self.stop_heartbeat()
        self._transport.close()

    @property
    def is_open(self) -> bool:
        return self._transport.is_open

    # ---- core send/receive ----

    def send_request(self, request: Request) -> Response:
        if not self._transport.is_open:
            raise HiveIOError("SerialHiveIOClient: transport not open")
        try:
            payload = request.to_jsonl().encode("utf-8")
            self._transport.write_line(payload)
        except TransportError as e:
            raise HiveIOError(f"Transport write failed: {e}") from e

        # Read response. Loop because some serial transports return
        # blank lines between requests when the device echoes.
        deadline = time.monotonic() + self._request_timeout_s
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise HiveIOError(
                    f"Timeout waiting for response (request_id={request.request_id})",
                    details={"request_id": request.request_id, "command": request.command},
                )
            try:
                line = self._transport.read_line(timeout_s=remaining)
            except TransportError as e:
                raise HiveIOError(f"Transport read failed: {e}") from e
            if line is None:
                continue  # empty read; loop until timeout
            try:
                text = line.decode("utf-8")
            except UnicodeDecodeError as e:
                raise HiveIOError(f"Non-UTF8 response from HIVE-IO: {line!r}") from e
            try:
                obj = json.loads(text)
            except json.JSONDecodeError as e:
                raise HiveIOError(f"Invalid JSON from HIVE-IO: {text[:200]!r}") from e
            return Response.model_validate(obj)

    # ---- heartbeat ----

    def start_heartbeat(self) -> None:
        """Start the background heartbeat thread.

        Idempotent: a second call while already running is a no-op.
        """
        if self._hb_thread is not None and self._hb_thread.is_alive():
            return
        self._hb_stop.clear()
        self._hb_lost_event.clear()
        self._hb_lost_error = None
        self._hb_thread = threading.Thread(
            target=self._heartbeat_loop,
            name="HiveIOClient-Heartbeat",
            daemon=True,
        )
        self._hb_thread.start()

    def stop_heartbeat(self) -> None:
        if self._hb_thread is None:
            return
        self._hb_stop.set()
        self._hb_thread.join(timeout=self._request_timeout_s + 1.0)
        self._hb_thread = None

    def _heartbeat_loop(self) -> None:
        """Background thread: send heartbeat every interval_ms."""
        interval_s = self._heartbeat_interval_ms / 1000.0
        while not self._hb_stop.is_set():
            try:
                resp = self.heartbeat()
                if isinstance(resp, ErrorResponse):
                    raise HeartbeatLostError(
                        f"Heartbeat error: {resp.error_class} — {resp.message}"
                    )
            except Exception as e:
                self._hb_lost_error = e
                self._hb_lost_event.set()
                return
            # Sleep in small chunks so stop_heartbeat is responsive.
            slept = 0.0
            while slept < interval_s and not self._hb_stop.is_set():
                step = min(0.05, interval_s - slept)
                time.sleep(step)
                slept += step

    def is_heartbeat_alive(self) -> bool:
        """True if the heartbeat thread is running and not lost."""
        if self._hb_thread is None or not self._hb_thread.is_alive():
            return False
        return not self._hb_lost_event.is_set()

    def heartbeat_lost_error(self) -> Exception | None:
        """If the heartbeat thread stopped due to an error, return it."""
        return self._hb_lost_error

    # ---- convenience constructors ----

    @classmethod
    def for_serial_port(
        cls,
        port: str,
        *,
        baudrate: int = 115200,
        request_timeout_s: float = 2.0,
        heartbeat_interval_ms: int = 200,
    ) -> SerialHiveIOClient:
        """Convenience constructor for a real USB CDC port."""
        return cls(
            SerialTransport(port=port, baudrate=baudrate, timeout_s=request_timeout_s),
            request_timeout_s=request_timeout_s,
            heartbeat_interval_ms=heartbeat_interval_ms,
        )

    # ---- high-level commands (HIVE-IO protocol surface) ----

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
            Request(command="power_set", params={"channel": channel, "state": state})
        )

    def power_cycle(self, channel: str, off_duration_ms: int = 500) -> Response:
        return self.send_request(
            Request(
                command="power_cycle",
                params={"channel": channel, "off_duration_ms": off_duration_ms},
            )
        )

    def reset_pulse(self, channel: str, duration_ms: int = 100) -> Response:
        return self.send_request(
            Request(command="reset_pulse", params={"channel": channel, "duration_ms": duration_ms})
        )

    def boot_set(self, channel: str, state: bool) -> Response:
        return self.send_request(
            Request(command="boot_set", params={"channel": channel, "state": state})
        )

    def motor_enable_set(self, state: bool) -> Response:
        return self.send_request(Request(command="motor_enable_set", params={"state": state}))

    def estop_status(self) -> Response:
        return self.send_request(Request(command="estop_status"))

    def firmware_version(self) -> Response:
        return self.send_request(Request(command="firmware_version"))


__all__ = ["HeartbeatLostError", "HiveIOError", "SerialHiveIOClient"]
