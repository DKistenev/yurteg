# Phase 20: Data Integrity - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase, discuss skipped)

<domain>
## Phase Boundary

Починить потерю данных при повторной обработке документов. 4 requirement-а:
- DATA-01: INSERT OR REPLACE → UPSERT чтобы не стирать lawyer_comment, review_status, manual_status, warning_days
- DATA-02: FK enforcement (PRAGMA foreign_keys = ON) + фикс document_versions/payments/embeddings не рвутся
- DATA-03: Добавить payment_terms, payment_amount, payment_frequency, payment_direction в schema (migration v7), но НЕ is_template и НЕ confidence (решение пользователя)
- DATA-04: Деанонимизировать subject и special_conditions (не только counterparty и parties)

Audit reference: .planning/AUDIT-2026-03-25.md

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure/bugfix phase. Key constraints from audit:

- database.py:314-326 — INSERT OR REPLACE → INSERT ... ON CONFLICT(file_hash) DO UPDATE SET (list specific columns, exclude id, review_status, lawyer_comment, manual_status, warning_days)
- database.py — add PRAGMA foreign_keys = ON after connection open
- database.py — migration v7: add payment_terms TEXT, payment_amount REAL, payment_frequency TEXT, payment_direction TEXT columns
- database.py:save_result() — persist payment_* fields
- controller.py:204-216 — extend deanonymization to subject and special_conditions fields
- database.py:379-384 — clear_all() should also delete from document_versions, payments, embeddings
- controller.py:289-293, 310-314 — wrap raw db.conn access in db._lock or add proper Database methods

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- `modules/database.py` — SQLite operations, schema, migrations v1-v6
- `controller.py` — pipeline orchestration, deanonymization
- `modules/models.py` — ContractMetadata dataclass with payment fields
- `services/payment_service.py` — uses payment_amount/frequency from ContractMetadata

### Established Patterns
- Migrations use `_is_migration_applied()` + `ALTER TABLE IF NOT EXISTS` pattern
- Threading lock via `self._lock = threading.Lock()` on Database class
- Deanonymization via `_deanonymize()` with regex replacement

</code_context>

<specifics>
## Specific Ideas

User decided: do NOT add is_template or confidence columns. Only payment_* fields.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
