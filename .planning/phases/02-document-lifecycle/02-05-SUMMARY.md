---
phase: 02-document-lifecycle
plan: 05
subsystem: payments
tags: [payments, calendar, dateutil, relativedelta, sqlite, lifecycle]

# Dependency graph
requires:
  - phase: 02-document-lifecycle
    plan: 01
    provides: "payments table (migration v5), Database.conn, Database._lock"
  - phase: 02-document-lifecycle
    plan: 03
    provides: "ContractMetadata payment fields, payment_service.py, save_payments hook in controller.py"
provides:
  - services/payment_service.py: unroll_payments, save_payments, get_calendar_events
  - Хук save_payments в controller.py после db.save_result (non-blocking)
  - Формат событий FullCalendar для streamlit-calendar (02-06)
affects:
  - 02-06 (UI платёжного календаря читает events из get_calendar_events)

# Tech tracking
tech-stack:
  added:
    - python-dateutil>=2.8.0 (relativedelta для точного разворота периодических платежей)
  patterns:
    - "FREQUENCY_DELTA маппинг: frequency str → relativedelta объект"
    - "Идемпотентность: DELETE + INSERT вместо INSERT OR IGNORE — гарантирует свежие данные"
    - "Non-blocking hook: try/except вокруг save_payments в controller.py, только WARNING при ошибке"
    - "FullCalendar формат: title, start, end, backgroundColor, extendedProps"

key-files:
  created:
    - services/payment_service.py
  modified:
    - modules/models.py (payment_terms, payment_amount, payment_frequency, payment_direction)
    - controller.py (import save_payments + hook после db.save_result)
    - requirements.txt (python-dateutil>=2.8.0)
    - services/pipeline_service.py (re-export save_payments для discoverability)

key-decisions:
  - "save_payments hook живёт в controller.py (не pipeline_service) — controller владеет db.save_result"
  - "Идемпотентность через DELETE+INSERT: повторная обработка не дублирует платежи"
  - "max_iter=1200 guard в unroll_payments: защита от бесконечного цикла (~100 лет monthly)"
  - "Если нет date_end — разовый платёж на date_start (не ошибка, а осознанное решение)"

patterns-established:
  - "get_calendar_events: JOIN payments + contracts без streamlit-зависимости"
  - "DIRECTION_COLOR dict: централизованный маппинг цветов для expense/income"

requirements-completed: [LIFE-07]

# Metrics
duration: 5min
completed: 2026-03-19
---

# Phase 2 Plan 05: Payment Service Summary

**Платёжный сервис с разворотом периодических платежей через relativedelta и формированием FullCalendar-событий для streamlit-calendar**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-19T22:29:35Z
- **Completed:** 2026-03-19T22:35:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- `services/payment_service.py` реализован с тремя функциями: unroll_payments, save_payments, get_calendar_events
- unroll_payments корректно разворачивает monthly/quarterly/yearly через relativedelta — не +30 days
- save_payments идемпотентна: DELETE + INSERT при каждом вызове, повторная обработка не дублирует записи
- get_calendar_events возвращает FullCalendar-совместимый JSON с правильными цветами (#ef4444 expense, #22c55e income)
- Хук save_payments вызывается из controller.py non-blocking — ошибки только WARNING, не прерывают пайплайн

## Task Commits

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| 1 | payment_service.py + ContractMetadata payment fields | ca5a582 | Выполнено в 02-03 |
| 2 | save_payments hook в controller.py | ca5a582 | Выполнено в 02-03 |
| 2+ | pipeline_service.py re-export (discoverability) | (текущий) | Выполнено |

## Files Created/Modified

- `services/payment_service.py` — новый файл: unroll_payments, save_payments, get_calendar_events
- `modules/models.py` — ContractMetadata: payment_terms, payment_amount, payment_frequency, payment_direction
- `controller.py` — import save_payments + non-blocking hook после db.save_result
- `requirements.txt` — python-dateutil>=2.8.0
- `services/pipeline_service.py` — re-export save_payments + комментарий об архитектуре хука

## Decisions Made

- Hook живёт в `controller.py` — это единственное место где вызывается `db.save_result`, pipeline_service — тонкая обёртка без доступа к db
- Идемпотентность через DELETE+INSERT (не INSERT OR IGNORE) — гарантирует актуальность при переобработке
- При отсутствии `date_end` — one-shot платёж на дату начала, не ошибка

## Deviations from Plan

### Context: Plan Pre-Implemented by 02-03

**[Context] Большая часть плана реализована в 02-03**
- **Ситуация:** При выполнении 02-03 (версионирование) предыдущий агент реализовал payment_service.py, payment fields в ContractMetadata, и hook в controller.py в одном коммите (ca5a582)
- **Обнаружено:** git log показал, что services/payment_service.py и controller.py изменения уже закоммичены
- **Действие:** Верифицировал корректность реализации (все тесты прошли), добавил pipeline_service.py re-export для discoverability
- **Влияние:** Функциональность полностью соответствует плану. Не требует исправлений.

### Auto-fixed Issues

None — план выполнен корректно предыдущим агентом и верифицирован.

## Issues Encountered

Нет блокирующих проблем. Вся функциональность работает корректно.

## User Setup Required

None.

## Next Phase Readiness

- Plan 06 (UI платёжного календаря) может вызывать `get_calendar_events(db)` напрямую
- Формат событий совместим со streamlit-calendar FullCalendar API
- Цвета централизованы в `DIRECTION_COLOR` dict — легко расширять

## Self-Check: PASSED

- services/payment_service.py: FOUND
- 02-05-SUMMARY.md: FOUND
- Commit ca5a582: FOUND
- Verification test: OK

---
*Phase: 02-document-lifecycle*
*Completed: 2026-03-19*
