---
phase: 06-ai-extractor-wiring
plan: 01
subsystem: ai_extractor
tags: [bug-fix, provider-routing, sanitize, local-llm, wiring]
dependency_graph:
  requires:
    - providers/ollama.py (OllamaProvider.complete)
    - modules/postprocessor.py (sanitize_metadata)
    - modules/models.py (ContractMetadata)
  provides:
    - modules/ai_extractor.py (Provider-aware extract_metadata with _try_provider)
  affects:
    - controller.py (passes provider to extract_metadata)
    - modules/postprocessor.py (now correctly called with dict)
tech_stack:
  added: []
  patterns:
    - _try_provider() helper with retry logic mirrors _try_model() pattern
    - asdict() + sanitize_metadata() + _json_to_metadata() pipeline for postprocessing
key_files:
  created:
    - tests/test_ai_extractor_wiring.py
  modified:
    - modules/ai_extractor.py
decisions:
  - "_try_provider added as separate helper: retry logic identical to _try_model but routes through LLMProvider.complete() interface"
  - "sanitize_metadata applied only for active_provider==ollama: cloud providers return clean responses"
  - "fallback_provider routing via _try_provider takes priority over legacy OPENROUTER_API_KEY path"
  - "asdict() converts ContractMetadata to dict before sanitize_metadata, _json_to_metadata() rebuilds from sanitized dict"
metrics:
  duration: "3min"
  completed: "2026-03-21"
  tasks: 2
  files_created: 1
  files_modified: 1
requirements:
  - SRVR-01
  - SRVR-02
  - PROV-01
  - PROC-01
---

# Phase 06 Plan 01: AI Extractor Wiring Summary

**One-liner:** Provider routing via `_try_provider(provider.complete)` + `sanitize_metadata(asdict(result))` pipeline closes the local LLM extraction gap.

## Objective

Fix two critical integration bugs preventing local LLM (OllamaProvider/llama-server) from processing documents:
1. `extract_metadata` ignored the `provider` parameter — always routed through `_try_model` → `_create_client` (ZAI/OpenRouter)
2. `sanitize_metadata` received a `ContractMetadata` dataclass instead of `dict`, and its return value was discarded

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write regression tests (TDD RED) | 890d72f | tests/test_ai_extractor_wiring.py |
| 2 | Fix provider routing and sanitize call | 2c70e07 | modules/ai_extractor.py, tests/test_ai_extractor_wiring.py |

## What Changed

### modules/ai_extractor.py

**Added `from dataclasses import asdict`** at import level.

**Added `_try_provider()` helper** — mirrors `_try_model()` retry structure but calls `provider.complete(messages)` instead of building an OpenAI client. Raises `RuntimeError` after all retries exhausted.

**Refactored `extract_metadata()` routing:**
```python
if provider is not None:
    raw_text = _try_provider(provider, messages, config.ai_max_retries)
    json_data = _parse_json_response(raw_text)
    result = _json_to_metadata(json_data)
else:
    result = _try_model(config, messages, config.active_model, use_fallback=False)
```

**Fixed `sanitize_metadata` call:**
```python
sanitized = sanitize_metadata(asdict(result))
result = _json_to_metadata(sanitized)
```

**Added `fallback_provider` routing:** when primary provider fails and `fallback_provider is not None`, routes through `_try_provider(fallback_provider, ...)`. Legacy `OPENROUTER_API_KEY` path preserved as secondary fallback.

### tests/test_ai_extractor_wiring.py (new)

5 regression tests:
- `test_provider_route_called` — provider.complete() called, _try_model not called
- `test_legacy_route_when_no_provider` — _try_model used when provider=None
- `test_sanitize_receives_dict_not_dataclass` — sanitize_metadata receives dict
- `test_sanitize_return_value_used` — sanitize return value rebuilds ContractMetadata
- `test_fallback_provider_used_on_failure` — fallback_provider.complete() called on primary failure

## Deviations from Plan

None — plan executed exactly as written.

## Verification

```
tests/test_ai_extractor_wiring.py: 5 passed
Full suite: 223 passed, 8 xfailed, 1 pre-existing failure (test_ollama_stub — llama-server not running in CI)
```

Pre-existing failure `test_providers.py::test_ollama_stub` is unrelated — it connects to localhost:8080 which isn't running in the test environment. Not introduced by this plan.

## Requirements Closed

| REQ-ID | Status Before | Status After |
|--------|--------------|-------------|
| SRVR-01 | partial | satisfied — llama-server now reachable via OllamaProvider.complete() |
| SRVR-02 | partial | satisfied — requests now route to local server |
| PROV-01 | partial | satisfied — provider param is live code, not dead |
| PROC-01 | unsatisfied | satisfied — sanitize_metadata receives dict, return value used |

## Known Stubs

None.

## Self-Check: PASSED

- [x] tests/test_ai_extractor_wiring.py exists: FOUND
- [x] modules/ai_extractor.py modified: FOUND
- [x] commit 890d72f exists: FOUND
- [x] commit 2c70e07 exists: FOUND
- [x] `grep -c "provider.complete" modules/ai_extractor.py` → 2
- [x] `grep -c "asdict" modules/ai_extractor.py` → 3
- [x] `grep -c "_try_provider" modules/ai_extractor.py` → 4
- [x] `grep -c "sanitize_metadata(asdict" modules/ai_extractor.py` → 2
- [x] `grep -c "_try_model" modules/ai_extractor.py` → 4 (legacy path preserved)
