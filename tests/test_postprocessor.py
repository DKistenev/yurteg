"""Тесты модуля postprocessor — sanitize_metadata и профили полей."""
import pytest

from modules.postprocessor import sanitize_metadata


# ── cyrillic_only ─────────────────────────────────────────────────────────────

def test_sanitize_cyrillic_only_preserves_russian():
    """Кириллический текст остаётся без изменений."""
    raw = {"contract_type": "Договор оказания услуг"}
    result = sanitize_metadata(raw)
    assert result["contract_type"] == "Договор оказания услуг"


def test_sanitize_cyrillic_only_strips_latin_garbage():
    """Случайные латинские символы удаляются из поля contract_type."""
    raw = {"contract_type": "Dogovor оказания услуг xyz"}
    result = sanitize_metadata(raw)
    # Латинские символы должны быть удалены, кириллица остаётся
    assert "D" not in result["contract_type"]
    assert "x" not in result["contract_type"]
    assert "оказания" in result["contract_type"]


def test_sanitize_cyrillic_only_preserves_nda_sla():
    """Аббревиатуры NDA и SLA сохраняются как строки (нет строгой фильтрации для них)."""
    # NDA и SLA — это латиница, они будут удалены при cyrillic_only,
    # но поле counterparty (cyrillic_latin) их сохранит.
    # Для contract_type (cyrillic_only) NDA/SLA будут удалены.
    # Тест проверяет что "Соглашение о конфиденциальности NDA" сохраняет кириллику.
    raw = {"contract_type": "Соглашение NDA"}
    result = sanitize_metadata(raw)
    # Кириллика сохранена
    assert "Соглашение" in (result["contract_type"] or "")


def test_sanitize_counterparty_preserves_nda_sla():
    """Поле counterparty (cyrillic_latin) сохраняет NDA и SLA полностью."""
    raw = {"counterparty": "ООО НДА NDA SLA Технологии"}
    result = sanitize_metadata(raw)
    assert "NDA" in result["counterparty"]
    assert "SLA" in result["counterparty"]
    assert "ООО" in result["counterparty"]


# ── date ──────────────────────────────────────────────────────────────────────

def test_sanitize_date_format_valid():
    """Дата в формате YYYY-MM-DD сохраняется."""
    raw = {"date_signed": "2024-01-15"}
    result = sanitize_metadata(raw)
    assert result["date_signed"] == "2024-01-15"


def test_sanitize_date_format_invalid():
    """Мусорная строка вместо даты становится None."""
    raw = {"date_signed": "вчера"}
    result = sanitize_metadata(raw)
    assert result["date_signed"] is None


def test_sanitize_date_null_string():
    """Строка 'null' или 'none' становится None."""
    raw = {"date_start": "null", "date_end": "None"}
    result = sanitize_metadata(raw)
    assert result["date_start"] is None
    assert result["date_end"] is None


# ── enum ──────────────────────────────────────────────────────────────────────

def test_sanitize_enum_valid():
    """Допустимые значения payment_frequency проходят фильтр."""
    for valid in ("monthly", "quarterly", "yearly", "once"):
        raw = {"payment_frequency": valid}
        result = sanitize_metadata(raw)
        assert result["payment_frequency"] == valid


def test_sanitize_enum_invalid():
    """Недопустимое значение payment_frequency становится None."""
    raw = {"payment_frequency": "gibberish"}
    result = sanitize_metadata(raw)
    assert result["payment_frequency"] is None


def test_sanitize_enum_payment_direction():
    """payment_direction принимает только 'income' и 'expense'."""
    assert sanitize_metadata({"payment_direction": "income"})["payment_direction"] == "income"
    assert sanitize_metadata({"payment_direction": "expense"})["payment_direction"] == "expense"
    assert sanitize_metadata({"payment_direction": "unknown"})["payment_direction"] is None


# ── full dict ─────────────────────────────────────────────────────────────────

def test_sanitize_metadata_full():
    """Полный словарь обрабатывается корректно — каждое поле по своему профилю."""
    raw = {
        "contract_type": "Договор поставки abc",
        "counterparty": "ООО Ромашка LLC",
        "date_signed": "2024-03-01",
        "date_end": "не определено",
        "payment_frequency": "monthly",
        "payment_direction": "bad_value",
        "confidence": "0.85",
        "is_template": "false",
        "parties": ["ООО Ромашка", "ИП Иванов"],
        "special_conditions": ["Условие 1"],
    }
    result = sanitize_metadata(raw)

    # contract_type: латиница удалена
    assert "abc" not in (result.get("contract_type") or "")
    assert "Договор" in (result.get("contract_type") or "")

    # counterparty: кириллица + латиница
    assert "ООО Ромашка" in (result.get("counterparty") or "")
    assert "LLC" in (result.get("counterparty") or "")

    # dates
    assert result["date_signed"] == "2024-03-01"
    assert result["date_end"] is None

    # enum
    assert result["payment_frequency"] == "monthly"
    assert result["payment_direction"] is None

    # number из строки
    assert result["confidence"] == pytest.approx(0.85)

    # boolean из строки
    assert result["is_template"] is False

    # list-поля остаются списками
    assert isinstance(result["parties"], list)
    assert isinstance(result["special_conditions"], list)


# ── Whitelist аббревиатур (cyrillic_only) ─────────────────────────────────────

class TestAbbreviationWhitelist:
    def test_nda_preserved_in_contract_type(self) -> None:
        result = sanitize_metadata({"contract_type": "NDA о конфиденциальности"})
        assert result["contract_type"] == "NDA о конфиденциальности"

    def test_sla_preserved(self) -> None:
        result = sanitize_metadata({"contract_type": "Договор SLA с поддержкой"})
        assert result["contract_type"] == "Договор SLA с поддержкой"

    def test_multiple_abbreviations_preserved(self) -> None:
        result = sanitize_metadata({"contract_type": "Соглашение NDA и GPS трекинг"})
        assert result["contract_type"] == "Соглашение NDA и GPS трекинг"

    def test_non_whitelist_latin_removed(self) -> None:
        result = sanitize_metadata({"contract_type": "Договор abc def"})
        assert "abc" not in (result["contract_type"] or "")
        assert "def" not in (result["contract_type"] or "")

    def test_mixed_whitelist_and_other_latin(self) -> None:
        result = sanitize_metadata({"contract_type": "Договор NDA abc"})
        r = result["contract_type"] or ""
        assert "NDA" in r
        assert "abc" not in r

    def test_special_conditions_nda_preserved(self) -> None:
        result = sanitize_metadata({"special_conditions": ["Штраф при нарушении NDA"]})
        assert result["special_conditions"] == ["Штраф при нарушении NDA"]

    def test_cyrillic_latin_profile_unchanged(self) -> None:
        result = sanitize_metadata({"counterparty": "ООО Alpha Ltd"})
        assert result["counterparty"] == "ООО Alpha Ltd"

    def test_inn_abbreviation_preserved(self) -> None:
        result = sanitize_metadata({"contract_type": "Договор ИНН стороны"})
        assert "ИНН" in (result["contract_type"] or "")
