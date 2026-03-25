---
phase: 28-cleanup
plan: "03"
subsystem: backend
tags: [stability, llama-server, ai-extractor, atexit, logging]
dependency_graph:
  requires: []
  provides: [STAB-01, STAB-02]
  affects: [services/llama_server.py, modules/ai_extractor.py]
tech_stack:
  added: []
  patterns: [TDD red-green, atexit lifecycle, logging.warning]
key_files:
  created:
    - tests/test_llama_server_atexit.py
    - tests/test_truncation_warning.py
  modified:
    - services/llama_server.py
    - modules/ai_extractor.py
decisions:
  - "atexit.register перемещён внутрь if started: — вызывается ровно 1 раз при успехе"
  - "logging.warning при обрезке >30K — юрист видит что часть документа не проанализирована"
metrics:
  duration: "~25 min"
  completed_date: "2026-03-26"
  tasks_completed: 2
  files_changed: 4
---

# Phase 28 Plan 03: Stability Fixes — atexit + truncation warning Summary

Two targeted stability fixes: atexit registered exactly once, user sees warning when document is truncated.

## What Was Built

**Task 1 — atexit.register() out of retry loop (`services/llama_server.py`)**

`atexit.register(self.stop)` was called inside the `for attempt in range(3)` loop, immediately after `subprocess.Popen()`. On every failed attempt the handler was registered anyway — meaning at process exit, `stop()` was called up to 3 times, producing spurious errors. Fix: moved the call inside `if started:` block, directly before `return`. Now it's called exactly once and only on successful start.

Also removed unused `import os` (flagged by ruff during edit).

**Task 2 — logging.warning on truncation (`modules/ai_extractor.py`)**

`extract_metadata` silently sliced text to 30,000 chars. Lawyers had no way of knowing 15%+ of their document was not analysed. Fix: capture `original_len` before slice, emit `logger.warning(...)` with the original character count when `original_len > 30_000`. Boundary (exactly 30,000) is not warned.

## Commits

| Hash | Message |
|------|---------|
| `1182994` | fix(28-03): move atexit.register outside retry loop in llama_server.py |
| `0a46186` | feat(28-03): add logging.warning when text truncated at 30K chars in ai_extractor |

## Tests

| File | Tests | Result |
|------|-------|--------|
| `tests/test_llama_server_atexit.py` | 2 | PASSED |
| `tests/test_truncation_warning.py` | 3 | PASSED |

All 5 tests green. Run time ~103s (dominated by llama-server health-check mock timeout).

## Deviations from Plan

**[Rule 1 - Bug] Removed unused `import os` in llama_server.py**
- Found during: Task 1 (ruff validator hook)
- Issue: `os` was imported but not used after earlier refactors
- Fix: removed the import line
- Files modified: `services/llama_server.py`
- Commit: `1182994`

## Known Stubs

None.

## Self-Check: PASSED
