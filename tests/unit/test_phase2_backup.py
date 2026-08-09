from __future__ import annotations

import sqlite3
from contextlib import closing

import pytest

from scripts.database_backup import backup, restore


def test_database_backup_and_guarded_restore(tmp_path):
    source = tmp_path / "source.sqlite3"
    backup_file = tmp_path / "backup.sqlite3"
    restored = tmp_path / "restored.sqlite3"
    with closing(sqlite3.connect(source)) as conn:
        conn.execute("CREATE TABLE sample (value TEXT NOT NULL)")
        conn.execute("INSERT INTO sample(value) VALUES ('phase2')")
        conn.commit()
    backup(source, backup_file)
    with pytest.raises(SystemExit, match="confirm-overwrite"):
        restore(backup_file, restored, confirm=False)
    restore(backup_file, restored, confirm=True)
    with closing(sqlite3.connect(restored)) as conn:
        assert conn.execute("SELECT value FROM sample").fetchone()[0] == "phase2"
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
