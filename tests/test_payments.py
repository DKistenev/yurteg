"""Тесты платёжного сервиса (Phase 2).

LIFE-07: Периодические платежи разворачиваются правильно (monthly/quarterly/yearly)
"""
import pytest
from datetime import date


@pytest.fixture
def temp_db(tmp_path):
    """Создаёт временную БД с миграциями для тестов."""
    try:
        from modules.database import Database
        db = Database(tmp_path / "test.db")
        yield db
        db.close()
    except ImportError:
        pytest.skip("modules.database недоступен — запустите после 02-01")


def test_payment_unroll():
    """LIFE-07: Периодические платежи разворачиваются в список конкретных дат."""
    from services.payment_service import unroll_payments

    # Ежемесячный платёж на 3 месяца
    payments = unroll_payments(
        start=date(2026, 1, 1),
        end=date(2026, 3, 31),
        amount=50_000.0,
        frequency="monthly",
        direction="expense",
    )
    assert len(payments) == 3, f"Ожидается 3 платежа (monthly x3), получено {len(payments)}"
    assert all(isinstance(p, dict) for p in payments)
    assert all(p["direction"] == "expense" for p in payments)
    assert all(p["amount"] == 50_000.0 for p in payments)

    # Ежеквартальный платёж на год
    payments_q = unroll_payments(
        start=date(2026, 1, 1),
        end=date(2026, 12, 31),
        amount=100_000.0,
        frequency="quarterly",
        direction="income",
    )
    assert len(payments_q) == 4, f"Ожидается 4 платежа (quarterly x4), получено {len(payments_q)}"


def test_payment_save_and_load(temp_db):
    """LIFE-07: Платежи сохраняются в БД через save_payments и загружаются через get_calendar_events."""
    from services.payment_service import save_payments, get_calendar_events
    from modules.models import ContractMetadata

    db = temp_db
    conn = db.conn
    conn.execute(
        "INSERT INTO contracts (filename, original_path, status) "
        "VALUES ('pay_test.pdf', '/tmp/p.pdf', 'done')"
    )
    conn.commit()
    cid = conn.execute("SELECT id FROM contracts WHERE filename='pay_test.pdf'").fetchone()[0]

    # Создаём метаданные с двумя ежемесячными платежами (январь–февраль)
    meta = ContractMetadata(
        contract_type="Договор",
        counterparty="ООО Тест",
        payment_amount=10_000.0,
        payment_direction="expense",
        payment_frequency="monthly",
        date_start="2026-01-01",
        date_end="2026-02-28",
    )
    count = save_payments(db, cid, meta)
    assert count == 2, f"Ожидается 2 сохранённых платежа, получено {count}"

    events = get_calendar_events(db)
    contract_events = [e for e in events if e.get("extendedProps", {}).get("contract_id") == cid]
    assert len(contract_events) == 2, f"Ожидается 2 события для contract_id={cid}"
