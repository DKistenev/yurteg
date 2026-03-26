"""Post-processing ответов локальной модели (llama-server).

Каждое поле ContractMetadata имеет свой профиль допустимых символов.
Санитайзер применяется после получения JSON-ответа от llama-server,
до передачи данных в валидатор и БД.
"""
import re
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Профили полей ─────────────────────────────────────────────────────────────

FIELD_PROFILES: dict[str, str] = {
    # Только кириллица + пробелы + пунктуация (латиница удаляется)
    "contract_type":        "cyrillic_only",
    "special_conditions":   "cyrillic_only",
    # Кириллица + латиница + цифры + пробелы + пунктуация
    "counterparty":         "cyrillic_latin",
    "parties":              "cyrillic_latin",
    "subject":              "cyrillic_latin",
    "amount":               "cyrillic_latin",
    "payment_terms":        "cyrillic_latin",
    # Строго из допустимого набора значений
    "payment_frequency":    "enum",
    "payment_direction":    "enum",
    # Формат YYYY-MM-DD или None
    "date_signed":          "date",
    "date_start":           "date",
    "date_end":             "date",
    # Числовое значение
    "confidence":           "number",
    "payment_amount":       "number",
    # Булево значение
    "is_template":          "boolean",
}

ENUM_VALUES: dict[str, set[str]] = {
    "payment_frequency": {"monthly", "quarterly", "yearly", "once"},
    "payment_direction": {"income", "expense"},
}

# ── Регулярные выражения для профилей ────────────────────────────────────────

# Только кириллица + цифры + пробелы + базовая пунктуация (без латиницы)
_RE_CYRILLIC_ONLY = re.compile(
    r"[^\u0400-\u04FF\u0451\u0401\s\d.,;:!?()«»\"\u2014\u2013\-/№%₽]"
)

# Кириллица + латиница + цифры + пробелы + расширенная пунктуация
_RE_CYRILLIC_LATIN = re.compile(
    r"[^\u0400-\u04FF\u0451\u0401a-zA-Z\s\d.,;:!?()«»\"\u2014\u2013\-/№%₽€$&@]"
)

# Дата YYYY-MM-DD
_RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Пустые/нулевые строки
_NULL_STRINGS = frozenset({"none", "null", "", "н/д", "н.д.", "отсутствует", "нет данных"})

# Аббревиатуры, которые НЕ удаляются из cyrillic_only полей
# Источник: CONTEXT.md Phase 29 — юридически важные сокращения
ABBREVIATION_WHITELIST: tuple[str, ...] = (
    "NDA", "SLA", "GPS",
    "ИНН", "МРОТ", "НДС", "ООО", "ИП", "ЗАО", "ОАО",
)


def _protect_abbreviations(value: str) -> tuple[str, dict[str, str]]:
    """Заменяет аббревиатуры из whitelist на placeholder-ы перед regex.

    Placeholder использует только символы из _RE_CYRILLIC_ONLY allowlist
    (цифры + «»), чтобы пережить фильтрацию без искажений.

    Returns:
        (protected_value, {placeholder: original_abbr})
    """
    placeholders: dict[str, str] = {}
    for i, abbr in enumerate(ABBREVIATION_WHITELIST):
        pattern = re.compile(r"(?<![A-Za-zА-Яа-яЁё])" + re.escape(abbr) + r"(?![A-Za-zА-Яа-яЁё])")
        placeholder = f"«{i}»"
        if pattern.search(value):
            value = pattern.sub(placeholder, value)
            placeholders[placeholder] = abbr
    return value, placeholders


def _restore_abbreviations(value: str, placeholders: dict[str, str]) -> str:
    """Восстанавливает аббревиатуры из placeholder-ов."""
    for placeholder, abbr in placeholders.items():
        value = value.replace(placeholder, abbr)
    return value


# ── Санитайзер ────────────────────────────────────────────────────────────────

def _to_none_if_empty(value: Any) -> Any:
    """Приводит строковые «null»-эквиваленты к Python None."""
    if isinstance(value, str) and value.strip().lower() in _NULL_STRINGS:
        return None
    return value


def _sanitize_string(value: str, profile: str, field: str) -> Optional[str]:
    """Применяет профиль очистки к строке."""
    value = value.strip()
    if not value:
        return None

    if profile == "cyrillic_only":
        # Защищаем аббревиатуры из whitelist перед regex
        protected, placeholders = _protect_abbreviations(value)
        cleaned = _RE_CYRILLIC_ONLY.sub("", protected).strip()
        # Восстанавливаем аббревиатуры
        if placeholders:
            cleaned = _restore_abbreviations(cleaned, placeholders)
            # Убираем двойные пробелы после удаления не-whitelist латиницы
            cleaned = re.sub(r" {2,}", " ", cleaned).strip()
        return cleaned if cleaned else None

    if profile == "cyrillic_latin":
        cleaned = _RE_CYRILLIC_LATIN.sub("", value).strip()
        return cleaned if cleaned else None

    if profile == "enum":
        allowed = ENUM_VALUES.get(field, set())
        return value if value in allowed else None

    if profile == "date":
        if _RE_DATE.match(value):
            return value
        logger.debug("Невалидная дата в поле %s: %r", field, value)
        return None

    # Для остальных профилей (number, boolean) — обработка отдельно
    return value


def _sanitize_value(value: Any, profile: str, field: str) -> Any:
    """Применяет профиль к значению любого типа."""
    # Нормализация null-значений
    value = _to_none_if_empty(value)
    if value is None:
        return None

    if profile == "number":
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.strip().replace(",", ".").replace(" ", ""))
            except (ValueError, AttributeError):
                logger.debug("Не удалось преобразовать в число поле %s: %r", field, value)
                return None
        return None

    if profile == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in ("true", "1", "да", "yes")
        return bool(value)

    if isinstance(value, str):
        return _sanitize_string(value, profile, field)

    # Для list-полей — обработка элементов
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, str):
                cleaned = _sanitize_string(item, profile, field)
                if cleaned is not None:
                    result.append(cleaned)
            elif item is not None:
                result.append(item)
        return result

    return value


def sanitize_metadata(raw: dict) -> dict:
    """Очищает сырой dict ответа локальной модели по профилям полей.

    - Нормализует строки "None", "null", "" → None
    - Для list-полей (parties, special_conditions) — профиль применяется к каждому элементу
    - Строки очищаются по профилю допустимых символов
    - Невалидные enum-значения → None
    - Невалидные даты → None
    - Числовые строки → float
    - Булевы строки → bool

    Args:
        raw: Сырой dict из JSON-ответа модели.

    Returns:
        Очищенный dict, готовый для передачи в ContractMetadata.
    """
    result: dict = {}

    # Обрабатываем все известные поля по профилям
    for field, profile in FIELD_PROFILES.items():
        if field not in raw:
            continue
        value = raw[field]
        result[field] = _sanitize_value(value, profile, field)

    # Копируем поля без профиля (если вдруг есть) без изменений
    for field, value in raw.items():
        if field not in FIELD_PROFILES:
            result[field] = _to_none_if_empty(value)

    # Гарантируем что list-поля — всегда list, не None
    for list_field in ("parties", "special_conditions"):
        if list_field in result and result[list_field] is None:
            result[list_field] = []

    return result


def get_grammar_path() -> Path:
    """Возвращает абсолютный путь к файлу GBNF грамматики.

    Returns:
        Path к data/contract.gbnf относительно корня проекта.
    """
    return Path(__file__).parent.parent / "data" / "contract.gbnf"
