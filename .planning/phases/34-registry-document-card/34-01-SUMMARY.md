---
phase: "34"
plan: "01"
subsystem: frontend/registry, frontend/document
tags: [ui-polish, calendar, search, preview, feedback]
dependency_graph:
  requires: [33-01]
  provides: [REG-01, REG-02, REG-03, DOC-01, DOC-02]
  affects: [app/pages/registry.py, app/pages/document.py]
tech_stack:
  added: []
  patterns: [container-clear-rerender, collapsible-expand-toggle]
key_files:
  modified:
    - app/pages/registry.py
    - app/pages/document.py
decisions:
  - "DOC-01 already implemented by prior executor — verified, skipped"
  - "Mini-calendar uses container.clear() + closure over cal_state dict for re-render"
  - "Past events use same expand/collapse pattern as deadline widget"
metrics:
  duration_minutes: 2
  completed: "2026-03-28"
---

# Phase 34 Plan 01: Registry & Document Card Summary

Search icon with clear button, calendar month navigation, past event filtering, PDF preview verification, and save feedback toast.

## Tasks Completed

| # | Task | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | REG-01: Search icon + clear button | a9753bc | Added `clearable` + `prepend-inner-icon=search` props |
| 2 | REG-02: Filter past events | 7da49b2 | New "past" group, collapsible "Просрочены" section |
| 3 | REG-03: Mini-calendar navigation | 9dbca89 | Month nav buttons, "Сегодня" reset link, container re-render |
| 4 | DOC-01: PDF preview | — (skip) | Already implemented: two-column layout with iframe |
| 5 | DOC-02: Toast on note save | e995d00 | `ui.notify("Сохранено")` after successful update_review |

## Deviations from Plan

### DOC-01 Already Implemented

- **Found during:** Task 4
- **Issue:** document.py already had full two-column layout with PDF iframe (D-01 through D-04)
- **Action:** Verified existing implementation, no changes needed
- **This is expected** — noted in phase requirements as possibility

No other deviations. Plan executed as written.

## Known Stubs

None — all features are fully wired to data sources.

## Verification

1. Search input: `clearable` + `prepend-inner-icon=search` props added at line 500
2. Mini-calendar: `_nav_month()` and `_nav_today()` functions with `_draw_calendar()` re-render
3. Past events: `groups["past"]` with collapsible header, events with `d < today` filtered out of "week"
4. Document preview: two-column layout confirmed in document.py lines 134-560
5. Note save toast: `ui.notify("Сохранено", type="positive")` after successful db.update_review
