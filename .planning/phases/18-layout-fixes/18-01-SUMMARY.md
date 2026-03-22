---
phase: 18-layout-fixes
plan: "01"
subsystem: registry-ui
tags: [bug-fix, nicegui, stats-bar, layout, ag-grid, aria]
dependency_graph:
  requires: []
  provides: [stats-bar-fixed, registry-centered, ag-grid-warnings-suppressed]
  affects: [app/pages/registry.py, app/components/registry_table.py]
tech_stack:
  added: []
  patterns:
    - "NiceGUI: create all labels INSIDE with-block to control DOM placement"
    - "STATS_BAR.replace('bg-white', 'bg-transparent') to avoid touching shared constant"
key_files:
  created: []
  modified:
    - app/pages/registry.py
    - app/components/registry_table.py
decisions:
  - "Replace bg-white with bg-transparent via .replace() — avoids touching styles.py constant used elsewhere"
  - "suppressPropertyNamesCheck: True added to grid options to suppress remaining AG Grid 32+ warnings"
metrics:
  duration_min: 5
  completed_date: "2026-03-22"
  tasks_completed: 2
  files_modified: 2
---

# Phase 18 Plan 01: Stats Bar Fix + Registry Centering Summary

**One-liner:** Fixed NiceGUI DOM creation order bug in stats bar (labels now inside flex container) + max-w-6xl centering + AG Grid floatingFilter warnings removed.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Fix stats bar DOM bug + centering + search width + aria-labels | 07e667a | app/pages/registry.py |
| 2 | Remove deprecated AG Grid floatingFilter warnings | 83c1c97 | app/components/registry_table.py |

## What Was Built

### Task 1 — Stats bar DOM creation order fix (LAY-01, LAY-02, LAY-06, LAY-07, RBST-02)

The stats bar was broken: `total_num`, `expiring_num`, `attention_num` labels were created **before** the `with stats_row:` context manager. In NiceGUI, elements are attached to their parent at creation time — creating them outside the `with` block placed them in the DOM outside the flex container, so numbers appeared detached from their labels at the top of the page.

Fix: rewrote the entire stats bar block as a single `with ui.row() as stats_row:` block where all three stat columns are created inside it.

Additional fixes in the same task:
- `STATS_BAR.replace("bg-white", "bg-transparent")` — stats bar now blends with slate-100 page background instead of showing as a white stripe
- Outer column: `w-full` → `w-full max-w-6xl mx-auto` — page content is now centered with max-width constraint
- Search input: `max-w-md` → `max-w-lg` — search bar is wider
- Added `aria-label` on stats bar row (`role="region"`), all three stat numbers, and empty state CTA button

### Task 2 — AG Grid floatingFilter deprecation (RBST-03)

Removed `"floatingFilter": True` from `contract_type` and `counterparty` column definitions. AG Grid Community 32+ deprecated `floatingFilter` as a per-column boolean property — it now triggers console warnings. Also added `"suppressPropertyNamesCheck": True` to grid options to suppress any remaining unrecognised property warnings.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all stats bar labels are wired to `_refresh_stats()` which calls `_fetch_counts()` against live DB.

## Self-Check: PASSED

- `app/pages/registry.py` — exists, syntax ok
- `app/components/registry_table.py` — exists, syntax ok
- Commit 07e667a — present in git log
- Commit 83c1c97 — present in git log
- `grep "with ui.row().classes(STATS_BAR" app/pages/registry.py` → line 125 with "as stats_row"
- `grep "total_num = ui.label" app/pages/registry.py` → line 128, inside with-block (after line 125)
- `grep "max-w-6xl" app/pages/registry.py` → line 121
- `grep "max-w-lg" app/pages/registry.py` → line 156
- `grep -c "aria-label" app/pages/registry.py` → 7
- `grep -c "floatingFilter" app/components/registry_table.py` → 0
