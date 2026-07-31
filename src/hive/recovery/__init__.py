"""Recovery strategies — skeleton (H0).

H3+: real execution of recovery strategies.
"""

from __future__ import annotations

from dataclasses import dataclass

from hive.common.errors import NotImplementedInStageError
from hive.common.models.device import DeviceManifest


@dataclass
class RecoveryContext:
    """Context for a recovery attempt."""

    device: DeviceManifest
    attempt: int
    session_id: str


class RecoveryRunner:
    """Executes a recovery strategy for a device."""

    def __init__(self, context: RecoveryContext) -> None:
        self.context = context

    def run(self) -> dict:
        """Execute the strategy. H0 raises NotImplementedInStageError."""
        raise NotImplementedInStageError("RecoveryRunner.run", "H3")
