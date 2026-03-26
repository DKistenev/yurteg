---
phase: 09-document-detail-card
plan: "01"
subsystem: document-card
tags: [nicegui, document-card, navigation, status, notes, data-layer]
dependency_graph:
  requires: [modules/database.py, app/state.py, services/lifecycle_service.py, app/components/registry_table.py]
  provides: [app/pages/document.py, get_contract_by_id, AppState.filtered_doc_ids]
  affects: [app/main.py routing, Phase 09 Plan 02]
tech_stack:
  added: []
  patterns: [run.io_bound for all DB calls, lambda default-arg capture for closures, STATUS_LABELS CSS badges]
key_files:
  created:
    - app/pages/document.py
    - tests/test_document_card.py
  modified:
    - modules/database.py
    - app/state.py
    - app/components/registry_table.py
    - tests/test_app_scaffold.py
decisions:
  - "filtered_doc_ids synced in load_table_data on every data load (not on click) — ensures prev/next always reflects current filter state (Pitfall 5)"
  - "get_contract_by_id mirrors get_all_results JSON deserialization pattern — consistent across single-record and bulk queries"
  - "Prev/next lambdas use default arg capture (pid=prev_id) — avoids closure cell issue"
  - "Status select rendered inline with set_visibility toggle — no JS event bus needed"
metrics:
  duration: "4min"
  completed_date: "2026-03-21"
  tasks_completed: 2
  files_modified: 6
requirements: [DOC-01, DOC-02, DOC-03, DOC-06]
---

# Phase 09 Plan 01: Document Card Scaffold Summary

**One-liner:** NiceGUI document card page with back/prev/next nav, 2-column metadata grid, status badge with manual override, and autosave lawyer notes on blur.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Data layer — get_contract_by_id + AppState.filtered_doc_ids + tests | 10ccaa1 | modules/database.py, app/state.py, app/components/registry_table.py, tests/test_document_card.py |
| 2 | Document card page — header, metadata, status, notes, prev/next nav | 6d2fb8a | app/pages/document.py |

## What Was Built

### Data Layer (Task 1)

- `Database.get_contract_by_id(contract_id)` — fetches single contract with JSON deserialization of `special_conditions`, `parties`, `validation_warnings`; sets defaults for `review_status`, `lawyer_comment`, `manual_status`
- `AppState.filtered_doc_ids: list` — added as `field(default_factory=list)`; holds ordered list of visible doc IDs for prev/next navigation
- `load_table_data` in `registry_table.py` — now syncs `state.filtered_doc_ids` after every data load (excludes child rows)
- 3 tests: `test_get_contract_by_id`, `test_get_contract_by_id_none`, `test_prevnext_logic` — all pass

### Document Card Page (Task 2)

`app/pages/document.py` — 210 lines, fully async:

1. **Header** (D-02): "← Назад к реестру" button left, `contract_type` center, ◀ ▶ right (disabled at edges)
2. **Prev/Next** (D-03): reads `state.filtered_doc_ids`, computes `prev_id`/`next_id`, navigates via `ui.navigate.to(f'/document/{id}')`
3. **Metadata grid** (D-04, D-05): 2-column NiceGUI grid — 7 fields (type, counterparty, subject, date_start, date_end, amount, date_signed) + special_conditions bulleted list below
4. **Status section** (D-06, D-07): STATUS_LABELS CSS badge, "Изменить" toggles select with MANUAL_STATUSES, "Применить" calls `set_manual_status` via `run.io_bound`, "Сбросить" calls `clear_manual_status` and refreshes
5. **Lawyer notes** (D-08, D-09): `ui.textarea` with `on('blur', _save_comment)` — saves via `db.update_review(file_hash, review_status, comment)`
6. **Placeholders**: comments at bottom for Plan 02 (AI review, version history sections)

All DB and service calls use `run.io_bound` — 7 total in the file.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test INSERT missing required `original_path`**
- **Found during:** Task 1 verification
- **Issue:** Test `_make_db()` INSERT didn't include `original_path` (NOT NULL in schema)
- **Fix:** Added `original_path` and `/tmp/test.pdf` value to INSERT statement
- **Files modified:** tests/test_document_card.py
- **Commit:** 10ccaa1 (included in Task 1 commit)

**2. [Rule 1 - Bug] Updated AppState field count assertion in scaffold test**
- **Found during:** Full suite run after Task 2
- **Issue:** `test_app_scaffold.py` asserted exactly 20 fields; adding `filtered_doc_ids` made it 21
- **Fix:** Updated assertion to 21 with explanatory comment
- **Files modified:** tests/test_app_scaffold.py
- **Commit:** b81419f

**3. [Rule 1 - Bug] Removed dead checkbox widget from status section**
- **Found during:** Task 2 code review before commit
- **Issue:** `show_select` checkbox using hack `type("obj", ...)` was never used — `status_row_el.set_visibility` was called directly
- **Fix:** Removed dead code
- **Files modified:** app/pages/document.py

## Known Stubs

None — all data is wired. `filtered_doc_ids` starts as `[]` on new connections but is populated by `load_table_data` on first registry load. Prev/next buttons are correctly disabled when `filtered_doc_ids` is empty.

## Verification

- `python -m pytest tests/test_document_card.py -x -q` → 3 passed
- `python -m pytest tests/ -q` → 246 passed, 8 xfailed (1 pre-existing failure: `test_ollama_stub` requires running Ollama server — network issue, out of scope)
- `python -c "from app.pages.document import build"` → OK
- `grep -c "run.io_bound" app/pages/document.py` → 7 (≥3 required)
- `wc -l app/pages/document.py` → 210 (≥120 required)

## Self-Check: PASSED
