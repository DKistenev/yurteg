# Phase 38: Cross-Scope + Config Hardening - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase, discuss skipped)

<domain>
## Phase Boundary

Разблокировать VioletRiver Phase 36 (APP_VERSION, STATUS_LABELS с css_class, database dict-only) и сделать Config безопасным (__post_init__ валидация, active_model fix, atomic settings, bare except cleanup).

Requirements: XSCOPE-04, XSCOPE-05, XSCOPE-06, CONF-01, CONF-02, CONF-03, CONF-04, CONF-05, CONF-06

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — infrastructure phase. Key constraints from research:
- RLock not needed yet (Phase 41) — just Lock for settings
- __post_init__ should raise ValueError, not silently clamp
- STATUS_LABELS 4th element: Tailwind css classes string (e.g. "bg-green-100 text-green-700")
- APP_VERSION: simple string constant at module level
- Atomic write: tempfile.mkstemp() + os.fsync() + os.replace()
- active_model: property should check active_provider and return correct model name

</decisions>

<code_context>
## Existing Code Insights

### Files to modify
- `config.py` — APP_VERSION, __post_init__(), active_model fix, atomic settings, bare except, telegram_chat_id, validation_mode
- `services/lifecycle_service.py` — STATUS_LABELS with css_class
- `modules/database.py` — dict-only returns from get_contract_by_id, get_all_results

### Established Patterns
- Config is a @dataclass with field defaults
- STATUS_LABELS is a dict mapping status → tuple(icon, label, hex_color)
- database.py uses sqlite3.Row with row_factory

</code_context>

<specifics>
## Specific Ideas

- XSCOPE items are cross-scope blockers — VioletRiver Phase 36 depends on them
- Notify VioletRiver via mcp_agent_mail after each XSCOPE commit

</specifics>

<deferred>
## Deferred Ideas

None — infrastructure phase.

</deferred>
