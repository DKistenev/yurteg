"""Shared UI utilities — date formatting, common helpers.

Single source of truth for _MONTHS_RU and _format_date_ru.
Per CLAUDE.md: strftime("%d %b") outputs English — use manual month arrays.
"""
from datetime import date as _date

_MONTHS_RU = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]

_MONTHS_RU_SHORT = [
    "", "янв", "фев", "мар", "апр", "мая", "июн",
    "июл", "авг", "сен", "окт", "ноя", "дек",
]


def format_date_ru(val: str | None, *, short: bool = False) -> str:
    """Format ISO date (2025-09-01) to Russian date string.

    Args:
        val: ISO date string or None.
        short: If True, use abbreviated months ('1 сен 2025').
               If False, use full months ('1 сентября 2025').

    Returns:
        Formatted date string, or '\u2014' on failure.
    """
    if not val or val == "\u2014":
        return "\u2014"
    try:
        d = _date.fromisoformat(str(val))
        months = _MONTHS_RU_SHORT if short else _MONTHS_RU
        return f"{d.day} {months[d.month]} {d.year}"
    except (ValueError, IndexError):
        return str(val)
