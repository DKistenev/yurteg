---
phase: 02-document-lifecycle
plan: 02
subsystem: ui
tags: [streamlit, lifecycle, status, manual-override, attention-panel]

# Dependency graph
requires:
  - phase: 02-document-lifecycle
    plan: 01
    provides: lifecycle_service (get_computed_status_sql, set_manual_status, clear_manual_status, get_attention_required, STATUS_LABELS)
provides:
  - Панель «требует внимания» в main.py — показывается при наличии истекающих/истёкших договоров
  - Колонка «Статус» (✔/⚠/✗/↻/...) в таблице реестра с вычисляемым статусом
  - Секция ручной коррекции статуса (terminated/extended/negotiation/suspended/авто-сброс)
  - Selectbox порога предупреждений (30/60/90 дней) в сайдбаре
affects:
  - 02-03 (payments UI использует тот же main.py)
  - 02-04 (templates UI использует тот же main.py)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lifecycle UI: открывать Database(db_path) как контекстный менеджер при каждом lifecycle-запросе — не хранить db между рендерами"
    - "computed_status загружается SQL CASE через get_computed_status_sql при открытии вкладки Реестр, мержится в df по id"
    - "st.rerun() после set_manual_status/clear_manual_status — немедленное обновление таблицы"

key-files:
  created: []
  modified:
    - main.py

key-decisions:
  - "computed_status вычисляется отдельным SQL-запросом в начале tab_registry (не через get_all_results) — чистое разделение ответственности"
  - "db открывается новым контекстным менеджером для каждого lifecycle-вызова — безопасно при Streamlit reruns"
  - "Секция ручного override показывается только если df_filtered непустой и есть колонка id"

patterns-established:
  - "Attention panel: get_attention_required → if alerts → st.expander (expanded=True) — скрывается автоматически при отсутствии проблем"
  - "Status column: STATUS_LABELS[computed_status][0] + ' ' + STATUS_LABELS[computed_status][1] — иконка + текст в одной ячейке"

requirements-completed: [LIFE-02, LIFE-05, LIFE-06]

# Metrics
duration: 2min
completed: 2026-03-19
---

# Phase 2 Plan 02: UI Lifecycle Controls Summary

**Streamlit UI с панелью «требует внимания», колонкой статуса (✔/⚠/✗/↻) и ручным override статуса договора (terminated/extended/negotiation/suspended)**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-19T22:25:35Z
- **Completed:** 2026-03-19T22:27:34Z
- **Tasks:** 2 (+ checkpoint:human-verify)
- **Files modified:** 1

## Accomplishments
- Импорт lifecycle_service в main.py — весь UI-код использует единый сервисный слой
- Sidebar: selectbox «Предупреждать о сроках за» (30/60/90 дней) с сохранением в session_state
- Панель «требует внимания» перед вкладками — список истекающих/истёкших договоров с иконками и текстом дней
- Колонка «Статус» в таблице реестра — computed_status через SQL CASE, отображается иконка + метка
- Секция ручного override: выбор договора + статуса + кнопка «Применить» → st.rerun()

## Task Commits

Каждая задача закоммичена атомарно:

1. **Task 1: Панель «требует внимания» и настройка порога в сайдбаре** - `40d48b5` (feat)
2. **Task 2: Статус-иконки и ручной override в таблице реестра** - `31b0552` (feat)

## Files Created/Modified
- `main.py` — Импорт lifecycle_service, sidebar selectbox, attention panel, computed_status в реестре, секция ручного override

## Decisions Made
- `computed_status` получается отдельным SQL-запросом в начале вкладки Реестр, а не через модификацию `get_all_results` — чтобы не смешивать слои
- Каждый lifecycle-вызов открывает `Database(db_path)` как новый контекстный менеджер — безопасно при Streamlit reruns
- Панель внимания исключает документы с manual_status (они под контролем юриста — из lifecycle_service 02-01)

## Deviations from Plan

None — план выполнен точно как написан.

## Issues Encountered
Нет — оба задания выполнены без блокирующих проблем.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- UI-слой жизненного цикла готов: статусы, панель внимания, ручной override
- Plan 03 (платежи) может добавить в main.py аналогичный payment UI
- Plan 04 (шаблоны) может добавить template browser в существующие вкладки
- Checkpoint human-verify ожидает подтверждения юристом что UI отображается корректно

---
*Phase: 02-document-lifecycle*
*Completed: 2026-03-19*
