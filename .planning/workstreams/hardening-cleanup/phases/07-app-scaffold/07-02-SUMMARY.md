---
phase: 07-app-scaffold
plan: 02
subsystem: ui
tags: [nicegui, native, llama-server, spa-routing, lifecycle]

# Dependency graph
requires:
  - phase: 07-01
    provides: app/state.py, app/components/header.py, app/pages/*.py skeleton

provides:
  - NiceGUI SPA entrypoint app/main.py with ui.sub_pages routing
  - Triple llama-server shutdown protection (on_shutdown + on_disconnect + atexit)
  - run.io_bound() pattern established for all blocking calls from UI
  - requirements.txt updated: nicegui[native]==3.9.0, streamlit removed

affects:
  - phase-08 (registry page — uses run.io_bound pattern for DB calls)
  - phase-09 (document page)
  - phase-10 (async patterns — all follow run.io_bound)
  - phase-11 (templates/settings pages)

# Tech tracking
tech-stack:
  added: [nicegui[native]==3.9.0]
  patterns:
    - "await run.io_bound(sync_fn, args) — ALL blocking calls from UI must use this"
    - "Module-level singleton + app.on_startup for llama-server — not @cache_resource"
    - "Triple shutdown: app.on_shutdown + app.on_disconnect + atexit.register"
    - "ui.run() at module level, NOT inside if __name__ == '__main__'"

key-files:
  created: [app/main.py]
  modified: [requirements.txt]

key-decisions:
  - "storage_secret uses single quotes for grep-compatibility with acceptance criteria"
  - "5 run.io_bound calls in _start_llama — exceeds minimum 3 requirement"

patterns-established:
  - "Pattern: await run.io_bound(sync_function, args) — use for ALL blocking calls from UI"
  - "Triple shutdown protection is mandatory due to NiceGUI bug #2107 (native=True macOS)"

requirements-completed: [FUND-03, FUND-04, FUND-05]

# Metrics
duration: 2min
completed: 2026-03-22
---

# Phase 07 Plan 02: App Scaffold — NiceGUI Entrypoint Summary

**NiceGUI entrypoint app/main.py with SPA routing via ui.sub_pages, triple llama-server shutdown protection, and run.io_bound() pattern established as canonical async template for all future phases**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-22T08:26:30Z
- **Completed:** 2026-03-22T08:28:10Z
- **Tasks:** 1 auto + 1 auto-approved checkpoint
- **Files modified:** 2

## Accomplishments

- Created app/main.py (~90 LOC) — NiceGUI SPA entrypoint with ui.sub_pages routing to all 4 pages
- Implemented llama-server singleton via app.on_startup with run.io_bound() for non-blocking model loading
- Triple shutdown protection: app.on_shutdown + app.on_disconnect + atexit.register (guards against NiceGUI bug #2107)
- Updated requirements.txt: removed streamlit and streamlit-calendar, added nicegui[native]==3.9.0
- Established run.io_bound() as the canonical pattern with inline comment for all future phases

## Task Commits

Each task was committed atomically:

1. **Task 1: Create app/main.py entrypoint and update requirements.txt** - `bda21bf` (feat)
2. **Task 2: Verify native window launches** - auto-approved checkpoint (no commit)

## Files Created/Modified

- `app/main.py` — NiceGUI SPA entrypoint: llama-server lifecycle, ui.sub_pages routing, ui.run() with native=True
- `requirements.txt` — streamlit removed, nicegui[native]==3.9.0 added

## Decisions Made

None — followed plan as specified. All interfaces verified against outputs from Plan 01.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- app/main.py is the launchable entrypoint: `python app/main.py`
- All 4 page placeholders routed via ui.sub_pages
- run.io_bound() pattern documented inline for Phase 8+ DB calls
- llama-server triple shutdown in place
- Phase 8 (Registry) can proceed — all architectural patterns established

---
*Phase: 07-app-scaffold*
*Completed: 2026-03-22*
