"""Database initialization and connection management for PoC Agent4.

Uses SQLite with WAL journal mode for concurrent read safety.
WAL mode must be configured from the start to avoid costly migrations later.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_DB_PATH = Path('workspace') / 'agent_sandbox' / 'poc_agent4.db'

_CREATE_SNAPSHOTS_TABLE = """
CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id  TEXT PRIMARY KEY,
    task_id      TEXT NOT NULL,
    timestamp    TEXT NOT NULL,
    git_commit   TEXT NOT NULL,
    state_json   TEXT NOT NULL,
    trigger      TEXT NOT NULL
);
"""


@dataclass(slots=True)
class DatabaseConfig:
    db_path: Path = field(default_factory=lambda: _DEFAULT_DB_PATH)
    wal_mode: bool = True


def init_db(cfg: DatabaseConfig) -> None:
    """Create the database file, enable WAL mode, and apply the schema.

    Idempotent: safe to call multiple times.
    """
    cfg.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(cfg.db_path))
    try:
        if cfg.wal_mode:
            conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute(_CREATE_SNAPSHOTS_TABLE)
        conn.commit()
    finally:
        conn.close()


def create_db_connection(cfg: DatabaseConfig) -> sqlite3.Connection:
    """Open and return a connection to an already-initialised database.

    Raises:
        FileNotFoundError: if the database file does not exist yet.
            Call `init_db` first.
    """
    if not cfg.db_path.exists():
        raise FileNotFoundError(
            f'Database not found at {cfg.db_path}. Call init_db() first.'
        )
    conn = sqlite3.connect(str(cfg.db_path))
    conn.row_factory = sqlite3.Row
    return conn
