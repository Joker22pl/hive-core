"""Unit tests for hive.io_controller.serial_client."""

from __future__ import annotations

import threading
import time

import pytest

from hive.io_controller.protocol import Request, Response
from hive.io_controller.serial_client import (
    HiveIOError,
    SerialHiveIOClient,
)
from hive.io_controller.transport import LoopbackTransport

# A fake firmware that emulates HIVE-IO behavior in pure Python.
# This is what would live in the real Pico firmware if written in
# Python instead of C; for tests it lets us verify the client logic
# end-to-end without hardware.


class FakeHiveIOFirmware:
    """Drop-in firmware emulator paired with a LoopbackTransport.

    Responds to JSON Lines requests with JSON Lines responses,
    tracks channel state, and enforces safety rules.

    Pair it with the "right" side of a LoopbackTransport pair:

        client_side, firmware_side = LoopbackTransport.create_pair()
        firmware = FakeHiveIOFirmware(firmware_side)
        firmware.start()
        client = SerialHiveIOClient(client_side)
    """

    def __init__(self, transport: LoopbackTransport) -> None:
        self._transport = transport
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

        # State
        self._power = {
            f"power_{n}": False
            for n in ("esp32_1", "esp32_2", "pico_1", "pico_2", "sensor_1", "aux_1", "host_1")
        }
        self._boot = {f"boot_{n}": False for n in ("esp32_1", "esp32_2", "pico_1")}
        self._reset = {f"reset_{n}": True for n in ("esp32_1", "esp32_2", "pico_1")}
        self._motor_enable = False
        self._estop_active = False
        self._state = "IDLE"
        self._firmware_version = "0.1.0-fake"

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            line = self._transport.read_line(0.1)
            if line is None:
                continue
            try:
                import json

                req = json.loads(line.decode("utf-8"))
                resp = self._handle(req)
                payload = (json.dumps(resp) + "\n").encode("utf-8")
                self._transport.write_line(payload)
            except Exception:
                # Drop malformed lines silently — matches real
                # firmware behavior (no point crashing the loop).
                continue

    def _handle(self, req: dict) -> dict:
        cmd = req.get("command")
        request_id = req.get("request_id", "")
        params = req.get("params") or {}

        def ok(state: dict | None = None) -> dict:
            r = {
                "protocol_version": "0.1.0",
                "request_id": request_id,
                "result": "ok",
                "observed_state": state or self._state_snapshot(),
            }
            return r

        def err(code: str, message: str) -> dict:
            return {
                "protocol_version": "0.1.0",
                "request_id": request_id,
                "result": "error",
                "error_class": code,
                "message": message,
            }

        if cmd == "get_status":
            return ok()
        if cmd == "get_capabilities":
            return ok(
                {
                    "channels": list(self._power)
                    + list(self._boot)
                    + list(self._reset)
                    + ["motor_enable"]
                }
            )
        if cmd == "firmware_version":
            return ok({"version": self._firmware_version})
        if cmd == "heartbeat":
            return ok()
        if cmd == "safe_state":
            for k in self._power:
                self._power[k] = False
            for k in self._boot:
                self._boot[k] = False
            for k in self._reset:
                self._reset[k] = True
            self._motor_enable = False
            self._state = "SAFE"
            return ok()
        if cmd == "power_set":
            ch = params.get("channel")
            if ch not in self._power:
                return err("UNKNOWN_CHANNEL", f"unknown channel: {ch}")
            self._power[ch] = bool(params.get("state"))
            return ok()
        if cmd == "motor_enable_set":
            new_state = bool(params.get("state"))
            if new_state and self._estop_active:
                return err("SAFETY_INTERLOCK_OPEN", "cannot enable motors: ESTOP active")
            self._motor_enable = new_state
            return ok()
        if cmd == "estop_status":
            return ok({"estop_active": self._estop_active})
        return err("UNKNOWN_COMMAND", f"unknown command: {cmd}")

    def _state_snapshot(self) -> dict:
        return {
            "state": self._state,
            "power": dict(self._power),
            "boot": dict(self._boot),
            "reset": dict(self._reset),
            "motor_enable": self._motor_enable,
            "estop_active": self._estop_active,
        }

    def inject_estop(self, active: bool) -> None:
        """Test-only hook: force ESTOP active/inactive."""
        self._estop_active = active


def _setup_pair() -> tuple[SerialHiveIOClient, FakeHiveIOFirmware]:
    client_side, firmware_side = LoopbackTransport.create_pair()
    firmware = FakeHiveIOFirmware(firmware_side)
    firmware.start()
    client = SerialHiveIOClient(client_side, request_timeout_s=1.0)
    return client, firmware


class TestSerialHiveIOClientBasic:
    def test_get_status_round_trip(self):
        client, fw = _setup_pair()
        try:
            resp = client.get_status()
            assert isinstance(resp, Response)
            assert resp.result == "ok"
            assert resp.observed_state is not None
            assert resp.observed_state["state"] == "IDLE"
        finally:
            client.close()
            fw.stop()

    def test_get_capabilities(self):
        client, fw = _setup_pair()
        try:
            resp = client.get_capabilities()
            assert resp.result == "ok"
            assert "power_esp32_1" in resp.observed_state["channels"]
        finally:
            client.close()
            fw.stop()

    def test_firmware_version(self):
        client, fw = _setup_pair()
        try:
            resp = client.firmware_version()
            assert resp.observed_state["version"] == "0.1.0-fake"
        finally:
            client.close()
            fw.stop()

    def test_heartbeat(self):
        client, fw = _setup_pair()
        try:
            resp = client.heartbeat()
            assert resp.result == "ok"
        finally:
            client.close()
            fw.stop()

    def test_power_set(self):
        client, fw = _setup_pair()
        try:
            resp = client.power_set("power_esp32_1", True)
            assert resp.result == "ok"
            # Verify by reading back the status
            status = client.get_status()
            assert status.observed_state["power"]["power_esp32_1"] is True
        finally:
            client.close()
            fw.stop()

    def test_safe_state_clears_all_outputs(self):
        client, fw = _setup_pair()
        try:
            client.power_set("power_esp32_1", True)
            client.boot_set("boot_esp32_1", True)
            resp = client.safe_state()
            assert resp.result == "ok"
            assert resp.observed_state["power"]["power_esp32_1"] is False
            assert resp.observed_state["boot"]["boot_esp32_1"] is False
            assert resp.observed_state["state"] == "SAFE"
        finally:
            client.close()
            fw.stop()

    def test_unknown_command_returns_error_response(self):
        client, fw = _setup_pair()
        try:
            req = Request(command="unknown_command_xyz", params={})
            resp = client.send_request(req)
            assert resp.result == "error"
            assert resp.error_class == "UNKNOWN_COMMAND"
        finally:
            client.close()
            fw.stop()


class TestSerialHiveIOClientSafety:
    def test_motor_enable_blocked_by_estop(self):
        client, fw = _setup_pair()
        try:
            fw.inject_estop(True)
            resp = client.motor_enable_set(True)
            assert resp.result == "error"
            assert resp.error_class == "SAFETY_INTERLOCK_OPEN"
            # Verify by reading status that motor_enable stayed off
            status = client.get_status()
            assert status.observed_state["motor_enable"] is False
        finally:
            client.close()
            fw.stop()

    def test_estop_release_allows_motor_enable(self):
        client, fw = _setup_pair()
        try:
            fw.inject_estop(True)
            client.motor_enable_set(True)  # rejected
            fw.inject_estop(False)
            resp = client.motor_enable_set(True)
            assert resp.result == "ok"
            assert resp.observed_state["motor_enable"] is True
        finally:
            client.close()
            fw.stop()


class TestSerialHiveIOClientHeartbeat:
    def test_heartbeat_thread_runs(self):
        client, fw = _setup_pair()
        try:
            assert not client.is_heartbeat_alive()
            client.start_heartbeat()
            assert client.is_heartbeat_alive()
            time.sleep(0.5)  # let it tick at least once
            assert client.is_heartbeat_alive()
        finally:
            client.close()
            fw.stop()

    def test_heartbeat_thread_stops_on_close(self):
        client, fw = _setup_pair()
        client.start_heartbeat()
        time.sleep(0.2)
        client.close()
        assert not client.is_heartbeat_alive()
        fw.stop()

    def test_heartbeat_lost_when_firmware_dies(self):
        client_side, firmware_side = LoopbackTransport.create_pair()
        fw = FakeHiveIOFirmware(firmware_side)
        fw.start()
        client = SerialHiveIOClient(client_side, request_timeout_s=0.3, heartbeat_interval_ms=50)
        client.start_heartbeat()
        time.sleep(0.2)
        # Kill the firmware — heartbeat should detect this
        fw.stop()
        # Wait up to 5 seconds for the heartbeat thread to notice
        for _ in range(50):
            if not client.is_heartbeat_alive():
                break
            time.sleep(0.1)
        assert not client.is_heartbeat_alive()
        err = client.heartbeat_lost_error()
        assert err is not None
        client.close()

    def test_start_heartbeat_is_idempotent(self):
        client, fw = _setup_pair()
        try:
            client.start_heartbeat()
            t1 = client._hb_thread  # type: ignore[attr-defined]
            client.start_heartbeat()
            t2 = client._hb_thread  # type: ignore[attr-defined]
            assert t1 is t2
        finally:
            client.close()
            fw.stop()


class TestSerialHiveIOClientErrors:
    def test_send_request_when_transport_closed_raises(self):
        client, fw = _setup_pair()
        fw.stop()
        client.close()
        with pytest.raises(HiveIOError):
            client.get_status()

    def test_unknown_response_json_raises(self):
        # Pair the client with a transport that returns garbage
        client_side, firmware_side = LoopbackTransport.create_pair()
        client = SerialHiveIOClient(client_side, request_timeout_s=1.0)

        def garbage_responder():
            # Just send malformed JSON to the client side
            time.sleep(0.05)
            firmware_side.write_line(b"not-json-at-all")

        t = threading.Thread(target=garbage_responder, daemon=True)
        t.start()
        with pytest.raises(HiveIOError, match="Invalid JSON"):
            client.get_status()
        t.join(timeout=1.0)
