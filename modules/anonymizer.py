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

# --- Regex-паттерны для ПД ---
PATTERNS: dict[str, re.Pattern] = {
    "ТЕЛЕФОН": re.compile(
        r'(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}'
    ),
    "EMAIL": re.compile(
        r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
    ),
    # ПАСПОРТ обрабатывается отдельно через контекстный поиск (см. _extract_passport_matches)
    "СНИЛС": re.compile(
        r'\d{3}[\s\-]\d{3}[\s\-]\d{3}\s?\d{2}'
    ),
    "ИНН_ФЛ": re.compile(
        r'(?<!\d)\d{12}(?!\d)'  # 12 цифр подряд — ИНН физлица
    ),
    "СЧЁТ": re.compile(
        r'(?:р/?с|к/?с|расч[её]тный\s+сч[её]т|корр[.\s]*сч[её]т)[\s.:]*(\d{20})',
        re.IGNORECASE,
    ),
}


def anonymize(text: str) -> AnonymizedText:
    """
    Анонимизирует текст. Возвращает AnonymizedText с:
    - text: анонимизированный текст
    - replacements: словарь маска -> оригинал
    - stats: количество замен по типам

    Принцип: консервативный. Лучше заменить лишнее, чем пропустить ПД.
    Если одно и то же лицо упоминается N раз — все замены с одним номером.
    """
    # Шаг 1: Собрать все сущности (NER + regex)
    matches: list[tuple[int, int, str, str]] = []  # (start, stop, entity_type, text)

    # NER — ФИО
    ner_matches = _extract_ner_entities(text)
    matches.extend(ner_matches)

    # Regex — все паттерны
    regex_matches = _extract_regex_matches(text)
    matches.extend(regex_matches)

    # Паспорт — контекстный поиск (отдельно от общих regex)
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
    """Извлекает ФИО через Natasha NER."""
    doc = Doc(text)
    doc.segment(_segmenter)
    doc.tag_ner(_ner_tagger)

    entities: list[tuple[int, int, str, str]] = []
    for span in doc.spans:
        if span.type == "PER":
            entities.append((span.start, span.stop, "ФИО", span.text))

    return entities


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


def _extract_regex_matches(text: str) -> list[tuple[int, int, str, str]]:
    """Извлекает ПД через regex-паттерны."""
    matches: list[tuple[int, int, str, str]] = []

    for entity_type, pattern in PATTERNS.items():
        for m in pattern.finditer(text):
            if entity_type == "СЧЁТ":
                # Для счетов: группа 1 — сам номер счёта (20 цифр)
                if m.group(1):
                    matches.append((m.start(), m.end(), entity_type, m.group(0)))
            else:
                matches.append((m.start(), m.end(), entity_type, m.group(0)))

    return matches


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
