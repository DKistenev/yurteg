---
phase: 12-onboarding
plan: "02"
subsystem: onboarding-ux
tags: [empty-state, guided-tour, onboarding, registry, nicegui]
dependency_graph:
  requires: ["12-01"]
  provides: ["empty-state-registry", "guided-tour-overlay"]
  affects: ["app/pages/registry.py", "app/components/onboarding/tour.py"]
tech_stack:
  added: []
  patterns: ["ui.html + JS tour overlay", "hidden NiceGUI button for JS-Python bridge", "getBoundingClientRect tooltip positioning"]
key_files:
  created:
    - app/components/onboarding/tour.py
  modified:
    - app/pages/registry.py
decisions:
  - "Empty state condition: len(rows)==0 AND filter_search empty AND segment=='all' — prevents false show on filtered 0-result queries (Pitfall 4)"
  - "Tour JS-Python bridge: hidden ui.button with id=tour-done-btn clicked by endTour() JS — cleanest NiceGUI pattern without custom endpoints"
  - "setTimeout(startTour, 500) — Pitfall 2 guard, gives AG Grid time to render before tour targets elements"
  - "Tour steps use getBoundingClientRect + position type (center-top, below-left, below-right) for adaptive tooltip placement"
metrics:
  duration: "~3 minutes"
  completed_date: "2026-03-22"
  tasks_completed: 2
  files_changed: 2
---

# Phase 12 Plan 02: Empty State + Guided Tour Summary

Empty state for registry with action-first CTA and 3-step spotlight guided tour after first document processing.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Empty state in registry.py | e0b396a | app/pages/registry.py |
| 2 | Guided tour overlay | d5139dc | app/components/onboarding/tour.py, app/pages/registry.py |

## What Was Built

**Empty state** (`_render_empty_state()` in `app/pages/registry.py`):
- Shown when DB has 0 rows AND no active search/segment filter
- Folder SVG icon (48x48, stroke #d1d5db), heading, body text, CTA button, 3 hint bullets
- CTA calls `pick_folder()` via `state._on_upload` callback — reuses pipeline wiring
- Exact copy and CSS classes per UI-SPEC Component 3

**Guided tour** (`app/components/onboarding/tour.py`):
- Full-screen overlay via `ui.html` + inline JS
- 3 steps: registry table → search/filter row → upload button
- Each step spotlights target element via `getBoundingClientRect` + inline style
- Tooltip positioned contextually per step (center-top / below-left / below-right)
- `tour_completed` flag saved via `save_setting()` on complete or skip
- Triggered from `registry.py` `_init()` after first data load when `tour_completed` not set

**Registry modifications**:
- `search-row` CSS class added to search+segments `ui.row` for tour JS targeting
- Upload button gets `id=upload-btn` prop when tour is about to start
- `_init()` checks empty state and tour conditions after `load_table_data()`
- `load_settings` / `save_setting` imported from `config`

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all functionality is fully wired:
- Empty state CTA calls real `pick_folder()` + `state._on_upload` pipeline
- Tour `on_complete` callback calls `save_setting("tour_completed", True)`
- `tour_completed` flag persists to `~/.yurteg/settings.json`

## Self-Check: PASSED

Files exist:
- app/components/onboarding/tour.py — FOUND
- app/pages/registry.py — FOUND (modified)

Commits:
- e0b396a — FOUND (empty state)
- d5139dc — FOUND (guided tour)
