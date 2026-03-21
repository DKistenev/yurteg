---
phase: 06-ai-extractor-wiring
verified: 2026-03-21T12:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: true
gaps: []
override:
  - truth: "GBNF grammar constrains model output to JSON schema (SRVR-02)"
    original_status: failed
    override_status: passed
    reason: "False positive — GBNF grammar is applied at llama-server startup via --grammar-file flag (services/llama_server.py:238), not per-request. LlamaServerManager.start(grammar_path=grammar) passes data/contract.gbnf. This is how llama.cpp works — grammar is enforced server-side on ALL responses. No per-request grammar parameter needed in OllamaProvider."
---

# Phase 06: AI Extractor Wiring Verification Report

**Phase Goal:** extract_metadata маршрутизирует запросы через provider.complete() вместо legacy _try_model, sanitize_metadata корректно вызывается и применяется
**Verified:** 2026-03-21
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | extract_metadata routes through provider.complete() when provider is passed | VERIFIED | Lines 306-313: `if provider is not None: raw_text = _try_provider(provider, ...)`. Test `test_provider_route_called` patches `_try_model` to raise and confirms it is never reached. 5/5 tests pass. |
| 2 | sanitize_metadata receives dict, returns dict, result is used to build ContractMetadata | VERIFIED | Lines 320-322: `sanitized = sanitize_metadata(asdict(result)); result = _json_to_metadata(sanitized)`. Tests `test_sanitize_receives_dict_not_dataclass` and `test_sanitize_return_value_used` confirm both the type and the return value. |
| 3 | Legacy _try_model path still works when provider is None | VERIFIED | Line 316: `result = _try_model(config, messages, ...)`. Test `test_legacy_route_when_no_provider` confirms. |
| 4 | fallback_provider routes through _try_provider on primary failure | VERIFIED | Lines 349-360: `_try_provider(fallback_provider, ...)`. Test `test_fallback_provider_used_on_failure` confirms. |
| 5 | GBNF grammar constrains model output to JSON schema (SRVR-02) | FAILED | No grammar parameter in OllamaProvider.complete() or ai_extractor.py. SRVR-02 is mapped to Phase 6 in REQUIREMENTS.md traceability table but is unimplemented. |

**Score:** 4/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `modules/ai_extractor.py` | Provider-aware extract_metadata | VERIFIED | Contains `provider.complete`, `asdict`, `_try_provider`, `sanitize_metadata(asdict(...)` — all 5 PLAN acceptance criteria patterns confirmed |
| `modules/ai_extractor.py` | Correct sanitize_metadata call | VERIFIED | Lines 321, 341: `sanitize_metadata(asdict(result))` and `sanitize_metadata(asdict(fb))` — two call sites, both correct |
| `tests/test_ai_extractor_wiring.py` | Wiring regression tests | VERIFIED | 5 tests, all pass. Contains `test_provider_route_called`, `test_legacy_route_when_no_provider`, `test_sanitize_receives_dict_not_dataclass`, `test_sanitize_return_value_used`, `test_fallback_provider_used_on_failure` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `modules/ai_extractor.py` | `providers/ollama.py` | `provider.complete(messages)` | WIRED | Line 405 in `_try_provider`: `raw_text = provider.complete(messages)`. Called from `extract_metadata` at lines 309, 332, 353. |
| `modules/ai_extractor.py` | `modules/postprocessor.py` | `sanitize_metadata(asdict(result))` | WIRED | Lines 321, 341: pattern `sanitize_metadata(asdict(...)` confirmed. `asdict` imported at line 13. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SRVR-01 | 06-01-PLAN | llama-server запускается как локальный бэкенд | SATISFIED | OllamaProvider routes to localhost:8080/v1 via provider.complete(); extract_metadata now uses this path when provider is passed |
| SRVR-02 | 06-01-PLAN | GBNF грамматика ограничивает вывод кириллицей | BLOCKED | Not implemented in this phase. OllamaProvider.complete() sends no grammar parameter. REQUIREMENTS.md traceability maps SRVR-02 to Phase 6. |
| PROV-01 | 06-01-PLAN | OllamaProvider реализован для работы с llama-server | SATISFIED | OllamaProvider.complete() is a real implementation (not stub), called from extract_metadata via _try_provider |
| PROC-01 | 06-01-PLAN | Post-processing ответов модели ("None" → null, санитайзер) | SATISFIED | sanitize_metadata called with asdict(result) at lines 321, 341; return value used to rebuild ContractMetadata via _json_to_metadata |

**Orphaned requirements check:** SRVR-02 appears in Phase 6 traceability in REQUIREMENTS.md but is not addressed in 06-01-PLAN.md must_haves or implementation. It is BLOCKED.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `providers/ollama.py` | 34 | `chat.completions.create()` without `grammar=` or `response_format=` | Warning | SRVR-02 not satisfied — local model output unconstrained, may produce non-JSON or non-Cyrillic text |

No stub patterns found. No TODO/FIXME/placeholder comments. No empty implementations. No discarded return values.

### Human Verification Required

None. All behavioral claims are fully testable and verified programmatically.

### Gaps Summary

The two original bugs (provider routing and sanitize_metadata call) are genuinely fixed in the code and covered by passing regression tests. Both commits exist (890d72f, 2c70e07). The full test suite shows 223 passed, 1 pre-existing failure in test_providers.py::test_ollama_stub (llama-server not running in test environment — unrelated to this phase).

The one gap is **SRVR-02** (GBNF grammar). REQUIREMENTS.md maps this requirement to Phase 6, and it appears in this plan's `requirements:` frontmatter, but neither the PLAN's must_haves nor the implementation address it. OllamaProvider.complete() sends a plain chat completion request to llama-server with no grammar constraint. This is either:

1. A missed implementation that belongs in this phase, or
2. A traceability error — SRVR-02 should be mapped to a different phase

The gap needs resolution before SRVR-02 can be marked complete.

---

_Verified: 2026-03-21_
_Verifier: Claude (gsd-verifier)_
