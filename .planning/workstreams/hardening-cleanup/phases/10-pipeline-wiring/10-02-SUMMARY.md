---
phase: 10-pipeline-wiring
plan: 02
subsystem: ui
tags: [nicegui, pipeline, progress, registry, async, linear_progress, ui_refs, on_upload]

requires:
  - phase: 10-01
    provides: start_pipeline(), pick_folder(), _header_refs, on_upload callback pattern in render_header
  - phase: 08-registry-view
    provides: registry.py page structure, load_table_data(), render_registry_table()

provides:
  - Progress section (linear_progress + count label + file label + error log) above registry table
  - ui_refs dict assembled in registry.build() and passed to start_pipeline
  - _on_upload async callback in registry.build() — triggers pipeline + table refresh
  - main.py wired with on_upload=_handle_upload so header button → registry progress section

affects:
  - phase 12 (design polish — progress section appearance)

tech-stack:
  added: []
  patterns:
    - "state._on_upload dynamic attr pattern: registry stores callback on state, main delegates via hasattr guard"
    - "ui_refs re-grabs upload_btn from _header_refs inside _on_upload — avoids stale ref at module init"
    - "Progress section set_visibility(False) by default — shown by start_pipeline, hides after completion"

key-files:
  created: []
  modified:
    - app/pages/registry.py
    - app/main.py

key-decisions:
  - "state._on_upload dynamic attribute used to bridge registry's callback to main.py — avoids passing callback through sub_pages routing"
  - "ui_refs['upload_btn'] re-grabbed inside _on_upload — _header_refs['upload_btn'] may be None at build() time if header renders after registry"
  - "Table refresh (load_table_data) called inside _on_upload after start_pipeline returns — not inside process.py (single responsibility)"

patterns-established:
  - "Pattern: progress section as sibling to grid_container, inside same outer column — D-06 inline above table"
  - "Pattern: ui_refs assembled at build() scope, re-grabbed for upload_btn inside callback"

requirements-completed: [PROC-03, PROC-04]

duration: 5min
completed: 2026-03-22
---

# Phase 10 Plan 02: Progress UI Wiring Summary

**Progress section wired into registry page above the table — upload button triggers real-time pipeline progress (bar + count + filename + error log) with auto-table-refresh on completion**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-22T00:00:00Z
- **Completed:** 2026-03-22T00:05:00Z
- **Tasks:** 2 (1 auto + 1 checkpoint auto-approved)
- **Files modified:** 2

## Accomplishments

- `app/pages/registry.py` extended with progress section: `ui.linear_progress`, count label, file label, `error_col` column — hidden by default via `set_visibility(False)`
- `ui_refs` dict assembled in `build()` with all keys expected by `start_pipeline()` from process.py
- `_on_upload` async callback defined in `build()` scope — calls `start_pipeline`, then `load_table_data` to auto-refresh table
- `state._on_upload` stores callback for delegation from `main.py`
- `app/main.py` updated: `render_header(state, on_upload=_handle_upload)` — `_handle_upload` delegates to `state._on_upload` with hasattr guard

## Task Commits

1. **Task 1: Add progress section to registry.py and wire on_upload callback** - `1ade9b9` (feat)
2. **Task 2: Visual verification checkpoint** - auto-approved (checkpoint:human-verify)

## Files Created/Modified

- `app/pages/registry.py` — progress section added above grid_container, ui_refs dict, _on_upload callback, state._on_upload assignment
- `app/main.py` — render_header now passes on_upload=_handle_upload

## Decisions Made

- `state._on_upload` dynamic attribute bridges callback from registry's `build()` to `main.py` — avoids threading callback through `ui.sub_pages` routing
- `ui_refs["upload_btn"]` re-grabbed from `_header_refs` inside `_on_upload` to avoid stale `None` ref at build time
- Table refresh stays in `_on_upload` (not in `process.py`) — clean separation: process.py handles pipeline, registry handles its own data reload

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Known Stubs

None — all wiring is real. The "Скачать оригинал" and "Переобработать" menu items in the action menu are pre-existing stubs from Phase 08 (not introduced in this plan).

## Next Phase Readiness

- Full pipeline wiring complete: header button → native picker → async pipeline → real-time progress → toast → table auto-refresh → error log
- Phase 10 pipeline-wiring phase is complete (both plans done)
- No blockers

---
*Phase: 10-pipeline-wiring*
*Completed: 2026-03-22*
