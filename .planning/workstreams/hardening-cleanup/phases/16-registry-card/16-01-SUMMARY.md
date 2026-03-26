---
phase: 16-registry-card
plan: "01"
subsystem: registry-ui
tags: [ag-grid, css-tokens, stats-bar, status-pills, filter-bar, typography]
dependency_graph:
  requires: []
  provides: [ag-grid-theming, status-pills, stats-bar, registry-heading, filter-bar-active-state]
  affects: [app/pages/registry.py, app/components/registry_table.py, app/static/design-system.css, app/styles.py]
tech_stack:
  added: []
  patterns: [CSS variables mapping (--yt-* → --ag-*), filled pill badges, async stats refresh via run.io_bound()]
key_files:
  created: []
  modified:
    - app/static/design-system.css
    - app/components/registry_table.py
    - app/styles.py
    - app/pages/registry.py
decisions:
  - "AG Grid theming via .ag-theme-quartz block with --ag-* CSS variables mapped from --yt-* tokens (no @layer — AG Grid ignores it)"
  - "Status pill class names (status-active, status-expiring, etc.) are API contracts — do not rename"
  - "Pitfall 7 guard: disable .ag-row animation before segment filter to prevent row entrance replay"
  - "_fetch_counts() as separate DB aggregation function — not bundled into _fetch_rows() to keep concerns separated"
metrics:
  duration: "~7 min"
  completed: "2026-03-22T19:43:03Z"
  tasks_completed: 2
  files_modified: 4
---

# Phase 16 Plan 01: Registry Visual Rework Summary

**One-liner:** AG Grid theming via --ag-* CSS variables, filled status pills, stats bar with 3 aggregate numbers, typography heading, Pitfall 7 animation guard.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | AG Grid theming + filled status pills + _fetch_counts | f56994d | app/static/design-system.css, app/components/registry_table.py |
| 2 | Stats bar, heading «Реестр», filter bar, Pitfall 7 guard | d15180f | app/pages/registry.py, app/styles.py |

## What Was Built

**Task 1 — CSS + registry_table.py:**
- Added `.ag-theme-quartz` block in `design-system.css` with 10 `--ag-*` variables mapped from `--yt-*` tokens (background, header, hover, border, font, row/header height)
- Added 8 `status-*` filled pill classes: green (active), amber (expiring), red (expired), blue (extended), violet (negotiation), slate (unknown/terminated/suspended) — all using `display:inline-flex` with padding and border-radius:9999px
- Rewrote `STATUS_CELL_RENDERER` JS: conditional `iconHtml` (empty string icons → no `<span>`), cleaner pill rendering
- Added `_fetch_counts(client_name, warning_days)` — sync function for run.io_bound(), returns `{total, expiring, attention}` aggregate counts

**Task 2 — registry.py + styles.py:**
- Added `STATS_BAR` and `STATS_ITEM` constants to `app/styles.py`
- Restructured `build()` layout: stats bar (white bg, border-b) → heading row (h2 + calendar toggles) → search+filter bar
- Stats bar shows 3 live numbers: total docs (slate-900), expiring (amber-600), attention (red-600) — initialized with "—", refreshed async
- Heading "Реестр" with `text-2xl font-semibold text-slate-900` (REGI-05)
- Filter bar kept visually unchanged but moved under heading (REGI-06 filled active state already in SEG_ACTIVE)
- Added `_refresh_stats()` — async helper called in `_init()` and after segment switch
- Pitfall 7 guard in `_switch_segment()`: `ui.run_javascript()` disables `.ag-row` animation before data reload

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. Stats bar fetches live data via `_fetch_counts()` → `run.io_bound()`. Numbers initialize to "—" and update on page load via `_init()` → `_refresh_stats()`.

## Self-Check: PASSED

Files verified:
- `app/static/design-system.css` — contains `.ag-theme-quartz` block and 8 `display:inline-flex` status pill classes
- `app/components/registry_table.py` — `_fetch_counts` importable, STATUS_CELL_RENDERER updated
- `app/styles.py` — `STATS_BAR` and `STATS_ITEM` constants present
- `app/pages/registry.py` — `_refresh_stats`, `text-2xl font-semibold`, Pitfall 7 guard, `_fetch_counts` import all present
- All Python imports: `import app.pages.registry; import app.components.registry_table; import app.styles` — OK
- Commits f56994d and d15180f exist in git log
