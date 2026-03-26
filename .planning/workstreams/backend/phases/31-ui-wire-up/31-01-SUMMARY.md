---
phase: 31-ui-wire-up
plan: "01"
subsystem: ui
tags: [action-bar, document, open-file, template, wiring]
dependency_graph:
  requires: []
  provides: [WIRE-01, WIRE-04]
  affects: [app/pages/document.py]
tech_stack:
  added: []
  patterns: [subprocess.Popen platform detection, run.io_bound async handler, inline lazy import]
key_files:
  created: []
  modified:
    - app/pages/document.py
decisions:
  - "Импорты platform/subprocess размещены внутри _open_file() чтобы ruff не блокировал на уровне модуля"
  - "mark_contract_as_template импортируется внутри _save_as_template() по той же причине"
metrics:
  duration_minutes: 5
  completed_date: "2026-03-26"
  tasks_completed: 2
  files_modified: 1
---

# Phase 31 Plan 01: UI Wire-up — Открыть файл + Сохранить как шаблон

**One-liner:** Две кнопки в action bar карточки документа: нативное открытие PDF/DOCX через subprocess и сохранение шаблона через mark_contract_as_template() с ui.notify.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Кнопка «Открыть файл» | 5c9c3fd | app/pages/document.py |
| 2 | Кнопка «Сохранить как шаблон» | 5c9c3fd | app/pages/document.py |

## What Was Built

**Task 1 — Открыть файл (WIRE-01):**
- Добавлена `async def _open_file()` внутри action bar
- platform.system() → subprocess.Popen(["open"]) на macOS, os.startfile на Windows, xdg-open на Linux
- Проверка: original_path пустой → ui.notify negative; файл не найден на диске → ui.notify negative
- Иконка `open_in_new`, стиль `flat dense no-caps` + ACTION_BTN

**Task 2 — Сохранить как шаблон (WIRE-04):**
- Добавлена `async def _save_as_template()` с disable/enable кнопки save_btn во время запроса
- mark_contract_as_template() вызывается через `await run.io_bound()`
- template_id is None → ui.notify negative; иначе → ui.notify positive
- try/except/finally — паттерн идентичен _reprocess

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] Lazy imports внутри функций вместо верхнего уровня**
- **Found during:** Task 1 — ruff-валидатор блокирует F401 (imported but unused) если импорт в верхней части файла не используется немедленно
- **Fix:** platform, subprocess, mark_contract_as_template импортируются внутри соответствующих async функций
- **Files modified:** app/pages/document.py
- **Commit:** 5c9c3fd

## Known Stubs

None — обе кнопки полностью подключены к backend.

## Self-Check: PASSED

- app/pages/document.py — существует, изменён
- python -c "import ast; ast.parse(...)" → OK
- grep subprocess.Popen → 2 строки (Darwin + Linux)
- grep open_in_new → 1 строка
- grep mark_contract_as_template → 1 строка (внутри функции)
- grep bookmark_add → 1 строка
- commit 5c9c3fd — подтверждён через git log
