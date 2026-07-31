"""CLI tests for the device subsystem (MEDIUM-2 fix)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from hive.cli.main import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_device_list_missing_registry_dir_exits_nonzero(runner: CliRunner, tmp_path: Path) -> None:
    """`hive device list --registry <missing>` exits non-zero with a clear message."""
    missing = tmp_path / "no-such-dir"
    result = runner.invoke(app, ["device", "list", "--registry", str(missing)])
    assert result.exit_code == 1
    assert "Registry directory not found" in result.stdout
    assert str(missing) in result.stdout


def test_device_list_path_is_file_exits_nonzero(runner: CliRunner, tmp_path: Path) -> None:
    """`hive device list --registry <file>` exits non-zero."""
    f = tmp_path / "iamafile.yaml"
    f.write_text("not: a directory", encoding="utf-8")
    result = runner.invoke(app, ["device", "list", "--registry", str(f)])
    assert result.exit_code == 1
    assert "Registry directory not found" in result.stdout


def test_device_list_unreadable_registry_exits_nonzero(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """OSError during enumeration → RegistryAccessError → exit 1."""

    def _raise(*args: object, **kwargs: object) -> object:
        raise OSError("simulated permission denied")

    d = tmp_path / "dir"
    d.mkdir()
    monkeypatch.setattr("pathlib.Path.glob", _raise)
    result = runner.invoke(app, ["device", "list", "--registry", str(d)])
    assert result.exit_code == 1
    assert "Cannot access registry" in result.stdout


def test_device_list_clean_registry_works(runner: CliRunner) -> None:
    """The bundled registry/devices directory loads cleanly."""
    # Use the default registry path (relative to the project).
    result = runner.invoke(app, ["device", "list"])
    assert result.exit_code == 0
    # We expect at least one of the bundled devices.
    assert "Devices" in result.stdout


def test_device_list_invalid_manifest_clean_error(runner: CliRunner, tmp_path) -> None:
    """An invalid manifest shows a clean error (no traceback), exit 1."""
    (tmp_path / "bad.yaml").write_text(
        "device_id: ok\ntype: NOT_A_TYPE\nproject: x\nrole: y\n"
        "identity: {usb_vid: '303A', usb_pid: '1001'}\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["device", "list", "--registry", str(tmp_path)])
    assert result.exit_code == 1
    assert "Invalid manifest" in result.stdout
    assert "Traceback" not in result.stdout
    assert "Failed to load" in result.stdout
    assert "details" in result.stdout
