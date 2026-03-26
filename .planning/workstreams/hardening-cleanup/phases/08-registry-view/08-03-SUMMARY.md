---
phase: 08-registry-view
plan: 03
subsystem: ui
tags: [nicegui, aggrid, version-grouping, hover-actions, registry]

# Dependency graph
requires:
  - phase: 08-registry-view
    provides: "AG Grid registry table (08-01), search/segments/header (08-02)"
  - phase: 02-document-lifecycle
    provides: "set_manual_status, MANUAL_STATUSES, STATUS_LABELS, get_version_group, DocumentVersion"
provides:
  - "Hover-actions column with ⋯ context menu (REG-06)"
  - "Quick status change submenu from MANUAL_STATUSES (REG-06)"
  - "Version grouping with ▶/▼ expand/collapse (REG-07)"
  - "build_version_rows() function for lazy version detection"
  - "load_version_children() for on-demand child row loading"
affects: [09-document-card, 10-processing, 12-design-polish]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy version loading: build_version_rows marks parents, load_version_children inserts children on expand"
    - "colId dispatch pattern: _on_cell_clicked branches on colId before navigation"
    - "actions-cell opacity: CSS hover transition on .ag-row:hover .actions-cell"
    - "bulk SQL check: document_versions IN (ids) to detect version groups efficiently"

key-files:
  created: []
  modified:
    - app/components/registry_table.py
    - app/pages/registry.py
    - app/main.py
    - tests/test_registry_view.py

key-decisions:
  - "Lazy child loading: build_version_rows only marks parents, children loaded on expand click — avoids N+1 queries on table render"
  - "colId dispatch in _on_cell_clicked: actions → menu, has_children → toggle, else → navigate (D-19)"
  - "bulk SQL IN() for version detection: single query for all visible rows vs per-row get_version_group calls"
  - "Confirm delete dialog is placeholder — full delete in Phase 10 (not in current scope)"

patterns-established:
  - "Pattern: hover-actions via CSS opacity transition on .ag-row:hover"
  - "Pattern: lazy expand/collapse — children inserted/removed from rowData on click"

requirements-completed: [REG-06, REG-07]

# Metrics
duration: 4min
completed: 2026-03-21
---

# Phase 08 Plan 03: Hover-Actions and Version Grouping Summary

**AG Grid registry with ⋯ context menu (Открыть/Скачать/Переобработать/Удалить), quick status change via MANUAL_STATUSES, and lazy ▶/▼ expand/collapse for versioned documents**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-21T22:18:03Z
- **Completed:** 2026-03-21T22:22:06Z
- **Tasks:** 2 (1 auto + 1 checkpoint auto-approved)
- **Files modified:** 4

## Accomplishments

- `build_version_rows()` detects version groups via bulk SQL and marks rows with `has_children=True`
- `load_version_children()` lazy-loads child rows on ▶ click, `_collapse_version_children()` removes them
- Actions column with CSS hover opacity: ⋯ icon appears on row hover, dispatched via `colId == "actions"`
- Context menu: Открыть, Скачать оригинал, Переобработать, Удалить with quick status submenu
- Quick status change calls `set_manual_status` via `run.io_bound`, reloads table after
- Expand/collapse toggle column with ▶/▼ icons, `_toggle_expand` dispatched via `colId == "has_children"`
- All 10 unit tests pass (7 existing + 3 new version grouping tests)
- All 7 REG requirements (REG-01..REG-07) now implemented

## Task Commits

Each task was committed atomically:

1. **TDD RED — Failing tests for build_version_rows** - `1d44f2c` (test)
2. **Task 1: Hover-actions + version grouping implementation** - `77fde53` (feat)
3. **Task 2: checkpoint auto-approved** (no code changes)

**Plan metadata:** (docs commit below)

_Note: TDD tasks have two commits (test RED → feat GREEN)_

## Files Created/Modified

- `app/components/registry_table.py` — Added `build_version_rows`, `load_version_children`, `_collapse_version_children`; actions + expand/collapse columns in COLUMN_DEFS; updated `load_table_data` to call `build_version_rows`
- `app/pages/registry.py` — Rewrote `_on_cell_clicked` with colId dispatch; added `_show_action_menu`, `_quick_status_change`, `_clear_status`, `_confirm_delete`, `_toggle_expand`; imports `MANUAL_STATUSES`, `STATUS_LABELS`, `set_manual_status`
- `app/main.py` — Added `_ACTIONS_CSS` with hover opacity transition for `.actions-cell` and `.expand-icon`
- `tests/test_registry_view.py` — Added `tmp_db_with_versions` fixture and 3 version grouping tests

## Decisions Made

- Lazy child loading: `build_version_rows` only marks parents, children loaded on expand click — avoids N+1 queries on table render
- `colId` dispatch in `_on_cell_clicked`: `actions` → menu, `has_children` → toggle, else → navigate (D-19 compliant)
- Bulk SQL `IN()` for version detection: single query for all visible rows vs per-row `get_version_group` calls
- Confirm delete dialog is placeholder — full delete in Phase 10

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Pre-existing `test_ollama_stub` failure (llama-server not running in test environment) — unrelated to this plan, pre-dates our changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Full registry REG-01..REG-07 complete — ready for Phase 09 (document detail card)
- `load_version_children` available for Phase 09 to show version history in document card
- Delete functionality placeholder ready to be wired in Phase 10 (reprocessing/delete)

---
*Phase: 08-registry-view*
*Completed: 2026-03-21*
