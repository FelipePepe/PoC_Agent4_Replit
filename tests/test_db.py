"""Tests for core/db.py — SQLite database initialization with WAL mode."""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from core.db import DatabaseConfig, create_db_connection, init_db


class TestDatabaseConfig:
    def test_default_path_is_under_workspace(self):
        cfg = DatabaseConfig()
        assert 'workspace' in str(cfg.db_path)

    def test_custom_path_accepted(self):
        cfg = DatabaseConfig(db_path=Path('/tmp/test.db'))
        assert cfg.db_path == Path('/tmp/test.db')

    def test_wal_mode_enabled_by_default(self):
        cfg = DatabaseConfig()
        assert cfg.wal_mode is True


class TestInitDb:
    def test_creates_db_file(self, tmp_path):
        db_path = tmp_path / 'test.db'
        cfg = DatabaseConfig(db_path=db_path)
        init_db(cfg)
        assert db_path.exists()

    def test_wal_journal_mode_is_set(self, tmp_path):
        db_path = tmp_path / 'test.db'
        cfg = DatabaseConfig(db_path=db_path)
        init_db(cfg)
        conn = sqlite3.connect(str(db_path))
        row = conn.execute('PRAGMA journal_mode;').fetchone()
        conn.close()
        assert row[0] == 'wal'

    def test_wal_mode_disabled_skips_pragma(self, tmp_path):
        db_path = tmp_path / 'test.db'
        cfg = DatabaseConfig(db_path=db_path, wal_mode=False)
        init_db(cfg)
        conn = sqlite3.connect(str(db_path))
        row = conn.execute('PRAGMA journal_mode;').fetchone()
        conn.close()
        assert row[0] == 'delete'  # default SQLite journal mode

    def test_snapshots_table_created(self, tmp_path):
        db_path = tmp_path / 'test.db'
        cfg = DatabaseConfig(db_path=db_path)
        init_db(cfg)
        conn = sqlite3.connect(str(db_path))
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            ).fetchall()
        }
        conn.close()
        assert 'snapshots' in tables

    def test_idempotent_double_init(self, tmp_path):
        db_path = tmp_path / 'test.db'
        cfg = DatabaseConfig(db_path=db_path)
        init_db(cfg)
        init_db(cfg)  # must not raise
        assert db_path.exists()


class TestCreateDbConnection:
    def test_returns_connection(self, tmp_path):
        db_path = tmp_path / 'test.db'
        cfg = DatabaseConfig(db_path=db_path)
        init_db(cfg)
        conn = create_db_connection(cfg)
        assert conn is not None
        conn.close()

    def test_connection_has_row_factory(self, tmp_path):
        db_path = tmp_path / 'test.db'
        cfg = DatabaseConfig(db_path=db_path)
        init_db(cfg)
        conn = create_db_connection(cfg)
        assert conn.row_factory is sqlite3.Row
        conn.close()

    def test_raises_if_db_not_initialized(self, tmp_path):
        db_path = tmp_path / 'nonexistent.db'
        cfg = DatabaseConfig(db_path=db_path)
        with pytest.raises(FileNotFoundError):
            create_db_connection(cfg)
