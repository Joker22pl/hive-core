"""Tests for HIVE-IO protocol model + mock client."""

from __future__ import annotations

import pytest

from hive.io_controller import MockHiveIOClient, get_test_hooks_for
from hive.io_controller.protocol import (
    POWER_CHANNELS,
    PROTOCOL_VERSION,
    Request,
    validate_protocol_version,
)

# ---------- Protocol validation ----------


def test_protocol_version_default() -> None:
    req = Request(command="ping")
    assert req.protocol_version == PROTOCOL_VERSION


def test_protocol_version_match_passes() -> None:
    validate_protocol_version(PROTOCOL_VERSION)  # no exception


def test_protocol_version_major_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="MAJOR"):
        validate_protocol_version("1.0.0")
    with pytest.raises(ValueError, match="MAJOR"):
        validate_protocol_version("99.0.0")


def test_protocol_version_minor_too_new_raises() -> None:
    # e.g. PROTOCOL_VERSION is "0.1.0"; a "0.5.0" message is too new for this client
    with pytest.raises(ValueError, match="MINOR"):
        validate_protocol_version("0.5.0")


def test_protocol_version_patch_differs_ok() -> None:
    validate_protocol_version("0.1.42")  # patch is fine


def test_protocol_version_old_minor_ok() -> None:
    validate_protocol_version("0.0.0")  # older minor, ok


# ---------- Request serialization ----------


def test_request_serializes_as_jsonl() -> None:
    req = Request(command="power_set", params={"channel": "esp32_1", "state": True})
    line = req.to_jsonl()
    assert line.endswith("\n")
    import json as _json

    parsed = _json.loads(line.rstrip("\n"))
    assert parsed["command"] == "power_set"
    assert parsed["params"]["channel"] == "esp32_1"


def test_request_id_is_unique() -> None:
    r1 = Request(command="ping")
    r2 = Request(command="ping")
    assert r1.request_id != r2.request_id


# ---------- Mock client ----------


def test_mock_starts_in_safe_state() -> None:
    client = MockHiveIOClient()
    client.connect()
    observed = client.get_status().observed_state
    assert isinstance(observed, dict)
    assert observed["motor_enable"] is False
    for ch in POWER_CHANNELS:
        assert observed["power"][ch] is False
    for ch in observed["boot"]:
        assert observed["boot"][ch] is False


def test_mock_safe_state_is_idempotent() -> None:
    client = MockHiveIOClient()
    client.connect()
    client.power_set("power_esp32_1", True)
    r1 = client.safe_state()
    r2 = client.safe_state()
    assert r1.result == "ok"
    assert r2.result == "ok"
    assert client.snapshot()["power"]["power_esp32_1"] is False


def test_mock_power_set_blocks_when_estop() -> None:
    client = MockHiveIOClient()
    client.connect()
    hooks = get_test_hooks_for(client)
    hooks.inject_estop(True)
    r = client.power_set("power_esp32_1", True)
    assert r.result == "error"
    assert r.error_class == "SAFETY_INTERLOCK_OPEN"


def test_mock_motor_enable_blocks_when_estop() -> None:
    client = MockHiveIOClient()
    client.connect()
    hooks = get_test_hooks_for(client)
    hooks.inject_estop(True)
    r = client.motor_enable_set(True)
    assert r.result == "error"
    assert r.error_class == "SAFETY_INTERLOCK_OPEN"


def test_mock_motor_enable_allows_when_estop_inactive() -> None:
    client = MockHiveIOClient()
    client.connect()
    r = client.motor_enable_set(True)
    assert r.result == "ok"
    assert r.observed_state is True


def test_mock_power_cycle() -> None:
    client = MockHiveIOClient()
    client.connect()
    client.power_set("power_esp32_1", True)
    r = client.power_cycle("power_esp32_1")
    assert r.result == "ok"
    assert client.snapshot()["power"]["power_esp32_1"] is True  # ends up on


def test_mock_unknown_channel_returns_error() -> None:
    client = MockHiveIOClient()
    client.connect()
    r = client.power_set("unicorn_channel", True)
    assert r.result == "error"
    assert r.error_class == "UNKNOWN_CHANNEL"


def test_mock_unknown_command_returns_error() -> None:
    client = MockHiveIOClient()
    client.connect()
    r = client.send_request(Request(command="unicorn_command"))
    assert r.result == "error"
    assert r.error_class == "UNKNOWN_COMMAND"


def test_mock_get_capabilities_reports_channels() -> None:
    client = MockHiveIOClient()
    client.connect()
    caps = client.get_capabilities().observed_state
    assert isinstance(caps, dict)
    assert "power_channels" in caps
    assert "power_esp32_1" in caps["power_channels"]


def test_mock_estop_status_inactive_by_default() -> None:
    client = MockHiveIOClient()
    client.connect()
    r = client.estop_status()
    assert r.observed_state == "INACTIVE"


def test_mock_estop_inject_emits_event() -> None:
    client = MockHiveIOClient()
    client.connect()
    hooks = get_test_hooks_for(client)
    hooks.inject_estop(True)
    events = hooks.poll_events()
    assert len(events) == 1
    assert events[0].event == "ESTOP_PRESSED"


def test_mock_heartbeat() -> None:
    client = MockHiveIOClient()
    client.connect()
    r = client.heartbeat()
    assert r.result == "ok"
    assert r.observed_state == "ack"


def test_mock_firmware_version() -> None:
    client = MockHiveIOClient()
    client.connect()
    r = client.firmware_version()
    assert r.observed_state == "0.1.0-mock"


def test_mock_estop_inject_via_wire_returns_unknown_command() -> None:
    """Per ADR-0006 follow-up: estop_inject is NOT a production wire command.

    The mock dispatcher MUST return UNKNOWN_COMMAND for it; production
    code must use the test hooks instead.
    """
    client = MockHiveIOClient()
    client.connect()
    r = client.send_request(Request(command="estop_inject", params={"active": True}))
    assert r.result == "error"
    assert r.error_class == "UNKNOWN_COMMAND"
    assert "estop_inject" in (r.message or "")


def test_mock_estop_status_unchanged_after_wire_inject_attempt() -> None:
    """A wire estop_inject that returns UNKNOWN_COMMAND must NOT change state."""
    client = MockHiveIOClient()
    client.connect()
    before = client.estop_status().observed_state
    client.send_request(Request(command="estop_inject", params={"active": True}))
    after = client.estop_status().observed_state
    assert before == after == "INACTIVE"
