# Project Research Summary

**Project:** ЮрТэг — Milestone 1 (deadline tracking, notifications, multi-provider AI, on-premise readiness)
**Domain:** Legal document processing pipeline — Python/Streamlit desktop app, brownfield evolution
**Researched:** 2026-03-19
**Confidence:** MEDIUM-HIGH

## Executive Summary

ЮрТэг is a local-first legal document processing tool that extracts metadata from PDF/DOCX contracts using AI, organizes files, and generates a registry. The existing MVP (v0.4) is a working Streamlit/SQLite/openai-SDK pipeline. Milestone 1 is a focused brownfield extension — not a rewrite — adding four capabilities: document status lifecycle with deadline tracking, in-app and Telegram notifications, multi-provider AI with automatic fallback, and architectural groundwork for on-premise B2B deployment. Research confirms that all four capabilities can be implemented using minimal new dependencies (APScheduler 3.x, python-telegram-bot 22.7, thin openai SDK wrapper) while maintaining the existing architecture.

The recommended approach is strictly additive and surgical: introduce a `providers/` directory for AI abstraction, a `services/` layer as a stable facade separating business logic from Streamlit, and `deadline_service` for notification logic. Document status should be computed at query time (not stored) to avoid staleness bugs. FastAPI is explicitly deferred — it adds deployment complexity with no current benefit for an in-process desktop app, and the service layer already enables a future FastAPI router with zero code duplication. The Russian SMB legal market strongly prefers Telegram over email for notifications, and local-first architecture is the primary competitive differentiator versus cloud-only global CLMs and heavy Russian enterprise СЭД platforms.

The three highest-severity risks are: (1) AI-extracted dates stored raw without normalization causing silent reminder failures, (2) the existing `try/except OperationalError` SQLite migration pattern breaking existing user databases on upgrade when new columns are added, and (3) multi-provider abstraction drifting into an overengineered custom LLM framework. All three must be addressed at the start of Milestone 1 before any feature code is written. Security (no `--local-only` mode, no audit log) is flagged as a deal-breaker for the enterprise B2B segment and must ship together with on-premise packaging, not as a separate follow-up.

---

## Key Findings

### Recommended Stack

The existing stack (Python 3.12, Streamlit, SQLite, openai SDK) requires only three net-new libraries for Milestone 1. APScheduler 3.11.2 (not the 4.x alpha) provides background deadline checking without blocking Streamlit's main thread — the scheduler writes alerts to SQLite, and the UI reads them on rerender via `st.toast`, which decouples the scheduler from Streamlit's session context. For Telegram notifications, python-telegram-bot 22.7 is used in one-way push mode only (`Bot.send_message()`), called via `asyncio.run()` from the APScheduler background thread. Multi-provider AI requires zero new dependencies — all three target providers (ZAI/GLM, OpenRouter, Ollama) expose OpenAI-compatible endpoints and are handled by the existing openai SDK with `base_url` overrides.

**Core technologies:**
- APScheduler 3.11.2: background deadline checking daemon thread — stable branch, alpha 4.x explicitly rejected
- python-telegram-bot 22.7: outbound-only Telegram push notifications — simpler than aiogram for non-interactive use
- openai SDK (existing): thin `ProviderRouter` wrapper over `base_url` — replaces LiteLLM (50+ transitive deps, overkill)
- FastAPI 0.135.1: business logic extraction target — deferred from Milestone 1 runtime, service layer is the actual deliverable
- st.toast (existing Streamlit): in-app deadline alerts — zero new dependency

**Explicitly rejected:** LiteLLM (50+ deps, adds memory pressure on Streamlit Cloud for no benefit over base_url pattern), LangChain (wrong abstraction for single-call extraction), APScheduler 4.x alpha, Celery (requires Redis, incompatible with single-process desktop).

### Expected Features

The feature research cross-references CLM industry patterns, competitor analysis (Juro, Ironclad, DIRECTUM, Docsvision), and CustDev findings (9 interviews). ЮрТэг's differentiation space — AI-powered + zero-onboarding + local-first + affordable — is made tangible day-to-day by status tracking and deadline reminders. Email notifications are an anti-feature for this market: Russian legal professionals have higher Telegram engagement than email; SMTP adds server infrastructure that contradicts zero-onboarding.

**Must have (table stakes — P1, current milestone):**
- Document status with 7 states (черновик / на согласовании / подписан / действует / истекает / истёк / расторгнут) and color-coded registry rows
- Configurable reminder threshold (30/60/90 days) — simplest config field, highest reported user value
- In-app "требует внимания" panel on launch — passive, zero user setup
- Manual status override — AI is not always right; users must correct lifecycle state
- Filter/sort registry by status — status is useless without filterability
- Multi-provider AI (GLM primary, OpenRouter fallback, Ollama future) — architectural requirement for B2B on-premise segment

**Should have (competitive — P2, add when stable):**
- Telegram notifications — trigger: users ask "can I be notified when the app is closed?"
- AI-confidence score visible in UI — trigger: users report errors they couldn't anticipate
- Deadline history/audit log — trigger: compliance-oriented user segment grows

**Defer (v2+):**
- Batch status update (500+ document scale not yet reached)
- Multi-user registry access (requires auth, breaks local-first)
- Email notifications (only if Telegram adoption proves insufficient)
- OS-level push notifications (requires tray app, separate tech stack)
- Cloud backup/sync (security barrier #1 per CustDev — contradicts positioning)

### Architecture Approach

The recommended architecture is a three-layer brownfield addition to the existing codebase: a `providers/` package abstracting AI vendor specifics behind an `LLMProvider` ABC, a `services/` package grouping business operations (pipeline, registry, deadline) as stable facades callable by both Streamlit and any future FastAPI router, and unchanged processing modules (`scanner`, `extractor`, `anonymizer`, `ai_extractor`, `validator`, `database`, `organizer`, `reporter`). Document status is computed at query time using SQL `CASE` expressions over `date_end`, never stored as a column updated by a background job — this eliminates the staleness bug class entirely. FastAPI is designed as a future thin router over the service layer, not a current deployment requirement.

**Major components (new additions):**
1. `providers/base.py` + `providers/zai.py` + `providers/openrouter.py` — LLMProvider ABC isolating vendor specifics from extraction logic; adding a new provider = one new file
2. `services/pipeline_service.py` — process_archive() facade; what Streamlit calls today, what FastAPI calls tomorrow
3. `services/registry_service.py` — query, filter, report generation
4. `services/deadline_service.py` — approaching deadline queries, notification formatting
5. `modules/models.py` (extended) — DocumentStatus enum, DeadlineAlert dataclass

**Build order dependency (critical):** Provider abstraction and schema migration infrastructure must be complete before any deadline or notification feature code is written. Service layer can be built in parallel with provider abstraction.

### Critical Pitfalls

1. **AI dates stored raw without normalization** — Add a dedicated date normalization pass using `dateutil.parser.parse()` immediately after AI extraction; store only ISO 8601 strings; surface LOW-confidence dates with a UI warning before any reminder fires. Must be implemented before reminder logic.

2. **SQLite migration breaks existing user databases** — Replace the existing `try/except OperationalError` column-addition pattern with a versioned `schema_migrations` table (50 lines). Backfill `status = 'active'` for all existing rows. This is the first task in Milestone 1, not an afterthought.

3. **Reminder logic built into Streamlit session** — Scheduler state must live in SQLite, not in `st.session_state`. APScheduler BackgroundScheduler must be guarded against double-registration (`if 'scheduler_started' not in st.session_state`). Reminders must be testable without a running Streamlit server.

4. **On-premise treated as packaging, not architecture** — `--local-only` mode (env var `LOCAL_ONLY=true` that blocks all external HTTP calls) and an append-only `audit.log` must ship together with the Docker image, not as a subsequent item. These are the trust signals that make the enterprise sale, not the Dockerfile itself.

5. **Multi-provider abstraction drifts into custom framework** — The entire abstraction is: a `ProviderConfig` dataclass, a factory function `get_provider(config) -> LLMProvider`, and one file per provider. Any file named `router.py`, `gateway.py`, or `llm_manager.py` is a warning sign. Code review gate must enforce this.

---

## Implications for Roadmap

Based on combined research, four phases are suggested. The ordering is driven by hard dependency constraints identified in the architecture research (provider abstraction and migration infrastructure are prerequisites for all features) and the pitfall research (infrastructure failures are harder to recover from than feature gaps).

### Phase 1: Infrastructure Foundation

**Rationale:** Two blocking prerequisites must be resolved before any feature can be safely built. SQLite migration fragility (PITFALL 5) affects every subsequent database change. Provider abstraction (ARCHITECTURE Step 1) is required before the multi-provider feature and before on-premise packaging. Both are zero-behavior-change refactors — safe to do first, dangerous to defer.

**Delivers:** Versioned schema migration system; `providers/` package with ZAI and OpenRouter providers extracted from current `ai_extractor.py`; `services/` skeleton (pipeline, registry services); `config.py` extended with `active_provider` and provider configs.

**Addresses:** Multi-provider AI (P1 feature prerequisite); clean upgrade path for all future schema changes.

**Avoids:** SQLite migration corruption (PITFALL 5); provider abstraction drift (PITFALL 3); vendor lock in prompt logic (ARCHITECTURE anti-pattern 2).

**Research flag:** Standard patterns — no additional research needed. Direct codebase analysis in ARCHITECTURE.md provides the exact refactoring steps.

---

### Phase 2: Deadline Tracking and Document Status

**Rationale:** Once the service layer and schema migration infrastructure exist, deadline tracking is purely additive: new columns, new service, new UI elements. Date normalization (PITFALL 1) must be implemented here, not discovered later. Status computation at query time (ARCHITECTURE anti-pattern 3 avoidance) is a design decision that must be made in this phase.

**Delivers:** Document status lifecycle (7 states, color-coded registry); `date_end` normalization with `confidence_date_end` flag; `services/deadline_service.py`; configurable reminder threshold (global setting); in-app "требует внимания" panel on launch; filter/sort by status.

**Addresses:** All P1 table-stakes features (document status, reminder threshold, in-app panel, manual status override, filter by status).

**Avoids:** Raw date storage (PITFALL 1); computed status staleness (ARCHITECTURE anti-pattern 3); performance trap of Python-loop status checking (use SQL `WHERE date_end BETWEEN` queries).

**Research flag:** Standard patterns — deadline service and status computation are well-documented SQL + Python patterns. No additional research needed.

---

### Phase 3: Notifications (In-App + Telegram)

**Rationale:** Notifications depend on deadline tracking (Phase 2) being complete and stable. APScheduler integration has known Streamlit threading caveats (PITFALL 2, STACK threading caveat) that require careful implementation — safer to validate deadline logic separately before adding scheduler complexity. Telegram is a separate delivery channel on top of in-app alerts, not a replacement.

**Delivers:** APScheduler BackgroundScheduler with double-registration guard; SQLite `alerts` table (write from scheduler, read on Streamlit rerender via `st.toast`); optional Telegram bot integration (token from env var only, never config file); async `send_deadline_alert()` called via `asyncio.run()` from scheduler thread; `pending_notifications` table for async delivery decoupling.

**Addresses:** P2 Telegram notifications; in-app panel refinement (acknowledgement, history).

**Avoids:** Reminder logic in Streamlit session (PITFALL 2); Telegram token in config (SECURITY pitfall); synchronous Telegram call blocking processing thread (INTEGRATION gotcha).

**Research flag:** Needs attention. APScheduler + Streamlit threading interaction has community-documented edge cases. The `ScriptRunContext` / `NoSessionContext` error pattern when calling `st.*` from background threads must be validated against the current Streamlit version before implementation.

---

### Phase 4: On-Premise Packaging and Security Hardening

**Rationale:** Docker packaging is purely additive (no code changes) and can only be correctly done once the service layer is stable (Phase 1) and features are complete (Phases 2-3). Security hardening (`--local-only` mode, audit log, path traversal fix) must ship together with the Docker image — they are the trust signals for the B2B segment, not optional polish.

**Delivers:** `Dockerfile` (multi-stage) + `docker-compose.yml` with volume mounts for documents, output, and SQLite; `LOCAL_ONLY=true` env var that blocks all external HTTP calls and raises exceptions; append-only `audit.log` (file-based, not just SQLite) recording filename hash, provider used, data-left-machine flag; path traversal fix in `organizer.py` (`Path.resolve()` check); `@st.cache_data(ttl=30)` on registry query to prevent sluggish UI at 500+ contracts; `PRAGMA journal_mode=WAL` in SQLite for concurrent access.

**Addresses:** On-premise B2B segment requirements; security checklist for enterprise sale; performance traps at scale.

**Avoids:** On-premise as packaging only (PITFALL 4); path traversal vulnerability (SECURITY pitfall); no `--local-only` mode (security mistake).

**Research flag:** `--local-only` enforcement pattern (how to intercept all outbound HTTP calls in a Streamlit + openai SDK + python-telegram-bot app) may need a brief spike — specifically whether patching at the `httpx` transport level is sufficient or whether each library needs explicit gating.

---

### Phase Ordering Rationale

- Phase 1 before everything: migration infrastructure and provider abstraction are prerequisites, not optimizations. Skipping them means Phases 2-4 introduce compounding tech debt.
- Phase 2 before Phase 3: notifications require deadline tracking to have stable, validated `date_end` data. Building the scheduler before date normalization means reminders fire on hallucinated dates.
- Phase 3 before Phase 4: packaging should include the complete notification feature set so on-premise deployments get all v1 functionality.
- FastAPI explicitly excluded from Milestone 1: the service layer (Phase 1) is the prerequisite. FastAPI as a running HTTP server adds two-process complexity with no current benefit for a single-machine desktop app.

### Research Flags

Phases needing attention during planning:
- **Phase 3 (Notifications):** APScheduler + Streamlit threading caveats need version-specific validation. The `scheduler_started` guard pattern from community docs should be tested against current Streamlit before implementation begins.
- **Phase 4 (On-Premise):** `LOCAL_ONLY` enforcement strategy — specifically how to block outbound calls across openai SDK, python-telegram-bot (which uses httpx internally), and any other HTTP clients — needs a brief implementation spike before committing to the approach.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Infrastructure):** Direct codebase analysis already provides exact refactoring steps. ABC provider pattern and service layer extraction are well-documented Python patterns.
- **Phase 2 (Deadline Tracking):** SQL-based status computation and date normalization with `dateutil` are standard. Feature requirements are fully specified.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core libraries verified via PyPI and official docs. APScheduler 3.x, python-telegram-bot 22.7, openai SDK base_url pattern all confirmed. FastAPI/uvicorn versions verified. LiteLLM rejection well-reasoned from direct dependency analysis. |
| Features | MEDIUM-HIGH | CLM industry patterns cross-referenced across multiple sources. Russian market specifics inferred from CustDev data (9 interviews, mix of real and synthetic). P1 feature set has strong convergent validity across research and CustDev. P2/P3 trigger conditions are hypotheses pending user feedback. |
| Architecture | HIGH | Based on direct codebase analysis of current `ai_extractor.py`, `config.py`, and `main.py`. ABC provider pattern and service layer extraction are established Python patterns with clear rationale for this codebase. Build order dependency constraints are directly derived from code structure. |
| Pitfalls | MEDIUM-HIGH | Critical pitfalls (date normalization, SQLite migration, scheduler threading) are directly observed from CONCERNS.md codebase analysis — HIGH confidence. On-premise enterprise trust signals inferred from PROJECT.md CustDev and general enterprise patterns — MEDIUM confidence. Performance traps at scale are threshold estimates, not measured values. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **APScheduler thread lifecycle in Streamlit Cloud:** Streamlit Community Cloud may restart processes in ways that affect the BackgroundScheduler's daemon thread. The desktop deployment path is clear; cloud deployment behavior of the scheduler needs validation if Streamlit Cloud remains a target.
- **GLM-specific error codes:** PITFALL research flags that GLM returns different HTTP status codes than OpenAI for rate limits and content policy violations. The exact error mapping needs a test harness against the live GLM API before the fallback logic can be declared correct.
- **Reminder threshold per-document vs global:** Feature research recommends launching with a global threshold (simpler). Whether the target user segment wants per-contract-type thresholds is a validated CustDev hypothesis but not a confirmed requirement. This gap should be raised during roadmap planning.
- **Ollama model quality for legal Russian text:** Local QWEN via Ollama is targeted for Milestone 3. The extraction prompt's performance against a Russian-language local model is untested. This gap is acceptable for Milestone 1 but must be addressed before the on-premise offline variant is promised to customers.

---

## Sources

### Primary (HIGH confidence)
- Current codebase direct analysis: `modules/ai_extractor.py`, `config.py`, `main.py`, CONCERNS.md — architecture and pitfall findings
- APScheduler 3.x User Guide — BackgroundScheduler docs: https://apscheduler.readthedocs.io/en/3.x/userguide.html
- Streamlit multithreading docs: https://docs.streamlit.io/develop/concepts/design/multithreading
- st.toast official docs: https://docs.streamlit.io/develop/api-reference/status/st.toast
- python-telegram-bot v22.7 PyPI and docs: https://pypi.org/project/python-telegram-bot/
- FastAPI PyPI v0.135.1: https://pypi.org/project/fastapi/
- LiteLLM GitHub (for rejection rationale): https://github.com/BerriAI/litellm
- PROJECT.md CustDev findings (9 interviews)

### Secondary (MEDIUM confidence)
- APScheduler PyPI version confirmation: https://pypi.org/project/APScheduler/
- FastAPI + Streamlit two-tier pattern: https://pybit.es/articles/from-backend-to-frontend-connecting-fastapi-and-streamlit/
- Streamlit service layer community pattern: https://discuss.streamlit.io/t/project-structure-for-medium-and-large-apps-full-example-ui-and-logic-splitted/59967
- CLM feature standards: ContractSafe, Agiloft, Juro (2025-2026 sources)
- Multi-provider LLM orchestration: https://dev.to/ash_dubai/multi-provider-llm-orchestration-in-production-a-2026-guide-1g10
- Legal tech pitfalls: American Bar Association (2025), LexWorkplace, LegalSoft
- Ten Python datetime pitfalls: https://dev.arie.bovenberg.net/blog/python-datetime-pitfalls/

### Tertiary (LOW confidence)
- Telegram bot deadline notifications blog: https://medium.com/@ewho.ruth2014/adding-telegram-bot-notifications-for-task-deadlines-41981bb0957c — implementation details need verification
- LiteLLM alternatives comparison: https://mljourney.com/litellm-alternatives-advanced-solutions-for-multi-model-llm-integration/ — single source

---
*Research completed: 2026-03-19*
*Ready for roadmap: yes*
