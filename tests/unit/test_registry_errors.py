"""Tests for registry loader failure modes (MEDIUM-2 fix)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hive.common.errors import RegistryNotFoundError
from hive.registry import load_all_device_manifests


def test_load_all_manifests_from_missing_directory(tmp_path: Path) -> None:
    """Missing directory raises RegistryNotFoundError, not silent empty list."""
    missing = tmp_path / "nope"
    with pytest.raises(RegistryNotFoundError) as exc_info:
        load_all_device_manifests(missing)
    assert (
        "does not exist" in exc_info.value.message
        or "not a directory" in exc_info.value.message
        or str(missing) in exc_info.value.message
    )
    assert exc_info.value.details["path"] == str(missing)


def test_load_all_manifests_from_path_is_file(tmp_path: Path) -> None:
    """If path is a file, not a directory, raise RegistryNotFoundError."""
    f = tmp_path / "iamafile.yaml"
    f.write_text("not: a directory", encoding="utf-8")
    with pytest.raises(RegistryNotFoundError) as exc_info:
        load_all_device_manifests(f)
    assert "not a directory" in exc_info.value.message


def test_load_all_manifests_unreadable_via_patch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """OS-level error during enumeration raises RegistryAccessError.

    We monkeypatch ``Path.glob`` to raise ``OSError``; this is portable
    across privilege levels (no chmod tricks needed) and exercises
    the same code path that PermissionError would.
    """
    d = tmp_path / "subdir"
    d.mkdir()

    def _raise(*args: object, **kwargs: object) -> object:
        raise OSError("simulated permission denied")

    monkeypatch.setattr("pathlib.Path.glob", _raise)
    from hive.common.errors import RegistryAccessError as _Rae

    with pytest.raises(_Rae) as exc_info:
        load_all_device_manifests(d)
    # The underlying error message is in details (not in the public message).
    assert exc_info.value.details.get("error") == "simulated permission denied"


def test_load_all_manifests_from_empty_directory(tmp_path: Path) -> None:
    """Empty existing directory returns empty list (not an error)."""
    d = tmp_path / "empty"
    d.mkdir()
    manifests = load_all_device_manifests(d)
    assert manifests == []


def test_load_all_manifests_returns_list(tmp_path: Path) -> None:
    """Return type is a list (caller can len() and re-iterate)."""
    d = tmp_path / "with-files"
    d.mkdir()
    (d / "a.yaml").write_text(
        "device_id: a\ntype: microcontroller\nproject: x\nrole: y\n"
        "identity: {usb_vid: '303A', usb_pid: '1001'}\n",
        encoding="utf-8",
    )
    (d / "b.yaml").write_text(
        "device_id: b\ntype: microcontroller\nproject: x\nrole: y\n"
        "identity: {usb_vid: '303A', usb_pid: '1001'}\n",
        encoding="utf-8",
    )
    result = load_all_device_manifests(d)
    assert isinstance(result, list)
    assert len(result) == 2
    # Iterate twice — list supports that.
    assert len(list(result)) == 2


def test_load_all_manifests_invalid_manifest_raises(tmp_path: Path) -> None:
    """An invalid manifest raises SchemaValidationError, not silently skipped."""
    from hive.common.errors import SchemaValidationError

    d = tmp_path / "mixed"
    d.mkdir()
    (d / "ok.yaml").write_text(
        "device_id: ok\ntype: microcontroller\nproject: x\nrole: y\n"
        "identity: {usb_vid: '303A', usb_pid: '1001'}\n",
        encoding="utf-8",
    )
    (d / "bad.yaml").write_text(
        "device_id: bad-id-WITH-UNDERSCORE\n"  # OK id
        "type: NOT_A_REAL_TYPE\n"  # invalid type
        "project: x\nrole: y\n"
        "identity: {usb_vid: '303A', usb_pid: '1001'}\n",
        encoding="utf-8",
    )
    with pytest.raises(SchemaValidationError):
        load_all_device_manifests(d)
