"""Base adapter class — common interface for all device adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Adapter(ABC):
    """Base adapter interface.

    An adapter encapsulates the I/O operations for a specific device class
    (USB, serial, ESP32 flashing, RP2040 flashing, SSH).
    """

    name: str = "adapter"

    @abstractmethod
    def open(self) -> None:
        """Open the underlying transport."""

    @abstractmethod
    def close(self) -> None:
        """Close the underlying transport."""

    def __enter__(self) -> Adapter:
        self.open()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
