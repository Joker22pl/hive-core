"""Example: mock HIVE-IO client usage.

Run from the hive-core root::

    python examples/mock_hive_io.py

Shows how to use ``MockHiveIOClient`` and the separate test-hooks
surface (``MockHiveIOTestHooks``) to script ESTOP scenarios without
real hardware.
"""

from __future__ import annotations

import sys

from hive.io_controller import (
    MockHiveIOClient,
    get_test_hooks_for,
)


def main() -> int:
    client = MockHiveIOClient()
    client.connect()

    # Wire-protocol surface — what production code uses.
    caps = client.get_capabilities()
    caps_dict = caps.observed_state if isinstance(caps.observed_state, dict) else {}
    print(f"protocol_version: {caps_dict.get('protocol_version')}")
    print(f"firmware_version:  {caps_dict.get('firmware_version')}")

    status = client.get_status()
    snapshot = status.observed_state if isinstance(status.observed_state, dict) else {}
    print(f"initial safe state: motor_enable={snapshot.get('motor_enable')}")

    # Test-only surface — obtained explicitly so production code cannot
    # accidentally use it.
    hooks = get_test_hooks_for(client)

    # Inject ESTOP and verify motor_enable is blocked.
    hooks.inject_estop(True)
    print(f"\nESTOP injected. events: {[e.event for e in hooks.poll_events()]}")

    r = client.motor_enable_set(True)
    print(f"motor_enable_set(true) under ESTOP: {r.result} ({r.error_class})")

    # Release ESTOP and retry.
    hooks.inject_estop(False)
    r = client.motor_enable_set(True)
    print(f"motor_enable_set(true) after release: {r.result} (observed={r.observed_state})")

    # Force safe state.
    r = client.safe_state()
    print(f"safe_state: {r.result} (observed={r.observed_state})")

    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
