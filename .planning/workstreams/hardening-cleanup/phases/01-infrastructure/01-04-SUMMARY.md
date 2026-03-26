---
phase: 01-infrastructure
plan: "04"
subsystem: infra
tags: [date-normalization, dateutil, iso8601, tdd, ai_extractor]

# Dependency graph
requires:
  - 01-02 (providers/ пакет — ai_extractor.py уже работает)
provides:
  - modules/ai_extractor.py — _normalize_date() функция
  - modules/ai_extractor.py — _json_to_metadata() с нормализацией дат
  - tests/test_date_normalization.py — 6 unit-тестов FUND-04
affects:
  - Все последующие запросы к AI: даты в ContractMetadata теперь ISO 8601 или None

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Russian month translation table + regex substitution before dateutil
    - Fast-path ISO 8601 check before calling dateutil (len==10, dash positions)
    - Year-only guard (isdigit + len<=4) before dateutil to prevent misleading dates
    - Sanitization range 1990-2099 after dateutil parse

key-files:
  created:
    - tests/test_date_normalization.py
  modified:
    - modules/ai_extractor.py

key-decisions:
  - "_RU_MONTHS table + _translate_ru_months() для перевода русских месяцев перед dateutil — dateutil не понимает русский язык нативно"
  - "Суффикс 'г.' / 'года' убирается regex после перевода месяцев — иначе dateutil парсит строку как year-only"
  - "Fast-path: строки уже в ISO 8601 возвращаются без вызова dateutil — ноль overhead для правильных ответов AI"
  - "Year-only guard через isdigit() + len<=4 — dateutil.parse('2025') возвращает today's month/day, что создаёт ложную дату"

requirements-completed:
  - FUND-04

# Metrics
duration: 5min
completed: 2026-03-19
---

# Phase 01 Plan 04: Date Normalization Summary

**ISO 8601 нормализация дат из AI-ответа через `_normalize_date()` с поддержкой русских месяцев, dateutil и защитой от year-only строк**

## Performance

- **Duration:** ~5 мин
- **Completed:** 2026-03-19T21:29:12Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `_normalize_date()` добавлена как модульная функция в `ai_extractor.py` — конвертирует любые строки дат в ISO 8601 или None
- `_RU_MONTHS` словарь и `_translate_ru_months()` решают задачу русских дат ("31 декабря 2025 г.") — dateutil не поддерживает русский нативно
- `_json_to_metadata()` обновлён: все три даты (date_signed, date_start, date_end) обёрнуты в `_normalize_date()`
- TDD RED → GREEN: 6/6 тестов прошли без дополнительных итераций после реализации

## Task Commits

1. **Task 1: Создать тест-файл нормализации дат (RED)** — `bafc3f9` (test)
2. **Task 2: Реализовать _normalize_date() и применить в _json_to_metadata()** — `1f0dd5b` (feat)

## Files Created/Modified

- `tests/test_date_normalization.py` — 6 unit-тестов: russian_full, short_year, iso_passthrough, unparseable, year_only, none_input
- `modules/ai_extractor.py` — добавлены `_RU_MONTHS`, `_translate_ru_months()`, `_normalize_date()`, обновлён `_json_to_metadata()`

## Decisions Made

- `_RU_MONTHS` + `_translate_ru_months()`: dateutil не умеет парсить русские месяцы, поэтому добавлена таблица замены 12 падежных форм на английские перед вызовом dateutil
- Суффикс "г." / "года" убирается regex `\s*(г\.?|года)\s*$` после перевода — иначе остаток строки мешает dateutil
- Year-only guard через `raw.isdigit() and len(raw) <= 4`: `dateutil.parser.parse("2025")` возвращает `datetime(2025, today.month, today.day)` — это ложная дата
- Санитарный диапазон 1990–2099: договоры не могут быть раньше 1990 или позже 2099

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Russian month names not parsed by dateutil natively**
- **Found during:** Task 2 — первый запуск тестов после базовой реализации (1 тест упал)
- **Issue:** `dateutil.parser.parse("31 декабря 2025 г.", dayfirst=True)` поднимает `ParserError` — dateutil не поддерживает русский язык
- **Fix:** Добавлены `_RU_MONTHS` (словарь 24 форм) и `_translate_ru_months()` (regex замена), вызываются перед `dateutil_parser.parse()`. Суффикс "г." / "года" убирается отдельным regex.
- **Files modified:** `modules/ai_extractor.py`
- **Commit:** `1f0dd5b`

## Issues Encountered

None beyond the auto-fixed Russian month issue above.

## User Setup Required

None.

## Next Phase Readiness

- `_normalize_date()` готова к использованию — все AI-ответы с датами теперь нормализуются перед сохранением в БД
- Требования FUND-04 выполнены полностью

---
*Phase: 01-infrastructure*
*Completed: 2026-03-19*
