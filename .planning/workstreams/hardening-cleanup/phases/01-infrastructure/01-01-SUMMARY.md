---
phase: 01-infrastructure
plan: "01"
subsystem: database
tags: [sqlite, migrations, schema, backup]

requires: []
provides:
  - "Versioned schema migrations with schema_migrations table"
  - "_run_migrations() entry point called from Database.__init__"
  - "_migrate_v1_review_columns() replaces fragile try/except OperationalError"
  - "Pre-migration timestamped backup for databases without schema_migrations"
  - "4 unit tests covering fresh DB, v0.4 upgrade, backup creation, idempotency"
affects:
  - 01-02
  - 01-03
  - 01-04

tech-stack:
  added: [shutil, time (stdlib)]
  patterns:
    - "Versioned migration functions: _migrate_vN_name(conn) guarded by _is_migration_applied"
    - "schema_migrations table as single source of truth for applied migrations"
    - "_INDEXES list applied separately after migrations for safe schema upgrade"

key-files:
  created:
    - tests/test_migrations.py
  modified:
    - modules/database.py

key-decisions:
  - "Indexes extracted from _SCHEMA into _INDEXES list applied after migrations — prevents OperationalError when upgrading minimal v0.4 schema"
  - "Backup only when DB is non-empty AND schema_migrations table doesn't yet exist — avoids duplicate backups on repeat opens"
  - "_mark_migration_applied uses INSERT OR IGNORE for idempotency without conditional logic"

patterns-established:
  - "Migration pattern: each version gets _migrate_vN_*(conn) function; add to _run_migrations() to activate"
  - "Schema upgrade safety: always run migrations before index creation"

requirements-completed:
  - FUND-01

duration: 2min
completed: 2026-03-20
---

# Phase 01 Plan 01: Schema Migrations Summary

**Versioned SQLite migration system with schema_migrations table, timestamped pre-upgrade backup, and idempotent _run_migrations() replacing a fragile bare try/except OperationalError pattern**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-19T21:22:26Z
- **Completed:** 2026-03-19T21:24:24Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Replaced `# Миграция v0.3` try/except block with versioned `_migrate_v1_review_columns` guarded by `_is_migration_applied`
- Added `schema_migrations` table tracking applied migrations by version number
- Pre-migration backup (`{stem}_backup_{timestamp}.sqlite`) created automatically on first open of an unversioned database
- 4 unit tests covering all four correctness properties: fresh DB, v0.4 data preservation, backup creation, idempotency

## Task Commits

Each task was committed atomically:

1. **Task 1: Создать тест-файл (RED state)** — `c2a7bc1` (test)
2. **Task 2: Реализовать миграции в database.py (GREEN)** — `adbdd2c` (feat)

_TDD: test commit first, then implementation commit._

## Files Created/Modified

- `tests/test_migrations.py` — 4 unit tests: test_fresh_db, test_v04_upgrade_preserves_rows, test_backup_created, test_idempotent
- `modules/database.py` — added shutil/time imports; added 6 migration helper functions; replaced old migration block in __init__; split _SCHEMA indexes into _INDEXES list

## Decisions Made

- **Indexes separated from _SCHEMA:** The original `_SCHEMA` contained `CREATE INDEX ... ON contracts(contract_type)`. When upgrading a minimal v0.4 DB (which lacks `contract_type`), `executescript(_SCHEMA)` raised `OperationalError`. Fixed by extracting indexes into `_INDEXES` and applying them after migrations with per-index try/except.
- **Backup trigger condition:** Backup is created only when `db_path.stat().st_size > 0` AND `schema_migrations` table is absent — meaning "first time this code sees an existing DB". Prevents redundant backups on subsequent opens.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed OperationalError on v0.4 schema upgrade**
- **Found during:** Task 2 (implementing _run_migrations)
- **Issue:** `executescript(_SCHEMA)` ran `CREATE INDEX ON contracts(contract_type)` which fails when upgrading a minimal v0.4 DB that doesn't have the `contract_type` column — `test_v04_upgrade_preserves_rows` and `test_backup_created` both failed
- **Fix:** Moved the three index DDL statements out of `_SCHEMA` into a `_INDEXES` list; applied them in `__init__` after `_run_migrations()` with per-index `try/except OperationalError`
- **Files modified:** `modules/database.py`
- **Verification:** All 4 migration tests pass GREEN; `python -c "from modules.database import Database..."` prints OK
- **Committed in:** `adbdd2c` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug)
**Impact on plan:** Required for correct upgrade path. No scope creep — fix stays within the database module and doesn't change any public API.

## Issues Encountered

None beyond the auto-fixed index bug above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Migration infrastructure is ready; future migrations follow the established pattern: add `_migrate_vN_*(conn)` and register in `_run_migrations()`
- `schema_migrations` table is the dependency contract for any future plans that need to track schema state
- Plans 01-02, 01-03, 01-04 can proceed without migration concerns

---
*Phase: 01-infrastructure*
*Completed: 2026-03-20*
