"""HIVE-IO controller client (USB CDC + JSON Lines).

H0 scope: model + protocol validation + in-process mock.
H1+: real USB-CDC transport.
H2: full integration with HIVE-IO firmware.
"""

from hive.io_controller.client import HiveIOClient
from hive.io_controller.mock import MockHiveIOClient
from hive.io_controller.mock_hooks import MockHiveIOTestHooks, get_test_hooks_for
from hive.io_controller.protocol import (
    PROTOCOL_VERSION,
    AsyncEvent,
    BootChannel,
    ErrorResponse,
    PowerChannel,
    Request,
    ResetChannel,
    Response,
    validate_protocol_version,
)

__all__ = [
    "PROTOCOL_VERSION",
    "AsyncEvent",
    "BootChannel",
    "ErrorResponse",
    "HiveIOClient",
    "MockHiveIOClient",
    "MockHiveIOTestHooks",
    "PowerChannel",
    "Request",
    "ResetChannel",
    "Response",
    "get_test_hooks_for",
    "validate_protocol_version",
]
