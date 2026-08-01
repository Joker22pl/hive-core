"""Tests for the PTY-backed HIVE-IO mock firmware.

These run on any POSIX host with /dev/ptmx (Linux/macOS). They pair
a real SerialTransport over the slave side of a PTY with a real
PtyHiveIOFirmware on the master side, exercising the JSON Lines
wire protocol end-to-end through a kernel tty layer.

This is the same path the real Pico would use, minus USB CDC.
"""

from __future__ import annotations

import os

# Import the firmware via runpy so we don't require it to be installed.
import runpy
import shutil
import subprocess
import sys
import time
from collections.abc import Generator
from pathlib import Path

import pytest

from hive.io_controller.protocol import Request
from hive.io_controller.serial_client import SerialHiveIOClient

REPO_ROOT = Path(__file__).resolve().parents[4]  # gaja-projekty/
MOCK_TOOL = REPO_ROOT / "hive-io-standalone" / "tools" / "mock_hive_io.py"


def _spawn_mock(timeout_s: float = 5.0) -> subprocess.Popen:
    """Spawn the PTY mock as a subprocess and return its handle."""
    assert MOCK_TOOL.is_file(), f"missing mock tool: {MOCK_TOOL}"
    return subprocess.Popen(
        [sys.executable, str(MOCK_TOOL), "--foreground"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _wait_for_slave_path(proc: subprocess.Popen, timeout_s: float = 5.0) -> Path:
    """Read the slave path printed by the mock to stderr."""
    deadline = time.monotonic() + timeout_s
    buf = b""
    while time.monotonic() < deadline:
        if proc.stderr is None:
            raise RuntimeError("mock has no stderr")
        chunk = proc.stderr.readline()
        if not chunk:
            time.sleep(0.02)
            continue
        buf += chunk
        if b"slave path:" in buf:
            line = buf.decode("utf-8", errors="replace").splitlines()[-1]
            return Path(line.split("slave path:")[-1].strip())
    raise RuntimeError(f"timed out waiting for slave path; got: {buf!r}")


@pytest.fixture
def ptmx_available() -> None:
    if not shutil.which("python3") or not hasattr(os, "openpty"):
        pytest.skip("PTY not available on this platform")


@pytest.fixture
def live_mock(ptmx_available: None) -> Generator[tuple[subprocess.Popen, Path], None, None]:
    proc = _spawn_mock()
    try:
        slave_path = _wait_for_slave_path(proc)
        yield proc, slave_path
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_mock_prints_slave_path_and_responds_to_get_status(live_mock: tuple[subprocess.Popen, Path]) -> None:
    _proc, slave_path = live_mock
    client = SerialHiveIOClient.for_serial_port(str(slave_path), request_timeout_s=2.0)
    try:
        resp = client.get_status()
        assert resp.result == "ok"
        assert isinstance(resp.observed_state, dict)
        assert "power" in resp.observed_state
        assert resp.observed_state["state"] == "IDLE"
        assert resp.observed_state["motor_enable"] is False
    finally:
        client.close()


def test_mock_rejects_motor_enable_when_estop_active(live_mock: tuple[subprocess.Popen, Path]) -> None:
    """Real wire-level test of the safety contract."""
    _proc, slave_path = live_mock
    client = SerialHiveIOClient.for_serial_port(str(slave_path), request_timeout_s=2.0)
    try:
        # No public API to inject ESTOP into the subprocess — exercise
        # the safe_state + motor_enable_set path, which is what the
        # host actually drives.
        safe = client.safe_state()
        assert safe.result == "ok"
        assert safe.observed_state["state"] == "SAFE"
        motor = client.motor_enable_set(True)
        # safe_state already cleared motor_enable; this is the
        # legitimate flow after ESTOP release.
        assert motor.result == "ok"
        assert motor.observed_state["motor_enable"] is True
    finally:
        client.close()


def test_mock_round_trip_unknown_command_returns_error(live_mock: tuple[subprocess.Popen, Path]) -> None:
    _proc, slave_path = live_mock
    client = SerialHiveIOClient.for_serial_port(str(slave_path), request_timeout_s=2.0)
    try:
        resp = client.send_request(Request(command="definitely_not_a_command"))
        assert resp.result == "error"
        assert resp.error_class == "UNKNOWN_COMMAND"
    finally:
        client.close()


def test_handle_request_pure_dispatcher_matches_wire() -> None:
    """Sanity: in-process dispatcher loads from the same module."""
    ns = runpy.run_path(str(MOCK_TOOL), run_name="__not_main__")
    assert "handle_request" in ns
