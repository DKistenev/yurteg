---
phase: 19-onboarding-demo
plan: 01
subsystem: onboarding
tags: [tour, guided-tour, header, onboarding, ux]
dependency_graph:
  requires: []
  provides: [5-step-guided-tour, tour-guide-button]
  affects: [app/components/onboarding/tour.py, app/components/header.py, app/pages/registry.py]
tech_stack:
  added: []
  patterns: [js-spotlight-tour, nicegui-html-bridge, hidden-button-callback]
key_files:
  modified:
    - app/components/onboarding/tour.py
    - app/components/header.py
    - app/pages/registry.py
decisions:
  - "TOUR_STEPS expanded 3→5: upload → nav tabs → search/filters → calendar-toggle → client dropdown"
  - "Tooltip visual: box-shadow 20px/60px, radius 12px, max-width 300px, progress bar + dots"
  - "z-index: overlay=9000, tooltip=9001 — no conflict with Quasar dialogs"
  - "«? Гид» placed between upload CTA and client dropdown — flat, text-xs, slate-400 (subtle)"
  - "_restart_tour closes over save_setting + ui.navigate.to('/') — same pattern as _switch_client"
metrics:
  duration: ~5 min
  completed: "2026-03-22"
  tasks_completed: 2
  files_modified: 3
---

# Phase 19 Plan 01: Guided Tour 5 Steps + «? Гид» Button Summary

**One-liner:** 5-step spotlight tour (upload→nav→filters→calendar→client) with SaaS-quality tooltip + «? Гид» restart button in dark chrome header.

## What Was Built

### Task 1: TOUR_STEPS 3→5 + tooltip visual polish (commit 4c24353)

Expanded `TOUR_STEPS` in `app/components/onboarding/tour.py` from 3 to 5 steps:

1. `#upload-btn` — «Загрузка документов» (below-right)
2. `.q-header` — «Навигация» (center-top)
3. `.search-row` — «Фильтры и поиск» (below-left)
4. `#calendar-toggle` — «Вид календаря» (below-right)
5. `.q-header .shrink-0:last-child` — «Рабочие пространства» (below-right)

Tooltip visual improvements (SaaS-quality per plan spec):
- `box-shadow: 0 20px 60px rgba(0,0,0,0.15), 0 4px 16px rgba(0,0,0,0.1)`
- `border-radius: 12px` (was 8px)
- `max-width: 300px` (was 256px)
- Indigo progress bar (proportional fill per step)
- Step indicator dots (active=indigo-600, inactive=slate-200)
- «Далее» button: `padding: 10px 28px`, hover state
- `z-index`: overlay=9000, tooltip=9001 (no Quasar dialog conflict)

`render_tour(on_complete)` signature unchanged — registry.py calls it without modification.

### Task 2: «? Гид» button in header + calendar-toggle id (commit e050bfa)

`app/components/header.py`:
- Added `from config import save_setting` import
- Added `_restart_tour()` closure inside `render_header()`
- Added flat button `«? Гид»` between upload CTA and client dropdown
  - props: `flat no-caps id=tour-guide-btn`
  - classes: `text-xs text-slate-400 hover:text-slate-200 transition-colors duration-150 px-2`
  - click: `save_setting("tour_completed", False)` + `ui.navigate.to("/")`

`app/pages/registry.py`:
- Calendar toggle row now has `.props("id=calendar-toggle")` — enables tour spotlight targeting step 4

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all 5 tour steps have real targets wired in the DOM.

## Self-Check: PASSED

- `app/components/onboarding/tour.py` — exists, `len(TOUR_STEPS) == 5`
- `app/components/header.py` — contains `tour-guide-btn`, `tour_completed`, `save_setting`
- `app/pages/registry.py` — contains `calendar-toggle`
- Commits: `4c24353`, `e050bfa`
