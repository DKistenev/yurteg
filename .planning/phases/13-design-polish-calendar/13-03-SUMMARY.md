---
phase: 13-design-polish-calendar
plan: 03
subsystem: ui
tags: [nicegui, fullcalendar, calendar-toggle, registry, python]

requires:
  - phase: 13-design-polish-calendar
    provides: window.initCalendar global JS function injected in main.py, FullCalendar CDN, AppState.calendar_visible field in state.py
  - phase: 08-registry-view
    provides: registry.py build() structure, _client_manager singleton, AG Grid table
  - phase: 04-server-provider
    provides: get_calendar_events() in payment_service.py
provides:
  - Calendar toggle buttons (list/calendar) in registry header row right-aligned
  - _show_calendar() async function fetching payment + end-date events
  - _switch_view() toggling grid/calendar visibility and button states
  - calendar_container with yurteg-calendar div for FullCalendar mount point
  - Empty state hides toggle buttons when no data
affects: [registry, document, calendar, phase-14]

tech-stack:
  added: []
  patterns:
    - "run.io_bound() for fetching payment and contract data from DB without blocking event loop"
    - "ui.timer(0.1, ..., once=True) to defer JS init until DOM element is rendered"
    - "Event color override at fetch time: payment_service colors replaced with #94a3b8 (slate-400) in registry layer"
    - "calendar_container.clear() + ui.html() pattern for re-rendering FullCalendar on each toggle"

key-files:
  created: []
  modified:
    - app/pages/registry.py

key-decisions:
  - "Payment events color overridden to #94a3b8 (slate-400) in registry.py, not in payment_service.py — keeps service layer color-neutral"
  - "end_date events built from get_all_results() directly in registry — no new service function needed"
  - "event id scheme: payment-{contract_id}-{start} and contract-{id} — avoids FullCalendar duplicate event conflicts"
  - "Empty state hides toggle buttons since calendar makes no sense with no data"

patterns-established:
  - "Pattern: toggle view state via AppState.calendar_visible + set_visibility() calls — no page reload"
  - "Pattern: initCalendar() global JS called after DOM element created via ui.timer delay"

requirements-completed: [DSGN-04]

duration: 2min
completed: 2026-03-22
---

# Phase 13 Plan 03: Calendar Toggle Summary

**List/Calendar view toggle in registry with FullCalendar rendering contract end dates (indigo) and payments (slate-400) from live DB data**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-22T13:18:11Z
- **Completed:** 2026-03-22T13:20:03Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Added List/Calendar toggle buttons (≡ / ⊞) right-aligned in the search-segments row
- Implemented `_show_calendar()` that fetches payment events and contract end-date events asynchronously and renders them in FullCalendar via `window.initCalendar`
- Implemented `_switch_view()` that toggles between AG Grid and FullCalendar views, updating button active states and container visibility
- Calendar events: contract end dates in indigo (#4f46e5), payments in slate-400 (#94a3b8)
- Empty state (no documents) hides toggle buttons — calendar with no data makes no sense

## Task Commits

1. **Task 1: Calendar toggle + FullCalendar component in registry.py** - `190d2ef` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/app/pages/registry.py` - Added import json + run + get_calendar_events, _TOGGLE_ACTIVE/_TOGGLE_INACTIVE constants, list_btn/cal_btn buttons, calendar_container, _show_calendar(), _switch_view(), empty state toggle hiding

## Decisions Made

- Payment event colors overridden to `#94a3b8` in registry.py (not in service layer) — payment_service stays color-neutral for other callers
- End-date events built from `db.get_all_results()` directly — no new service function needed since contract data is already available
- `ui.timer(0.1, ..., once=True)` used to defer `initCalendar` JS call until DOM element is guaranteed to exist (Pitfall 2 from research)
- `event.id` scheme uses `payment-{contract_id}-{start}` to prevent FullCalendar duplicate-event conflicts on re-render

## Deviations from Plan

None — plan executed exactly as written. The `extendedProps.type = "payment"` normalisation was added as a minor correctness measure (payment_service doesn't set `type` field, but the JS tooltip checks it), which falls under Rule 2 (missing critical field for tooltip rendering).

## Issues Encountered

None. `get_calendar_events` signature takes optional `start_date`/`end_date` parameters — called without them to fetch all events for the calendar (full history view is appropriate).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Calendar toggle fully functional in registry
- Phase 13 Plan 04 (final verification / cleanup) can proceed
- The `window.initCalendar` global JS function was already injected in main.py by Plan 13-01

---
*Phase: 13-design-polish-calendar*
*Completed: 2026-03-22*
