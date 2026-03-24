---
gsd_state_version: 1.0
milestone: v0.8
milestone_name: Hardening & Cleanup
status: Ready to execute
stopped_at: Completed 21-ui-fixes 21-02-PLAN.md
last_updated: "2026-03-24T22:35:57.058Z"
last_activity: 2026-03-24
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 3
  completed_plans: 2
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-25)

**Core value:** Юрист загружает папку с документами и за 20 минут получает готовый реестр — без ручного ввода, без обучения, без «проекта внедрения»
**Current focus:** Phase 21 — ui-fixes

## Current Position

Phase: 21 (ui-fixes) — EXECUTING
Plan: 2 of 2

## Performance Metrics

**Velocity:**

- Total plans completed: ~52 (phases 1-19)
- Average duration: ~4 min/plan (v0.6-v0.7 reference)
- Total execution time: ~3.5 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| v0.8 phases | TBD | TBD | TBD |

*Updated after each plan completion*
| Phase 20-data-integrity P01 | 5 | 2 tasks | 2 files |
| Phase 21-ui-fixes P02 | 5 | 1 tasks | 2 files |

## Accumulated Context

### Decisions

Recent decisions affecting v0.8 work:

- [Audit 2026-03-25]: 7 CRITICAL багов задокументированы с точными строками — AUDIT-2026-03-25.md
- [v0.8 Roadmap]: Phase 20 первая — данные важнее UI; починить UPSERT и schema до UI-фиксов
- [v0.8 Roadmap]: Phase 22 (Streamlit удаление) после Phase 21 — не потерять reference при отладке
- [v0.8 Roadmap]: Phase 23 тесты — покрывают уже исправленный код, не сломанный
- [v0.7 Decisions]: tokens.css + --yt-* prefix, @layer discipline, AG Grid --ag-* theming — см. историю выше
- [Phase 20-data-integrity]: UPSERT excludes user-editable fields (review_status, lawyer_comment, manual_status, warning_days) so user annotations survive reprocessing
- [Phase 20-data-integrity]: clear_all() deletes in FK order: payments → document_versions → embeddings → contracts
- [Phase 20-data-integrity]: get_contract_id_by_hash() replaces raw db.conn.execute in controller pipeline for thread safety
- [Phase 21-ui-fixes]: Download route placed after redline route — FastAPI specificity ensures correct matching

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 23]: PROD-04 — L5 verification через провайдер-систему требует рефакторинга ai_extractor.py:518-582
- [Phase 22]: CLEAN-03 — 15 FAIL тестов нужно разобрать до удаления xfail; часть связана с proxy в conftest

## Session Continuity

Last activity: 2026-03-24
Stopped at: Completed 21-ui-fixes 21-02-PLAN.md
Resume file: None
Next: /gsd:plan-phase 20
