"""Тесты Telegram-бота (Phase 3).

INTG-01: Telegram-бот принимает документы (PDF/DOCX) — очередь файлов
INTG-02: Telegram-бот отправляет уведомления о приближающихся сроках

Wave 0: тест-скелеты созданы до реализации (RED стадия).
Assertions дополняются после 03-03 (telegram bot implementation).
"""
import pytest


@pytest.fixture
def temp_db(tmp_path):
    """Создаёт временную БД с миграциями для тестов."""
    try:
        from modules.database import Database
        db = Database(tmp_path / "test.db", tmp_path)
        yield db
        db.close()
    except ImportError:
        pytest.skip("modules.database недоступен")


@pytest.mark.xfail(reason="INTG-01: file_queue реализуется в 03-03", strict=False)
def test_file_queue_enqueue(tmp_path):
    """INTG-01: enqueue_file вставляет строку в таблицу file_queue."""
    try:
        from server.queue_service import enqueue_file
    except ImportError:
        pytest.xfail("server.queue_service не существует — реализуется в 03-03")

    db_path = tmp_path / "queue.db"
    file_id = "BQACAgIAAxkBAAIB"
    chat_id = 123456789
    filename = "contract.pdf"

    enqueue_file(db_path, chat_id=chat_id, file_id=file_id, filename=filename)

    import sqlite3
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT chat_id, file_id, filename, fetched FROM file_queue WHERE file_id=?",
        (file_id,)
    ).fetchone()
    conn.close()

    assert row is not None, "enqueue_file должна создать запись в file_queue"
    assert row[0] == chat_id
    assert row[1] == file_id
    assert row[2] == filename
    assert row[3] == 0, "Новые файлы не должны быть помечены как fetched"


@pytest.mark.xfail(reason="INTG-01: fetch_queue реализуется в 03-03", strict=False)
def test_file_queue_fetch(tmp_path):
    """INTG-01: fetch_queue возвращает необработанные файлы и помечает их как fetched."""
    try:
        from server.queue_service import enqueue_file, fetch_queue
    except ImportError:
        pytest.xfail("server.queue_service не существует — реализуется в 03-03")

    db_path = tmp_path / "queue.db"
    enqueue_file(db_path, chat_id=111, file_id="FILE001", filename="doc1.pdf")
    enqueue_file(db_path, chat_id=111, file_id="FILE002", filename="doc2.pdf")

    files = fetch_queue(db_path, chat_id=111)
    assert len(files) == 2, "Должны вернуться 2 необработанных файла"

    # Повторный вызов — файлы уже помечены как fetched
    files_again = fetch_queue(db_path, chat_id=111)
    assert len(files_again) == 0, "После fetch файлы должны быть помечены как fetched"


@pytest.mark.xfail(reason="INTG-01: binding_code реализуется в 03-03", strict=False)
def test_binding_code_generation(tmp_path):
    """INTG-01: generate_binding_code создаёт 6-значный код и сохраняет в pending_bindings."""
    try:
        from server.binding_service import generate_binding_code
    except ImportError:
        pytest.xfail("server.binding_service не существует — реализуется в 03-03")

    db_path = tmp_path / "binding.db"
    chat_id = 987654321

    code = generate_binding_code(db_path, chat_id=chat_id)

    assert isinstance(code, str), "Код должен быть строкой"
    assert len(code) == 6, f"Код должен быть 6-значным, получен: '{code}'"
    assert code.isdigit(), "Код должен состоять только из цифр"


@pytest.mark.xfail(reason="INTG-01: binding_code expiry реализуется в 03-03", strict=False)
def test_binding_code_expiry(tmp_path):
    """INTG-01: истёкший код возвращает None при consume."""
    try:
        from server.binding_service import consume_binding_code
    except ImportError:
        pytest.xfail("server.binding_service не существует — реализуется в 03-03")

    import sqlite3
    from datetime import datetime, timedelta

    db_path = tmp_path / "binding.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS pending_bindings "
        "(code TEXT PRIMARY KEY, chat_id INTEGER, expires_at TEXT)"
    )
    # Вставляем истёкший код
    expired_at = (datetime.utcnow() - timedelta(minutes=10)).isoformat()
    conn.execute(
        "INSERT INTO pending_bindings (code, chat_id, expires_at) VALUES (?, ?, ?)",
        ("123456", 111222333, expired_at)
    )
    conn.commit()
    conn.close()

    result = consume_binding_code(db_path, code="123456")
    assert result is None, "Истёкший код должен возвращать None"


@pytest.mark.xfail(reason="INTG-01: binding_code consume реализуется в 03-03", strict=False)
def test_binding_code_consume(tmp_path):
    """INTG-01: валидный код возвращает chat_id и удаляет запись из pending_bindings."""
    try:
        from server.binding_service import generate_binding_code, consume_binding_code
    except ImportError:
        pytest.xfail("server.binding_service не существует — реализуется в 03-03")

    db_path = tmp_path / "binding.db"
    chat_id = 555666777

    code = generate_binding_code(db_path, chat_id=chat_id)
    result = consume_binding_code(db_path, code=code)

    assert result == chat_id, f"consume должен вернуть chat_id={chat_id}, получен {result}"

    # Повторный consume — должен вернуть None (запись удалена)
    result_again = consume_binding_code(db_path, code=code)
    assert result_again is None, "Повторный consume одноразового кода должен вернуть None"


@pytest.mark.xfail(reason="INTG-02: deadline_alerts реализуется в 03-04", strict=False)
def test_deadline_alerts(temp_db):
    """INTG-02: get_alerts_for_user возвращает контракты с date_end в пределах порога."""
    try:
        from server.deadline_service import get_alerts_for_user
    except ImportError:
        pytest.xfail("server.deadline_service не существует — реализуется в 03-04")

    db = temp_db
    conn = db.conn

    conn.execute(
        "INSERT INTO contracts (filename, original_path, status, date_end) "
        "VALUES ('near_deadline.pdf', '/tmp/n.pdf', 'done', date('now', '+10 days'))"
    )
    conn.execute(
        "INSERT INTO contracts (filename, original_path, status, date_end) "
        "VALUES ('far_deadline.pdf', '/tmp/f.pdf', 'done', date('now', '+90 days'))"
    )
    conn.commit()

    alerts = get_alerts_for_user(db, warning_days=30)
    filenames = [a["filename"] for a in alerts]

    assert "near_deadline.pdf" in filenames, "Документ с датой через 10 дней должен быть в алертах"
    assert "far_deadline.pdf" not in filenames, "Документ с датой через 90 дней не должен быть в алертах"


@pytest.mark.xfail(reason="INTG-02: push_deadlines реализуется в 03-04", strict=False)
def test_push_deadlines_minimal_data(temp_db):
    """INTG-02: алерт содержит только date_end, filename, counterparty, status — никаких сумм/текстов."""
    try:
        from server.deadline_service import get_alerts_for_user
    except ImportError:
        pytest.xfail("server.deadline_service не существует — реализуется в 03-04")

    db = temp_db
    conn = db.conn

    conn.execute(
        "INSERT INTO contracts (filename, original_path, status, date_end, counterparty, amount) "
        "VALUES ('secret.pdf', '/tmp/s.pdf', 'done', date('now', '+5 days'), 'ООО Рога', 150000)"
    )
    conn.commit()

    alerts = get_alerts_for_user(db, warning_days=30)
    assert len(alerts) > 0

    alert = alerts[0]
    allowed_keys = {"date_end", "filename", "counterparty", "status"}
    actual_keys = set(alert.keys())

    assert actual_keys <= allowed_keys, (
        f"Алерт содержит лишние поля: {actual_keys - allowed_keys}. "
        f"Разрешены только: {allowed_keys}"
    )
    assert "amount" not in alert, "Сумма договора не должна передаваться в серверный дедлайн-алерт"
