"""Tests for document card data layer (Phase 9, DOC-01, DOC-02, DOC-03)."""
import json
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.database import Database


def _make_db():
    """Create temporary Database with one test contract."""
    tmp = tempfile.mkdtemp()
    db = Database(Path(tmp) / "test.sqlite")
    db.conn.execute(
        "INSERT INTO contracts (id, original_path, filename, file_hash, status, contract_type, "
        "counterparty, subject, date_start, date_end, amount, special_conditions, "
        "parties, review_status, lawyer_comment) "
        "VALUES (1, '/tmp/test.pdf', 'test.pdf', 'abc123', 'done', 'Аренда', 'ООО Тест', "
        "'Аренда помещения', '2025-01-01', '2026-01-01', '100 000 руб', "
        "?, ?, 'not_reviewed', '')",
        (json.dumps(["Условие 1", "Условие 2"]), json.dumps(["Сторона А", "Сторона Б"])),
    )
    db.conn.commit()
    return db


def test_get_contract_by_id():
    db = _make_db()
    result = db.get_contract_by_id(1)
    assert result is not None
    assert result["contract_type"] == "Аренда"
    assert result["counterparty"] == "ООО Тест"
    assert isinstance(result["special_conditions"], list)
    assert len(result["special_conditions"]) == 2
    assert isinstance(result["parties"], list)
    assert result["lawyer_comment"] == ""
    db.close()


def test_get_contract_by_id_none():
    db = _make_db()
    result = db.get_contract_by_id(999)
    assert result is None
    db.close()


def test_prevnext_logic():
    """Test prev/next index computation from filtered_doc_ids list."""
    doc_ids = [10, 20, 30, 40, 50]
    current_id = 30
    idx = doc_ids.index(current_id)
    prev_id = doc_ids[idx - 1] if idx > 0 else None
    next_id = doc_ids[idx + 1] if idx < len(doc_ids) - 1 else None
    assert prev_id == 20
    assert next_id == 40

    # Edge: first element
    idx = doc_ids.index(10)
    assert (doc_ids[idx - 1] if idx > 0 else None) is None

    # Edge: last element
    idx = doc_ids.index(50)
    assert (doc_ids[idx + 1] if idx < len(doc_ids) - 1 else None) is None
