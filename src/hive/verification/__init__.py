"""Verification profile runner — skeleton (H0).

H1+: real execution engine for steps.
"""

from __future__ import annotations

from dataclasses import dataclass

from hive.common.errors import NotImplementedInStageError
from hive.common.models.verification_profile import VerificationProfile


@dataclass
class VerificationContext:
    """Context passed to the verification runner."""

    device_id: str
    artifact_ref: str | None
    session_id: str
    lock_owner: str = "hare"


class VerificationRunner:
    """Profile runner. H0 is a skeleton that validates the profile only."""

    def __init__(self, context: VerificationContext) -> None:
        self.context = context

    def run(self, profile: VerificationProfile) -> dict:
        """Execute a profile. H0 returns a placeholder result.

        H1+ executes steps in order, collecting results.
        """
        raise NotImplementedInStageError("VerificationRunner.run", "H1")
