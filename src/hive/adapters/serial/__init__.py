"""Serial adapter skeleton (H0) — pyserial transport (H1+)."""

from __future__ import annotations

from hive.adapters.base import Adapter
from hive.common.errors import NotImplementedInStageError


class SerialAdapter(Adapter):
    """Serial transport adapter (uses pyserial in H1+)."""

    name = "serial"

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

    def open(self) -> None:
        raise NotImplementedInStageError("SerialAdapter.open", "H1")

    def close(self) -> None:
        raise NotImplementedInStageError("SerialAdapter.close", "H1")

    def read_until(self, pattern: bytes, timeout_s: float) -> bytes:
        raise NotImplementedInStageError("SerialAdapter.read_until", "H1")

    def write(self, data: bytes) -> int:
        raise NotImplementedInStageError("SerialAdapter.write", "H1")
