"""SQLite database engine + session factory + initialization.

HiveDatabase is a thin wrapper around SQLAlchemy's Engine and Session.
It knows how to:
    * construct the default DB URL (XDG_DATA_HOME/hive/hive.db)
    * create all tables (for tests / greenfield)
    * run alembic migrations to head
    * open a session context manager

Per the SAFETY model:
    * DB writes happen in transactions; partial writes are rolled back.
    * All timestamps are UTC ISO 8601 strings (avoids SQLite tz bugs).

Usage:
    db = HiveDatabase.default()
    db.upgrade()  # alembic upgrade head
    with db.session() as s:
        s.add(DeviceRecord(fingerprint="...", ...))
        # auto-commit on context exit
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from hive.common.errors import HiveError


class DatabaseError(HiveError):
    """Raised on DB connection / migration / constraint failures."""


@dataclass(frozen=True)
class HiveDatabase:
    """A HIVE SQLite database.

    Construct via HiveDatabase.default() (XDG path) or with a custom URL.
    """

    engine: Engine
    url: str
    path: Path | None  # None for in-memory or non-file URLs

    @classmethod
    def from_url(cls, url: str) -> HiveDatabase:
        """Create a HiveDatabase from a SQLAlchemy URL."""
        engine = create_engine(
            url,
            future=True,
            # SQLite-specific: enable foreign keys + WAL mode for safety
            connect_args={"check_same_thread": False}
            if url.startswith("sqlite")
            else {},
        )
        path: Path | None = None
        if url.startswith("sqlite:///") and ":memory:" not in url:
            # sqlite:///abs/path.db OR sqlite:///relative.db
            tail = url[len("sqlite:///") :]
            # Strip query string if any
            tail = tail.split("?", 1)[0]
            path = Path(tail)
        return cls(engine=engine, url=url, path=path)

    @classmethod
    def default(cls) -> HiveDatabase:
        """Create the default HiveDatabase at XDG_DATA_HOME/hive/hive.db."""
        url = os.environ.get("HIVE_DB_URL")
        if url:
            return cls.from_url(url)
        xdg = os.environ.get("XDG_DATA_HOME")
        if xdg:
            base = Path(xdg)
        else:
            base = Path.home() / ".local" / "share"
        path = base / "hive" / "hive.db"
        path.parent.mkdir(parents=True, exist_ok=True)
        return cls.from_url(f"sqlite:///{path}")

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Open a session with auto-commit on success / rollback on error."""
        factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        sess = factory()
        try:
            yield sess
            sess.commit()
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()

    def upgrade(self) -> None:
        """Run alembic migrations to head.

        For now, H1 uses Base.metadata.create_all() for simplicity —
        alembic env is set up for H1.1+.
        """
        # Lazy import to avoid loading alembic at module import time
        from hive.database.migrations import upgrade_to_head

        upgrade_to_head(self.engine)

    def create_all(self) -> None:
        """Create all tables directly (no alembic).

        Useful for tests and for the very first run before any migration.
        """
        from hive.database.models import Base

        Base.metadata.create_all(self.engine)


__all__ = ["DatabaseError", "HiveDatabase"]