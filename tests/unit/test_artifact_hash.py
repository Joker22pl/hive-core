"""Tests for artifact hashing."""

from __future__ import annotations

from pathlib import Path

import pytest

from hive.artifacts.hash import sha256_bytes, sha256_file


def test_sha256_bytes_known_value() -> None:
    # SHA-256("") = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
    assert sha256_bytes(b"") == ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")


def test_sha256_bytes_hello() -> None:
    # SHA-256("hello") = 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824
    assert sha256_bytes(b"hello") == (
        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )


def test_sha256_file(tmp_path: Path) -> None:
    p = tmp_path / "data.bin"
    p.write_bytes(b"hello")
    assert sha256_file(p) == sha256_bytes(b"hello")


def test_sha256_file_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        sha256_file(tmp_path / "does-not-exist.bin")


def test_sha256_file_large_chunks(tmp_path: Path) -> None:
    p = tmp_path / "big.bin"
    data = b"x" * 1_000_000  # 1 MB
    p.write_bytes(data)
    assert sha256_file(p) == sha256_bytes(data)
