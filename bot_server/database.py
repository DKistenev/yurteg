"""Server-side SQLite database for the Telegram bot.

Manages file queue, user bindings, pending binding codes, deadline sync,
and notification settings. Thread-safe via threading.Lock for all writes.
"""
import logging
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS file_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    mime_type TEXT,
    enqueued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fetched INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS bindings (
    chat_id INTEGER PRIMARY KEY,
    bound_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pending_bindings (
    code TEXT PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    expires_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS deadline_sync (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    contract_ref TEXT NOT NULL,
    counterparty TEXT,
    date_end TEXT,
    status TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notification_settings (
    chat_id INTEGER PRIMARY KEY,
    digest_enabled INTEGER DEFAULT 1,
    threshold_enabled INTEGER DEFAULT 1,
    warning_days INTEGER DEFAULT 30,
    digest_hour INTEGER DEFAULT 9
);
"""


class ServerDatabase:
    """Thread-safe SQLite backend for the Telegram bot server."""

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(db_path),
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        """Create all tables if they don't exist."""
        for statement in _SCHEMA.strip().split(";"):
            stmt = statement.strip()
            if stmt:
                self._conn.execute(stmt)
        self._conn.commit()
        logger.debug("ServerDatabase schema initialised")

    # ------------------------------------------------------------------
    # File queue
    # ------------------------------------------------------------------

    def enqueue_file(
        self,
        chat_id: int,
        file_path: str,
        filename: str,
        mime_type: str | None,
    ) -> int:
        """Insert a new file into the queue. Returns the new row id."""
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO file_queue (chat_id, file_path, filename, mime_type) "
                "VALUES (?, ?, ?, ?)",
                (chat_id, file_path, filename, mime_type),
            )
            self._conn.commit()
            return cur.lastrowid  # type: ignore[return-value]

    def fetch_queue(self, chat_id: int) -> list[dict]:
        """Return all un-fetched files for chat_id."""
        rows = self._conn.execute(
            "SELECT id, file_path, filename, mime_type, enqueued_at "
            "FROM file_queue WHERE chat_id = ? AND fetched = 0",
            (chat_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def mark_fetched(self, file_id: int) -> None:
        """Mark a queued file as fetched (consumed by local app)."""
        with self._lock:
            self._conn.execute(
                "UPDATE file_queue SET fetched = 1 WHERE id = ?", (file_id,)
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # Bindings
    # ------------------------------------------------------------------

    def get_binding(self, chat_id: int) -> dict | None:
        """Return binding record for chat_id, or None if not bound."""
        row = self._conn.execute(
            "SELECT chat_id, bound_at FROM bindings WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        return dict(row) if row else None

    def save_binding(self, chat_id: int) -> None:
        """Persist a confirmed binding for chat_id."""
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO bindings (chat_id, bound_at) VALUES (?, ?)",
                (chat_id, datetime.utcnow().isoformat()),
            )
            self._conn.commit()

    def get_all_bindings(self) -> list[dict]:
        """Return all confirmed bindings (used by scheduler to iterate users)."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT chat_id, bound_at FROM bindings"
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Pending bindings (one-time codes)
    # ------------------------------------------------------------------

    def save_pending_binding(
        self, chat_id: int, code: str, ttl_minutes: int
    ) -> None:
        """Store a pending binding code with expiry."""
        expires_at = (datetime.utcnow() + timedelta(minutes=ttl_minutes)).isoformat()
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO pending_bindings (code, chat_id, expires_at) "
                "VALUES (?, ?, ?)",
                (code, chat_id, expires_at),
            )
            self._conn.commit()

    def consume_pending_binding(self, code: str) -> dict | None:
        """
        Validate and consume a binding code in one atomic step.

        Returns {chat_id} if the code is valid and not expired, otherwise None.
        The code is deleted immediately to prevent re-use.
        """
        with self._lock:
            now = datetime.utcnow().isoformat()
            row = self._conn.execute(
                "SELECT chat_id FROM pending_bindings WHERE code = ? AND expires_at > ?",
                (code, now),
            ).fetchone()
            if row is None:
                return None
            result = dict(row)
            self._conn.execute(
                "DELETE FROM pending_bindings WHERE code = ?", (code,)
            )
            self._conn.commit()
            return result

    # ------------------------------------------------------------------
    # Deadline sync
    # ------------------------------------------------------------------

    def save_deadlines(self, chat_id: int, alerts: list[dict]) -> None:
        """Replace all deadline records for chat_id with the provided list."""
        with self._lock:
            self._conn.execute(
                "DELETE FROM deadline_sync WHERE chat_id = ?", (chat_id,)
            )
            now = datetime.utcnow().isoformat()
            for alert in alerts:
                self._conn.execute(
                    "INSERT INTO deadline_sync "
                    "(chat_id, contract_ref, counterparty, date_end, status, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        chat_id,
                        alert.get("contract_ref", ""),
                        alert.get("counterparty"),
                        alert.get("date_end"),
                        alert.get("status"),
                        now,
                    ),
                )
            self._conn.commit()

    def get_alerts_for_user(self, chat_id: int, warning_days: int) -> list[dict]:
        """Return deadline records expiring within warning_days from today."""
        cutoff = (datetime.utcnow() + timedelta(days=warning_days)).date().isoformat()
        today = datetime.utcnow().date().isoformat()
        rows = self._conn.execute(
            "SELECT contract_ref, counterparty, date_end, status "
            "FROM deadline_sync "
            "WHERE chat_id = ? AND date_end >= ? AND date_end <= ?",
            (chat_id, today, cutoff),
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Notification settings
    # ------------------------------------------------------------------

    def get_notification_settings(self, chat_id: int) -> dict:
        """Return notification settings for chat_id (returns defaults if not set)."""
        row = self._conn.execute(
            "SELECT chat_id, digest_enabled, threshold_enabled, warning_days, digest_hour "
            "FROM notification_settings WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()
        if row:
            return dict(row)
        return {
            "chat_id": chat_id,
            "digest_enabled": 1,
            "threshold_enabled": 1,
            "warning_days": 30,
            "digest_hour": 9,
        }

    def save_notification_settings(self, chat_id: int, settings: dict) -> None:
        """Persist notification settings for chat_id."""
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO notification_settings "
                "(chat_id, digest_enabled, threshold_enabled, warning_days, digest_hour) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    chat_id,
                    settings.get("digest_enabled", 1),
                    settings.get("threshold_enabled", 1),
                    settings.get("warning_days", 30),
                    settings.get("digest_hour", 9),
                ),
            )
            self._conn.commit()
