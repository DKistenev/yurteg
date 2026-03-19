---
phase: 01-infrastructure
plan: "02"
subsystem: infra
tags: [openai-sdk, abc, providers, zai, openrouter, ollama, glm, config]

# Dependency graph
requires: []
provides:
  - providers/base.py — LLMProvider ABC с методами complete() и verify_key()
  - providers/zai.py — ZAIProvider с extra_body thinking:disabled
  - providers/openrouter.py — OpenRouterProvider с _merge_system_into_user
  - providers/ollama.py — OllamaProvider stub (Веха 3)
  - providers/__init__.py — get_provider() и get_fallback_provider() фабрики
  - config.py — поля active_provider и fallback_provider
affects:
  - 01-03 (ai_extractor.py refactoring — перейдёт на get_provider() вместо _create_client())
  - 01-04 (controller — будет использовать providers через ai_extractor)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Factory function get_provider(config) по строке active_provider
    - ABC с abstractmethod для контракта провайдера
    - extra_body ZAI-специфичный параметр изолирован в ZAIProvider
    - _merge_system_into_user изолирован в openrouter.py

key-files:
  created:
    - providers/__init__.py
    - providers/base.py
    - providers/zai.py
    - providers/openrouter.py
    - providers/ollama.py
    - tests/test_providers.py
  modified:
    - config.py

key-decisions:
  - "extra_body thinking:disabled изолирован только в ZAIProvider — не утекает в base/openrouter"
  - "OllamaProvider — stub с NotImplementedError, реализация в Вехе 3"
  - "get_fallback_provider возвращает None для неизвестных значений (не поднимает ValueError)"
  - "ai_extractor.py в этом плане не тронут — переход на providers/ в плане 01-03"

patterns-established:
  - "Provider pattern: LLMProvider ABC → конкретный провайдер → фабрика get_provider(config)"
  - "Config-driven routing: переключение провайдера через active_provider строку без изменения кода"

requirements-completed:
  - FUND-03

# Metrics
duration: 2min
completed: 2026-03-19
---

# Phase 01 Plan 02: LLM Provider Abstraction Summary

**providers/ пакет с ZAI/OpenRouter/Ollama-провайдерами и фабрикой get_provider(config) — переключение через одну строку конфига**

## Performance

- **Duration:** ~2 мин
- **Started:** 2026-03-19T21:22:32Z
- **Completed:** 2026-03-19T21:24:21Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- LLMProvider ABC определяет контракт для всех провайдеров: complete() и verify_key()
- ZAIProvider изолирует GLM-специфичный extra_body (thinking:disabled), OpenRouterProvider содержит _merge_system_into_user для бесплатных моделей
- Фабрика get_provider(config) маршрутизирует по строке active_provider, ValueError при неизвестном значении
- 6/6 тестов TDD прошли (RED → GREEN) без дополнительных правок

## Task Commits

1. **Task 1: Создать тест-файл для провайдеров** — `7ebea41` (test)
2. **Task 2: Создать providers/ пакет и расширить config.py** — `5690e02` (feat)

## Files Created/Modified

- `providers/base.py` — LLMProvider ABC с complete() и verify_key()
- `providers/zai.py` — ZAIProvider, extra_body thinking:disabled только здесь
- `providers/openrouter.py` — OpenRouterProvider + _merge_system_into_user
- `providers/ollama.py` — OllamaProvider stub (NotImplementedError)
- `providers/__init__.py` — get_provider() и get_fallback_provider() фабрики
- `config.py` — добавлены поля active_provider="zai" и fallback_provider="openrouter"
- `tests/test_providers.py` — 6 unit-тестов (фабрика, thinking, merge, stub)

## Decisions Made

- extra_body с thinking:disabled изолирован строго в ZAIProvider — при переключении на OpenRouter не утекает
- OllamaProvider оставлен как stub с NotImplementedError — реализация в Вехе 3 (дообученная QWEN)
- get_fallback_provider возвращает None для неизвестного fallback_provider (не поднимает ValueError, в отличие от get_provider)
- ai_extractor.py намеренно не затронут — он продолжает работать через _create_client(), миграция в плане 01-03

## Deviations from Plan

None — план выполнен точно как описан.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- providers/ пакет готов для использования в плане 01-03 (рефакторинг ai_extractor.py)
- ai_extractor.py продолжает работать через старый _create_client() до плана 01-03

---
*Phase: 01-infrastructure*
*Completed: 2026-03-19*
