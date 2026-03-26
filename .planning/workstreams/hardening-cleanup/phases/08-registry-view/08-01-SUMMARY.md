---
phase: 08-registry-view
plan: 01
subsystem: ui
tags: [nicegui, aggrid, rapidfuzz, sqlite, registry]

requires:
  - phase: 07-nicegui-scaffold
    provides: "AppState, get_state(), run.io_bound() pattern, NiceGUI SPA sub_pages"
  - phase: 02-document-lifecycle
    provides: "lifecycle_service.get_computed_status_sql(), STATUS_LABELS, MANUAL_STATUSES"
  - phase: 03-integrations-multitenancy
    provides: "ClientManager.get_db(), list_clients()"

provides:
  - "_fetch_rows(): SQL query with computed_status, segment filter, fuzzy search"
  - "_fuzzy_filter(): multi-word AND-logic rapidfuzz search with 80% threshold"
  - "COLUMN_DEFS: 4 visible columns + 5 hidden columns for AG Grid"
  - "STATUS_CELL_RENDERER: JS cellRenderer for colored status badges"
  - "render_registry_table() / load_table_data(): async UI helpers"
  - "STATUS_CSS: @layer components Tailwind classes for all 8 statuses"
  - "registry.py: real build() replacing placeholder stub"

affects:
  - 08-registry-view (plans 02-03: search bar, segments, hover-actions)
  - 09-document-card (will use grid rowClicked → navigate to /document/{id})

tech-stack:
  added: []
  patterns:
    - "run.io_bound(_fetch_rows, ...) for blocking DB calls from async UI"
    - "ClientManager singleton at module level (_client_manager) — not per-call"
    - "JS cellRenderer string in Python COLUMN_DEFS for status badges"
    - "ui.timer(0, _init, once=True) for async initialization in sync build()"
    - "STATUS_CSS via ui.add_head_html at module level in main.py"

key-files:
  created:
    - "app/components/registry_table.py — _fetch_rows, _fuzzy_filter, COLUMN_DEFS, render_registry_table, load_table_data"
    - "tests/test_registry_view.py — 7 unit tests for data layer"
  modified:
    - "app/pages/registry.py — replaced placeholder with real registry build()"
    - "app/main.py — added STATUS_CSS via ui.add_head_html"

key-decisions:
  - "_client_manager singleton at module level prevents re-init on every grid load (Research Pitfall 5)"
  - "Segment filter and fuzzy search applied Python-side after SQL fetch — keeps SQL simple, logic testable"
  - "STATUS_CELL_RENDERER as Python string constant — JS embedded in columnDef, no separate file"
  - "ui.timer(0, once=True) pattern for async grid init inside sync build() — established in Phase 7"

requirements-completed: [REG-01, REG-04]

duration: 10min
completed: 2026-03-21
---

# Phase 08 Plan 01: Registry Data Layer and AG Grid Table Summary

**AG Grid registry table with live SQLite data, computed status badges via JS cellRenderer, and rapidfuzz multi-word AND-logic fuzzy search**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-21T22:08:28Z
- **Completed:** 2026-03-21T22:18:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `_fetch_rows()` loads contracts from SQLite with `get_computed_status_sql()` for computed status, filters by segment (expiring/attention/all) and fuzzy search
- `_fuzzy_filter()` implements multi-word AND-logic search across 5 fields via `rapidfuzz.fuzz.partial_ratio` at 80% threshold
- AG Grid `COLUMN_DEFS` with 4 visible columns (Тип, Контрагент, Статус badge, Сумма) + 5 hidden (date_end, validation_score, filename, processed_at, id)
- Status badges via JS `cellRenderer` string referencing Tailwind `@layer components` CSS classes defined in `main.py`
- Registry page `build()` uses `ui.timer(0, once=True)` pattern for async grid initialization

## Task Commits

1. **Task 1: Test scaffold + data layer** - `1748363` (feat) — TDD: tests RED then GREEN
2. **Task 2: AG Grid table with status badges** - `2372567` (feat)

## Files Created/Modified

- `app/components/registry_table.py` — full data layer + UI component (created)
- `tests/test_registry_view.py` — 7 unit tests for _fetch_rows and _fuzzy_filter (created)
- `app/pages/registry.py` — replaced placeholder stub with real implementation
- `app/main.py` — added `_STATUS_CSS` with 8 status classes via `ui.add_head_html`

## Decisions Made

- `_client_manager` instantiated once at module level — ClientManager creates file connections, re-creating on every call would be wasteful
- Segment and fuzzy filter implemented Python-side (not SQL WHERE) — simpler SQL, easier to unit test without SQL fixtures
- `STATUS_CELL_RENDERER` as a Python string constant embedded in `COLUMN_DEFS` — no separate JS file, easy to maintain

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test assertion for fuzzy match on Russian morphology**
- **Found during:** Task 1 (TDD GREEN)
- **Issue:** Test asserted `"аренда" in "Договор аренды".lower()` — but "аренда" != "аренды" (Russian declension)
- **Fix:** Changed assertion to check for stem "аренд" which appears in both `contract_type` and `subject` fields
- **Files modified:** tests/test_registry_view.py
- **Committed in:** 1748363 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug in test assertion)
**Impact on plan:** Minor — test logic corrected. No scope creep.

## Issues Encountered

None — plan executed cleanly. DB schema already had all required columns from earlier phases.

## User Setup Required

None — no external service configuration required.

## Known Stubs

None — all columns are wired to real DB data. `rowData` is populated from live SQLite queries via `_fetch_rows`. No hardcoded empty arrays or placeholder text in the data path.

## Next Phase Readiness

- Data layer ready for Plan 02 (search bar + segment buttons wired to state)
- `render_registry_table` returns grid element — Plan 02 can add `rowClicked` handler for navigation
- `load_table_data(grid, state, segment=...)` accepts segment param — Plan 02 just needs to call it with the active segment

---
*Phase: 08-registry-view*
*Completed: 2026-03-21*
