"""SSH adapter skeleton (H0) — paramiko transport (H4+)."""

from __future__ import annotations

from hive.adapters.base import Adapter
from hive.common.errors import NotImplementedInStageError


class SshAdapter(Adapter):
    """SSH transport adapter (paramiko in H4+)."""

    name = "ssh"

    def __init__(
        self,
        host: str,
        user: str,
        port: int = 22,
        credential_reference: str | None = None,
        expected_host_key_fingerprint: str | None = None,
    ) -> None:
        self.host = host
        self.user = user
        self.port = port
        self.credential_reference = credential_reference
        self.expected_host_key_fingerprint = expected_host_key_fingerprint

    def open(self) -> None:
        raise NotImplementedInStageError("SshAdapter.open", "H4")

    def close(self) -> None:
        raise NotImplementedInStageError("SshAdapter.close", "H4")

    def exec(self, command: str, timeout_s: float = 30.0) -> tuple[int, str, str]:
        """Run a command, return (exit_code, stdout, stderr)."""
        raise NotImplementedInStageError("SshAdapter.exec", "H4")

    def put_file(self, local_path: str, remote_path: str) -> None:
        raise NotImplementedInStageError("SshAdapter.put_file", "H4")
