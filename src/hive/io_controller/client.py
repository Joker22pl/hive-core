"""HiveIOClient — high-level interface to HIVE-IO.

H0: abstract interface only.
H1+: real USB CDC transport via `pyserial` + JSON Lines framing is
provided by ``hive.io_controller.serial_client.SerialHiveIOClient``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from hive.io_controller.protocol import (
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


__all__ = ["HiveIOClient"]
