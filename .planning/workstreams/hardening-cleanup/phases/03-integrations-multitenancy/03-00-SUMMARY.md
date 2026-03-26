---
phase: 03-integrations-multitenancy
plan: "00"
subsystem: testing
tags: [pytest, xfail, telegram, notifications, client-manager, multi-tenant]

# Dependency graph
requires:
  - phase: 02-document-lifecycle
    provides: lifecycle_service.get_attention_required (used in notification stubs)
provides:
  - xfail test skeletons for INTG-01, INTG-02, INTG-04, PROF-01
  - test contracts defining interfaces for phase 3 implementation tasks
affects:
  - 03-01 (notifications)
  - 03-02 (telegram file queue)
  - 03-03 (telegram binding)
  - 03-04 (deadline alerts)
  - 03-05 (client manager)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wave 0 xfail skeleton: test files created before services exist, try/except ImportError for graceful failure"
    - "pytest.xfail() inside test body for conditional xfail based on import success"

key-files:
  created:
    - tests/test_notifications.py
    - tests/test_telegram_bot.py
    - tests/test_client_manager.py
  modified: []

key-decisions:
  - "xfail strict=False: тесты помечены XFAIL до реализации — CI безопасен (продолжаем паттерн из Phase 2)"
  - "Conditional imports в test_telegram_bot: server.queue_service / server.binding_service / server.deadline_service — несуществующие пакеты не ломают коллекцию"
  - "test_notifications использует существующий get_attention_required из lifecycle_service — INTG-04 переиспользует готовый сервис"

patterns-established:
  - "Wave 0 skeleton pattern: создавать xfail-тесты до реализации в каждой фазе"
  - "try/except ImportError + pytest.xfail() внутри тела теста для несуществующих модулей"

requirements-completed:
  - INTG-01
  - INTG-02
  - INTG-04
  - PROF-01

# Metrics
duration: 2min
completed: 2026-03-19
---

# Phase 3 Plan 00: Wave 0 Test Skeletons Summary

**18 xfail test stubs across 3 files covering Telegram file queue, binding codes, deadline alerts, in-app notifications, and multi-client manager — all collected without import errors**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-19T23:36:14Z
- **Completed:** 2026-03-19T23:38:01Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments

- 3 xfail test skeletons created defining interfaces for all phase 3 implementation tasks
- 18 tests collected with 0 import errors — CI-safe baseline established
- Conditional import guards (`try/except ImportError + pytest.xfail()`) ensure tests survive until server modules are created

## Task Commits

1. **Task 1: Create xfail test skeletons for all phase 3 requirements** - `a674c15` (test)

**Plan metadata:** pending docs commit

## Files Created/Modified

- `tests/test_notifications.py` - 3 xfail stubs for INTG-04 (startup toast via get_attention_required)
- `tests/test_telegram_bot.py` - 7 xfail stubs for INTG-01/INTG-02 (file_queue, binding codes, deadline alerts)
- `tests/test_client_manager.py` - 8 xfail stubs for PROF-01 (ClientManager: add/list/switch, fuzzy matching)

## Decisions Made

- Continued Phase 2 Wave 0 pattern with `xfail strict=False` — safe for CI before implementation
- `test_notifications.py` stubs call `get_attention_required` from existing `lifecycle_service` — INTG-04 is a thin UI layer on top of already-implemented logic, no new service needed
- Server-side modules namespaced as `server.queue_service`, `server.binding_service`, `server.deadline_service` — these will live in a `server/` package for the Telegram bot component

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Test contracts are established for all 4 phase 3 requirements
- Implementation tasks (03-01 through 03-05) have clear interfaces to target
- `server/` package structure anticipated: `queue_service`, `binding_service`, `deadline_service`
- `services/client_manager.py` interface defined: `ClientManager(clients_dir)` with `add_client`, `get_db`, `list_clients`, `find_client_by_counterparty`, `switch_client`, `active_db_path`

## Self-Check: PASSED

- tests/test_notifications.py: FOUND
- tests/test_telegram_bot.py: FOUND
- tests/test_client_manager.py: FOUND
- commit a674c15: FOUND
- 18 xfailed, 0 errors confirmed

---
*Phase: 03-integrations-multitenancy*
*Completed: 2026-03-19*
