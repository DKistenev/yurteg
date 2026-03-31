"""Centralized logging configuration — local file + optional BetterStack Logtail.

Local: RotatingFileHandler → ~/.yurteg/logs/yurteg.log (5 MB, 3 backups)
Remote: BetterStack Logtail with machine_id context (INFO+, no document content)
"""

import logging
import logging.handlers
import os
import uuid
from pathlib import Path

from config import APP_VERSION

_LOG_DIR = Path.home() / ".yurteg" / "logs"
_LOG_FILE = _LOG_DIR / "yurteg.log"
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# Modules that may log document content at DEBUG level
_SENSITIVE_MODULES = {"modules.text_extractor", "modules.anonymizer"}


class _ContentFilter(logging.Filter):
    """Reject DEBUG records from sensitive modules to prevent document content leaking to remote logs.

    Rules:
    - WARNING/ERROR/CRITICAL — always accept
    - INFO — always accept
    - DEBUG from sensitive modules — reject (may contain document text)
    - DEBUG with very long messages (>500 chars) — reject
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno >= logging.WARNING:
            return True
        if record.levelno >= logging.INFO:
            return True
        # DEBUG level checks
        if record.name in _SENSITIVE_MODULES:
            return False
        # Check for suspiciously long messages (likely document content)
        msg = str(record.msg)
        if len(msg) > 500:
            return False
        if record.args:
            for arg in (record.args if isinstance(record.args, (list, tuple)) else [record.args]):
                if isinstance(arg, str) and len(arg) > 500:
                    return False
        return True


def setup_logging() -> None:
    """Configure root logger with local file handler and optional BetterStack handler."""
    root = logging.getLogger()

    # Prevent duplicate handlers on repeated calls
    if root.handlers:
        return

    root.setLevel(logging.DEBUG)

    # ── 1. Local file handler ─────────────────────────────────────────────────
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    file_handler = logging.handlers.RotatingFileHandler(
        filename=str(_LOG_FILE),
        maxBytes=5_242_880,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(file_handler)

    # ── 2. BetterStack Logtail handler (remote) ──────────────────────────────
    _DEFAULT_TOKEN = "yFQhG2XsqXgdvnwazhVB8rgK"
    token = os.environ.get("BETTERSTACK_SOURCE_TOKEN", "")
    if not token:
        from config import load_settings
        token = load_settings().get("betterstack_token", "") or _DEFAULT_TOKEN

    if not token:
        logging.getLogger(__name__).warning(
            "BETTERSTACK_SOURCE_TOKEN не задан — удалённое логирование отключено"
        )
        return

    try:
        from logtail import LogtailHandler

        machine_id = format(uuid.getnode(), "x")
        logtail_handler = LogtailHandler(
            source_token=token,
            context={
                "machine_id": machine_id,
                "app_version": APP_VERSION,
            },
        )
        logtail_handler.setLevel(logging.INFO)
        logtail_handler.addFilter(_ContentFilter())
        root.addHandler(logtail_handler)
    except ImportError:
        logging.getLogger(__name__).warning(
            "logtail-python не установлен — удалённое логирование отключено"
        )
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "BetterStack handler не удалось создать: %s", exc
        )
