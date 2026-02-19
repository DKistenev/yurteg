"""Модуль работы с SQLite.

Хранит метаданные всех обработанных файлов. Обеспечивает
резюмируемость: при повторном запуске пропускает уже обработанные файлы.
"""
import json
import logging
import sqlite3
from pathlib import Path

from modules.models import ProcessingResult

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_hash TEXT UNIQUE,
    status TEXT DEFAULT 'pending',
    error_message TEXT,

    -- Метаданные
    contract_type TEXT,
    counterparty TEXT,
    subject TEXT,
    date_signed TEXT,
    date_start TEXT,
    date_end TEXT,
    amount TEXT,
    special_conditions TEXT,  -- JSON array
    parties TEXT,             -- JSON array
    confidence REAL,

    -- Валидация
    validation_status TEXT,
    validation_warnings TEXT,  -- JSON array
    validation_score REAL,

    -- Системные
    organized_path TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model_used TEXT
);

CREATE INDEX IF NOT EXISTS idx_file_hash ON contracts(file_hash);
CREATE INDEX IF NOT EXISTS idx_status ON contracts(status);
CREATE INDEX IF NOT EXISTS idx_contract_type ON contracts(contract_type);
"""


class Database:
    """CRUD-обёртка над SQLite для хранения результатов обработки."""

    def __init__(self, db_path: Path) -> None:
        """Создаёт/открывает БД. Автоматически создаёт таблицы если их нет."""
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        logger.info("БД открыта: %s", db_path)

    def is_processed(self, file_hash: str) -> bool:
        """True если файл с таким хешем уже обработан (status=done)."""
        cursor = self.conn.execute(
            "SELECT 1 FROM contracts WHERE file_hash = ? AND status = 'done'",
            (file_hash,),
        )
        return cursor.fetchone() is not None

    def save_result(self, result: ProcessingResult) -> None:
        """Сохраняет результат обработки. Upsert по file_hash."""
        m = result.metadata
        v = result.validation

        data = (
            str(result.file_info.path),
            result.file_info.filename,
            result.file_info.file_hash,
            result.status,
            result.error_message,
            m.contract_type if m else None,
            m.counterparty if m else None,
            m.subject if m else None,
            m.date_signed if m else None,
            m.date_start if m else None,
            m.date_end if m else None,
            m.amount if m else None,
            json.dumps(m.special_conditions, ensure_ascii=False) if m else None,
            json.dumps(m.parties, ensure_ascii=False) if m else None,
            m.confidence if m else None,
            v.status if v else None,
            json.dumps(v.warnings, ensure_ascii=False) if v else None,
            v.score if v else None,
            str(result.organized_path) if result.organized_path else None,
            result.model_used,
        )

        self.conn.execute(
            """
            INSERT OR REPLACE INTO contracts
            (original_path, filename, file_hash, status, error_message,
             contract_type, counterparty, subject, date_signed, date_start, date_end,
             amount, special_conditions, parties, confidence,
             validation_status, validation_warnings, validation_score,
             organized_path, model_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            data,
        )
        self.conn.commit()
        logger.debug("Сохранён: %s (статус=%s)", result.file_info.filename, result.status)

    def get_all_results(self) -> list[dict]:
        """Возвращает все записи для генерации отчёта."""
        cursor = self.conn.execute(
            "SELECT * FROM contracts ORDER BY processed_at"
        )
        rows = cursor.fetchall()
        results = []
        for row in rows:
            d = dict(row)
            # Десериализация JSON-полей
            for field in ("special_conditions", "parties", "validation_warnings"):
                if d.get(field):
                    try:
                        d[field] = json.loads(d[field])
                    except (json.JSONDecodeError, TypeError):
                        d[field] = []
            results.append(d)
        return results

    def get_stats(self) -> dict:
        """Статистика: {total, done, error, pending}."""
        cursor = self.conn.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as done,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
            FROM contracts
            """
        )
        row = cursor.fetchone()
        return {
            "total": row["total"] or 0,
            "done": row["done"] or 0,
            "error": row["error"] or 0,
            "pending": row["pending"] or 0,
        }

    def close(self) -> None:
        """Закрывает соединение."""
        self.conn.close()
        logger.info("БД закрыта")

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *args) -> None:
        self.close()
