"""Сервис платёжного календаря.

Разворачивает периодические платежи из ContractMetadata в конкретные даты
i сохраняет в SQLite таблицу payments. Формирует события в формате FullCalendar.

Не зависит от UI-слоя — вызывается из pipeline_service и main.py.
"""
import logging
from datetime import date, datetime
from typing import Optional

from dateutil.relativedelta import relativedelta

from modules.database import Database
from modules.models import ContractMetadata

logger = logging.getLogger(__name__)

# Маппинг частоты → relativedelta
FREQUENCY_DELTA = {
    "monthly":   relativedelta(months=1),
    "quarterly": relativedelta(months=3),
    "yearly":    relativedelta(years=1),
}

# Цвета направления платежа (FullCalendar backgroundColor)
DIRECTION_COLOR = {
    "income":  "#22c55e",   # зелёный
    "expense": "#ef4444",   # красный
}


def _parse_date(s: Optional[str]) -> Optional[date]:
    """Парсит ISO 8601 строку в date. Возвращает None при ошибке."""
    if not s or len(s) < 10:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def unroll_payments(
    start: date,
    end: date,
    amount: float,
    frequency: Optional[str],
    direction: str = "expense",
) -> list[dict]:
    """Разворачивает периодический платёж в список событий.

    Для разового платежа (frequency=None или 'once') возвращает одну запись.
    Для периодических — все даты от start до end включительно.

    Returns: список dict с ключами: date (date), amount (float),
             direction (str), is_periodic (bool), frequency (str|None)
    """
    if amount is not None and amount < 0:
        raise ValueError(f"Сумма платежа не может быть отрицательной: {amount}")
    if start > end:
        raise ValueError(f"Дата начала ({start}) позже даты окончания ({end})")

    valid_frequencies = {None, "once", "monthly", "quarterly", "yearly"}
    if frequency not in valid_frequencies:
        raise ValueError(f"Неизвестная частота платежа: {frequency!r}")

    delta = FREQUENCY_DELTA.get(frequency or "")
    is_periodic = delta is not None

    if not is_periodic:
        return [{
            "date": start,
            "amount": amount,
            "direction": direction,
            "is_periodic": False,
            "frequency": None,
        }]

    result = []
    current = start
    # Защита от бесконечного цикла: максимум 1200 итераций (~100 лет monthly)
    max_iter = 1200
    while current <= end and max_iter > 0:
        result.append({
            "date": current,
            "amount": amount,
            "direction": direction,
            "is_periodic": True,
            "frequency": frequency,
        })
        current += delta
        max_iter -= 1

    return result


def save_payments(
    db: Database,
    contract_id: int,
    meta: ContractMetadata,
) -> int:
    """Сохраняет платежи для договора в таблицу payments.

    Удаляет существующие записи перед записью (идемпотентно).
    Returns: количество сохранённых записей.
    """
    with db.lock:
        db.conn.execute("DELETE FROM payments WHERE contract_id=?", (contract_id,))
        db.conn.commit()

    if meta.payment_amount is None:
        return 0

    # Определить временной диапазон
    start = _parse_date(meta.date_start) or _parse_date(meta.date_signed)
    end = _parse_date(meta.date_end)

    if start is None:
        logger.warning(
            "contract_id=%d: нет даты начала, платежи не сохранены", contract_id
        )
        return 0

    if end is None:
        # Если нет даты окончания — записать только начальный платёж
        end = start

    direction = meta.payment_direction or "expense"
    events = unroll_payments(start, end, meta.payment_amount, meta.payment_frequency, direction)

    with db.lock:
        db.conn.executemany(
            """INSERT INTO payments (contract_id, payment_date, amount, direction,
                                     is_periodic, frequency)
               VALUES (:contract_id, :payment_date, :amount, :direction,
                       :is_periodic, :frequency)""",
            [
                {
                    "contract_id": contract_id,
                    "payment_date": e["date"].isoformat(),
                    "amount": e["amount"],
                    "direction": e["direction"],
                    "is_periodic": 1 if e["is_periodic"] else 0,
                    "frequency": e["frequency"],
                }
                for e in events
            ],
        )
        db.conn.commit()

    logger.info(
        "contract_id=%d: сохранено %d платежей (%s)",
        contract_id, len(events), meta.payment_frequency or "once",
    )
    return len(events)


def get_calendar_events(
    db: Database,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[dict]:
    """Возвращает события календаря в формате FullCalendar.

    Если start_date/end_date заданы — фильтрует по диапазону.
    Каждое событие: title, start, end, backgroundColor, extendedProps.
    """
    sql = """
        SELECT p.id, p.contract_id, p.payment_date, p.amount,
               p.direction, p.frequency,
               c.counterparty, c.contract_type, c.filename
        FROM payments p
        JOIN contracts c ON c.id = p.contract_id
        WHERE 1=1
    """
    params: list = []
    if start_date:
        sql += " AND p.payment_date >= ?"
        params.append(start_date.isoformat())
    if end_date:
        sql += " AND p.payment_date <= ?"
        params.append(end_date.isoformat())
    sql += " ORDER BY p.payment_date ASC"

    with db.lock:
        rows = db.conn.execute(sql, params).fetchall()

    events = []
    for row in rows:
        pid, cid, pdate, amount, direction, freq, counterparty, ctype, fname = row
        color = DIRECTION_COLOR.get(direction, "#9ca3af")
        amount_str = f"{amount:,.0f} ₽".replace(",", " ")
        title = f"{counterparty or fname} • {amount_str}"
        events.append({
            "title": title,
            "start": pdate,
            "end": pdate,
            "backgroundColor": color,
            "extendedProps": {
                "contract_id": cid,
                "direction": direction,
                "amount": amount,
                "counterparty": counterparty,
                "contract_type": ctype,
            },
        })
    return events
