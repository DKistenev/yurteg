---
phase: 13-design-polish-calendar
plan: "01"
subsystem: ui
tags: [nicegui, tailwind, css, fullcalendar, animations, ibm-plex-sans, design-system]

requires:
  - phase: 12-onboarding
    provides: NiceGUI app scaffold, AppState dataclass, ui.add_head_html pattern established

provides:
  - IBM Plex Sans font globally injected via Google Fonts (weights 400+600, cyrillic)
  - FullCalendar v6.1.15 CDN loaded globally (CSS + JS)
  - Staggered row animation keyframes (8-row cap, 80ms steps, cubic-bezier ease-out-quart)
  - Page fade-in animation on .nicegui-content
  - _STATUS_CSS migrated: unknown/terminated now use slate-100/slate-500 (not gray)
  - _ACTIONS_CSS migrated: all hex codes to slate/indigo ramp
  - AppState.calendar_visible: bool = False field added
  - Test scaffold: 7 source-level inspection tests for DSGN-01 through DSGN-05

affects: [13-02, 13-03, 13-04, all subsequent design-polish-calendar plans]

tech-stack:
  added:
    - FullCalendar v6.1.15 (jsDelivr CDN)
    - IBM Plex Sans (Google Fonts, 400+600 weights, cyrillic subset)
  patterns:
    - Font injection first (before any other add_head_html) — prevents FOUC
    - CSS variable blocks defined as module-level strings (_FONT_CSS, _ANIMATION_CSS, etc.)
    - Source-level inspection tests via pathlib read_text (avoids ui.run() import side-effect)

key-files:
  created:
    - tests/test_design_polish.py
    - .planning/phases/13-design-polish-calendar/13-01-SUMMARY.md
  modified:
    - app/main.py
    - app/state.py

key-decisions:
  - "Font injection order: _FONT_CSS must be first add_head_html call — ensures IBM Plex Sans loads before any element renders (Pitfall 4 from UI-SPEC)"
  - "Source-level inspection in tests: read main.py as text (not import) to avoid ui.run() side-effect during pytest"
  - "FullCalendar JS: window.initCalendar as global function — called via ui.run_javascript from registry.py in Plan 13-03"
  - "_STATUS_CSS migration scope: only unknown/terminated migrate to slate; semantic colors (green/yellow/red/blue/purple/orange) unchanged per D-25"

patterns-established:
  - "Pattern: CSS blocks as module-level string constants (_FONT_CSS, _ANIMATION_CSS, etc.) injected once via ui.add_head_html at module load"
  - "Pattern: source-level test inspection — pathlib.read_text() + regex instead of import for files with ui.run() side-effects"

requirements-completed: [DSGN-01, DSGN-02, DSGN-03, DSGN-05]

duration: 3min
completed: 2026-03-22
---

# Phase 13 Plan 01: Design Polish — Global CSS Foundation Summary

**IBM Plex Sans font + FullCalendar CDN + row/page animations injected globally; _STATUS_CSS/_ACTIONS_CSS migrated from gray to slate/indigo; AppState gets calendar_visible field; 7-test design polish scaffold GREEN**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-22T12:49:10Z
- **Completed:** 2026-03-22T12:52:20Z
- **Tasks:** 2
- **Files modified:** 3 (app/main.py, app/state.py, tests/test_design_polish.py)

## Accomplishments

- Created 7 source-level inspection tests covering DSGN-01 through DSGN-05 — all GREEN after migration
- Added `_FONT_CSS` (IBM Plex Sans Google Fonts, cyrillic subset, 400+600), `_FULLCALENDAR_CSS` (FullCalendar v6.1.15 jsDelivr), `_ANIMATION_CSS` (staggered row-in with 8-row cap + page-fade-in), `_CALENDAR_JS` (initCalendar global + tooltip) to app/main.py
- Migrated `_STATUS_CSS`: `.status-unknown` and `.status-terminated` now use `bg-slate-100 text-slate-500` (were `bg-gray-100 text-gray-500`); all semantic status colors untouched
- Migrated `_ACTIONS_CSS`: `#6b7280` → `#64748b` (slate-500), `#111827` → `#4f46e5` (indigo-600 hover), `#9ca3af` → `#94a3b8` (slate-400), `#374151` → `#475569` (slate-600)
- Added `calendar_visible: bool = False` to AppState dataclass (prerequisite for Plan 13-03 calendar toggle)

## Task Commits

1. **Task 1: Test scaffold for DSGN-01 through DSGN-05** - `abfaa24` (test)
2. **Task 2: Global CSS injection + migration + AppState** - `0cdb253` (feat)

## Files Created/Modified

- `app/main.py` — Added 4 new CSS/JS blocks (_FONT_CSS, _FULLCALENDAR_CSS, _ANIMATION_CSS, _CALENDAR_JS); migrated _STATUS_CSS and _ACTIONS_CSS; updated ui.add_head_html injection order
- `app/state.py` — Added `calendar_visible: bool = False` field to AppState dataclass
- `tests/test_design_polish.py` — 7 source-level inspection tests for DSGN-01 through DSGN-05

## Decisions Made

- **Font injection order:** _FONT_CSS is first add_head_html call — ensures IBM Plex Sans loads before any element renders (UI-SPEC Pitfall 4)
- **Test approach:** Read app/main.py as text via pathlib (not import) — avoids triggering ui.run() side-effect during pytest execution
- **FullCalendar JS:** initCalendar defined as `window.initCalendar` global — ready to be called via `ui.run_javascript` from registry.py in Plan 13-03
- **_STATUS_CSS migration scope:** Only unknown/terminated migrate to slate — semantic colors (green/yellow/red/blue/purple/orange) explicitly preserved per D-25

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

**Import side-effect:** Initial test scaffold tried to `from app.main import _STATUS_CSS` which triggered `ui.run()` at module level, causing test failure. Auto-fixed by switching to `pathlib.read_text()` + regex extraction pattern (Rule 1 — code doesn't work as intended, fixed inline).

## Known Stubs

None — this plan injects CSS/JS infrastructure only. No UI rendering stubs.

## Next Phase Readiness

- Global design system foundation in place — font, animations, FullCalendar CDN all globally available
- `calendar_visible` field ready for Plan 13-03 (calendar toggle in registry)
- `window.initCalendar()` JS function ready in global scope for Plan 13-03 initialization
- Plans 13-02 through 13-04 can proceed — all depend on this foundation

---
*Phase: 13-design-polish-calendar*
*Completed: 2026-03-22*
