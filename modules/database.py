"""Модуль работы с SQLite.

Хранит метаданные всех обработанных файлов. Обеспечивает
резюмируемость: при повторном запуске пропускает уже обработанные файлы.
"""
import json
import logging
import shutil
import sqlite3
import threading
import time
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
"""

# Индексы создаются отдельно с graceful fallback — безопасно при апгрейде
_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_file_hash ON contracts(file_hash)",
    "CREATE INDEX IF NOT EXISTS idx_status ON contracts(status)",
    "CREATE INDEX IF NOT EXISTS idx_contract_type ON contracts(contract_type)",
]


def _backup_database(db_path: Path) -> Path:
    """Создаёт timestamped backup перед миграцией. Возвращает путь к backup."""
    ts = int(time.time())
    backup = db_path.parent / f"{db_path.stem}_backup_{ts}.sqlite"
    shutil.copy2(db_path, backup)
    logger.info("DB backup создан: %s", backup)
    return backup


def _ensure_migrations_table(conn: sqlite3.Connection) -> None:
    """Создаёт таблицу schema_migrations если не существует."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()


def _is_migration_applied(conn: sqlite3.Connection, version: int) -> bool:
    """True если миграция с данным версионным номером уже применена."""
    row = conn.execute(
        "SELECT 1 FROM schema_migrations WHERE version = ?", (version,)
    ).fetchone()
    return row is not None


def _mark_migration_applied(conn: sqlite3.Connection, version: int) -> None:
    """Записывает факт применения миграции."""
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations (version) VALUES (?)", (version,)
    )
    conn.commit()
    logger.info("Миграция v%d применена", version)


def _migrate_v1_review_columns(conn: sqlite3.Connection) -> None:
    """v1: Добавить review_status и lawyer_comment (заменяет старый try/except паттерн)."""
    if _is_migration_applied(conn, 1):
        return
    # ALTER TABLE не работает внутри транзакции в SQLite.
    # Используем отдельные execute() для идемпотентности:
    for col, default in [("review_status", "'not_reviewed'"), ("lawyer_comment", "''")]:
        try:
            conn.execute(
                f"ALTER TABLE contracts ADD COLUMN {col} TEXT DEFAULT {default}"
            )
        except sqlite3.OperationalError:
            pass  # Колонка уже существует — безопасно
    conn.commit()
    _mark_migration_applied(conn, 1)


def _migrate_v2_lifecycle_columns(conn: sqlite3.Connection) -> None:
    """v2: Добавить manual_status и warning_days в contracts."""
    if _is_migration_applied(conn, 2):
        return
    for col, col_def in [
        ("manual_status", "TEXT DEFAULT NULL"),
        ("warning_days", "INTEGER DEFAULT NULL"),
    ]:
        try:
            conn.execute(f"ALTER TABLE contracts ADD COLUMN {col} {col_def}")
        except sqlite3.OperationalError:
            pass  # Колонка уже существует — безопасно
    conn.commit()
    _mark_migration_applied(conn, 2)


def _migrate_v3_embeddings(conn: sqlite3.Connection) -> None:
    """v3: Создать таблицу embeddings для семантического поиска."""
    if _is_migration_applied(conn, 3):
        return
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
                vector BLOB NOT NULL,
                model_version TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (contract_id)
            )
        """)
        conn.commit()
    except sqlite3.OperationalError:
        pass
    _mark_migration_applied(conn, 3)


def _migrate_v4_document_versions(conn: sqlite3.Connection) -> None:
    """v4: Создать таблицу document_versions для версионирования документов."""
    if _is_migration_applied(conn, 4):
        return
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS document_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_group_id INTEGER NOT NULL,
                contract_id INTEGER NOT NULL REFERENCES contracts(id),
                version_number INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                link_method TEXT NOT NULL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_versions_group ON document_versions(contract_group_id)"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass
    _mark_migration_applied(conn, 4)


def _migrate_v5_payments(conn: sqlite3.Connection) -> None:
    """v5: Создать таблицу payments для учёта платежей по договорам."""
    if _is_migration_applied(conn, 5):
        return
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
                payment_date TEXT NOT NULL,
                amount REAL NOT NULL,
                direction TEXT NOT NULL,
                is_periodic INTEGER DEFAULT 0,
                frequency TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(payment_date)"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass
    _mark_migration_applied(conn, 5)


def _migrate_v6_templates(conn: sqlite3.Connection) -> None:
    """v6: Создать таблицу templates для хранения шаблонов-эталонов."""
    if _is_migration_applied(conn, 6):
        return
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_type TEXT NOT NULL,
                name TEXT NOT NULL,
                original_path TEXT,
                content_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        """)
        conn.commit()
    except sqlite3.OperationalError:
        pass
    _mark_migration_applied(conn, 6)


def _migrate_v7_payment_columns(conn: sqlite3.Connection) -> None:
    """v7: Добавить платёжные поля в contracts."""
    if _is_migration_applied(conn, 7):
        return
    columns = [
        ("payment_terms", "TEXT"),
        ("payment_amount", "REAL"),
        ("payment_frequency", "TEXT"),
        ("payment_direction", "TEXT"),
    ]
    for col_name, col_type in columns:
        try:
            conn.execute(f"ALTER TABLE contracts ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            pass  # Column already exists
    conn.commit()
    _mark_migration_applied(conn, 7)


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """Проверяет существование таблицы в БД."""
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
    ).fetchone()
    return row is not None


def _run_migrations(db_path: Path, conn: sqlite3.Connection) -> None:
    """Запускает все ожидающие миграции по порядку.
    Вызывается из Database.__init__ после создания основной схемы.
    Для добавления новой миграции — добавить _migrate_vN_* функцию сюда.
    """
    # Backup только если БД уже содержит данные И ещё не версионирована
    needs_backup = (
        db_path.exists()
        and db_path.stat().st_size > 0
        and not _table_exists(conn, "schema_migrations")
    )
    _ensure_migrations_table(conn)
    if needs_backup:
        _backup_database(db_path)
    _migrate_v1_review_columns(conn)
    _migrate_v2_lifecycle_columns(conn)
    _migrate_v3_embeddings(conn)
    _migrate_v4_document_versions(conn)
    _migrate_v5_payments(conn)
    _migrate_v6_templates(conn)
    _migrate_v7_payment_columns(conn)


class Database:
    """CRUD-обёртка над SQLite для хранения результатов обработки."""

    def __init__(self, db_path: Path) -> None:
        """Создаёт/открывает БД. Автоматически создаёт таблицы если их нет."""
        self.db_path = db_path
        self._lock = threading.Lock()
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)

        _run_migrations(self.db_path, self.conn)

        # Создать индексы после миграций (безопасно для апгрейда с частичной схемой)
        for idx_sql in _INDEXES:
            try:
                self.conn.execute(idx_sql)
            except sqlite3.OperationalError as e:
                logger.warning("Не удалось создать индекс: %s", e)
        self.conn.commit()

        logger.info("БД открыта: %s", db_path)

    def is_processed(self, file_hash: str) -> bool:
        """True если файл с таким хешем уже обработан (status=done)."""
        cursor = self.conn.execute(
            "SELECT 1 FROM contracts WHERE file_hash = ? AND status = 'done'",
            (file_hash,),
        )
        return cursor.fetchone() is not None

    def save_result(self, result: ProcessingResult) -> None:
        """Сохраняет результат обработки. Upsert по file_hash. Thread-safe."""
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
            json.dumps(m.special_conditions or [], ensure_ascii=False) if m else None,
            json.dumps(m.parties or [], ensure_ascii=False) if m else None,
            m.confidence if m else None,
            v.status if v else None,
            json.dumps(v.warnings, ensure_ascii=False) if v else None,
            v.score if v else None,
            str(result.organized_path) if result.organized_path else None,
            result.model_used,
            m.payment_terms if m else None,
            m.payment_amount if m else None,
            m.payment_frequency if m else None,
            m.payment_direction if m else None,
        )

        with self._lock:
            self.conn.execute(
                """
                INSERT INTO contracts
                (original_path, filename, file_hash, status, error_message,
                 contract_type, counterparty, subject, date_signed, date_start, date_end,
                 amount, special_conditions, parties, confidence,
                 validation_status, validation_warnings, validation_score,
                 organized_path, model_used,
                 payment_terms, payment_amount, payment_frequency, payment_direction)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_hash) DO UPDATE SET
                  original_path = excluded.original_path,
                  filename = excluded.filename,
                  status = excluded.status,
                  error_message = excluded.error_message,
                  contract_type = excluded.contract_type,
                  counterparty = excluded.counterparty,
                  subject = excluded.subject,
                  date_signed = excluded.date_signed,
                  date_start = excluded.date_start,
                  date_end = excluded.date_end,
                  amount = excluded.amount,
                  special_conditions = excluded.special_conditions,
                  parties = excluded.parties,
                  confidence = excluded.confidence,
                  validation_status = excluded.validation_status,
                  validation_warnings = excluded.validation_warnings,
                  validation_score = excluded.validation_score,
                  organized_path = excluded.organized_path,
                  model_used = excluded.model_used,
                  payment_terms = excluded.payment_terms,
                  payment_amount = excluded.payment_amount,
                  payment_frequency = excluded.payment_frequency,
                  payment_direction = excluded.payment_direction,
                  processed_at = CURRENT_TIMESTAMP
                """,
                data,
            )
            self.conn.commit()
        logger.debug("Сохранён: %s (статус=%s)", result.file_info.filename, result.status)

    def get_contract_by_id(self, contract_id: int) -> dict | None:
        """Возвращает один контракт по ID с десериализованными JSON-полями."""
        with self._lock:
            row = self.conn.execute(
                "SELECT * FROM contracts WHERE id = ?", (contract_id,)
            ).fetchone()
        if row is None:
            return None
        d = dict(row)
        for field in ("special_conditions", "parties", "validation_warnings"):
            raw = d.get(field)
            if raw:
                try:
                    parsed = json.loads(raw)
                    d[field] = parsed if isinstance(parsed, list) else []
                except (json.JSONDecodeError, TypeError):
                    d[field] = []
            else:
                d[field] = []
        d.setdefault("review_status", "not_reviewed")
        d.setdefault("lawyer_comment", "")
        d.setdefault("manual_status", None)
        return d

    def get_contract_id_by_hash(self, file_hash: str) -> int | None:
        """Возвращает ID контракта по хешу файла."""
        with self._lock:
            row = self.conn.execute(
                "SELECT id FROM contracts WHERE file_hash = ?", (file_hash,)
            ).fetchone()
        return row[0] if row else None

    def get_all_results(self) -> list[dict]:
        """Возвращает все записи для генерации отчёта."""
        cursor = self.conn.execute(
            "SELECT * FROM contracts ORDER BY processed_at"
        )
        rows = cursor.fetchall()
        results = []
        for row in rows:
            d = dict(row)
            # Десериализация JSON-полей (null → [], строка → [строка])
            for field in ("special_conditions", "parties", "validation_warnings"):
                raw = d.get(field)
                if raw:
                    try:
                        parsed = json.loads(raw)
                        d[field] = parsed if isinstance(parsed, list) else []
                    except (json.JSONDecodeError, TypeError):
                        d[field] = []
                else:
                    d[field] = []
            # Гарантируем наличие полей v0.3
            d.setdefault("review_status", "not_reviewed")
            d.setdefault("lawyer_comment", "")
            results.append(d)
        return results

    def clear_all(self) -> None:
        """Удаляет все записи. Используется при принудительной переобработке."""
        with self._lock:
            self.conn.execute("DELETE FROM payments")
            self.conn.execute("DELETE FROM document_versions")
            self.conn.execute("DELETE FROM embeddings")
            self.conn.execute("DELETE FROM contracts")
            self.conn.commit()
        logger.info("БД очищена для переобработки")

    def update_review(self, file_hash: str, review_status: str, comment: str) -> None:
        """Обновляет пометку юриста для файла."""
        with self._lock:
            self.conn.execute(
                "UPDATE contracts SET review_status=?, lawyer_comment=? WHERE file_hash=?",
                (review_status, comment, file_hash),
            )
            self.conn.commit()
        logger.debug("Пометка обновлена: %s → %s", file_hash[:8], review_status)

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
