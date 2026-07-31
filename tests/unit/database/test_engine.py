"""Unit tests for hive.database.engine + migrations."""

from __future__ import annotations

from pathlib import Path

import pytest

from hive.database.engine import HiveDatabase


@pytest.fixture
def tmp_db(tmp_path: Path) -> HiveDatabase:
    """Fresh in-tmpdir HiveDatabase."""
    db_path = tmp_path / "test.db"
    return HiveDatabase.from_url(f"sqlite:///{db_path}")


@pytest.fixture
def mem_db() -> HiveDatabase:
    """In-memory HiveDatabase — fastest for tests."""
    return HiveDatabase.from_url("sqlite:///:memory:")


class TestHiveDatabase:
    def test_default_path_under_xdg(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        db = HiveDatabase.default()
        assert db.path is not None
        assert db.path.parent == tmp_path / "hive"
        assert str(db.path).endswith("hive.db")

    def test_default_honours_hive_db_url_env(self, monkeypatch):
        monkeypatch.setenv("HIVE_DB_URL", "sqlite:///:memory:")
        db = HiveDatabase.default()
        assert ":memory:" in db.url

    def test_in_memory_url(self):
        db = HiveDatabase.from_url("sqlite:///:memory:")
        assert db.path is None

    def test_file_url_extracts_path(self):
        # sqlite:////tmp/foo.db = absolute /tmp/foo.db (4 slashes for absolute path)
        db = HiveDatabase.from_url("sqlite:////tmp/foo.db")
        assert db.path == Path("/tmp/foo.db")

    def test_session_commits_on_success(self, mem_db):
        from sqlalchemy import text

        mem_db.upgrade()
        with mem_db.session() as s:
            s.execute(text("CREATE TABLE t (x INTEGER)"))
            s.execute(text("INSERT INTO t VALUES (1)"))
        # After context exit, data should persist
        with mem_db.session() as s:
            rows = s.execute(text("SELECT x FROM t")).all()
            assert rows == [(1,)]

    def test_session_rolls_back_on_error(self, mem_db):
        # SQLite does NOT support transactional DDL — CREATE TABLE is
        # auto-committed and cannot be rolled back. We test rollback
        # with DML instead.
        from sqlalchemy import text

        mem_db.upgrade()
        with mem_db.session() as s:
            s.execute(text("CREATE TABLE t (x INTEGER)"))
        with pytest.raises(RuntimeError):
            with mem_db.session() as s:
                s.execute(text("INSERT INTO t VALUES (1)"))
                s.execute(text("INSERT INTO t VALUES (2)"))
                raise RuntimeError("boom")
        # Rows from the failed transaction should NOT exist
        with mem_db.session() as s:
            rows = s.execute(text("SELECT x FROM t")).all()
            assert rows == []


class TestMigrations:
    def test_upgrade_creates_tables(self, mem_db):
        mem_db.upgrade()
        from sqlalchemy import text

        with mem_db.session() as s:
            tables = (
                s.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))
                .scalars()
                .all()
            )
            # devices + locks + alembic_version
            assert "devices" in tables
            assert "locks" in tables
            assert "alembic_version" in tables

    def test_upgrade_is_idempotent(self, mem_db):
        mem_db.upgrade()
        mem_db.upgrade()
        mem_db.upgrade()
        from sqlalchemy import text

        with mem_db.session() as s:
            version = s.execute(text("SELECT version_num FROM alembic_version")).scalar()
            assert version == "0001"

    def test_devices_table_has_required_columns(self, mem_db):
        mem_db.upgrade()
        from sqlalchemy import text

        with mem_db.session() as s:
            cols = s.execute(text("PRAGMA table_info(devices)")).all()
            col_names = {row[1] for row in cols}
        assert "fingerprint" in col_names
        assert "device_id" in col_names
        assert "usb_vid" in col_names
        assert "last_seen_at" in col_names

    def test_locks_table_has_required_columns(self, mem_db):
        mem_db.upgrade()
        from sqlalchemy import text

        with mem_db.session() as s:
            cols = s.execute(text("PRAGMA table_info(locks)")).all()
            col_names = {row[1] for row in cols}
        assert "device_id" in col_names
        assert "session_id" in col_names
        assert "expires_at" in col_names
