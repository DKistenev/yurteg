"""Тесты уведомлений внутри приложения (Phase 3).

INTG-04: st.toast при запуске — «⚠️ N документов истекают на этой неделе»

Wave 0: тест-скелеты созданы до реализации (RED стадия).
Assertions дополняются после 03-02 (notifications implementation).
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
        db = Database(tmp_path / "test.db", tmp_path)
        yield db
        db.close()
    except ImportError:
        pytest.skip("modules.database недоступен")


@pytest.mark.xfail(reason="INTG-04: уведомления реализуются в 03-02", strict=False)
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


@pytest.mark.xfail(reason="INTG-04: session_state флаг реализуется в 03-02", strict=False)
def test_startup_toast_only_once():
    """INTG-04: session_state флаг предотвращает повторный показ тоста при рерандере."""
    # Проверяем что функция показа тоста использует st.session_state для защиты от повторов
    assert False, "Placeholder: реализуется в 03-02 — show_startup_toast должна проверять session_state['toast_shown']"


@pytest.mark.xfail(reason="INTG-04: уведомления реализуются в 03-02", strict=False)
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
