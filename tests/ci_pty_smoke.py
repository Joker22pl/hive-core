"""CI smoke test: the PTY-backed mock firmware accepts a real JSON Lines request
and the host client parses the response correctly.

Designed to be cheap (no fixtures, no pytest machinery, no xdist):
runs as a single subprocess script invoked from the CI workflow.

Exit codes:
    0 — smoke passed
    1 — smoke failed (output on stderr)
    2 — environment not supported (PTY unavailable, missing dependency)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]  # gaja-projekty/
MOCK_TOOL = REPO_ROOT / "hive-io-standalone" / "tools" / "mock_hive_io.py"


def _probe_pty() -> bool:
    try:
        import pty  # noqa: F401
    except ImportError:
        return False
    if not hasattr(os, "openpty"):
        return False
    return True


def _spawn_mock() -> tuple[subprocess.Popen, Path]:
    proc = subprocess.Popen(
        [sys.executable, str(MOCK_TOOL), "--foreground"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    deadline = time.monotonic() + 5
    buf = b""
    slave_path: Path | None = None
    while time.monotonic() < deadline:
        chunk = proc.stderr.readline() if proc.stderr is not None else b""
        if not chunk:
            time.sleep(0.02)
            continue
        buf += chunk
        if b"slave path:" in buf:
            line = buf.decode().splitlines()[-1]
            slave_path = Path(line.split("slave path:")[-1].strip())
            break
    if slave_path is None:
        proc.kill()
        raise RuntimeError(f"mock did not announce a slave path; got: {buf!r}")
    return proc, slave_path


def main() -> int:
    if not _probe_pty():
        print("PTY unavailable on this platform — skipping", file=sys.stderr)
        return 2
    if not MOCK_TOOL.is_file():
        print(f"missing mock tool: {MOCK_TOOL}", file=sys.stderr)
        return 1
    mock, slave = _spawn_mock()
    try:
        # Use the host client directly so we exercise the same code
        # path CI integration tests do.
        sys.path.insert(0, str(REPO_ROOT / "hive-core-standalone"))
        from hive.io_controller.serial_client import SerialHiveIOClient  # type: ignore

        client = SerialHiveIOClient.for_serial_port(
            str(slave), request_timeout_s=3.0
        )
        try:
            status = client.get_status()
            assert status.result == "ok", status
            assert status.observed_state is not None
            assert "power" in status.observed_state
            caps = client.get_capabilities()
            assert caps.result == "ok"
            assert "power_esp32_1" in caps.observed_state["channels"]
            safe = client.safe_state()
            assert safe.result == "ok"
            assert safe.observed_state["state"] == "SAFE"
            print(json.dumps({"smoke": "ok", "channels": len(caps.observed_state["channels"])}))
        finally:
            client.close()
    finally:
        mock.terminate()
        try:
            mock.wait(timeout=2)
        except subprocess.TimeoutExpired:
            mock.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())
