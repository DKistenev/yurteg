---
phase: 28-cleanup
plan: "01"
subsystem: backend/pipeline
tags: [cleanup, dead-code, validator, reporter]
dependency_graph:
  requires: []
  provides: [clean-controller, no-validator, no-reporter]
  affects: [controller.py, tests/test_controller.py]
tech_stack:
  added: []
  patterns: []
key_files:
  created: []
  modified:
    - controller.py
    - tests/test_controller.py
  deleted:
    - modules/validator.py
    - modules/reporter.py
    - tests/test_reporter.py
decisions:
  - "stress_test.py validator sections deferred — too large to scope-creep, logged in deferred-items.md"
metrics:
  duration_minutes: 25
  completed_date: "2026-03-25"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 5
---

# Phase 28 Plan 01: Cleanup — Удаление validator и reporter — Summary

**One-liner:** Удалены modules/validator.py (L1–L5 валидация) и modules/reporter.py (Excel reporter), controller.py работает без них, report_path всегда None.

## What Was Done

Удалена вся облачная наследственность: L1–L5 валидация метаданных и Excel-генератор реестра. Оба модуля были написаны под облачные модели — с GBNF-грамматикой Ollama они стали мёртвым кодом.

**Task 1 — validator.py:**
- Удалён `modules/validator.py` (~400 LOC)
- Из `controller.py` удалены: импорт `validate_batch`/`validate_metadata`/`verify_metadata`, блок «Валидация L1–L3», блок «AI-верификация L5», блок «Перекрёстная валидация L4»
- Обновлён docstring `_run_pipeline`
- `tests/test_controller.py` — убраны все патчи на validator, удалена неиспользуемая фикстура `sample_validation`, почищены неиспользуемые импорты

**Task 2 — reporter.py:**
- Удалён `modules/reporter.py` (~330 LOC)
- Удалён `tests/test_reporter.py`
- Из `controller.py` удалён импорт `generate_report`, блок «Генерация Excel-реестра» заменён на `report_path = None`
- Обновлён docstring `process_archive()` — явно указано что `report_path: None` с версии v0.9
- `tests/test_controller.py` — убраны все патчи на `generate_report`

## Deviations from Plan

### Auto-fixed Issues

None beyond the plan spec.

### Out-of-Scope Discoveries

**1. [Deferred] tests/stress_test.py — validator references**
- **Found during:** Task 2 final verification
- **Issue:** `tests/stress_test.py` (2345 LOC) содержит `TestValidatorStress` (lines 569–1042) и другие секции с прямыми импортами из удалённого `modules/validator.py`. При запуске `pytest tests/stress_test.py` будет ImportError.
- **Decision:** Не трогать в рамках этого плана — слишком большой scope creep. Файл не указан в `files_modified` плана.
- **Logged:** `.planning/workstreams/backend/phases/28-cleanup/deferred-items.md`

### Ruff Violations Fixed Inline (Rule 1)

Ruff hook заблокировал несколько промежуточных коммитов — все исправлено в рамках той же задачи:
- `verify_api_key`, `verify_metadata` — unused imports после удаления L5-блока
- `Path`, `call`, `datetime`, `AnonymizedText`, `ProcessingResult`, `ValidationResult` — unused imports в test_controller.py после очистки патчей

## Test Results

```
pytest tests/test_controller.py -x -q
6 passed, 8 warnings in 2.13s
```

## Known Stubs

None. `report_path = None` — это не стаб, это задокументированное поведение v0.9.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| modules/validator.py deleted | PASSED |
| modules/reporter.py deleted | PASSED |
| tests/test_reporter.py deleted | PASSED |
| controller imports clean | PASSED |
| commit e7c698a exists | PASSED |
| commit 0e0c8bf exists | PASSED |
