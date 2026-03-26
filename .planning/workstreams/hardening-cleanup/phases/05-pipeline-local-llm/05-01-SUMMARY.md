---
phase: 05-pipeline-local-llm
plan: 01
subsystem: pipeline, ai_extractor, ui
tags: [local-llm, sanitize, anonymizer, provider-switch]
dependency_graph:
  requires: [04-02]
  provides: [PROC-01, PROC-02, PROV-03]
  affects: [modules/ai_extractor.py, controller.py, main.py]
tech_stack:
  added: []
  patterns: [conditional-anonymize, json-file-persistence, sanitize-postprocess]
key_files:
  modified:
    - modules/ai_extractor.py
    - controller.py
    - main.py
decisions:
  - "sanitize_metadata вызывается только для ollama-провайдера — облачные провайдеры возвращают чистые ответы"
  - "Анонимизация пропускается через AnonymizedText(replacements={}) — интерфейс пайплайна не меняется"
  - "Persistence через ~/.yurteg/settings.json — переживает перезапуск приложения (D-08)"
  - "Глобальный config = Config() добавлен до sidebar — фикс NameError в Telegram-секции"
metrics:
  duration: 5min
  completed: 2026-03-21
  tasks_completed: 2
  files_modified: 3
---

# Phase 05 Plan 01: Pipeline Local LLM — Pipeline Integration Summary

**One-liner:** Post-processing ollama-ответов через sanitize_metadata, пропуск анонимизации для локального провайдера, UI-переключатель с JSON-persistence.

## What Was Built

Три изменения для end-to-end обработки через локальную LLM:

1. **ai_extractor.py** — sanitize_metadata вызывается после получения ответа от основной и fallback-модели, только при `active_provider == "ollama"`. Облачные провайдеры (zai/openrouter) не затрагиваются.

2. **controller.py** — в Этапе A анонимизация пропускается для ollama: создаётся `AnonymizedText(text=text.text, replacements={}, stats={})`. Де-анонимизация в Этапе B уже была защищена условием `if anonymized.replacements:` — без изменений.

3. **main.py** — добавлен глобальный `config = Config()` до sidebar (фикс предсуществующего NameError), expander "Провайдер" с selectbox из трёх вариантов, file-based persistence через `~/.yurteg/settings.json`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Глобальный config отсутствовал в sidebar**
- **Found during:** Task 2
- **Issue:** `config` использовался в Telegram-секции sidebar (line 706) без определения — NameError при любом rerun без нажатия кнопки обработки
- **Fix:** Добавлен `config = Config()` с восстановлением из settings.json перед `with st.sidebar:` блоком
- **Files modified:** main.py
- **Commit:** e4058e0

**2. [D-08 upgrade] Session_state → JSON-file persistence**
- **Found during:** Task 2 (objective header явно указывал file-based)
- **Issue:** План предлагал session_state, но D-08 и objective override требовали JSON-файл
- **Fix:** Реализована полная JSON-persistence через `~/.yurteg/settings.json` — переживает перезапуск приложения
- **Files modified:** main.py
- **Commit:** e4058e0

## Known Stubs

None — все данные реально читаются из config и сохраняются в файл.

## Requirements Closed

- PROV-03: UI-переключатель провайдера в sidebar
- PROC-01: sanitize_metadata вызывается в ai_extractor.py для ollama
- PROC-02: Анонимизация пропускается в controller.py для ollama

## Self-Check: PASSED

- FOUND: modules/ai_extractor.py
- FOUND: controller.py
- FOUND: main.py
- FOUND: 05-01-SUMMARY.md
- FOUND: commit d9950e5 (feat sanitize + skip anon)
- FOUND: commit e4058e0 (UI provider switch)
