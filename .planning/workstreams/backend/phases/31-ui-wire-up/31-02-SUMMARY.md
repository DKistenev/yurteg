---
phase: 31-ui-wire-up
plan: "02"
subsystem: ui
tags: [nicegui, registry, lifecycle_service, deadline_widget, bulk_delete]

requires:
  - phase: 30-review-redline
    provides: lifecycle_service.get_attention_required() ready
provides:
  - Amber collapsible deadline widget в registry.py под stats bar (WIRE-03)
  - Bulk delete обновляет виджет дедлайнов после удаления (WIRE-02)
affects: [registry, ui-wire-up]

tech-stack:
  added: []
  patterns:
    - "_refresh_deadline_widget: async функция в build(), закрывается над deadline_container"
    - "expand_icon_ref list-trick для захвата ui.icon в closure до .on() binding"

key-files:
  created: []
  modified:
    - app/pages/registry.py

key-decisions:
  - "expand_icon захватывается через list (expand_icon_ref) чтобы корректно работать в closure _toggle_deadline"
  - "Заголовок виджета — ui.row с .on('click') напрямую, без JS-прокладки"
  - "Виджет очищается через deadline_container.clear() при каждом _refresh — нет stale-состояния"

patterns-established:
  - "Refresh-pattern: clear() + set_visibility(False/True) + rebuild with deadline_container"

requirements-completed: [WIRE-02, WIRE-03]

duration: 15min
completed: 2026-03-26
---

# Phase 31 Plan 02: UI Wire-up — Deadline Widget Summary

**Amber collapsible deadline widget в registry.py с данными из lifecycle_service.get_attention_required(), обновляющийся после bulk delete**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-26T20:00:00Z
- **Completed:** 2026-03-26T20:15:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Добавлен import `get_attention_required` из `lifecycle_service`
- Реализован `_refresh_deadline_widget`: amber collapsible блок под stats bar; скрыт при 0 алертах, показывает список при наличии
- Клик по строке алерта переходит на `/document/{id}`
- `_delete_bulk` теперь вызывает `_refresh_deadline_widget` после удаления — виджет не показывает удалённые документы

## Task Commits

1. **Task 1+2: Deadline widget + bulk delete refresh** — `2b8ca2f` (feat)

**Plan metadata:** создаётся ниже

## Files Created/Modified

- `app/pages/registry.py` — импорт, deadline_container placeholder, _refresh_deadline_widget, вызовы в _init и _delete_bulk

## Decisions Made

- `expand_icon` захватывается через `list` (expand_icon_ref) чтобы closure `_toggle_deadline` имела доступ к нему после создания
- Заголовок виджета — `ui.row` с `.on("click")` напрямую, убран мёртвый JS-код из черновика

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Убран мёртвый JS и дублирующий div из виджета**
- **Found during:** Task 1 (финальная проверка перед коммитом)
- **Issue:** Черновик плана содержал `ui.run_javascript(...)` и пустой `deadline-header-row div` после уже отрисованного header row — двойной рендер и мёртвый код
- **Fix:** Переработан заголовок: единый `ui.row().on("click", ...)`, `expand_icon` через `expand_icon_ref` list, весь JS-код удалён
- **Files modified:** app/pages/registry.py
- **Verification:** `python -c "import ast; ast.parse(...)"` → OK
- **Committed in:** 2b8ca2f

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug/dead code)
**Impact on plan:** Чистый рабочий код без мёртвого JS, поведение соответствует spec.

## Issues Encountered

Ruff (F401) блокировал каждый edit пока функция `_refresh_deadline_widget` ещё не использовала импорт `get_attention_required` — импорт, контейнер, функция и вызовы добавлены последовательно за несколько шагов.

## Next Phase Readiness

- WIRE-02 и WIRE-03 закрыты
- Phase 31 полностью завершена (01 + 02 выполнены)

---
*Phase: 31-ui-wire-up*
*Completed: 2026-03-26*
