---
phase: 20-data-integrity
plan: 01
subsystem: database
tags: [sqlite, upsert, migration, fk, deanonymization]

# Dependency graph
requires: []
provides:
  - UPSERT in contracts table preserving review_status, lawyer_comment, manual_status, warning_days
  - PRAGMA foreign_keys = ON on every DB connection
  - Migration v7 adding payment_terms, payment_amount, payment_frequency, payment_direction columns
  - save_result() persisting all 4 payment fields
  - clear_all() correctly deleting payments/document_versions/embeddings before contracts
  - get_contract_id_by_hash() thread-safe helper method
  - subject and special_conditions deanonymized with real names in controller pipeline
  - No raw db.conn.execute in controller pipeline

affects: [21-ui-fixes, 23-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ON CONFLICT(file_hash) DO UPDATE SET — UPSERT preserving user-editable fields"
    - "Migration vN pattern with _is_migration_applied / _mark_migration_applied guards"
    - "db.get_contract_id_by_hash() instead of raw db.conn.execute in pipeline"

key-files:
  created: []
  modified:
    - modules/database.py
    - controller.py

key-decisions:
  - "UPSERT excludes id, review_status, lawyer_comment, manual_status, warning_days from UPDATE SET — user data survives reprocessing"
  - "clear_all() deletes child tables in FK order: payments → document_versions → embeddings → contracts"
  - "get_contract_id_by_hash() wraps raw SQL in _lock for thread safety, replaces inline db.conn.execute"
  - "move_record_to_client() left using from_db.conn/to_db.conn — different variable scope, not the pipeline db variable, out of this plan's scope"

patterns-established:
  - "Database methods only in pipeline — no raw .conn access from controller.py"
  - "Deanonymize all human-readable fields: counterparty, parties, subject, special_conditions"

requirements-completed: [DATA-01, DATA-02, DATA-03, DATA-04]

# Metrics
duration: 5min
completed: 2026-03-25
---

# Phase 20 Plan 01: Data Integrity Summary

**SQLite UPSERT preserving user annotations, FK constraints enabled, payment columns migrated, subject/special_conditions deanonymized with real names**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-24T22:25:02Z
- **Completed:** 2026-03-24T22:30:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Replaced INSERT OR REPLACE with ON CONFLICT UPSERT — review_status, lawyer_comment, manual_status, warning_days now survive reprocessing
- Enabled PRAGMA foreign_keys = ON on every Database connection — orphaned rows impossible
- Added migration v7 with 4 payment columns; save_result() persists them; clear_all() respects FK order
- Extended deanonymization to subject and special_conditions — real names in DB instead of [ФИО_1] masks
- Replaced two raw db.conn.execute calls in controller pipeline with thread-safe db.get_contract_id_by_hash()

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix database.py — UPSERT, FK pragma, migration v7, clear_all, payment persistence** - `53af789` (fix)
2. **Task 2: Fix controller.py — deanonymize subject/special_conditions, replace raw db.conn** - `078a8bb` (fix)

## Files Created/Modified

- `modules/database.py` — PRAGMA FK, UPSERT, migration v7, clear_all fix, get_contract_id_by_hash
- `controller.py` — deanonymize subject + special_conditions, db.get_contract_id_by_hash() in versioning and payments blocks

## Decisions Made

- UPSERT UPDATE SET deliberately omits user-editable fields (id, review_status, lawyer_comment, manual_status, warning_days) — these are preserved across reprocessing
- clear_all() now deletes in child-first FK order to avoid constraint violations when foreign_keys = ON
- move_record_to_client() uses from_db.conn/to_db.conn variables — different from the pipeline `db` variable, left as-is (refactoring it would be architectural scope creep for this plan)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Data integrity is solid — user annotations survive reprocessing, payment data persists, real names in DB
- Phase 21 (UI fixes) can proceed with confidence that DB layer is correct
- Phase 23 (tests) can now test UPSERT behavior and deanonymization correctness

---
*Phase: 20-data-integrity*
*Completed: 2026-03-25*
