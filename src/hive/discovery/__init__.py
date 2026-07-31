"""Device discovery — skeleton (H0).

H1+: real USB / serial / SSH discovery via pyudev, pyserial, paramiko.
"""

from __future__ import annotations

from hive.common.errors import NotImplementedInStageError


class DiscoveryService:
    """Discovers USB / serial / SSH devices."""

    def scan(self) -> list[dict]:
        """Scan for devices. H0 raises NotImplementedInStageError."""
        raise NotImplementedInStageError("DiscoveryService.scan", "H1")
