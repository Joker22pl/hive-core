"""Transport abstraction for HIVE-IO.

Decouples the JSON Lines protocol from the physical transport
(USB CDC serial, loopback for tests, future TCP/IP for H7+).

Implementations:
    * SerialTransport — pyserial.Serial wrapper (real USB CDC)
    * LoopbackTransport — pair of byte buffers for tests
    * TcpTransport — (H7+, future)

All transports present a line-oriented interface: write_line(bytes),
read_line(timeout). The transport does NOT do any JSON parsing —
that's the protocol layer's job (hive.io_controller.protocol).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from typing import Any

from hive.common.errors import HiveError


class TransportError(HiveError):
    """Raised when the transport fails irrecoverably."""


class HiveIOTransport(ABC):
    """Abstract transport for HIVE-IO."""

    @abstractmethod
    def open(self) -> None:
        """Open the transport."""

    @abstractmethod
    def close(self) -> None:
        """Close the transport."""

    @abstractmethod
    def write_line(self, line: bytes) -> None:
        """Write a single line (with trailing \\n added by the transport).

        The transport MUST add the trailing newline — the protocol
        layer just provides the JSON document as bytes.
        """

    @abstractmethod
    def read_line(self, timeout_s: float) -> bytes | None:
        """Read a single line (newline-stripped).

        Returns None on timeout.
        """

    @property
    @abstractmethod
    def is_open(self) -> bool:
        """True if the transport is open."""


class SerialTransport(HiveIOTransport):
    """Real USB CDC transport via pyserial.

    Lazy-imports pyserial so this module is usable in environments
    where pyserial isn't installed (e.g. a minimal CI worker that
    only runs protocol-layer tests).
    """

    def __init__(
        self,
        port: str,
        *,
        baudrate: int = 115200,
        timeout_s: float = 2.0,
        write_timeout_s: float | None = None,
    ) -> None:
        self._port = port
        self._baudrate = baudrate
        self._timeout_s = timeout_s
        self._write_timeout_s = write_timeout_s
        self._ser: Any = None
        self._open = False

    def open(self) -> None:
        if self._open:
            return
        try:
            import serial  # type: ignore[import-not-found]
        except ImportError as e:
            raise TransportError(
                "pyserial is required for SerialTransport",
                details={"missing_module": "pyserial"},
            ) from e
        try:
            self._ser = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                timeout=self._timeout_s,
                write_timeout=self._write_timeout_s,
            )
        except Exception as e:
            raise TransportError(
                f"Failed to open serial port {self._port!r}: {e}",
                details={"port": self._port, "baudrate": self._baudrate},
            ) from e
        self._open = True

    def close(self) -> None:
        if not self._open:
            return
        try:
            if self._ser is not None:
                self._ser.close()
        finally:
            self._ser = None
            self._open = False

    def write_line(self, line: bytes) -> None:
        if not self._open or self._ser is None:
            raise TransportError("SerialTransport is not open")
        if not line.endswith(b"\n"):
            line = line + b"\n"
        try:
            self._ser.write(line)
        except Exception as e:
            raise TransportError(f"Serial write failed: {e}") from e

    def read_line(self, timeout_s: float) -> bytes | None:
        if not self._open or self._ser is None:
            raise TransportError("SerialTransport is not open")
        # pyserial honors its own timeout from construction; for
        # per-call timeouts we just respect the existing timeout.
        try:
            data = self._ser.readline()
        except Exception as e:
            raise TransportError(f"Serial read failed: {e}") from e
        if not data:
            return None
        # Strip trailing newline (CR, LF, CRLF)
        while data.endswith((b"\n", b"\r")):
            data = data[:-1]
        return data

    @property
    def is_open(self) -> bool:
        return self._open


class LoopbackTransport(HiveIOTransport):
    """In-memory transport for tests.

    Two paired transports share a pair of byte queues. Lines written
    to one side are immediately readable on the other.

    Usage in tests:
        a, b = LoopbackTransport.create_pair()
        a.write_line(b'{"hello": "from a"}')
        assert b.read_line(1.0) == b'{"hello": "from a"}'
        b.write_line(b'{"reply": "from b"}')
        assert a.read_line(1.0) == b'{"reply": "from b"}'
    """

    def __init__(self, peer: LoopbackTransport | None = None) -> None:
        # peer is the OTHER side; we send to peer's inbox, read from ours.
        # Inbox: lines I can read
        # Outbox: lines I send (go to peer's inbox)
        self._inbox: deque[bytes] = deque()
        self._peer_inbox: deque[bytes] | None = None
        if peer is not None:
            # I am "left", peer is "right"
            self._peer_inbox = peer._inbox
            peer._peer_inbox = self._inbox
        self._open = True

    @classmethod
    def create_pair(cls) -> tuple[LoopbackTransport, LoopbackTransport]:
        # Create right first (no peer), then left (with right as peer).
        right = cls()
        left = cls(peer=right)
        return left, right

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    def write_line(self, line: bytes) -> None:
        if not self._open:
            raise TransportError("LoopbackTransport is closed")
        if self._peer_inbox is None:
            raise TransportError("LoopbackTransport is not paired")
        if not line.endswith(b"\n"):
            line = line + b"\n"
        self._peer_inbox.append(line)

    def read_line(self, timeout_s: float) -> bytes | None:
        if not self._open:
            raise TransportError("LoopbackTransport is closed")
        if self._inbox:
            data = self._inbox.popleft()
            while data.endswith((b"\n", b"\r")):
                data = data[:-1]
            return data
        return None

    @property
    def is_open(self) -> bool:
        return self._open


__all__ = [
    "HiveIOTransport",
    "LoopbackTransport",
    "SerialTransport",
    "TransportError",
]
