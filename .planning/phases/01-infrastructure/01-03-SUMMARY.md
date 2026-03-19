---
phase: 01-infrastructure
plan: "03"
subsystem: infra
tags: [services, pipeline, facade, separation-of-concerns, tdd]

# Dependency graph
requires:
  - phase: 01-02
    provides: providers/base.py — LLMProvider ABC для type-hint в extract_metadata()
provides:
  - services/__init__.py — пакет сервис-слоя без Streamlit-зависимостей
  - services/pipeline_service.py — process_archive() facade для UI, Telegram-бота, CLI
  - services/registry_service.py — get_all_contracts() и generate_report() facades
  - modules/ai_extractor.py — extract_metadata() с provider/fallback_provider параметрами
affects:
  - 01-04 (controller рефакторинг — provider уже принимается в extract_metadata)
  - Phase 3 (Telegram-бот вызывает pipeline_service.process_archive напрямую)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Service layer pattern: бизнес-логика в services/ без зависимости от Streamlit
    - Facade pattern: pipeline_service оборачивает Controller — одна точка входа

key-files:
  created:
    - services/__init__.py
    - services/pipeline_service.py
    - services/registry_service.py
    - tests/test_service_layer.py
  modified:
    - modules/ai_extractor.py
    - main.py

key-decisions:
  - "services/ не импортирует streamlit — Telegram-бот и CLI могут вызывать pipeline_service без UI"
  - "extract_metadata() принимает provider/fallback_provider с None-дефолтами — обратная совместимость сохранена до Phase 2"
  - "main.py импортирует Controller через from controller import Controller, но вызывает только через pipeline_service — изоляция на один уровень"

patterns-established:
  - "Service facade: UI вызывает services.pipeline_service.process_archive(), не Controller напрямую"
  - "TYPE_CHECKING guard: LLMProvider используется только для type hints, не создаёт runtime-зависимость"

requirements-completed:
  - FUND-02

# Metrics
duration: 5min
completed: 2026-03-20
---

# Phase 01 Plan 03: Service Layer Summary

**services/ пакет (pipeline_service, registry_service) без Streamlit-зависимостей — Telegram-бот и CLI вызывают process_archive() напрямую, минуя UI**

## Performance

- **Duration:** ~5 мин
- **Started:** 2026-03-20T00:00:00Z
- **Completed:** 2026-03-20T00:05:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- services/pipeline_service.py — единая точка входа process_archive() без единой строки streamlit
- services/registry_service.py — facades для работы с реестром договоров из любого контекста
- extract_metadata() расширена provider/fallback_provider параметрами с обратной совместимостью
- main.py переключён с прямого вызова Controller на pipeline_service.process_archive()
- 3/3 TDD-тестов GREEN (RED → GREEN цикл)

## Task Commits

1. **Task 1: Тест-файл сервис-слоя (RED)** — `09588b4` (test)
2. **Task 2: services/ пакет + рефакторинг ai_extractor + обновление main.py** — `097369c` (feat)

## Files Created/Modified

- `services/__init__.py` — пустой пакет-маркер с docstring
- `services/pipeline_service.py` — process_archive() facade, NO import streamlit
- `services/registry_service.py` — get_all_contracts() и generate_report() facades
- `modules/ai_extractor.py` — добавлены provider и fallback_provider параметры с TYPE_CHECKING guard
- `main.py` — вызов переключён на pipeline_service.process_archive(), добавлен импорт
- `tests/test_service_layer.py` — 3 unit-теста сервис-слоя

## Decisions Made

- provider/fallback_provider добавлены с None-дефолтами — существующий код controller.py не требует изменений, полный wire-up в Phase 2
- TYPE_CHECKING guard для LLMProvider импорта — нет runtime-зависимости от providers/, только type hints
- Импорт `from controller import Controller` оставлен в main.py — он нужен controller.py транзитивно через pipeline_service

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Исправлен тест test_no_streamlit_import — ложное срабатывание на комментарий**
- **Found during:** Task 2 (запуск тестов)
- **Issue:** Тест искал слово `'streamlit'` в исходном коде, но комментарий `# NO import streamlit` содержит это слово — тест падал на собственной документации файла
- **Fix:** Заменил строковый поиск на regex `r'^\s*(import streamlit|from streamlit)'` — ищет только реальные импорты
- **Files modified:** tests/test_service_layer.py
- **Verification:** 3/3 тестов GREEN
- **Committed in:** `097369c` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in test assertion)
**Impact on plan:** Минимальный — исправление строки в тесте, смысл проверки не изменился.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- services/ пакет готов для Phase 3 (Telegram-бот вызывает pipeline_service.process_archive напрямую)
- extract_metadata() принимает LLMProvider параметр — план 01-04 может провести полный wire-up providers/ → controller → ai_extractor

---
*Phase: 01-infrastructure*
*Completed: 2026-03-20*
