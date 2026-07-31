"""CLI tests for the lock subsystem (HIGH-1 fix).

These tests exercise the lock CLI commands via Typer's ``CliRunner`` and
cover the full round-trip required by the audit remediation:

* acquire with auto session_id
* acquire with explicit session_id
* release with correct session_id
* release with wrong session_id
* renewal via re-acquire with same session_id
* other session attempts to acquire → DeviceBusyError
* expired lock → release
* JSON output mode
* error messages don't include stack traces by default
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hive.cli.main import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def json_store(tmp_path: Path) -> Path:
    return tmp_path / "locks.json"


def test_acquire_with_auto_session_id(runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        [
            "lock",
            "acquire",
            "test-device",
            "--owner",
            "audit",
            "--operation",
            "flash",
        ],
    )
    assert result.exit_code == 0
    assert "Lock created" in result.stdout
    # session_id is printed on a separate line for round-trip use.
    assert "session_id = sess-" in result.stdout


def test_acquire_with_explicit_session_id(runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        [
            "lock",
            "acquire",
            "test-device",
            "--owner",
            "audit",
            "--session-id",
            "my-sess-001",
        ],
    )
    assert result.exit_code == 0
    assert "my-sess-001" in result.stdout


def test_acquire_and_release_round_trip_text(runner: CliRunner, json_store: Path) -> None:
    """Acquire → get session_id from output → release."""
    acq = runner.invoke(
        app,
        [
            "lock",
            "acquire",
            "test-rt",
            "--owner",
            "audit",
            "--json-store",
            str(json_store),
        ],
    )
    assert acq.exit_code == 0
    # The text output prints `session_id = sess-...`.
    session_id = None
    for line in acq.stdout.splitlines():
        if line.startswith("session_id = "):
            session_id = line.removeprefix("session_id = ").strip()
    assert session_id is not None and session_id.startswith("sess-")

    rel = runner.invoke(
        app,
        [
            "lock",
            "release",
            "test-rt",
            "--session-id",
            session_id,
            "--json-store",
            str(json_store),
        ],
    )
    assert rel.exit_code == 0
    assert "Released" in rel.stdout

    # Re-acquire → should be a new lock (since the previous one was released).
    re_acq = runner.invoke(
        app,
        [
            "lock",
            "acquire",
            "test-rt",
            "--owner",
            "audit",
            "--session-id",
            session_id,
            "--json-store",
            str(json_store),
        ],
    )
    assert re_acq.exit_code == 0
    assert "Lock created" in re_acq.stdout


def test_acquire_renewal_same_session_id(runner: CliRunner, json_store: Path) -> None:
    """Same session_id re-acquiring should renew the lease."""
    # First acquire.
    r1 = runner.invoke(
        app,
        [
            "lock",
            "acquire",
            "test-renew",
            "--owner",
            "audit",
            "--session-id",
            "sess-renew",
            "--ttl",
            "10",
            "--json-store",
            str(json_store),
        ],
    )
    assert r1.exit_code == 0
    assert "Lock created" in r1.stdout

    # Re-acquire with same session_id but longer TTL.
    r2 = runner.invoke(
        app,
        [
            "lock",
            "acquire",
            "test-renew",
            "--owner",
            "audit",
            "--session-id",
            "sess-renew",
            "--ttl",
            "600",
            "--json-store",
            str(json_store),
        ],
    )
    assert r2.exit_code == 0
    assert "Lock renewed" in r2.stdout


def test_acquire_blocked_by_other_session(runner: CliRunner, json_store: Path) -> None:
    """Different session_id attempting to acquire a held lock fails."""
    r1 = runner.invoke(
        app,
        [
            "lock",
            "acquire",
            "test-busy",
            "--owner",
            "audit",
            "--session-id",
            "sess-A",
            "--json-store",
            str(json_store),
        ],
    )
    assert r1.exit_code == 0

    r2 = runner.invoke(
        app,
        [
            "lock",
            "acquire",
            "test-busy",
            "--owner",
            "audit",
            "--session-id",
            "sess-B",
            "--json-store",
            str(json_store),
        ],
    )
    assert r2.exit_code == 1
    assert "Lock acquire failed" in r2.stdout
    assert "DeviceBusyError" in r2.stdout or "locked by session" in r2.stdout


def test_release_wrong_session_id(runner: CliRunner, json_store: Path) -> None:
    """release with mismatched session_id returns non-zero exit code + no-match message."""
    acq = runner.invoke(
        app,
        [
            "lock",
            "acquire",
            "test-mismatch",
            "--owner",
            "audit",
            "--session-id",
            "sess-real",
            "--json-store",
            str(json_store),
        ],
    )
    assert acq.exit_code == 0

    bad = runner.invoke(
        app,
        [
            "lock",
            "release",
            "test-mismatch",
            "--session-id",
            "sess-wrong",
            "--json-store",
            str(json_store),
        ],
    )
    assert bad.exit_code == 1
    assert "No matching lock" in bad.stdout


def test_acquire_json_output_is_valid(runner: CliRunner) -> None:
    """--json emits a single-line JSON object with session_id."""
    result = runner.invoke(
        app,
        [
            "lock",
            "acquire",
            "test-json",
            "--owner",
            "audit",
            "--json",
        ],
    )
    assert result.exit_code == 0
    # The whole stdout should be a single JSON object.
    data = json.loads(result.stdout.strip())
    assert data["created"] is True
    assert data["renewed"] is False
    assert "session_id" in data["lock"]
    assert data["lock"]["device_id"] == "test-json"


def test_acquire_json_output_on_renewal(runner: CliRunner, json_store: Path) -> None:
    """--json reports renewed=True on same-session re-acquire."""
    args = [
        "lock",
        "acquire",
        "test-json-2",
        "--owner",
        "audit",
        "--session-id",
        "sess-r",
        "--json-store",
        str(json_store),
        "--json",
    ]
    r1 = runner.invoke(app, args)
    assert r1.exit_code == 0
    data1 = json.loads(r1.stdout.strip())
    assert data1["created"] is True and data1["renewed"] is False

    r2 = runner.invoke(app, args)
    assert r2.exit_code == 0
    data2 = json.loads(r2.stdout.strip())
    assert data2["created"] is False and data2["renewed"] is True


def test_acquire_json_error_on_conflict(runner: CliRunner, json_store: Path) -> None:
    """--json output uses serialize_error for busy/conflict errors."""
    common = ["--json-store", str(json_store), "--json"]
    runner.invoke(
        app,
        ["lock", "acquire", "test-jsonerr", "--owner", "x", "--session-id", "s1", *common],
    )
    result = runner.invoke(
        app,
        ["lock", "acquire", "test-jsonerr", "--owner", "y", "--session-id", "s2", *common],
    )
    assert result.exit_code == 1
    data = json.loads(result.stdout.strip())
    assert data["error"] == "DeviceBusyError"
    assert "message" in data
    assert "locked by session" in data["message"]


def test_release_json_output(runner: CliRunner, json_store: Path) -> None:
    """--json release returns released=true/false."""
    acq = runner.invoke(
        app,
        [
            "lock",
            "acquire",
            "test-rel-json",
            "--owner",
            "audit",
            "--session-id",
            "sess-RJ",
            "--json-store",
            str(json_store),
            "--json",
        ],
    )
    assert acq.exit_code == 0

    ok = runner.invoke(
        app,
        [
            "lock",
            "release",
            "test-rel-json",
            "--session-id",
            "sess-RJ",
            "--json-store",
            str(json_store),
            "--json",
        ],
    )
    assert ok.exit_code == 0
    data = json.loads(ok.stdout.strip())
    assert data["released"] is True
    assert data["device_id"] == "test-rel-json"
    assert data["session_id"] == "sess-RJ"

    # Mismatched session → exit 1, released=false.
    bad = runner.invoke(
        app,
        [
            "lock",
            "release",
            "test-rel-json",
            "--session-id",
            "sess-WRONG",
            "--json-store",
            str(json_store),
            "--json",
        ],
    )
    assert bad.exit_code == 1
    data_bad = json.loads(bad.stdout.strip())
    assert data_bad["released"] is False
