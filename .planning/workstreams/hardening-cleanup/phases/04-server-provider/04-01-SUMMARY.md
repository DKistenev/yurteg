---
phase: 04-server-provider
plan: 01
subsystem: infra
tags: [llama-server, llama.cpp, gguf, huggingface_hub, gbnf, postprocessor, local-llm, subprocess]

# Dependency graph
requires:
  - phase: 03-integrations-multitenancy
    provides: provider abstraction (OllamaProvider stub, LLMProvider base class)
provides:
  - LlamaServerManager class for downloading model/binary and managing llama-server lifecycle
  - GBNF grammar constraining ContractMetadata JSON output with enum validation
  - Field-level post-processing sanitizer with per-profile character cleaning
affects:
  - 04-02 (OllamaProvider implementation will call LlamaServerManager.start() and use base_url)
  - providers/ollama.py (gets base_url from LlamaServerManager)
  - modules/ai_extractor.py (sanitize_metadata called after local model response)

# Tech tracking
tech-stack:
  added:
    - huggingface_hub>=0.23.0 (model download from HuggingFace Hub)
    - urllib.request (health check + binary download, stdlib)
    - zipfile (llama.cpp release archive extraction, stdlib)
    - atexit (server shutdown hook, stdlib)
    - subprocess (llama-server process management, stdlib)
  patterns:
    - GBNF grammar for JSON output control in llama-server
    - Field-profile sanitizer pattern (FIELD_PROFILES dict mapping field → profile name)
    - atexit.register for subprocess cleanup
    - Health-poll loop (urllib.request GET /health every 0.5s, 30s timeout)

key-files:
  created:
    - services/llama_server.py
    - modules/postprocessor.py
    - data/contract.gbnf
  modified:
    - requirements.txt (added huggingface_hub>=0.23.0)

key-decisions:
  - "llama-server binary fetched from GitHub Releases (llama.cpp b5606) per platform map — no manual install required"
  - "huggingface_hub.hf_hub_download used for model — handles resume, caching, progress natively"
  - "Port conflict handling: tries port, port+1, port+2 before giving up and logging warning (no raise — fallback provider takes over)"
  - "start() does not raise on failure — logs warning, caller falls back to cloud provider transparently"
  - "Grammar file path resolved via Path(__file__).parent.parent/data/contract.gbnf — works from any working directory"
  - "list fields (parties, special_conditions) guaranteed non-None after sanitize_metadata even if model outputs null"

patterns-established:
  - "FIELD_PROFILES pattern: dict mapping each ContractMetadata field to a sanitizer profile name"
  - "Profile-driven sanitizer: cyrillic_only removes Latin, cyrillic_latin keeps both, enum nullifies invalid values"
  - "Subprocess lifecycle: Popen + atexit.register(stop) + polling health endpoint"

requirements-completed: [SRVR-01, SRVR-02, SRVR-03, SRVR-04]

# Metrics
duration: 8min
completed: 2026-03-21
---

# Phase 04 Plan 01: Server Provider — LlamaServer + Postprocessor Summary

**llama-server download manager (GitHub Releases + HuggingFace Hub) and GBNF grammar + field-level Cyrillic sanitizer for local model output**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-21T14:04:37Z
- **Completed:** 2026-03-21T14:12:30Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `LlamaServerManager` manages full lifecycle: auto-download GGUF model (~940MB) from HuggingFace, auto-download llama-server binary from GitHub Releases (macOS arm64/x86_64, Linux, Windows), start/stop as subprocess, health polling, atexit shutdown hook
- `data/contract.gbnf` — GBNF grammar constraining llama-server output to valid ContractMetadata JSON with strict enum values for `payment_frequency` and `payment_direction`
- `modules/postprocessor.py` — field-level sanitizer with 5 profiles: `cyrillic_only` (removes Latin), `cyrillic_latin`, `enum` (nullifies invalid), `date` (YYYY-MM-DD or null), `number`/`boolean`

## Task Commits

1. **Task 1: LlamaServerManager** - `4f32be3` (feat)
2. **Task 2: GBNF grammar + postprocessor** - `57b93ca` (feat)

## Files Created/Modified

- `services/llama_server.py` (318 lines) — LlamaServerManager: download + process manager
- `modules/postprocessor.py` (189 lines) — GBNF grammar builder + sanitizer
- `data/contract.gbnf` (54 lines) — GBNF grammar for ContractMetadata JSON
- `requirements.txt` — added huggingface_hub>=0.23.0

## Decisions Made

- Port conflict handling tries port, port+1, port+2 before giving up — no RuntimeError raised, just warning logged; fallback cloud provider activates transparently
- `huggingface_hub.hf_hub_download` chosen over manual urllib download for GGUF — handles resume, caching, checksum automatically
- `start()` does not raise on failure (per plan D-06) — designed to let provider fallback work without changes to controller
- `list` fields (`parties`, `special_conditions`) are guaranteed `[]` (not `None`) after sanitize_metadata — defensive contract for downstream validators

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required. Binary and model are downloaded automatically on first run to `~/.yurteg/`.

## Known Stubs

None — both modules are fully functional. `LlamaServerManager.start()` does nothing if binary/model are not yet downloaded (returns without raising), which is by design — Plan 04-02 will wire the startup into the provider lifecycle.

## Next Phase Readiness

- `services/llama_server.py` is ready for Plan 04-02: OllamaProvider implementation calls `LlamaServerManager.ensure_model()`, `ensure_server_binary()`, `start()`, and passes `base_url` to the OpenAI client
- `modules/postprocessor.py` is ready to be called in `ai_extractor.py` after local model responses
- `data/contract.gbnf` path is returned by `get_grammar_path()` — pass to `LlamaServerManager.start(grammar_path=...)`

---
*Phase: 04-server-provider*
*Completed: 2026-03-21*
