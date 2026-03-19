"""Тесты платёжного сервиса (Phase 2).

LIFE-07: Периодические платежи разворачиваются правильно (monthly/quarterly/yearly)

Wave 0: тест-скелет создан до реализации (RED стадия).
Assertions дополняются после 02-05 (payment_service).
"""
import pytest
from datetime import date


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


@pytest.mark.xfail(reason="payment_service создаётся в 02-05", strict=False)
def test_payment_unroll():
    """LIFE-07: Периодические платежи разворачиваются в список конкретных дат."""
    from services.payment_service import unroll_periodic_payment
    from modules.models import Payment

    # Ежемесячный платёж на 3 месяца
    payments = unroll_periodic_payment(
        contract_id=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        amount=50_000.0,
        direction="expense",
        frequency="monthly",
    )
    assert len(payments) == 3, f"Ожидается 3 платежа (monthly x3), получено {len(payments)}"
    assert all(isinstance(p, Payment) for p in payments)
    assert all(p.direction == "expense" for p in payments)
    assert all(p.amount == 50_000.0 for p in payments)

    # Ежеквартальный платёж на год
    payments_q = unroll_periodic_payment(
        contract_id=2,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        amount=100_000.0,
        direction="income",
        frequency="quarterly",
    )
    assert len(payments_q) == 4, f"Ожидается 4 платежа (quarterly x4), получено {len(payments_q)}"


@pytest.mark.xfail(reason="payment_service создаётся в 02-05", strict=False)
def test_payment_save_and_load(temp_db):
    """LIFE-07: Платежи сохраняются в БД и корректно загружаются."""
    from services.payment_service import save_payments, get_payments_for_contract
    from modules.models import Payment

    db = temp_db
    conn = db._conn
    conn.execute(
        "INSERT INTO contracts (filename, original_path, status) "
        "VALUES ('pay_test.pdf', '/tmp/p.pdf', 'done')"
    )
    conn.commit()
    cid = conn.execute("SELECT id FROM contracts WHERE filename='pay_test.pdf'").fetchone()[0]

    payments = [
        Payment(
            id=0, contract_id=cid,
            payment_date="2026-02-01", amount=10_000.0,
            direction="expense", is_periodic=False,
        ),
        Payment(
            id=0, contract_id=cid,
            payment_date="2026-03-01", amount=10_000.0,
            direction="expense", is_periodic=False,
        ),
    ]
    save_payments(db, payments)

    loaded = get_payments_for_contract(db, cid)
    assert len(loaded) == 2, f"Ожидается 2 платежа, загружено {len(loaded)}"
    assert all(p.contract_id == cid for p in loaded)
