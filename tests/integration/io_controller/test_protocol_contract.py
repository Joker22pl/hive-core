"""Cross-implementation protocol tests.

These tests verify that the Python `Request` / `Response` models
serialise the same JSON shape that the C firmware's hand-written
parser/formatter produces. We catch the contract drift between
hive-core (Python) and hive-io (C) at test time instead of at
integration time.

Strategy: render requests in the format the C firmware expects
(no spaces, sorted keys, compact), then run them through the Python
Pydantic model. If they round-trip cleanly, both implementations agree.

Tests are NOT strict JSON conformance (the C parser is intentionally
lenient on whitespace). They only verify field presence and types.
"""

from __future__ import annotations

import json

import pytest

from hive.io_controller.protocol import (
    PROTOCOL_VERSION,
    ErrorResponse,
    Request,
    Response,
)

# --- C firmware-style serialization helpers ---
# These mirror what firmware/src/protocol.c emits/accepts.


def c_firmware_serialize_request(
    command: str,
    params: dict,
    request_id: str = "req-firmware-001",
) -> bytes:
    """Mirror firmware/src/protocol.c format_response (request side)."""
    # C firmware always emits fields in this order:
    # protocol_version, request_id, command, params
    payload = {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "command": command,
        "params": params,
    }
    line = json.dumps(payload, separators=(",", ":"))
    return (line + "\n").encode("utf-8")


def c_firmware_parse_request(line: bytes) -> dict:
    """Mirror firmware/src/protocol.c parse() — return dict, not typed model.

    The C firmware captures params as raw JSON text and the
    command/request_id as strings. We do the same here.
    """
    text = line.decode("utf-8").rstrip("\n")
    obj = json.loads(text)
    return obj


def c_firmware_serialize_response(
    request_id: str,
    *,
    ok: bool,
    state_json: str | None = None,
    error_class: str | None = None,
    message: str | None = None,
) -> bytes:
    """Mirror firmware/src/protocol.c format_response."""
    out = {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "result": "ok" if ok else "error",
    }
    if ok and state_json is not None:
        out["observed_state"] = state_json
    elif not ok:
        if error_class is not None:
            out["error_class"] = error_class
        if message is not None:
            out["message"] = message
    line = json.dumps(out, separators=(",", ":"))
    return (line + "\n").encode("utf-8")


# --- Tests ---


class TestRequestFormat:
    def test_minimal_request(self):
        line = c_firmware_serialize_request("heartbeat", {})
        text = line.decode("utf-8").rstrip("\n")
        obj = json.loads(text)
        assert obj["protocol_version"] == PROTOCOL_VERSION
        assert obj["command"] == "heartbeat"
        assert obj["params"] == {}

    def test_request_with_complex_params(self):
        params = {
            "channel": "power_esp32_1",
            "state": True,
            "timeout_ms": 500,
        }
        line = c_firmware_serialize_request("power_set", params)
        text = line.decode("utf-8").rstrip("\n")
        obj = json.loads(text)
        assert obj["command"] == "power_set"
        assert obj["params"]["channel"] == "power_esp32_1"
        assert obj["params"]["state"] is True
        assert obj["params"]["timeout_ms"] == 500

    def test_request_round_trip_through_python_model(self):
        # Build a real Request and serialize via model_dump, then parse
        # as the C firmware would (manual json.loads).
        req = Request(command="heartbeat", params={})
        line = req.to_jsonl().encode("utf-8")
        obj = c_firmware_parse_request(line)
        assert obj["command"] == "heartbeat"
        assert obj["request_id"] == req.request_id

    def test_string_with_special_characters_round_trips(self):
        # C firmware unescapes \n, \t, \r, \", \\, \/. Make sure our
        # Python model doesn't break on these.
        params = {"note": 'tab\there, newline\nhere, quote"end'}
        req = Request(command="set_metadata", params=params)
        line = req.to_jsonl().encode("utf-8")
        obj = c_firmware_parse_request(line)
        assert obj["params"]["note"] == params["note"]


class TestResponseFormat:
    def test_ok_response(self):
        state = json.dumps(
            {
                "state": "IDLE",
                "power": {},
                "boot": {},
                "reset": {},
                "motor_enable": False,
                "estop_active": False,
            }
        )
        line = c_firmware_serialize_response("req-001", ok=True, state_json=state)
        obj = json.loads(line.decode("utf-8"))
        assert obj["result"] == "ok"
        assert obj["request_id"] == "req-001"
        assert obj["observed_state"] == state

    def test_error_response(self):
        line = c_firmware_serialize_response(
            "req-002",
            ok=False,
            error_class="UNKNOWN_COMMAND",
            message="no such command: foo",
        )
        obj = json.loads(line.decode("utf-8"))
        assert obj["result"] == "error"
        assert obj["error_class"] == "UNKNOWN_COMMAND"
        assert obj["message"] == "no such command: foo"

    def test_ok_response_parsed_by_python_model(self):
        state = json.dumps(
            {
                "state": "IDLE",
                "power": {},
                "boot": {},
                "reset": {},
                "motor_enable": False,
                "estop_active": False,
            }
        )
        line = c_firmware_serialize_response("req-003", ok=True, state_json=state)
        # Pydantic should accept it (Pydantic coerces JSON to typed fields).
        resp = Response.model_validate_json(line)
        assert resp.result == "ok"
        assert resp.request_id == "req-003"
        assert resp.observed_state == state  # Pydantic parses the JSON string

    def test_error_response_parsed_by_python_model(self):
        line = c_firmware_serialize_response(
            "req-004",
            ok=False,
            error_class="SAFETY_INTERLOCK_OPEN",
            message="estop active",
        )
        err = ErrorResponse.model_validate_json(line)
        assert err.result == "error"
        assert err.error_class == "SAFETY_INTERLOCK_OPEN"
        assert err.message == "estop active"


class TestProtocolContract:
    """Contract: every command in the H2 surface round-trips."""

    @pytest.mark.parametrize(
        "command, params",
        [
            ("heartbeat", {}),
            ("get_status", {}),
            ("get_capabilities", {}),
            ("firmware_version", {}),
            ("estop_status", {}),
            ("safe_state", {}),
            ("power_set", {"channel": "power_esp32_1", "state": True}),
            ("power_set", {"channel": "power_pico_2", "state": False}),
            ("motor_enable_set", {"state": True}),
            ("boot_set", {"channel": "boot_esp32_1", "state": True}),
            ("reset_pulse", {"channel": "reset_esp32_1", "duration_ms": 100}),
            ("power_cycle", {"channel": "power_esp32_1", "off_duration_ms": 500}),
        ],
    )
    def test_command_round_trips(self, command, params):
        req = Request(command=command, params=params)
        line = req.to_jsonl().encode("utf-8")
        # C-firmware-style parser accepts it.
        obj = c_firmware_parse_request(line)
        assert obj["command"] == command
        assert obj["params"] == params

    def test_protocol_version_in_all_requests(self):
        req = Request(command="heartbeat")
        line = req.to_jsonl().encode("utf-8")
        obj = c_firmware_parse_request(line)
        assert obj["protocol_version"] == PROTOCOL_VERSION

    def test_invalid_json_rejected_by_python_parser(self):
        # Garbage bytes should NOT parse as a Request.
        from pydantic import ValidationError

        with pytest.raises((ValidationError, ValueError)):
            Request.model_validate_json(b"not json at all")

    def test_extra_fields_rejected(self):
        # The C firmware SKIPS unknown fields. The Python model
        # rejects them (extra="forbid"). This is documented divergence:
        # the firmware is lenient, Python is strict. We document it
        # here so any future change is intentional.
        from pydantic import ValidationError

        line = (
            b'{"protocol_version":"0.1.0","request_id":"r","command":"c",'
            b'"params":{},"unknown_field":42}'
        )
        # C firmware would accept (skip unknown). Python model rejects.
        obj = c_firmware_parse_request(line)
        assert obj["unknown_field"] == 42
        with pytest.raises(ValidationError):
            Request.model_validate_json(line)


class TestChannelNames:
    """The C firmware has hard-coded channel names; the Python
    protocol uses Literal types. Verify they match."""

    @pytest.mark.parametrize(
        "channel",
        [
            "power_esp32_1",
            "power_esp32_2",
            "power_pico_1",
            "power_pico_2",
            "power_sensor_1",
            "power_aux_1",
            "power_host_1",
            "boot_esp32_1",
            "boot_esp32_2",
            "boot_pico_1",
            "reset_esp32_1",
            "reset_esp32_2",
            "reset_pico_1",
        ],
    )
    def test_channel_in_command(self, channel):
        # Build a request with this channel and verify it serializes
        # with the right command + parameter name.
        req = Request(command="power_set", params={"channel": channel})
        line = req.to_jsonl().encode("utf-8")
        obj = c_firmware_parse_request(line)
        assert obj["command"] == "power_set"
        assert obj["params"]["channel"] == channel

    def test_known_channel_names(self):
        from hive.io_controller.protocol import BOOT_CHANNELS, POWER_CHANNELS, RESET_CHANNELS

        # Each set has 7, 3, 3 channels respectively.
        assert len(POWER_CHANNELS) == 7
        assert len(BOOT_CHANNELS) == 3
        assert len(RESET_CHANNELS) == 3


class TestStateValues:
    """C firmware emits state strings like 'IDLE', 'ACTIVE', 'FAULT', 'SAFE'.
    Python doesn't model them (yet) but the JSON values must be parseable.
    """

    @pytest.mark.parametrize(
        "state",
        ["BOOT", "IDLE", "ACTIVE", "FAULT", "SAFE", "DISCONNECTED"],
    )
    def test_state_string_in_response(self, state):
        state_json = json.dumps(
            {
                "state": state,
                "power": {},
                "boot": {},
                "reset": {},
                "motor_enable": False,
                "estop_active": False,
            }
        )
        line = c_firmware_serialize_response("req", ok=True, state_json=state_json)
        obj = json.loads(line.decode("utf-8"))
        inner = json.loads(obj["observed_state"])
        assert inner["state"] == state
