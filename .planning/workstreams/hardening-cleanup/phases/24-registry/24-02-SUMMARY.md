---
phase: 24-registry
plan: 02
subsystem: ui
tags: [nicegui, calendar, timeline, design-system, css]

requires:
  - phase: 24-registry-01
    provides: "Registry UI foundation with toggle buttons (list/calendar) and calendar_container"

provides:
  - "Timeline calendar view in registry.py replacing FullCalendar JS"
  - "Mini-calendar with colored event dots (220px sidebar)"
  - "Monthly summary panel with event counts and payment totals"
  - "CSS classes in design-system.css: timeline-card, mini-cal, cal-summary"

affects: [25-document-card, 26-dialogs-pages]

tech-stack:
  added: []
  patterns:
    - "NiceGUI-native calendar rendering — no JS libraries, pure Python ui.element() tree"
    - "Event grouping by temporal proximity: today/week/month/later"
    - "Unified events list from two DB queries (payments + contracts)"

key-files:
  created: []
  modified:
    - app/pages/registry.py
    - app/static/design-system.css

key-decisions:
  - "Removed FullCalendar JS entirely — _ensure_fullcalendar() and _fc_loaded deleted"
  - "Timeline uses NiceGUI ui.element('div') for pixel-perfect CSS class attachment"
  - "Expiring contracts overlap with end-date contracts — unified by checking expiring_ids set"
  - "Mini-calendar rendered inline using Python calendar.Calendar(firstweekday=0)"

patterns-established:
  - "Helper functions _sum_row/_render_mini_calendar defined as closures inside registry_page() scope"
  - "Event cards use lambda capture pattern for contract_id click navigation"

requirements-completed: [REG-05]

duration: 12min
completed: 2026-03-25
---

# Phase 24 Plan 02: Registry Calendar Timeline Summary

**FullCalendar JS replaced with NiceGUI timeline — event cards with color-coded left borders (red/blue/yellow), temporal grouping (today/week/month/later), 220px mini-calendar with colored dots, and monthly summary panel**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-03-25T20:55:00Z
- **Completed:** 2026-03-25T21:07:00Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Eliminated FullCalendar JS dependency entirely — calendar is now pure NiceGUI Python
- Timeline feed left-side: events grouped Сегодня / На этой неделе / В [месяце] / Позже
- Each event card has colored left border: red=end, blue=payment, yellow=expiring
- Right sidebar: mini-calendar grid with colored dots on dates + monthly summary counts + payment total
- Click on any event card navigates to /document/{contract_id}
- All CSS values (colors, radius, spacing, font sizes) match approved mockup variant B exactly

## Task Commits

1. **Task 1: Replace FullCalendar with timeline + mini-calendar** - `49a3bf6` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `app/pages/registry.py` — Replaced _ensure_fullcalendar/_fc_loaded/_show_calendar with timeline rendering; added _sum_row and _render_mini_calendar helpers
- `app/static/design-system.css` — Added 100+ lines of timeline-card, mini-cal, cal-summary CSS matching mockup variant B; also added .ag-paging-page-size hide rule

## Decisions Made

- Used Python's stdlib `calendar.Calendar(firstweekday=0)` for mini-calendar grid generation — no JS needed
- Expiring events share date_end with regular end events — deduplication via expiring_ids set built from second DB query
- payment_events from get_calendar_events() use `start` field for date, `extendedProps.amount` for amount
- DB query for end_rows includes `subject` column (not present in old FullCalendar query) — needed for card subtitle

## Deviations from Plan

None — plan executed exactly as written. CSS copied verbatim from approved mockup HTML. All six plan steps executed in order.

## Issues Encountered

Pre-existing import error in split_panel.py (`PANEL_TYPE_TAG` missing from app.styles) prevents `python -c "from app.pages.registry import registry_page"` from working — this is out of scope for this plan and existed before any changes (confirmed via git stash check). Logged as pre-existing issue.

## Known Stubs

None — all event data is wired to live DB queries. Empty state ("Нет предстоящих событий") displays when no events found.

## Next Phase Readiness

- Calendar view complete, ready for Phase 25 (Document Card) and Phase 26 (Dialogs & Pages)
- The split_panel.py import error (PANEL_TYPE_TAG) needs resolution in Phase 24-01 context before full import works

---
*Phase: 24-registry*
*Completed: 2026-03-25*
