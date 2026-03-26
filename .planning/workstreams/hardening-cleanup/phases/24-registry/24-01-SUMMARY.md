---
phase: 24-registry
plan: "01"
subsystem: ui/registry
tags: [registry, split-panel, bulk-actions, ag-grid, linear-style]
dependency_graph:
  requires: []
  provides: [REG-01, REG-02, REG-03, REG-04]
  affects: [app/components/split_panel.py, app/components/registry_table.py, app/components/bulk_actions.py, app/styles.py]
tech_stack:
  added: []
  patterns: [Linear/Stripe panel sections, NiceGUI ui.column/ui.row composition]
key_files:
  created: []
  modified:
    - app/components/split_panel.py
    - app/components/registry_table.py
    - app/components/bulk_actions.py
    - app/styles.py
    - app/static/design-system.css
decisions:
  - "REG-01: confidence_display column removed from COLUMN_DEFS; html_columns=[1,5,7] correct"
  - "REG-04: Linear-style panel chosen (variant C from side-panel-v2.html mockup)"
  - "PANEL_FIELD_LABEL: changed from uppercase to plain 11px text per mockup spec"
metrics:
  duration: ~15min
  completed_date: "2026-03-25"
  tasks_completed: 2
  files_modified: 5
---

# Phase 24 Plan 01: Registry Table Cleanup + Linear Panel Summary

**One-liner:** Registry table stripped of confidence/Excel, sidebar rebuilt as Linear/Stripe three-section panel matching side-panel-v2.html variant C exactly.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Вычистить таблицу — убрать Уверенность, Excel, русифицировать footer | 3139ea6 | registry_table.py, bulk_actions.py, styles.py, design-system.css |
| 2 | Переделать боковую панель в Linear-style | 455155a | split_panel.py, styles.py |

## What Was Built

**Task 1 — Registry table cleanup (REG-01, REG-02, REG-03):**
- `confidence_display` column was already absent from COLUMN_DEFS (prior cleanup)
- `html_columns=[1, 5, 7]` already correct
- Excel button already removed from bulk toolbar
- Pagination `"pageSize": ""` already set, CSS hide rule in design-system.css
- Committed existing correct state to lock in REG-01/02/03 compliance

**Task 2 — Linear-style side panel (REG-04):**
- Fully rewrote `render_split_panel()` per variant C of `.superpowers/brainstorm/99248-1774442361/side-panel-v2.html`
- TOP: counterparty 15px/600, indigo type-tag badge (bg-indigo-50, text-indigo-600, 10px)
- Three sections with uppercase 10px mini-headers: Документ / Сроки / Финансы
- Field labels: 11px plain text (no uppercase) — matches `pnl-field-lbl` from mockup
- Amount: 20px/700 bold, letter-spacing -0.02em
- Button "Открыть карточку →" at bottom, outlined, outlined style
- Removed `_confidence_field()` function entirely
- Added `PANEL_TYPE_TAG` and `PANEL_SEC_TITLE` tokens to `styles.py`
- Updated `PANEL_FIELD_LABEL` to remove uppercase

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written, with one observation:

**Note:** REG-01, REG-02, REG-03 items were already implemented in prior work (confidence column was never in COLUMN_DEFS, Excel button was already removed, pagination was already russified). Task 1 commit locks in the correct state of these files.

## Known Stubs

None — all data fields are wired from `doc` dict passed to `render_split_panel()`.

## Self-Check

- `app/components/split_panel.py` — FOUND
- `app/styles.py` — FOUND (PANEL_TYPE_TAG, PANEL_SEC_TITLE added)
- Commit 3139ea6 — FOUND
- Commit 455155a — FOUND

## Self-Check: PASSED
