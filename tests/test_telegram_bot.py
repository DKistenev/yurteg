"""Тесты Telegram-бота (Phase 3).

INTG-01: Telegram-бот принимает документы (PDF/DOCX) — очередь файлов
INTG-02: Telegram-бот отправляет уведомления о приближающихся сроках

Реализовано в 03-03: bot_server/database.py (ServerDatabase).
Тесты используют ServerDatabase напрямую через tmp_path.
"""
import pytest
from datetime import date, timedelta


@pytest.fixture
def server_db(tmp_path):
    """Создаёт ServerDatabase во временной директории."""
    from bot_server.database import ServerDatabase
    db = ServerDatabase(tmp_path / "server.db")
    yield db


# ------------------------------------------------------------------
# File queue tests (INTG-01)
# ------------------------------------------------------------------

def test_file_queue_enqueue(server_db):
    """INTG-01: enqueue_file вставляет строку в таблицу file_queue."""
    server_db.enqueue_file(
        chat_id=123,
        file_path="/tmp/test.pdf",
        filename="test.pdf",
        mime_type="application/pdf",
    )
    items = server_db.fetch_queue(123)
    assert len(items) == 1, "enqueue_file должна создать запись в file_queue"
    assert items[0]["filename"] == "test.pdf"


def test_file_queue_fetch(server_db):
    """INTG-01: fetch_queue возвращает необработанные файлы; mark_fetched скрывает их."""
    server_db.enqueue_file(123, "/tmp/doc1.pdf", "doc1.pdf", "application/pdf")
    server_db.enqueue_file(123, "/tmp/doc2.pdf", "doc2.pdf", "application/pdf")

    items = server_db.fetch_queue(123)
    assert len(items) == 2, "Должны вернуться 2 необработанных файла"

    # Пометить первый как fetched
    server_db.mark_fetched(items[0]["id"])

    remaining = server_db.fetch_queue(123)
    assert len(remaining) == 1, "После mark_fetched должен остаться 1 файл"
    assert remaining[0]["filename"] == "doc2.pdf"


def test_binding_code_generation(server_db):
    """INTG-01: save_pending_binding сохраняет код; consume_pending_binding возвращает {chat_id}."""
    server_db.save_pending_binding(chat_id=123, code="654321", ttl_minutes=15)
    result = server_db.consume_pending_binding("654321")
    assert result is not None, "consume должен вернуть не-None для валидного кода"
    assert result["chat_id"] == 123, f"Ожидался chat_id=123, получен {result}"


def test_binding_code_expiry(server_db, tmp_path):
    """INTG-01: истёкший код возвращает None при consume."""
    import sqlite3
    from datetime import UTC, datetime, timedelta

    # Вставляем код с уже истёкшим expires_at напрямую в БД
    expired_at = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
    conn = sqlite3.connect(str(tmp_path / "server.db"))
    conn.execute(
        "INSERT OR REPLACE INTO pending_bindings (code, chat_id, expires_at) VALUES (?, ?, ?)",
        ("999999", 111, expired_at),
    )
    conn.commit()
    conn.close()

    result = server_db.consume_pending_binding("999999")
    assert result is None, "Истёкший код должен возвращать None"


def test_binding_code_consume(server_db):
    """INTG-01: после consume повторный consume того же кода возвращает None."""
    server_db.save_pending_binding(chat_id=555, code="111222", ttl_minutes=15)

    first = server_db.consume_pending_binding("111222")
    assert first is not None, "Первый consume должен успешно вернуть результат"
    assert first["chat_id"] == 555

    second = server_db.consume_pending_binding("111222")
    assert second is None, "Повторный consume одноразового кода должен вернуть None"


# ------------------------------------------------------------------
# Deadline tests (INTG-02)
# ------------------------------------------------------------------

def test_deadline_alerts(server_db):
    """INTG-02: get_alerts_for_user возвращает записи с date_end в пределах порога."""
    today = date.today()
    near = (today + timedelta(days=5)).isoformat()
    far = (today + timedelta(days=60)).isoformat()

    server_db.save_deadlines(chat_id=123, alerts=[
        {"contract_ref": "near", "counterparty": "ООО А", "date_end": near, "status": "done"},
        {"contract_ref": "far", "counterparty": "ООО Б", "date_end": far, "status": "done"},
    ])

    alerts = server_db.get_alerts_for_user(chat_id=123, warning_days=30)
    refs = [a["contract_ref"] for a in alerts]

    assert "near" in refs, "Документ с датой через 5 дней должен быть в алертах"
    assert "far" not in refs, "Документ с датой через 60 дней не должен быть в алертах (порог 30)"


def test_push_deadlines_minimal_data(server_db):
    """INTG-02: алерт содержит только contract_ref, counterparty, date_end, status — без лишних полей."""
    today = date.today()
    near = (today + timedelta(days=5)).isoformat()

    server_db.save_deadlines(chat_id=999, alerts=[
        {"contract_ref": "C001", "counterparty": "ООО Рога", "date_end": near, "status": "done"},
    ])

    alerts = server_db.get_alerts_for_user(chat_id=999, warning_days=30)
    assert len(alerts) == 1

    alert = alerts[0]
    allowed_keys = {"contract_ref", "counterparty", "date_end", "status"}
    actual_keys = set(alert.keys())

    assert actual_keys <= allowed_keys, (
        f"Алерт содержит лишние поля: {actual_keys - allowed_keys}. "
        f"Разрешены только: {allowed_keys}"
    )
    assert "amount" not in alert, "Сумма договора не должна передаваться в серверный дедлайн-алерт"
