"""Модуль анонимизации персональных данных.

Заменяет ФИО, телефоны, email, паспорта, СНИЛС, ИНН физлиц и банковские
реквизиты на типизированные маски. Сохраняет названия организаций, даты, суммы.
"""
import logging
import re
from typing import Optional

from natasha import (
    Segmenter, MorphVocab, NewsEmbedding, NewsNERTagger, NamesExtractor, Doc
)

from modules.models import AnonymizedText

logger = logging.getLogger(__name__)

# --- Natasha NER (загружаются один раз при импорте модуля) ---
_segmenter = Segmenter()
_morph_vocab = MorphVocab()
_emb = NewsEmbedding()
_ner_tagger = NewsNERTagger(_emb)
_names_extractor = NamesExtractor(_morph_vocab)

# --- Доступные типы ПД для UI ---
ENTITY_TYPES = {
    "ФИО": "Фамилия, имя, отчество",
    "ТЕЛЕФОН": "Номера телефонов",
    "EMAIL": "Электронная почта",
    "ПАСПОРТ": "Серия и номер паспорта",
    "СНИЛС": "Номер СНИЛС",
    "ИНН": "ИНН физлиц и юрлиц",
    "ОГРН": "ОГРН организаций",
    "КПП": "КПП организаций",
    "СЧЁТ": "Банковские счета",
}

# Маппинг внутренних типов → ключи UI (для фильтрации)
_TYPE_TO_UI_KEY = {
    "ФИО": "ФИО",
    "ТЕЛЕФОН": "ТЕЛЕФОН",
    "EMAIL": "EMAIL",
    "ПАСПОРТ": "ПАСПОРТ",
    "СНИЛС": "СНИЛС",
    "ИНН_ФЛ": "ИНН",
    "ИНН_ЮЛ": "ИНН",
    "ОГРН": "ОГРН",
    "КПП": "КПП",
    "ИП": "ФИО",  # ИП содержит ФИО
    "СЧЁТ": "СЧЁТ",
}

# --- Regex-паттерны для ПД ---
PATTERNS: dict[str, re.Pattern] = {
    "ТЕЛЕФОН": re.compile(
        r'(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}'
    ),
    "EMAIL": re.compile(
        r'[a-zA-Z0-9а-яА-ЯёЁ._%+\-]+@[a-zA-Z0-9а-яА-ЯёЁ.\-]+\.[a-zA-ZА-Яа-яёЁ]{2,}',
        re.UNICODE,
    ),
    # ПАСПОРТ обрабатывается отдельно через контекстный поиск (см. _extract_passport_matches)
    "СНИЛС": re.compile(
        r'\d{3}[\s\-]\d{3}[\s\-]\d{3}\s?\d{2}'
    ),
    "ИНН_ФЛ": re.compile(
        r'(?<!\d)\d{12}(?!\d)'  # 12 цифр подряд — ИНН физлица
    ),
    "ИНН_ЮЛ": re.compile(
        r'(?:ИНН|инн)\s*:?\s*(\d{10})(?!\d)',  # 10 цифр только с контекстом "ИНН"
        re.IGNORECASE,
    ),
    "ОГРН": re.compile(
        r'(?:ОГРН|огрн)\s*:?\s*(\d{13})(?!\d)',  # 13 цифр с контекстом "ОГРН"
        re.IGNORECASE,
    ),
    "КПП": re.compile(
        r'(?:КПП|кпп)\s*:?\s*(\d{9})(?!\d)',  # 9 цифр с контекстом "КПП"
        re.IGNORECASE,
    ),
    "ИП": re.compile(
        r'ИП\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){0,2}(?:\s+[А-ЯЁ]\.?\s*[А-ЯЁ]\.?)?',
        re.UNICODE,
    ),
    "СЧЁТ": re.compile(
        r'(?:р/?с|к/?с|расч[её]тный\s+сч[её]т|корр[.\s]*сч[её]т|(?:на\s+)?сч[её]т)[\s.:]*(\d{20})',
        re.IGNORECASE,
    ),
}


def anonymize(text: str, enabled_types: Optional[set[str]] = None) -> AnonymizedText:
    """
    Анонимизирует текст. Возвращает AnonymizedText с:
    - text: анонимизированный текст
    - replacements: словарь маска -> оригинал
    - stats: количество замен по типам

    Args:
        text: исходный текст
        enabled_types: какие типы ПД маскировать (None = все).
            Ключи из ENTITY_TYPES: {"ФИО", "ТЕЛЕФОН", "EMAIL", ...}

    Принцип: консервативный. Лучше заменить лишнее, чем пропустить ПД.
    Если одно и то же лицо упоминается N раз — все замены с одним номером.
    """
    # Шаг 1: Собрать все сущности (NER + regex)
    matches: list[tuple[int, int, str, str]] = []  # (start, stop, entity_type, text)

    # NER — ФИО (кириллица)
    if _is_type_enabled("ФИО", enabled_types):
        ner_matches = _extract_ner_entities(text)
        matches.extend(ner_matches)

        # Латинские имена в контексте (Natasha их не ловит)
        latin_matches = _extract_latin_names(text)
        matches.extend(latin_matches)

    # Regex — все паттерны (фильтруем по enabled_types)
    regex_matches = _extract_regex_matches(text, enabled_types)
    matches.extend(regex_matches)

    # Паспорт — контекстный поиск (отдельно от общих regex)
    if _is_type_enabled("ПАСПОРТ", enabled_types):
        passport_matches = _extract_passport_matches(text)
        matches.extend(passport_matches)

    # Шаг 2: Убрать перекрытия (приоритет: более длинные совпадения)
    matches = _remove_overlaps(matches)

    # Шаг 3: Заменить в тексте (с конца, чтобы индексы не сдвигались)
    matches.sort(key=lambda m: m[0], reverse=True)

    replacements: dict[str, str] = {}
    counters: dict[str, int] = {}
    seen_values: dict[str, str] = {}  # нормализованный текст -> маска
    stats: dict[str, int] = {}

    result_text = text
    for start, stop, entity_type, original in matches:
        # Нормализуем для сравнения (убираем лишние пробелы)
        normalized = " ".join(original.split()).lower()
        type_key = entity_type

        # Проверяем, встречалось ли уже это значение
        lookup_key = f"{type_key}:{normalized}"
        if lookup_key in seen_values:
            mask = seen_values[lookup_key]
        else:
            counters[type_key] = counters.get(type_key, 0) + 1
            mask = f"[{type_key}_{counters[type_key]}]"
            seen_values[lookup_key] = mask
            replacements[mask] = original

        # Считаем статистику (все вхождения, включая повторы)
        stats[type_key] = stats.get(type_key, 0) + 1

        # Заменяем в тексте
        result_text = result_text[:start] + mask + result_text[stop:]

    return AnonymizedText(
        text=result_text,
        replacements=replacements,
        stats=stats,
    )


def _extract_ner_entities(text: str) -> list[tuple[int, int, str, str]]:
    """Извлекает ФИО через Natasha NER.

    Включает трёхпроходную стратегию:
    1. Первый проход — по оригинальному тексту.
    2. Второй проход — по нормализованному тексту (точки перед метками).
    3. Третий проход — по тексту со склеенными побуквенными словами (OCR).

    Результаты объединяются с приоритетом первого прохода.
    """
    # --- Первый проход: оригинальный текст ---
    entities = _ner_pass(text)

    # --- Второй проход: нормализованный текст ---
    normalized = _normalize_for_ner(text)
    if normalized != text:
        entities_pass2 = _ner_pass(normalized)
        occupied = set()
        for start, stop, _, _ in entities:
            for pos in range(start, stop):
                occupied.add(pos)
        for start, stop, etype, etext in entities_pass2:
            if not any(pos in occupied for pos in range(start, stop)):
                entities.append((start, stop, etype, etext))

    # --- Третий проход: склейка побуквенных OCR-слов ---
    ocr_entities = _extract_ocr_spaced_names(text)
    if ocr_entities:
        occupied = set()
        for start, stop, _, _ in entities:
            for pos in range(start, stop):
                occupied.add(pos)
        for start, stop, etype, etext in ocr_entities:
            if not any(pos in occupied for pos in range(start, stop)):
                entities.append((start, stop, etype, etext))

    return entities


# Метки полей, после которых Natasha теряет ФИО
_STRUCTURAL_LABELS = (
    "Телефон", "Тел", "Email", "E-mail", "Почта",
    "Паспорт", "СНИЛС", "ИНН", "ОГРН", "КПП",
    "Счёт", "Счет", "Реквизиты", "Должность",
    "Адрес", "Подпись", "Дата", "Факс", "Моб",
    "р/с", "к/с", "БИК",
)

_LABEL_PATTERN = re.compile(
    r'([^\n.!?])(\n(?:' + '|'.join(re.escape(l) for l in _STRUCTURAL_LABELS) + r')[\s:])',
    re.IGNORECASE,
)


def _normalize_for_ner(text: str) -> str:
    """Вставляет точку перед \\n{Метка}: чтобы помочь NER-сегментации."""
    return _LABEL_PATTERN.sub(r'\1.\2', text)


# Regex для побуквенных OCR-слов: 3+ кириллических букв через пробелы
_OCR_SPACED_WORD = re.compile(
    r'(?<![а-яёА-ЯЁ])([А-ЯЁа-яё](?:\s[А-ЯЁа-яё]){2,})(?![а-яёА-ЯЁ])',
)


def _extract_ocr_spaced_names(text: str) -> list[tuple[int, int, str, str]]:
    """Находит побуквенные OCR-слова и пробует NER по склеенному тексту.

    Пример: 'И в а н о в  И в а н' → склеиваем → 'Иванов Иван' → NER.
    Позиции возвращаются для ОРИГИНАЛЬНОГО текста.
    """
    # Найти все побуквенные последовательности
    spaced_regions = list(_OCR_SPACED_WORD.finditer(text))
    if not spaced_regions:
        return []

    # Собрать непрерывный регион с побуквенными словами
    # (могут быть несколько слов подряд: 'И в а н о в  И в а н  И в а н о в и ч')
    entities: list[tuple[int, int, str, str]] = []

    # Группируем близкие матчи (расстояние < 5 символов)
    groups: list[list[re.Match]] = []
    current_group: list[re.Match] = []
    for m in spaced_regions:
        if current_group and m.start() - current_group[-1].end() > 4:
            groups.append(current_group)
            current_group = [m]
        else:
            current_group.append(m)
    if current_group:
        groups.append(current_group)

    for group in groups:
        region_start = group[0].start()
        region_end = group[-1].end()
        region_text = text[region_start:region_end]

        # Склеить: убрать пробелы внутри каждого побуквенного слова,
        # сохранить двойные пробелы как разделители слов
        collapsed = re.sub(r'(?<=[А-ЯЁа-яё])\s(?=[А-ЯЁа-яё](?:\s[А-ЯЁа-яё]|$|[^а-яёА-ЯЁ]))', '', region_text)
        # Если ещё остались одиночные пробелы между буквами — убрать тоже
        collapsed = re.sub(r'(?<=[А-ЯЁа-яё])\s(?=[А-ЯЁа-яё])', '', collapsed)

        # Прогоняем NER по склеенному тексту
        ner_result = _ner_pass(collapsed)
        if ner_result:
            # Если NER нашёл ФИО — маскируем весь оригинальный регион
            entities.append((region_start, region_end, "ФИО", region_text))

    return entities


def _ner_pass(text: str) -> list[tuple[int, int, str, str]]:
    """Один проход NER по тексту."""
    doc = Doc(text)
    doc.segment(_segmenter)
    doc.tag_ner(_ner_tagger)

    entities: list[tuple[int, int, str, str]] = []
    for span in doc.spans:
        if span.type == "PER":
            entities.append((span.start, span.stop, "ФИО", span.text))

    return entities


# Regex для латинских имён (Имя Фамилия) в контексте
_LATIN_NAME_CONTEXT = re.compile(
    r'(?:представитель|гражданин\w*|директор|менеджер|г-н|г-жа|mr\.?|mrs\.?|ms\.?'
    r'|лицо|контрагент|агент|партн[её]р|исполнитель|заказчик)[\s:,]+',
    re.IGNORECASE,
)
_LATIN_NAME = re.compile(
    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
)


def _extract_latin_names(text: str) -> list[tuple[int, int, str, str]]:
    """Извлекает латинские имена (John Smith) в контексте указания лица."""
    matches: list[tuple[int, int, str, str]] = []
    for ctx in _LATIN_NAME_CONTEXT.finditer(text):
        # Ищем латинское имя сразу после контекстного слова
        search_start = ctx.end()
        search_end = min(len(text), search_start + 60)
        region = text[search_start:search_end]
        m = _LATIN_NAME.match(region)
        if m:
            abs_start = search_start + m.start()
            abs_end = search_start + m.end()
            matches.append((abs_start, abs_end, "ФИО", m.group(1)))
    return matches


def _extract_passport_matches(text: str) -> list[tuple[int, int, str, str]]:
    """
    Извлекает паспортные данные через контекстный поиск.

    Проблема: паспорт — это просто цифры (например, 4515 123456),
    которые легко спутать с другими числами. Поэтому вместо глобального
    regex ищем числовые паттерны ТОЛЬКО рядом с контекстными словами.

    Алгоритм:
    1. Находим все контекстные слова (паспорт, серия, выдан и т.д.)
    2. В окрестности ±200 символов от каждого слова ищем числовой паттерн
    3. Паттерн: 2-4 цифры (серия) + разделитель + 6 цифр (номер)
       Также: просто 10 цифр подряд (серия+номер слитно)
    """
    # Исключения: "паспорт" в техническом контексте (не персональный документ)
    false_passport_pattern = re.compile(
        r'(?:технический|кадастровый|ветеринарный|санитарный|энергетический'
        r'|сертификат|качеств\w+)\s+паспорт',
        re.IGNORECASE,
    )

    # Контекстные слова, указывающие на паспортные данные
    context_pattern = re.compile(
        r'(?:паспорт(?:ные\s+данные)?|серия\s+(?:и\s+)?(?:номер|№|н\.?)'
        r'|документ[,\s]+удостоверяющ\w+\s+личность'
        r'|выдан\w*\s+(?:\d|отдел|управлен|[А-ЯЁ])'
        r'|удостоверение\s+личности)',
        re.IGNORECASE,
    )

    # Числовые паттерны паспорта (ищем только в контексте)
    number_patterns = [
        # серия 4515 номер 123456 / серия 4515 № 123456
        re.compile(
            r'(?:серия\s*)?(\d{2}\s?\d{2})\s*(?:номер|№|н\.?)?\s*(\d{6})',
            re.IGNORECASE,
        ),
        # 4515 123456 (4 цифры + пробел + 6 цифр)
        re.compile(r'(\d{4})\s+(\d{6})'),
        # 45 15 123456 (2+2+6 через пробелы)
        re.compile(r'(\d{2}\s\d{2})\s+(\d{6})'),
        # 4515123456 (10 цифр подряд, но не часть более длинного числа)
        re.compile(r'(?<!\d)(\d{4})(\d{6})(?!\d)'),
    ]

    matches: list[tuple[int, int, str, str]] = []
    found_ranges: list[tuple[int, int]] = []  # чтобы не дублировать

    # Шаг 1: Найти все контекстные слова
    for ctx_match in context_pattern.finditer(text):
        # Баг #13: пропускаем ложные контексты (технический паспорт и т.п.)
        # Проверяем в широком окне ±200 символов от контекстного матча
        fp_start = max(0, ctx_match.start() - 200)
        fp_end = min(len(text), ctx_match.end() + 200)
        fp_region = text[fp_start:fp_end]
        if false_passport_pattern.search(fp_region):
            continue

        # Окрестность ±200 символов от контекстного слова
        search_start = max(0, ctx_match.start() - 200)
        search_end = min(len(text), ctx_match.end() + 200)
        search_region = text[search_start:search_end]

        # Шаг 2: В окрестности искать числовые паттерны
        for num_pat in number_patterns:
            for num_match in num_pat.finditer(search_region):
                # Пересчитать позиции в исходном тексте
                abs_start = search_start + num_match.start()
                abs_end = search_start + num_match.end()

                # Проверка: не дублируем ли уже найденный диапазон
                already_found = False
                for fs, fe in found_ranges:
                    if abs_start < fe and abs_end > fs:
                        already_found = True
                        break

                if not already_found:
                    # Проверка: не является ли это ИНН, ОГРН, КПП и т.д.
                    # Смотрим 20 символов перед найденным числом
                    prefix_start = max(0, abs_start - 20)
                    prefix = text[prefix_start:abs_start].lower().strip()
                    skip_prefixes = ("инн", "огрн", "кпп", "бик", "р/с", "к/с",
                                     "расчётный", "расчетный", "корр")
                    if any(prefix.endswith(p) for p in skip_prefixes):
                        continue

                    original = text[abs_start:abs_end]
                    matches.append((abs_start, abs_end, "ПАСПОРТ", original))
                    found_ranges.append((abs_start, abs_end))

    return matches


def _is_type_enabled(entity_type: str, enabled_types: Optional[set[str]]) -> bool:
    """Проверяет, включён ли данный тип ПД для маскировки."""
    if enabled_types is None:
        return True  # None = маскировать всё
    ui_key = _TYPE_TO_UI_KEY.get(entity_type, entity_type)
    return ui_key in enabled_types


def _extract_regex_matches(text: str, enabled_types: Optional[set[str]] = None) -> list[tuple[int, int, str, str]]:
    """Извлекает ПД через regex-паттерны."""
    matches: list[tuple[int, int, str, str]] = []

    # Паттерны с группами: маскируем весь match, но проверяем наличие группы 1
    _group_patterns = {"СЧЁТ", "ИНН_ЮЛ", "ОГРН", "КПП"}

    # Нормализованный текст для поиска телефонов (кириллические цифры → ASCII)
    normalized_text = _normalize_cyrillic_digits(text)

    for entity_type, pattern in PATTERNS.items():
        # Пропускаем отключённые типы
        if not _is_type_enabled(entity_type, enabled_types):
            continue
        # Для телефонов ищем по нормализованному тексту (кириллическая О→0 и т.д.)
        search_text = normalized_text if entity_type == "ТЕЛЕФОН" else text

        for m in pattern.finditer(search_text):
            if entity_type in _group_patterns:
                if m.lastindex and m.group(1):
                    matches.append((m.start(), m.end(), entity_type, text[m.start():m.end()]))
            elif entity_type == "СНИЛС":
                if _validate_snils_match(text, m):
                    matches.append((m.start(), m.end(), entity_type, text[m.start():m.end()]))
            elif entity_type == "ТЕЛЕФОН":
                if not _is_inside_bank_account(text, m):
                    # Используем оригинальный текст для значения маски
                    matches.append((m.start(), m.end(), entity_type, text[m.start():m.end()]))
            elif entity_type == "ИНН_ФЛ":
                if not _is_monetary_context(text, m):
                    matches.append((m.start(), m.end(), entity_type, m.group(0)))
            else:
                matches.append((m.start(), m.end(), entity_type, m.group(0)))

    return matches


# Таблица замен кириллических символов, похожих на цифры
_CYRILLIC_DIGIT_MAP = str.maketrans({
    'О': '0', 'о': '0',  # кириллическая О → 0
    'З': '3', 'з': '3',  # кириллическая З → 3
    'Ч': '4',             # кириллическая Ч → 4 (визуально)
    'Б': '6',             # кириллическая Б → 6 (визуально)
})


def _normalize_cyrillic_digits(text: str) -> str:
    """Заменяет кириллические символы, похожие на цифры, для regex-поиска."""
    return text.translate(_CYRILLIC_DIGIT_MAP)


def _validate_snils_match(text: str, match: re.Match) -> bool:
    """Проверяет, является ли совпадение настоящим СНИЛС (контекст или чексумма)."""
    # Извлекаем только цифры
    digits_only = re.sub(r'\D', '', match.group(0))
    if len(digits_only) != 11:
        return False

    # Контрольная сумма СНИЛС
    digits = [int(d) for d in digits_only]
    checksum = sum(d * (9 - i) for i, d in enumerate(digits[:9]))
    if checksum > 101:
        checksum = checksum % 101
    if checksum in (100, 101):
        checksum = 0
    if checksum == digits[9] * 10 + digits[10]:
        return True

    # Если чексумма не совпала — ищем контекстное слово рядом
    prefix_start = max(0, match.start() - 50)
    prefix = text[prefix_start:match.start()].lower()
    context_words = ("снилс", "страхов", "пенсион", "свидетельств")
    return any(w in prefix for w in context_words)


def _is_monetary_context(text: str, match: re.Match) -> bool:
    """Проверяет, не является ли 12-цифровая последовательность суммой (а не ИНН)."""
    # Смотрим 40 символов до и 20 после
    prefix_start = max(0, match.start() - 40)
    prefix = text[prefix_start:match.start()].lower()
    suffix_end = min(len(text), match.end() + 20)
    suffix = text[match.end():suffix_end].lower()

    money_words = (
        "стоимост", "сумм", "цен", "оплат", "платёж", "платеж",
        "составляет", "равн", "итого", "всего", "бюджет",
    )
    currency_words = (
        "руб", "рос", "коп", "usd", "eur", "долл", "евро",
        "тыс", "млн", "млрд", "₽", "$", "€",
    )
    if any(w in prefix for w in money_words):
        return True
    if any(w in suffix for w in currency_words):
        return True
    return False


def _is_inside_bank_account(text: str, match: re.Match) -> bool:
    """Проверяет, не является ли телефонный матч частью банковского счёта (20 цифр)."""
    # Расширяем окрестность и проверяем, есть ли 20+ цифр подряд
    start = max(0, match.start() - 5)
    end = min(len(text), match.end() + 10)
    region = text[start:end]
    # Убираем пробелы и дефисы, проверяем на длинные числовые последовательности
    digits_only = re.sub(r'[\s\-()]', '', region)
    if re.search(r'\d{15,}', digits_only):
        return True
    # Проверяем контекст банковского счёта
    prefix_start = max(0, match.start() - 30)
    prefix = text[prefix_start:match.start()].lower()
    bank_words = ("р/с", "к/с", "расч", "корр", "счёт", "счет", "лицев")
    return any(w in prefix for w in bank_words)


def _remove_overlaps(
    matches: list[tuple[int, int, str, str]],
) -> list[tuple[int, int, str, str]]:
    """Убирает перекрывающиеся совпадения. Приоритет: более длинные."""
    # Сортируем по длине (длинные первые), потом по позиции
    matches.sort(key=lambda m: (-(m[1] - m[0]), m[0]))

    result: list[tuple[int, int, str, str]] = []
    occupied: list[tuple[int, int]] = []

    for start, stop, etype, etext in matches:
        # Проверяем, не перекрывается ли с уже принятыми
        overlaps = False
        for ostart, ostop in occupied:
            if start < ostop and stop > ostart:
                overlaps = True
                break
        if not overlaps:
            result.append((start, stop, etype, etext))
            occupied.append((start, stop))

    return result
