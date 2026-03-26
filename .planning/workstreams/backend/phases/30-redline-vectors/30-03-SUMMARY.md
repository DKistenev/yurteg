---
phase: 30-redline-vectors
plan: "03"
subsystem: services
tags: [redline, version-service, review-service, refactor]
dependency_graph:
  requires: [30-01]
  provides: [unified-redline-engine-wired]
  affects: [services/version_service.py, services/review_service.py, modules/database.py]
tech_stack:
  added: []
  patterns: [re-export, delegation, sqlite-migration]
key_files:
  modified:
    - services/version_service.py
    - services/review_service.py
    - modules/database.py
decisions:
  - "generate_redline_docx в version_service — re-export из redline_service (noqa: F401)"
  - "Миграция v9 добавляет full_text в contracts (было отсутствие колонки)"
  - "ContractMetadata перенесён в TYPE_CHECKING блок (F821 fix)"
metrics:
  duration_minutes: 12
  completed_date: "2026-03-26"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 3
---

# Phase 30 Plan 03: Wire Redline Engine Summary

**One-liner:** Переключить version_service и review_service на единый word-level redline движок из redline_service — старый sentence-level код удалён, добавлен get_redline_for_template.

## What Was Done

### Task 1: Заменить generate_redline_docx в version_service делегированием
- Удалено ~75 строк sentence-level реализации `generate_redline_docx` из `version_service.py`
- Добавлен re-export: `from services.redline_service import generate_redline_docx  # noqa: F401`
- `review_service` продолжает импортировать из `version_service` без изменений (re-export прозрачен)
- Commit: `7574c0c`

### Task 2: Добавить get_redline_for_template в review_service.py
- Добавлен прямой импорт `generate_redline_docx` из `services.redline_service`
- Реализована функция `get_redline_for_template(db, contract_id, template_id) -> Optional[bytes]`
- Функция читает тексты из БД (`contracts.full_text`, `templates.content_text`) и возвращает DOCX с track changes
- Commit: `0623854`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Миграция v9: добавить full_text в contracts**
- **Found during:** Task 2 verification
- **Issue:** `contracts` таблица не содержала колонку `full_text` — `get_redline_for_template` упал с `OperationalError`
- **Fix:** Добавлена миграция `_migrate_v9_full_text` в `modules/database.py`
- **Files modified:** `modules/database.py`
- **Commit:** `0623854`

**2. [Rule 1 - Bug] ContractMetadata F821 в version_service**
- **Found during:** Task 1 (ruff validator)
- **Issue:** `ContractMetadata` использовался как строковый тип-хинт в параметрах `diff_versions`, но импортировался только внутри тела функции — ruff F821
- **Fix:** Добавлен `TYPE_CHECKING` блок с `from modules.models import ContractMetadata`
- **Files modified:** `services/version_service.py`
- **Commit:** `7574c0c`

## Verification Results

```
OK: version_service.generate_redline_docx === redline_service.generate_redline_docx
OK: get_redline_for_template возвращает валидный DOCX с track changes
14 passed (test_redline_service, test_versioning, test_service_layer, test_migrations)
```

## Known Stubs

None — оба use case производят реальный DOCX с `w:del`/`w:ins`.

## Self-Check: PASSED

- `services/version_service.py` — существует, не содержит `def generate_redline_docx`
- `services/review_service.py` — содержит `def get_redline_for_template`
- `modules/database.py` — содержит `_migrate_v9_full_text`
- Commits: `7574c0c`, `0623854` — оба присутствуют в git log
