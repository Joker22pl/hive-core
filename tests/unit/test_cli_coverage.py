"""Coverage tests for the Hive CLI subcommands.

Many H0 subcommands are intentionally stubs (H1+/H3+ work). To keep
coverage above the 90% CI threshold, we exercise each subcommand once
to confirm it prints a "planned for Hn" marker without raising.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from hive.cli.main import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# ---------- device ----------


def test_device_scan_stub(runner: CliRunner) -> None:
    res = runner.invoke(app, ["device", "scan"])
    assert res.exit_code == 0
    assert "planned for H1" in res.stdout


def test_device_register_stub(runner: CliRunner) -> None:
    res = runner.invoke(app, ["device", "register", "my-dev"])
    assert res.exit_code == 0
    assert "my-dev" in res.stdout


def test_device_inspect_clean_registry(runner: CliRunner) -> None:
    """device inspect on a missing manifest shows a clear error."""
    res = runner.invoke(app, ["device", "inspect", "does-not-exist"])
    assert res.exit_code == 1
    assert "Manifest not found" in res.stdout


# ---------- artifact ----------


def test_artifact_build_stub(runner: CliRunner) -> None:
    res = runner.invoke(app, ["artifact", "build"])
    assert res.exit_code == 0
    assert "planned for H3" in res.stdout


def test_artifact_list_stub(runner: CliRunner) -> None:
    res = runner.invoke(app, ["artifact", "list"])
    assert res.exit_code == 0
    assert "planned for H3" in res.stdout


def test_artifact_inspect_stub(runner: CliRunner) -> None:
    res = runner.invoke(app, ["artifact", "inspect", "a1"])
    assert res.exit_code == 0
    assert "a1" in res.stdout


def test_artifact_mark_known_good_stub(runner: CliRunner) -> None:
    res = runner.invoke(app, ["artifact", "mark-known-good", "a1"])
    assert res.exit_code == 0
    assert "a1" in res.stdout


# ---------- io ----------


def test_io_safe_state(runner: CliRunner) -> None:
    res = runner.invoke(app, ["io", "safe-state"])
    assert res.exit_code == 0
    assert "safe_state" in res.stdout


def test_io_power_invalid_state(runner: CliRunner) -> None:
    res = runner.invoke(app, ["io", "power", "power_esp32_1", "bogus"])
    assert res.exit_code == 1
    assert "must be 'on' or 'off'" in res.stdout


def test_io_power_on_and_cycle(runner: CliRunner) -> None:
    runner.invoke(app, ["io", "power", "power_esp32_1", "on"])
    res = runner.invoke(app, ["io", "power-cycle", "power_esp32_1"])
    assert res.exit_code == 0


def test_io_reset(runner: CliRunner) -> None:
    res = runner.invoke(app, ["io", "reset", "reset_esp32_1"])
    assert res.exit_code == 0


# ---------- flash / verify / recover / evidence ----------


def test_flash_stub(runner: CliRunner) -> None:
    res = runner.invoke(app, ["flash", "device", "dev1", "--artifact", "a1"])
    assert res.exit_code == 0
    assert "planned for H3" in res.stdout


def test_verify_run_stub(runner: CliRunner) -> None:
    res = runner.invoke(app, ["verify", "run", "dev1", "--profile", "p1"])
    assert res.exit_code == 0
    assert "planned for H1" in res.stdout


def test_recover_stub(runner: CliRunner) -> None:
    res = runner.invoke(app, ["recover", "device", "dev1"])
    assert res.exit_code == 0
    assert "planned for H3" in res.stdout


def test_evidence_show_stub(runner: CliRunner) -> None:
    res = runner.invoke(app, ["evidence", "show", "eb-001"])
    assert res.exit_code == 0
    assert "planned for H3" in res.stdout


def test_evidence_export_stub(runner: CliRunner) -> None:
    res = runner.invoke(app, ["evidence", "export", "eb-001"])
    assert res.exit_code == 0
    assert "planned for H3" in res.stdout


# ---------- version ----------


def test_version_callback(runner: CliRunner) -> None:
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0
    assert "hive 0.1.0" in res.stdout
    assert "H0" in res.stdout


# ---------- system status ----------


def test_system_status(runner: CliRunner) -> None:
    res = runner.invoke(app, ["system", "status"])
    assert res.exit_code == 0
    assert "hive-core" in res.stdout
    assert "0.1.0" in res.stdout
    assert "H0" in res.stdout


# ---------- lock list (json store) ----------


def test_lock_list_empty_via_json_store(runner: CliRunner, tmp_path) -> None:
    """lock list with json-store returns empty JSON when no locks exist."""
    from json import loads

    store = tmp_path / "locks.json"
    res = runner.invoke(
        app,
        ["lock", "list", "--json", "--json-store", str(store)],
    )
    assert res.exit_code == 0
    data = loads(res.stdout.strip())
    assert data == {"locks": []}
