"""Тесты версионированных миграций схемы БД (FUND-01)."""
import sqlite3
import time
from pathlib import Path

import pytest

from modules.database import Database


@pytest.fixture
def tmp_db(tmp_path) -> Path:
    """Путь к временной БД (файл не создан)."""
    return tmp_path / "test.db"


def test_fresh_db(tmp_db):
    """Создание на пустом месте — нет ошибок, schema_migrations существует."""
    db = Database(tmp_db)
    db.close()
    conn = sqlite3.connect(str(tmp_db))
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    )
    assert cursor.fetchone() is not None, "Таблица schema_migrations не создана"
    conn.close()


def test_v04_upgrade_preserves_rows(tmp_db):
    """Апгрейд с v0.4-базы: существующие строки сохраняются, новые столбцы добавлены."""
    # Создать v0.4-like базу: без schema_migrations, без review_status/lawyer_comment
    conn = sqlite3.connect(str(tmp_db))
    conn.execute("""
        CREATE TABLE contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_path TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_hash TEXT UNIQUE,
            status TEXT DEFAULT 'pending'
        )
    """)
    conn.execute(
        "INSERT INTO contracts (original_path, filename, file_hash, status) "
        "VALUES ('test.pdf', 'test.pdf', 'abc123', 'done')"
    )
    conn.commit()
    conn.close()

    # Открыть через Database — должна применить миграцию
    db = Database(tmp_db)
    db.close()

    conn = sqlite3.connect(str(tmp_db))
    row = conn.execute("SELECT * FROM contracts WHERE file_hash='abc123'").fetchone()
    assert row is not None, "Строка потеряна при миграции"

    # Новые столбцы добавлены
    cols = {d[1] for d in conn.execute("PRAGMA table_info(contracts)").fetchall()}
    assert "review_status" in cols, "review_status не добавлен"
    assert "lawyer_comment" in cols, "lawyer_comment не добавлен"
    conn.close()


def test_backup_created(tmp_db):
    """На непустой БД перед миграцией создаётся backup-файл."""
    # Создать непустую БД (без schema_migrations — триггер для backup)
    conn = sqlite3.connect(str(tmp_db))
    conn.execute("""
        CREATE TABLE contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_path TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_hash TEXT UNIQUE,
            status TEXT DEFAULT 'pending'
        )
    """)
    conn.execute(
        "INSERT INTO contracts (original_path, filename, file_hash, status) "
        "VALUES ('x.pdf', 'x.pdf', 'deadbeef', 'done')"
    )
    conn.commit()
    conn.close()

    db = Database(tmp_db)
    db.close()

    backups = list(tmp_db.parent.glob(f"{tmp_db.stem}_backup_*.sqlite"))
    assert len(backups) >= 1, f"Backup не создан. Файлы в папке: {list(tmp_db.parent.iterdir())}"


def test_idempotent(tmp_db):
    """Открыть БД дважды — в schema_migrations ровно одна запись version=1."""
    db = Database(tmp_db)
    db.close()
    db2 = Database(tmp_db)
    db2.close()

    conn = sqlite3.connect(str(tmp_db))
    count = conn.execute(
        "SELECT COUNT(*) FROM schema_migrations WHERE version=1"
    ).fetchone()[0]
    conn.close()
    assert count == 1, f"Ожидалась 1 запись v1 в schema_migrations, найдено {count}"
