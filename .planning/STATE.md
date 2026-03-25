---
gsd_state_version: 1.0
milestone: v0.8.1
milestone_name: UI Polish
status: Defining requirements
stopped_at: null
last_updated: "2026-03-25T00:00:00.000Z"
last_activity: 2026-03-25
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-25)

**Core value:** Юрист загружает папку с документами и за 20 минут получает готовый реестр — без ручного ввода, без обучения, без «проекта внедрения»
**Current focus:** Phase 23 — production-readiness

## Current Position

Phase: 23
Plan: Not started

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
| Phase 21-ui-fixes P01 | 5 | 2 tasks | 6 files |
| Phase 22-code-cleanup P01 | 8min | 2 tasks | 15 files |
| Phase 22-code-cleanup P02 | 25min | 1 tasks | 7 files |
| Phase 23-production-readiness P02 | 15min | 2 tasks | 5 files |
| Phase 23-production-readiness P01 | 15min | 2 tasks | 10 files |

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
- [Phase 21-ui-fixes]: logger.exception() used (not logger.error()) to capture full traceback in all silent except blocks
- [Phase 21-ui-fixes]: Dead action_review_btn removed from document.py — duplicate of working review_btn
- [Phase 22-code-cleanup]: CLEAN-01: Deleted Streamlit main.py (2247 lines) and desktop_app.py — both replaced by NiceGUI app/main.py
- [Phase 22-code-cleanup]: CLEAN-02: _merge_system_into_user moved to single source in providers/openrouter.py; active_model simplified to 'glm-4.7'; AppState reduced from 19 to 16 fields
- [Phase 22-code-cleanup]: CLEAN-03: proxy env cleanup is session-scoped in conftest.py — fixes httpx socks5h failures in 10 tests
- [Phase 22-code-cleanup]: CLEAN-03: test_design_polish assertions moved from Tailwind classes in main.py to hex values in design-system.css
- [Phase 23-production-readiness]: Controller tests patch at import site (controller.scan_directory) not at source — ensures mock intercepts Python's already-imported reference
- [Phase 23-production-readiness]: FullCalendar v6 CSS is bundled into JS — placeholder CSS file created for lazy-loader link compatibility
- [Phase 23-production-readiness]: OllamaProvider port is now config-driven via config.llama_server_port; verify_metadata/verify_api_key delegate to provider system

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 23]: PROD-04 — L5 verification через провайдер-систему требует рефакторинга ai_extractor.py:518-582
- [Phase 22]: CLEAN-03 — 15 FAIL тестов нужно разобрать до удаления xfail; часть связана с proxy в conftest

## Session Continuity

Last activity: 2026-03-24
Stopped at: Completed 23-production-readiness 23-01-PLAN.md
Resume file: None
Next: /gsd:plan-phase 20
