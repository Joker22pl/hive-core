"""ESP32 adapter skeleton (H0) — esptool integration (H3+)."""

from __future__ import annotations

from hive.adapters.base import Adapter
from hive.common.errors import NotImplementedInStageError


class Esp32Adapter(Adapter):
    """ESP32 flashing adapter (esptool in H3+)."""

    name = "esp32"

    def __init__(self, port: str, baudrate: int = 115200) -> None:
        self.port = port
        self.baudrate = baudrate

    def open(self) -> None:
        raise NotImplementedInStageError("Esp32Adapter.open", "H3")

    def close(self) -> None:
        raise NotImplementedInStageError("Esp32Adapter.close", "H3")

    def enter_bootloader(self) -> None:
        raise NotImplementedInStageError("Esp32Adapter.enter_bootloader", "H3")

    def flash(self, image_path: str, address: int = 0x0) -> None:
        raise NotImplementedInStageError("Esp32Adapter.flash", "H3")

    def reset(self) -> None:
        raise NotImplementedInStageError("Esp32Adapter.reset", "H3")
