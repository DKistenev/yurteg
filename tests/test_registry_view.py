"""Тесты data layer реестра: _fetch_rows, _fuzzy_filter.

Phase 08, Plan 01 — TDD RED phase.
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from modules.database import Database


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path):
    """Создаёт временную SQLite БД с тестовыми договорами."""
    db_path = tmp_path / "test.db"
    db = Database(db_path)

    # Вставляем тестовые договоры
    rows = [
        # 2 active (date_end в будущем, validation_score=0.9)
        {
            "filename": "active1.pdf",
            "file_hash": "hash_active1",
            "status": "done",
            "contract_type": "Договор аренды",
            "counterparty": "ООО Ромашка",
            "subject": "Аренда офисного помещения",
            "date_end": "2030-12-31",
            "amount": "120000",
            "validation_score": 0.9,
            "validation_warnings": "[]",
            "processed_at": "2026-03-20 10:00:00",
        },
        {
            "filename": "active2.pdf",
            "file_hash": "hash_active2",
            "status": "done",
            "contract_type": "Договор поставки",
            "counterparty": "ИП Иванов",
            "subject": "Поставка оборудования",
            "date_end": "2028-06-30",
            "amount": "500000",
            "validation_score": 0.9,
            "validation_warnings": "[]",
            "processed_at": "2026-03-21 11:00:00",
        },
        # 1 expiring (date_end в течение 30 дней)
        {
            "filename": "expiring1.pdf",
            "file_hash": "hash_expiring1",
            "status": "done",
            "contract_type": "Договор оказания услуг",
            "counterparty": "ООО Берёзка",
            "subject": "Юридические услуги",
            "date_end": "2026-04-05",
            "amount": "30000",
            "validation_score": 0.85,
            "validation_warnings": "[]",
            "processed_at": "2026-03-19 09:00:00",
        },
        # 1 expired (date_end в прошлом)
        {
            "filename": "expired1.pdf",
            "file_hash": "hash_expired1",
            "status": "done",
            "contract_type": "Договор подряда",
            "counterparty": "ООО Стройка",
            "subject": "Строительные работы",
            "date_end": "2025-01-01",
            "amount": "1000000",
            "validation_score": 0.8,
            "validation_warnings": "[]",
            "processed_at": "2026-03-18 08:00:00",
        },
        # 1 low-quality (validation_score=0.5, warnings непустые)
        {
            "filename": "lowquality1.pdf",
            "file_hash": "hash_low1",
            "status": "done",
            "contract_type": "Договор займа",
            "counterparty": "ООО Финансы",
            "subject": "Займ на развитие",
            "date_end": "2029-12-31",
            "amount": "200000",
            "validation_score": 0.5,
            "validation_warnings": '["missing field: date_signed"]',
            "processed_at": "2026-03-17 07:00:00",
        },
        # 1 с manual_status="terminated"
        {
            "filename": "terminated1.pdf",
            "file_hash": "hash_term1",
            "status": "done",
            "contract_type": "Договор аренды",
            "counterparty": "ООО Лютик",
            "subject": "Аренда склада",
            "date_end": "2030-06-01",
            "amount": "80000",
            "validation_score": 0.9,
            "validation_warnings": "[]",
            "processed_at": "2026-03-16 06:00:00",
            "manual_status": "terminated",
        },
    ]

    for row in rows:
        manual_status = row.get("manual_status")
        db.conn.execute(
            """
            INSERT INTO contracts
            (filename, file_hash, original_path, status, contract_type, counterparty,
             subject, date_end, amount, validation_score, validation_warnings,
             processed_at, manual_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["filename"],
                row["file_hash"],
                row["filename"],
                row["status"],
                row["contract_type"],
                row["counterparty"],
                row["subject"],
                row["date_end"],
                row["amount"],
                row["validation_score"],
                row["validation_warnings"],
                row["processed_at"],
                manual_status,
            ),
        )
    db.conn.commit()
    return db


@pytest.fixture
def mock_cm(tmp_db):
    """Mock ClientManager, возвращающий tmp_db."""
    cm = MagicMock()
    cm.get_db.return_value = tmp_db
    return cm


# ── Tests for _fuzzy_filter ───────────────────────────────────────────────────

def _make_rows():
    """Тестовые строки для fuzzy filter."""
    return [
        {"contract_type": "Договор аренды", "counterparty": "ООО Ромашка",
         "subject": "Аренда офиса", "filename": "active1.pdf", "amount": "120000"},
        {"contract_type": "Договор поставки", "counterparty": "ИП Иванов",
         "subject": "Поставка оборудования", "filename": "active2.pdf", "amount": "500000"},
        {"contract_type": "Договор займа", "counterparty": "ООО Финансы",
         "subject": "Займ", "filename": "loan.pdf", "amount": "200000"},
    ]


def test_fuzzy_filter_single_word():
    """_fuzzy_filter("аренда", rows) возвращает строки, где есть 'аренда'."""
    from app.components.registry_table import _fuzzy_filter
    rows = _make_rows()
    result = _fuzzy_filter(rows, "аренда")
    assert len(result) >= 1
    # Строки с "аренд" в contract_type или subject должны быть в результате
    types = [r["contract_type"] for r in result]
    subjects = [r["subject"] for r in result]
    assert any("аренд" in t.lower() for t in types + subjects), \
        f"Expected rows with 'аренд', got types: {types}, subjects: {subjects}"


def test_fuzzy_filter_multi_word_and_logic():
    """_fuzzy_filter("аренда Ромашка", rows) требует оба слова (AND)."""
    from app.components.registry_table import _fuzzy_filter
    rows = _make_rows()
    result = _fuzzy_filter(rows, "аренда Ромашка")
    # Только строка с и 'аренда' и 'Ромашка' должна пройти
    assert len(result) == 1
    assert result[0]["counterparty"] == "ООО Ромашка"


def test_fuzzy_filter_empty_query():
    """_fuzzy_filter("", rows) возвращает все строки."""
    from app.components.registry_table import _fuzzy_filter
    rows = _make_rows()
    result = _fuzzy_filter(rows, "")
    assert len(result) == len(rows)


# ── Tests for _fetch_rows ─────────────────────────────────────────────────────

def test_fetch_rows_returns_dicts_with_computed_status(mock_cm, monkeypatch):
    """_fetch_rows возвращает list[dict] с ключом 'computed_status'."""
    monkeypatch.setattr(
        "app.components.registry_table._client_manager", mock_cm
    )
    from app.components.registry_table import _fetch_rows
    rows = _fetch_rows("Основной реестр", "all", "", 30)
    assert isinstance(rows, list)
    assert len(rows) > 0
    for row in rows:
        assert isinstance(row, dict), f"Expected dict, got {type(row)}"
        assert "computed_status" in row, f"Missing computed_status in {list(row.keys())}"


def test_fetch_rows_orders_by_processed_at_desc(mock_cm, monkeypatch):
    """Первая строка имеет наибольший processed_at."""
    monkeypatch.setattr(
        "app.components.registry_table._client_manager", mock_cm
    )
    from app.components.registry_table import _fetch_rows
    rows = _fetch_rows("Основной реестр", "all", "", 30)
    assert len(rows) >= 2
    # Первая строка должна быть наиболее поздней
    first_ts = rows[0]["processed_at"]
    second_ts = rows[1]["processed_at"]
    assert first_ts >= second_ts, f"Expected DESC order: {first_ts!r} >= {second_ts!r}"


def test_fetch_rows_segment_expiring(mock_cm, monkeypatch):
    """Сегмент 'expiring' возвращает только строки с computed_status='expiring'."""
    monkeypatch.setattr(
        "app.components.registry_table._client_manager", mock_cm
    )
    from app.components.registry_table import _fetch_rows
    rows = _fetch_rows("Основной реестр", "expiring", "", 30)
    assert len(rows) >= 1
    for row in rows:
        assert row["computed_status"] == "expiring", \
            f"Expected 'expiring', got '{row['computed_status']}' for {row.get('filename')}"


def test_fetch_rows_segment_attention(mock_cm, monkeypatch):
    """Сегмент 'attention' возвращает строки с validation_score<0.7 или непустыми warnings."""
    monkeypatch.setattr(
        "app.components.registry_table._client_manager", mock_cm
    )
    from app.components.registry_table import _fetch_rows
    rows = _fetch_rows("Основной реестр", "attention", "", 30)
    assert len(rows) >= 1
    for row in rows:
        score = row.get("validation_score") or 1.0
        warnings_raw = row.get("validation_warnings") or "[]"
        try:
            warnings = json.loads(warnings_raw)
        except (json.JSONDecodeError, TypeError):
            warnings = []
        assert score < 0.7 or bool(warnings), \
            f"Row should have low score or warnings: score={score}, warnings={warnings}"
