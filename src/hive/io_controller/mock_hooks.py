"""Test hooks for ``MockHiveIOClient``.

This module exposes helpers that are **only** intended for use in
tests. They are intentionally not part of the public ``HiveIOClient``
interface, so production code cannot accidentally rely on them.

The contract:

* Production code interacts with HIVE-IO through the JSON Lines wire
  protocol — i.e. ``HiveIOClient.send_request()`` and its typed
  helpers (``safe_state``, ``motor_enable_set``, etc.). ESTOP state
  is **read** via ``estop_status`` and is **changed** by the firmware
  itself (hardware E-stop button) — the host cannot inject it via the
  wire.

* Tests need a way to set up ESTOP scenarios without a real button.
  They obtain a :class:`MockHiveIOTestHooks` from
  :func:`get_test_hooks_for` and call ``inject_estop()`` on it.
  This is *not* discoverable from the regular HiveIOClient API — you
  must ask for the hooks explicitly.

See ``docs/io-protocol.md`` for the canonical statement that ESTOP
injection is a test-only mechanism and is not part of the production
wire protocol.
"""

from __future__ import annotations

from hive.io_controller.mock import MockHiveIOClient


class MockHiveIOTestHooks:
    """Test-only hooks for ``MockHiveIOClient``.

    Production code MUST NOT depend on this class — there is no
    production equivalent. The whole point is to keep the test surface
    separate from the wire-protocol surface.
    """

    def __init__(self, mock: MockHiveIOClient) -> None:
        self._mock = mock

    def inject_estop(self, active: bool) -> None:
        """Inject an ESTOP state change (test helper).

        Emits an :class:`AsyncEvent` (``ESTOP_PRESSED`` or
        ``ESTOP_RELEASED``) that becomes visible via ``poll_events``.
        """
        self._mock._inject_estop(active)

    def poll_events(self) -> list:
        """Drain and return pending async events (test helper)."""
        return self._mock._poll_events()

    def snapshot(self) -> dict:
        """Read-only snapshot of the mock state (test helper).

        Returns a deep copy of the channel state — safe to inspect and
        assert against without locking.
        """
        return self._mock.snapshot()


def get_test_hooks_for(mock: MockHiveIOClient) -> MockHiveIOTestHooks:
    """Return a :class:`MockHiveIOTestHooks` for the given mock client.

    This is the only way tests should obtain injection hooks — by
    asking explicitly. The function lives in a separate module so the
    name itself signals "test code only".
    """
    if not isinstance(mock, MockHiveIOClient):
        raise TypeError(
            f"get_test_hooks_for only accepts MockHiveIOClient, got {type(mock).__name__}"
        )
    return MockHiveIOTestHooks(mock)
