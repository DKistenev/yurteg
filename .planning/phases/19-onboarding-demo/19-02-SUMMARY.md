---
phase: 19-onboarding-demo
plan: "02"
subsystem: onboarding
tags: [demo-data, empty-state, registry, templates, sqlite]
dependency_graph:
  requires: []
  provides: [app/demo_data.py, demo-button-registry, demo-card-templates]
  affects: [app/pages/registry.py, app/pages/templates.py]
tech_stack:
  added: []
  patterns: [insert_demo_contracts idempotent via md5 file_hash dedup]
key_files:
  created:
    - app/demo_data.py
  modified:
    - app/pages/registry.py
    - app/pages/templates.py
decisions:
  - "amount хранится как TEXT (не float sum_rub) — соответствует реальной схеме modules/database.py"
  - "is_latest_version колонки нет в схеме — убрана из INSERT, достаточно status='done'"
  - "Demo кнопка — flat/subtle стиль, не конкурирует с основным CTA «Выбрать папку»"
  - "navigate.to('/') после вставки — перезагружает страницу и сбрасывает empty state"
metrics:
  duration_minutes: 8
  completed_date: "2026-03-22"
  tasks_completed: 2
  files_changed: 3
---

# Phase 19 Plan 02: Demo Data + Demo Template Card Summary

**One-liner:** 10 pre-computed контрактов вставляются напрямую в SQLite через insert_demo_contracts() — без pipeline, без AI; пустой реестр получает кнопку «Загрузить тестовые данные», пустые шаблоны показывают greyed-out demo карточку.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Создать app/demo_data.py с 10 pre-computed контрактами | cd37880 | app/demo_data.py |
| 2 | Empty state — demo button в registry + demo карточка в templates | 6290664 | app/pages/registry.py, app/pages/templates.py |

## What Was Built

### app/demo_data.py
- `DEMO_CONTRACTS` — список 10 контрактов: 7 типов (поставка ×2, аренда ×2, услуги ×2, трудовой, подряд, лицензия, займ)
- Разные статусы: 2 контракта с `date_end` в пределах 30 дней (→ expiring), 2 истёкших, остальные активные
- Договор займа с `validation_score=0.65` → попадает в «требуют внимания»
- `insert_demo_contracts(db) → int` — идемпотентная (md5 dedup по filename), возвращает кол-во вставленных

### app/pages/registry.py
- Импорт `insert_demo_contracts` добавлен
- В `_render_empty_state`: под кнопкой «Выбрать папку» добавлена кнопка «Загрузить тестовые данные»
- flat/subtle стиль — не конкурирует с основным CTA
- `_on_load_demo()`: `run.io_bound(insert_demo_contracts, db)` → `ui.notify` → `ui.navigate.to("/")`

### app/pages/templates.py
- В `_render_cards` empty state: после CTA добавлена demo карточка
- `opacity:0.45 + pointer-events:none` — визуально greyed-out, не кликабельна
- Использует `TMPL_TYPE_COLORS["Договор аренды"]` — зелёный акцент, 4px color bar, badge, preview текст
- Метка «Пример — после добавления шаблона карточка будет настоящей»

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Убран несуществующий столбец is_latest_version из INSERT**
- **Found during:** Task 1 verification
- **Issue:** Схема `modules/database.py` не содержит колонку `is_latest_version` — план ссылался на устаревший интерфейс из старой спецификации
- **Fix:** Убрал `is_latest_version` из INSERT, оставил только реальные колонки схемы
- **Files modified:** app/demo_data.py
- **Commit:** cd37880

**2. [Rule 2 - Missing] Идемпотентность через md5 file_hash**
- **Found during:** Task 1
- **Issue:** Повторный вызов `insert_demo_contracts` не должен дублировать данные
- **Fix:** Реализована dedup-проверка через `md5(filename)` → `file_hash` unique check перед каждым INSERT
- **Files modified:** app/demo_data.py
- **Commit:** cd37880

## Known Stubs

None — demo данные полностью pre-computed, все поля реальные.

## Self-Check: PASSED

- [x] app/demo_data.py создан: `[ -f "app/demo_data.py" ]` → FOUND
- [x] insert_demo_contracts работает: 10 inserted, 0 on second call → VERIFIED
- [x] registry.py содержит "Загрузить тестовые данные" → line 110
- [x] templates.py содержит "Пример" → line 119, "opacity:0.45" → line 88
- [x] commit cd37880 (Task 1), commit 6290664 (Task 2) → FOUND
