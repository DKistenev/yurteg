"""Тесты нормализации дат из AI-ответа (FUND-04).

_normalize_date() конвертирует произвольные строки дат в ISO 8601 (YYYY-MM-DD).
Возвращает None для неразбираемых строк и year-only значений.
"""
import pytest

# _normalize_date будет добавлена в ai_extractor.py
from modules.ai_extractor import _normalize_date


def test_russian_full():
    """Полная русская дата нормализуется в ISO 8601."""
    result = _normalize_date("31 декабря 2025 г.")
    assert result == "2025-12-31", f"Ожидалось '2025-12-31', получено {result!r}"


def test_short_year():
    """Дата с двузначным годом нормализуется корректно."""
    result = _normalize_date("31.12.25")
    assert result == "2025-12-31", f"Ожидалось '2025-12-31', получено {result!r}"


def test_iso_passthrough():
    """Дата уже в ISO 8601 проходит fast-path и возвращается без изменений."""
    result = _normalize_date("2025-12-31")
    assert result == "2025-12-31", f"Ожидалось '2025-12-31', получено {result!r}"


def test_unparseable():
    """Неразбираемая строка возвращает None, не поднимает исключение."""
    result = _normalize_date("бессрочный")
    assert result is None, f"Ожидался None, получено {result!r}"


def test_year_only_returns_none():
    """Строка из одного года возвращает None (dateutil даёт misleading результат)."""
    result = _normalize_date("2025")
    assert result is None, (
        f"Ожидался None для year-only строки '2025', получено {result!r}. "
        "dateutil.parser.parse('2025') = datetime(2025, current_month, current_day) — это неверно."
    )


def test_none_input():
    """None на входе возвращает None."""
    result = _normalize_date(None)
    assert result is None, f"Ожидался None для None-входа, получено {result!r}"
