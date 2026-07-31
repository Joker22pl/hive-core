"""SSH device discovery via paramiko.

H1 placeholder: this module exists so HARE / HIVE can refer to
SshAdapter as part of the public discovery surface. Real SSH
scanning (LAN scan, host_key_fingerprint collection) is planned
for H4 when SSH host support arrives.

The SshAdapter stub returns an empty list and is always present.
H4 will replace list_devices() with real paramiko-based scanning
(per ADR-0003: SshIdentity requires host_key_fingerprint SHA-256
for autonomous SSH operations).

The reason we include the stub now:
* keeps DiscoveryService's import surface stable across H1 → H4
* lets the CLI advertise `device scan` with ssh support without
  crashing on hosts without paramiko installed
* tests can construct a fake SshAdapter without depending on paramiko
"""

from __future__ import annotations

from typing import Any

from hive.common.errors import HiveError


def _require_paramiko():
    try:
        import paramiko

        return paramiko
    except ImportError as e:
        raise HiveError(
            "paramiko is required for SSH discovery. Install with: pip install paramiko",
            details={"missing_module": "paramiko"},
        ) from e


class SshAdapter:
    """SSH device enumeration via paramiko (H4 stub).

    H1: returns empty list. The class is constructable so tests can
    verify DiscoveryService wiring.

    H4+: implement list_devices() to scan configured subnets, attempt
    SSH connections, and collect host_key_fingerprint for each.
    """

    source = "ssh"

    def __init__(self) -> None:
        """Construct the SshAdapter.

        H1: just verifies paramiko is importable. H4: takes a list of
        subnets + credentials to probe.
        """
        _require_paramiko()

    def list_devices(self) -> list[dict[str, Any]]:
        """Return discovered SSH hosts.

        H1: always returns empty list (real SSH scan lands in H4).
        H4: returns dicts with ssh_host, ssh_port, ssh_user,
        ssh_host_key_fingerprint for each reachable host.
        """
        return []
