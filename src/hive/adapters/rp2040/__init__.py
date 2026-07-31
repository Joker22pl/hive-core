"""RP2040 adapter skeleton (H0) — UF2 / picotool (H3+)."""

from __future__ import annotations

from hive.adapters.base import Adapter
from hive.common.errors import NotImplementedInStageError


class Rp2040Adapter(Adapter):
    """RP2040 flashing adapter (UF2 / picotool in H3+)."""

    name = "rp2040"

    def __init__(self, port: str | None = None) -> None:
        self.port = port

    def open(self) -> None:
        raise NotImplementedInStageError("Rp2040Adapter.open", "H3")

    def close(self) -> None:
        raise NotImplementedInStageError("Rp2040Adapter.close", "H3")

    def enter_bootsel(self) -> None:
        raise NotImplementedInStageError("Rp2040Adapter.enter_bootsel", "H3")

    def copy_uf2(self, uf2_path: str) -> None:
        raise NotImplementedInStageError("Rp2040Adapter.copy_uf2", "H3")

    def reset(self) -> None:
        raise NotImplementedInStageError("Rp2040Adapter.reset", "H3")
