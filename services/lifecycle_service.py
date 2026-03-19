"""Сервис жизненного цикла документа: статусы и панель внимания.

Stateless: все функции принимают db как параметр, не хранят состояние.
Не импортирует streamlit — вызывается из main.py и будущего Telegram-бота.
"""
import logging
from typing import Optional

from modules.database import Database
from modules.models import DeadlineAlert

logger = logging.getLogger(__name__)

# Допустимые ручные статусы
MANUAL_STATUSES = frozenset({"terminated", "extended", "negotiation", "suspended"})

# Метки для отображения в UI
STATUS_LABELS = {
    "active":      ("\u2714", "\u0414\u0435\u0439\u0441\u0442\u0432\u0443\u0435\u0442",         "#22c55e"),
    "expiring":    ("\u26a0", "\u0421\u043a\u043e\u0440\u043e \u0438\u0441\u0442\u0435\u043a\u0430\u0435\u0442",    "#f59e0b"),
    "expired":     ("\u2717", "\u0418\u0441\u0442\u0451\u043a",             "#ef4444"),
    "unknown":     ("?", "\u041d\u0435\u0442 \u0434\u0430\u0442\u044b",           "#9ca3af"),
    "terminated":  ("\u2716", "\u0420\u0430\u0441\u0442\u043e\u0440\u0433\u043d\u0443\u0442",        "#6b7280"),
    "extended":    ("\u21bb", "\u041f\u0440\u043e\u0434\u043b\u0451\u043d",           "#3b82f6"),
    "negotiation": ("~", "\u041d\u0430 \u0441\u043e\u0433\u043b\u0430\u0441\u043e\u0432\u0430\u043d\u0438\u0438",  "#8b5cf6"),
    "suspended":   ("\u23f8", "\u041f\u0440\u0438\u043e\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d",    "#f97316"),
}


def get_computed_status_sql(warning_days: int) -> str:
    """Возвращает SQL-фрагмент CASE для вычисления статуса на лету.

    manual_status имеет приоритет над автоматическим статусом.
    warning_days — количество дней для порога 'expiring'.

    Использование:
        sql = f"SELECT *, {get_computed_status_sql(30)} AS computed_status FROM contracts"
        conn.execute(sql, {"warning_days": warning_days})
    """
    return """
        CASE
            WHEN manual_status IS NOT NULL THEN manual_status
            WHEN date_end IS NULL          THEN 'unknown'
            WHEN date_end < date('now')    THEN 'expired'
            WHEN date_end < date('now', '+' || :warning_days || ' days') THEN 'expiring'
            ELSE 'active'
        END
    """.strip()


def set_manual_status(db: Database, contract_id: int, status: str) -> None:
    """Устанавливает ручной статус договора. status должен быть из MANUAL_STATUSES."""
    if status not in MANUAL_STATUSES:
        raise ValueError(f"Недопустимый статус: {status!r}. Допустимые: {MANUAL_STATUSES}")
    with db._lock:
        db.conn.execute(
            "UPDATE contracts SET manual_status = ? WHERE id = ?",
            (status, contract_id)
        )
        db.conn.commit()
    logger.info("Ручной статус '%s' установлен для договора id=%d", status, contract_id)


def clear_manual_status(db: Database, contract_id: int) -> None:
    """Сбрасывает ручной статус — договор возвращается к автоматическому."""
    with db._lock:
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
            CAST(julianday(date_end) - julianday('now') AS INTEGER) AS days_until_expiry,
            {get_computed_status_sql(warning_days)} AS computed_status,
            validation_status
        FROM contracts
        WHERE manual_status IS NULL
          AND date_end IS NOT NULL
          AND date_end < date('now', '+' || :warning_days || ' days')
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
