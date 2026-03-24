---
phase: 21-ui-fixes
plan: "01"
subsystem: ui
tags: [bugfix, logging, registry, document, settings, templates]
dependency_graph:
  requires: []
  provides: [UIFIX-01, UIFIX-04, UIFIX-05, UIFIX-06]
  affects: [app/pages/registry.py, app/components/bulk_actions.py, app/main.py, app/pages/settings.py, app/pages/templates.py, app/pages/document.py]
tech_stack:
  added: []
  patterns: [logger.exception for structured error logging]
key_files:
  created: []
  modified:
    - app/pages/registry.py
    - app/components/bulk_actions.py
    - app/main.py
    - app/pages/settings.py
    - app/pages/templates.py
    - app/pages/document.py
decisions:
  - "logger.exception() used (not logger.error()) to capture full traceback in all silent except blocks"
  - "Dead action_review_btn removed — duplicate of review_btn that already wires _run_review"
metrics:
  duration: "~5 min"
  completed: "2026-03-25"
  tasks: 2
  files: 6
---

# Phase 21 Plan 01: UI Bug Fixes Summary

**One-liner:** Fixed 4 crash/data bugs — broken DB method name, mismatched settings key, tuple display in status dialog, and 14 silent except blocks now log via logger.exception().

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix method name and settings key mismatches | 0b42e4a | registry.py, bulk_actions.py, main.py |
| 2 | Fix bulk status labels + logging + dead button | baa73ec | bulk_actions.py, registry.py, settings.py, templates.py, document.py |

## What Was Done

**Task 1 (UIFIX-01, UIFIX-04):**
- `app/pages/registry.py:917`: `db.get_contract` → `db.get_contract_by_id` — split panel no longer crashes on row click
- `app/components/bulk_actions.py:62`: same fix in bulk export loop
- `app/main.py:157`: `"warning_days"` → `"warning_days_threshold"` — warning days setting now persists correctly across restarts

**Task 2 (UIFIX-05, UIFIX-06):**
- `app/components/bulk_actions.py:117`: `{k: v for k, v in STATUS_LABELS.items()}` → `{k: v[1] for k, v in STATUS_LABELS.items()}` — bulk status dialog shows "Действует", "Истёк" etc. instead of Python tuples
- Added `import logging` + `logger = logging.getLogger(__name__)` to registry.py, settings.py, templates.py (document.py already had it)
- Added `logger.exception(...)` to 14 silent except blocks across all 4 pages (registry: 4, settings: 2, templates: 4, document: 8)
- Removed dead `action_review_btn` duplicate button from document.py (lines 272-274) — the working `review_btn` below it was already wired to `_run_review`

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — no placeholder data or unconnected UI elements introduced.

## Self-Check: PASSED

- `app/pages/registry.py` — FOUND: get_contract_by_id at line 919, logger lines 5+
- `app/components/bulk_actions.py` — FOUND: get_contract_by_id at line 62, v[1] at line 117
- `app/main.py` — FOUND: warning_days_threshold at line 157
- Commits: 0b42e4a and baa73ec confirmed in git log
- No broken `db.get_contract(` calls remain (verified via grep)
- logger count (23) > except count (18) across app/pages/
