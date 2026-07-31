"""HIVE-IO controller client (USB CDC + JSON Lines).

H0: model + protocol validation + in-process mock.
H1: real USB-CDC transport via pyserial.
H2: full integration with HIVE-IO firmware — SerialHiveIOClient
with timeouts, retry, heartbeat thread.
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
from hive.io_controller.serial_client import (
    HeartbeatLostError,
    HiveIOError,
    SerialHiveIOClient,
)
from hive.io_controller.transport import (
    HiveIOTransport,
    LoopbackTransport,
    SerialTransport,
    TransportError,
)

__all__ = [
    "PROTOCOL_VERSION",
    "AsyncEvent",
    "BootChannel",
    "ErrorResponse",
    "HeartbeatLostError",
    "HiveIOClient",
    "HiveIOError",
    "HiveIOTransport",
    "LoopbackTransport",
    "MockHiveIOClient",
    "MockHiveIOTestHooks",
    "PowerChannel",
    "Request",
    "ResetChannel",
    "Response",
    "SerialHiveIOClient",
    "SerialTransport",
    "TransportError",
    "get_test_hooks_for",
    "validate_protocol_version",
]
