"""H1 database migrations — hand-written SQL applied via SQLAlchemy.

For H1, we use a simple "alembic_version" table to track the current
schema revision. Migrations are applied in order from a list of
(version, [sql statements]) tuples.

This avoids the complexity of the full alembic CLI for an H1 schema
that's small enough to keep as a single migration. When H1.1+ needs
real schema evolution (columns, indices, ...), we can migrate to the
full alembic setup with autogenerate.

Schema versions:

    0001 — initial schema (devices, locks, alembic_version)
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

CURRENT_REVISION = "0001"

INITIAL_STATEMENTS = [
    # 1. alembic_version table (track schema revision)
    """
    CREATE TABLE IF NOT EXISTS alembic_version (
        version_num VARCHAR(32) NOT NULL PRIMARY KEY
    )
    """,
    # 2. devices table — see hive.database.models.DeviceRecord
    """
    CREATE TABLE IF NOT EXISTS devices (
        fingerprint     VARCHAR(64)  NOT NULL PRIMARY KEY,
        device_id       VARCHAR(128),
        usb_vid         VARCHAR(4),
        usb_pid         VARCHAR(4),
        serial_number   VARCHAR(128),
        serial_port     VARCHAR(256),
        serial_by_id    VARCHAR(512),
        ssh_host        VARCHAR(256),
        ssh_port        INTEGER,
        ssh_user        VARCHAR(64),
        description     VARCHAR(512),
        manufacturer    VARCHAR(128),
        product         VARCHAR(128),
        discovered_at   VARCHAR(32) NOT NULL,
        last_seen_at    VARCHAR(32) NOT NULL,
        manifest_path   VARCHAR(512),
        notes           TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_devices_device_id ON devices (device_id)",
    "CREATE INDEX IF NOT EXISTS ix_devices_last_seen_at ON devices (last_seen_at)",
    "CREATE INDEX IF NOT EXISTS ix_devices_usb ON devices (usb_vid, usb_pid, serial_number)",
    "CREATE INDEX IF NOT EXISTS ix_devices_ssh ON devices (ssh_host, ssh_user)",
    # 3. locks table
    """
    CREATE TABLE IF NOT EXISTS locks (
        device_id       VARCHAR(128) NOT NULL PRIMARY KEY,
        owner           VARCHAR(128) NOT NULL,
        session_id      VARCHAR(64)  NOT NULL,
        operation       VARCHAR(128) NOT NULL,
        acquired_at     VARCHAR(32)  NOT NULL,
        expires_at      VARCHAR(32)  NOT NULL,
        metadata_json   TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_locks_expires_at ON locks (expires_at)",
]

# Future migrations go here:
#   ("0002", ["ALTER TABLE devices ADD COLUMN foo VARCHAR(64)"]),
MIGRATIONS: list[tuple[str, list[str]]] = [
    ("0001", INITIAL_STATEMENTS),
]


def upgrade_to_head(engine: Engine) -> None:
    """Apply all pending migrations in order.

    Idempotent: re-running on an already-current DB is a no-op.
    """
    with engine.begin() as conn:
        # Ensure alembic_version table exists (for fresh DBs)
        conn.execute(text(INITIAL_STATEMENTS[0]))

        current_row = conn.execute(text("SELECT version_num FROM alembic_version")).first()
        current = current_row[0] if current_row else None

        for version, statements in MIGRATIONS:
            if current is not None and version <= current:
                continue  # already applied
            for stmt in statements:
                conn.execute(text(stmt))
            # Set version (replace if exists)
            if current is None:
                conn.execute(
                    text("INSERT INTO alembic_version (version_num) VALUES (:v)"),
                    {"v": version},
                )
            else:
                conn.execute(
                    text("UPDATE alembic_version SET version_num = :v"),
                    {"v": version},
                )
            current = version