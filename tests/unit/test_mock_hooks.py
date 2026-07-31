"""Tests for the test-hooks separation (MEDIUM-4 fix)."""

from __future__ import annotations

import pytest

from hive.io_controller import MockHiveIOClient, get_test_hooks_for
from hive.io_controller.mock_hooks import MockHiveIOTestHooks


def test_mock_client_does_not_expose_inject_estop_publicly() -> None:
    """`inject_estop` is private on MockHiveIOClient — it has a leading underscore."""
    client = MockHiveIOClient()
    assert not hasattr(client, "inject_estop"), (
        "inject_estop must be private (renamed to _inject_estop) on MockHiveIOClient"
    )
    assert hasattr(client, "_inject_estop")


def test_mock_client_does_not_expose_poll_events_publicly() -> None:
    """`poll_events` is private on MockHiveIOClient."""
    client = MockHiveIOClient()
    assert not hasattr(client, "poll_events")
    assert hasattr(client, "_poll_events")


def test_get_test_hooks_for_returns_hooks_object() -> None:
    """get_test_hooks_for(mock) returns a MockHiveIOTestHooks."""
    client = MockHiveIOClient()
    hooks = get_test_hooks_for(client)
    assert isinstance(hooks, MockHiveIOTestHooks)


def test_get_test_hooks_for_rejects_non_mock() -> None:
    """Only MockHiveIOClient instances are accepted (defense in depth)."""
    with pytest.raises(TypeError, match="only accepts MockHiveIOClient"):

        class OtherClient:
            pass

        get_test_hooks_for(OtherClient())


def test_hooks_inject_estop_blocks_motor_enable() -> None:
    """Hooks.inject_estop → motor_enable_set is refused via wire."""
    client = MockHiveIOClient()
    client.connect()
    hooks = get_test_hooks_for(client)
    hooks.inject_estop(True)
    r = client.motor_enable_set(True)
    assert r.result == "error"
    assert r.error_class == "SAFETY_INTERLOCK_OPEN"


def test_hooks_poll_events_returns_inject_event() -> None:
    """Hooks.poll_events returns the ESTOP_PRESSED event after inject_estop(True)."""
    client = MockHiveIOClient()
    client.connect()
    hooks = get_test_hooks_for(client)
    hooks.inject_estop(True)
    events = hooks.poll_events()
    assert len(events) == 1
    assert events[0].event == "ESTOP_PRESSED"


def test_hooks_only_set_once_per_transition() -> None:
    """Injecting the same state twice does not emit a duplicate event."""
    client = MockHiveIOClient()
    client.connect()
    hooks = get_test_hooks_for(client)
    hooks.inject_estop(True)
    hooks.inject_estop(True)  # second True is no-op
    events = hooks.poll_events()
    assert len(events) == 1


def test_hooks_snapshot_returns_state() -> None:
    """Hooks.snapshot returns a dict representation of mock state."""
    client = MockHiveIOClient()
    client.connect()
    hooks = get_test_hooks_for(client)
    snap = hooks.snapshot()
    assert isinstance(snap, dict)
    assert snap["motor_enable"] is False
    assert snap["estop_active"] is False


def test_production_code_pattern_does_not_use_hooks() -> None:
    """Sanity: a typical production call chain does not mention hooks."""
    # Ensure that the public HiveIOClient surface does not include
    # the test hooks — the only way to obtain them is via
    # get_test_hooks_for, which is intentionally absent from
    # ``hive.io_controller.protocol`` and the wire protocol.
    client = MockHiveIOClient()
    client.connect()
    client.safe_state()
    client.get_status()
    # No hooks attribute exposed on client itself.
    assert "inject_estop" not in dir(client)
    assert "poll_events" not in dir(client)
