"""Тесты уведомлений внутри приложения (Phase 3).

INTG-04: st.toast при запуске — «Внимание: N истекают скоро, N уже истекли»

Реализовано в 03-01: toast-блок добавлен в main.py,
защищён st.session_state['startup_toast_shown'].
"""
import pytest

try:
    from services.lifecycle_service import get_attention_required
    _HAS_LIFECYCLE = True
except ImportError:
    _HAS_LIFECYCLE = False


@pytest.fixture
def temp_db(tmp_path):
    """Создаёт временную БД с миграциями для тестов."""
    try:
        from modules.database import Database
        db = Database(tmp_path / "test.db")
        yield db
        db.close()
    except ImportError:
        pytest.skip("modules.database недоступен")


def test_startup_toast_flag(temp_db):
    """INTG-04: get_attention_required возвращает список алертов при наличии истекающих документов."""
    from services.lifecycle_service import get_attention_required

    db = temp_db
    conn = db.conn

    conn.execute(
        "INSERT INTO contracts (filename, original_path, status, date_end) "
        "VALUES ('expiring.pdf', '/tmp/e.pdf', 'done', date('now', '+5 days'))"
    )
    conn.commit()

    alerts = get_attention_required(db, warning_days=30)
    assert len(alerts) > 0, "Должен быть хотя бы один алерт для истекающего документа"


def test_no_toast_when_no_alerts(temp_db):
    """INTG-04: get_attention_required возвращает пустой список если нет истекающих документов."""
    from services.lifecycle_service import get_attention_required

    db = temp_db
    conn = db.conn

    conn.execute(
        "INSERT INTO contracts (filename, original_path, status, date_end) "
        "VALUES ('far_future.pdf', '/tmp/f.pdf', 'done', date('now', '+180 days'))"
    )
    conn.commit()

    alerts = get_attention_required(db, warning_days=30)
    assert len(alerts) == 0, "Не должно быть алертов для документов с датой далеко в будущем"


def test_startup_toast_with_alerts(temp_db):
    """INTG-04: get_attention_required возвращает алерт для документа с date_end = today + 10 дней."""
    from services.lifecycle_service import get_attention_required

    db = temp_db
    conn = db.conn

    conn.execute(
        "INSERT INTO contracts (filename, original_path, status, date_end) "
        "VALUES ('soon_expiring.pdf', '/tmp/s.pdf', 'done', date('now', '+10 days'))"
    )
    conn.commit()

    alerts = get_attention_required(db, warning_days=30)
    assert len(alerts) == 1, "Должен быть ровно один алерт"
    assert alerts[0].computed_status == "expiring", "Статус должен быть 'expiring'"
    assert alerts[0].filename == "soon_expiring.pdf"
