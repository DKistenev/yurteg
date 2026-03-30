"""Сервис жизненного цикла документа: статусы и панель внимания.

Stateless: все функции принимают db как параметр, не хранят состояние.
Не зависит от UI-слоя — вызывается из main.py и будущего Telegram-бота.
"""
import logging

from modules.database import Database
from modules.models import DeadlineAlert

logger = logging.getLogger(__name__)

# Допустимые ручные статусы
MANUAL_STATUSES = frozenset({"negotiation"})

# Метки для отображения в UI
STATUS_LABELS = {
    "active":      ("\u2714", "Действует",      "#22c55e", "bg-green-100 text-green-800"),
    "expiring":    ("\u26a0", "Заканчивается",  "#f59e0b", "bg-amber-100 text-amber-800"),
    "expired":     ("\u2717", "Закончился",     "#ef4444", "bg-red-100 text-red-800"),
    "unknown":     ("?",      "Нет даты",       "#9ca3af", "bg-gray-100 text-gray-600"),
    "negotiation": ("~",      "На согласовании","#8b5cf6", "bg-violet-100 text-violet-800"),
}


def get_computed_status_sql(warning_days: int) -> str:
    """Возвращает SQL-фрагмент CASE для вычисления статуса на лету.

    manual_status имеет приоритет над автоматическим статусом.
    warning_days — количество дней для порога 'expiring'.

    Raises:
        ValueError: если warning_days <= 0.

    Использование:
        sql = f"SELECT *, {get_computed_status_sql(30)} AS computed_status FROM contracts"
        conn.execute(sql, {"warning_days": warning_days})
    """
    if not isinstance(warning_days, int) or warning_days <= 0:
        raise ValueError(f"warning_days должен быть положительным int, получено: {warning_days}")
    return """
        CASE
            WHEN manual_status IS NOT NULL THEN manual_status
            WHEN date_end IS NULL          THEN 'unknown'
            WHEN date_end < date('now')    THEN 'expired'
            WHEN date_end <= date('now', '+' || :warning_days || ' days') THEN 'expiring'
            ELSE 'active'
        END
    """.strip()


def set_manual_status(db: Database, contract_id: int, status: str) -> None:
    """Устанавливает ручной статус договора. status должен быть из MANUAL_STATUSES."""
    if status not in MANUAL_STATUSES:
        raise ValueError(f"Недопустимый статус: {status!r}. Допустимые: {MANUAL_STATUSES}")
    with db.lock:
        db.conn.execute(
            "UPDATE contracts SET manual_status = ? WHERE id = ?",
            (status, contract_id)
        )
        db.conn.commit()
    logger.info("Ручной статус '%s' установлен для договора id=%d", status, contract_id)


def clear_manual_status(db: Database, contract_id: int) -> None:
    """Сбрасывает ручной статус — договор возвращается к автоматическому."""
    with db.lock:
        db.conn.execute(
            "UPDATE contracts SET manual_status = NULL WHERE id = ?",
            (contract_id,)
        )
        db.conn.commit()
    logger.info("Ручной статус сброшен для договора id=%d", contract_id)


def get_attention_required(db: Database, warning_days: int) -> list[DeadlineAlert]:
    """Возвращает документы для панели «требует внимания»:
    - истёкшие (date_end < today)
    - истекающие в течение warning_days дней
    Исключает документы с manual_status (они под контролем юриста).
    Сортировка: сначала истёкшие, потом по дате окончания ASC.
    """
    sql = f"""
        SELECT
            id, filename, counterparty, contract_type, date_end,
            CAST(julianday(date_end) - julianday(date('now')) AS INTEGER) AS days_until_expiry,
            {get_computed_status_sql(warning_days)} AS computed_status,
            validation_status
        FROM contracts
        WHERE (manual_status IS NULL OR manual_status NOT IN ('negotiation'))
          AND date_end IS NOT NULL
          AND date_end <= date('now', '+' || :warning_days || ' days')
          AND status = 'done'
        ORDER BY date_end ASC
    """
    rows = db.conn.execute(sql, {"warning_days": warning_days}).fetchall()
    alerts = []
    for row in rows:
        alerts.append(DeadlineAlert(
            contract_id=row[0],
            filename=row[1],
            counterparty=row[2],
            contract_type=row[3],
            date_end=row[4],
            days_until_expiry=row[5],
            computed_status=row[6],
            validation_status=row[7],
        ))
    return alerts
