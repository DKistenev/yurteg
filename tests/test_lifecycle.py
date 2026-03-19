"""Тесты жизненного цикла документа (Phase 2).

LIFE-01: SQL CASE возвращает expired/expiring/active/unknown по date_end
LIFE-02: manual_status перекрывает auto_status
LIFE-05: Панель внимания возвращает документы в пределах warning_days
LIFE-06: Порог предупреждения конфигурируется (30/60/90)

Wave 0: тест-скелеты созданы до реализации (RED стадия).
Assertions дополняются после 02-01 (lifecycle_service).
"""
import pytest
import sqlite3
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_db(tmp_path):
    """Создаёт временную БД с миграциями для тестов."""
    try:
        from modules.database import Database
        db = Database(tmp_path / "test.db", tmp_path)
        yield db
        db.close()
    except ImportError:
        pytest.skip("modules.database недоступен — запустите после 02-01")


@pytest.mark.xfail(reason="lifecycle_service создаётся в 02-01", strict=False)
def test_auto_status_computation(temp_db):
    """LIFE-01: SQL CASE корректно вычисляет статус по date_end."""
    from services.lifecycle_service import get_computed_status_sql

    db = temp_db
    conn = db._conn

    # Истёкший договор
    conn.execute(
        "INSERT INTO contracts (filename, original_path, status, date_end) "
        "VALUES ('expired.pdf', '/tmp/e.pdf', 'done', date('now', '-10 days'))"
    )
    # Активный договор
    conn.execute(
        "INSERT INTO contracts (filename, original_path, status, date_end) "
        "VALUES ('active.pdf', '/tmp/a.pdf', 'done', date('now', '+60 days'))"
    )
    # Истекающий договор
    conn.execute(
        "INSERT INTO contracts (filename, original_path, status, date_end) "
        "VALUES ('expiring.pdf', '/tmp/x.pdf', 'done', date('now', '+15 days'))"
    )
    # Без даты
    conn.execute(
        "INSERT INTO contracts (filename, original_path, status) "
        "VALUES ('nodate.pdf', '/tmp/n.pdf', 'done')"
    )
    conn.commit()

    sql = f"SELECT filename, {get_computed_status_sql(30)} AS cs FROM contracts WHERE status='done'"
    rows = {r[0]: r[1] for r in conn.execute(sql, {"warning_days": 30}).fetchall()}

    assert rows["expired.pdf"] == "expired", f"Ожидается expired, получен {rows['expired.pdf']}"
    assert rows["active.pdf"] == "active", f"Ожидается active, получен {rows['active.pdf']}"
    assert rows["expiring.pdf"] == "expiring", f"Ожидается expiring, получен {rows['expiring.pdf']}"
    assert rows["nodate.pdf"] == "unknown", f"Ожидается unknown, получен {rows.get('nodate.pdf')}"


@pytest.mark.xfail(reason="lifecycle_service создаётся в 02-01", strict=False)
def test_manual_status_override(temp_db):
    """LIFE-02: manual_status имеет приоритет над автоматическим статусом."""
    from services.lifecycle_service import get_computed_status_sql, set_manual_status

    db = temp_db
    conn = db._conn

    conn.execute(
        "INSERT INTO contracts (filename, original_path, status, date_end) "
        "VALUES ('test.pdf', '/tmp/t.pdf', 'done', date('now', '-5 days'))"
    )
    conn.commit()
    cid = conn.execute("SELECT id FROM contracts WHERE filename='test.pdf'").fetchone()[0]

    # Без ручного статуса — должен быть expired
    sql = f"SELECT {get_computed_status_sql(30)} AS cs FROM contracts WHERE id=?"
    row = conn.execute(sql, {"warning_days": 30}, (cid,)).fetchone()
    # Примечание: sqlite3 не поддерживает смешанные positional+named params
    # Правильный вызов:
    row = conn.execute(
        f"SELECT {get_computed_status_sql(30)} AS cs FROM contracts WHERE id=:id",
        {"warning_days": 30, "id": cid}
    ).fetchone()
    assert row[0] == "expired"

    # Устанавливаем ручной статус
    set_manual_status(db, cid, "extended")

    row = conn.execute(
        f"SELECT {get_computed_status_sql(30)} AS cs FROM contracts WHERE id=:id",
        {"warning_days": 30, "id": cid}
    ).fetchone()
    assert row[0] == "extended", f"manual_status должен перекрыть auto, получен {row[0]}"


@pytest.mark.xfail(reason="lifecycle_service создаётся в 02-01", strict=False)
def test_attention_panel(temp_db):
    """LIFE-05: Панель внимания возвращает только документы в пределах warning_days."""
    from services.lifecycle_service import get_attention_required

    db = temp_db
    conn = db._conn

    # Попадает в панель (истёк)
    conn.execute(
        "INSERT INTO contracts (filename, original_path, status, date_end) "
        "VALUES ('in_panel.pdf', '/tmp/i.pdf', 'done', date('now', '-5 days'))"
    )
    # НЕ попадает (далёкое будущее)
    conn.execute(
        "INSERT INTO contracts (filename, original_path, status, date_end) "
        "VALUES ('out_panel.pdf', '/tmp/o.pdf', 'done', date('now', '+120 days'))"
    )
    conn.commit()

    alerts = get_attention_required(db, warning_days=30)
    filenames = [a.filename for a in alerts]
    assert "in_panel.pdf" in filenames, "Истёкший документ должен быть в панели"
    assert "out_panel.pdf" not in filenames, "Далёкий документ не должен быть в панели"


@pytest.mark.xfail(reason="lifecycle_service создаётся в 02-01", strict=False)
def test_configurable_threshold(temp_db):
    """LIFE-06: Порог warning_days влияет на состав панели внимания."""
    from services.lifecycle_service import get_attention_required

    db = temp_db
    conn = db._conn

    conn.execute(
        "INSERT INTO contracts (filename, original_path, status, date_end) "
        "VALUES ('borderline.pdf', '/tmp/b.pdf', 'done', date('now', '+45 days'))"
    )
    conn.commit()

    # При пороге 30 — не попадает
    alerts_30 = get_attention_required(db, warning_days=30)
    assert not any(a.filename == "borderline.pdf" for a in alerts_30)

    # При пороге 60 — попадает
    alerts_60 = get_attention_required(db, warning_days=60)
    assert any(a.filename == "borderline.pdf" for a in alerts_60)
