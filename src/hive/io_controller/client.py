"""HiveIOClient — high-level interface to HIVE-IO.

H0: abstract interface + dependency-injected transport.
H1+: real USB CDC transport via `pyserial` + JSON Lines framing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from hive.common.errors import NotImplementedInStageError
from hive.io_controller.protocol import (
    POWER_CHANNELS,
    PROTOCOL_VERSION,
    Request,
    Response,
)


class HiveIOClient(ABC):
    """Abstract client for HIVE-IO controller."""

    protocol_version: str = PROTOCOL_VERSION

    @abstractmethod
    def connect(self) -> None:
        """Open the transport (USB CDC)."""

    @abstractmethod
    def close(self) -> None:
        """Close the transport."""

    @abstractmethod
    def send_request(self, request: Request) -> Response:
        """Send a request and wait for the response."""

    @abstractmethod
    def get_status(self) -> Response:
        """Return HIVE-IO status report."""

    @abstractmethod
    def get_capabilities(self) -> Response:
        """Return HIVE-IO capabilities (channels, FW version)."""

    @abstractmethod
    def heartbeat(self) -> Response:
        """Send a heartbeat."""

    @abstractmethod
    def safe_state(self) -> Response:
        """Force HIVE-IO into safe state (MOTOR_ENABLE=OFF, BOOT inactive, RESET released)."""

    @abstractmethod
    def power_set(self, channel: str, state: bool) -> Response:
        """Set power channel state."""

    @abstractmethod
    def power_cycle(self, channel: str, off_duration_ms: int = 500) -> Response:
        """Power-cycle a channel."""

    @abstractmethod
    def reset_pulse(self, channel: str, duration_ms: int = 100) -> Response:
        """Emit a reset pulse on a channel."""

    @abstractmethod
    def boot_set(self, channel: str, state: bool) -> Response:
        """Set BOOT line state."""

    @abstractmethod
    def motor_enable_set(self, state: bool) -> Response:
        """Set master motor enable."""

    @abstractmethod
    def estop_status(self) -> Response:
        """Return ESTOP status (ACTIVE / INACTIVE)."""

    @abstractmethod
    def firmware_version(self) -> Response:
        """Return HIVE-IO firmware version."""


class UsbHiveIOClient(HiveIOClient):
    """Real USB CDC client — planned for H2.

    H0 raises NotImplementedInStageError on every method.
    """

    _STAGE = "H2"

    def connect(self) -> None:
        raise NotImplementedInStageError("HiveIOClient USB CDC transport", self._STAGE)

    def close(self) -> None:
        raise NotImplementedInStageError("HiveIOClient USB CDC transport", self._STAGE)

    def send_request(self, request: Request) -> Response:
        raise NotImplementedInStageError("HiveIOClient USB CDC transport", self._STAGE)

    def get_status(self) -> Response:
        raise NotImplementedInStageError("HiveIOClient.get_status", self._STAGE)

    def get_capabilities(self) -> Response:
        raise NotImplementedInStageError("HiveIOClient.get_capabilities", self._STAGE)

    def heartbeat(self) -> Response:
        raise NotImplementedInStageError("HiveIOClient.heartbeat", self._STAGE)

    def safe_state(self) -> Response:
        raise NotImplementedInStageError("HiveIOClient.safe_state", self._STAGE)

    def power_set(self, channel: str, state: bool) -> Response:
        if channel not in POWER_CHANNELS:
            raise ValueError(f"Unknown power channel: {channel!r}")
        raise NotImplementedInStageError("HiveIOClient.power_set", self._STAGE)

    def power_cycle(self, channel: str, off_duration_ms: int = 500) -> Response:
        if channel not in POWER_CHANNELS:
            raise ValueError(f"Unknown power channel: {channel!r}")
        raise NotImplementedInStageError("HiveIOClient.power_cycle", self._STAGE)

    def reset_pulse(self, channel: str, duration_ms: int = 100) -> Response:
        raise NotImplementedInStageError("HiveIOClient.reset_pulse", self._STAGE)

    def boot_set(self, channel: str, state: bool) -> Response:
        raise NotImplementedInStageError("HiveIOClient.boot_set", self._STAGE)

    def motor_enable_set(self, state: bool) -> Response:
        raise NotImplementedInStageError("HiveIOClient.motor_enable_set", self._STAGE)

    def estop_status(self) -> Response:
        raise NotImplementedInStageError("HiveIOClient.estop_status", self._STAGE)

    def firmware_version(self) -> Response:
        raise NotImplementedInStageError("HiveIOClient.firmware_version", self._STAGE)


__all__ = ["HiveIOClient", "UsbHiveIOClient"]
