---
phase: 23-production-readiness
plan: "01"
subsystem: infrastructure
tags: [offline-assets, dependencies, provider-system, fonts, fullcalendar]
dependency_graph:
  requires: []
  provides: [offline-fonts, offline-calendar, pinned-deps, config-driven-ollama, provider-based-verify]
  affects: [app/main.py, app/pages/registry.py, providers/ollama.py, modules/ai_extractor.py]
tech_stack:
  added: []
  patterns: [local-font-face, vendor-bundle, config-driven-port, provider-delegation]
key_files:
  created:
    - app/static/fonts/IBMPlexSans-Regular.woff2
    - app/static/fonts/IBMPlexSans-Bold.woff2
    - app/static/vendor/fullcalendar.global.min.js
    - app/static/vendor/fullcalendar.global.min.css
  modified:
    - app/main.py
    - app/pages/registry.py
    - requirements.txt
    - providers/ollama.py
    - modules/ai_extractor.py
    - tests/test_design_polish.py
decisions:
  - "FullCalendar v6 bundles CSS into JS — created minimal placeholder .css file so the lazy-loader link doesn't 404"
  - "python-dotenv pinned to 0.21.0 (actual installed version, not 1.0.1 as plan suggested)"
  - "python-dateutil pinned to 2.9.0.post0 (actual installed version)"
  - "_create_client() marked DEPRECATED but kept — still used by extract_metadata()"
metrics:
  duration: "~15min"
  completed_date: "2026-03-25"
  tasks_completed: 2
  files_modified: 6
  files_created: 4
---

# Phase 23 Plan 01: Infrastructure Hardening Summary

**One-liner:** Offline font/calendar bundling + pinned deps + config-driven OllamaProvider port + provider-based verify_metadata/verify_api_key.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Bundle offline assets and pin dependencies | dd130b4 | app/main.py, app/pages/registry.py, requirements.txt, 4 static files |
| 2 | Fix OllamaProvider port and refactor verify_metadata | d1f0d2c | providers/ollama.py, modules/ai_extractor.py |

## What Was Built

**PROD-02: Offline assets**
- IBM Plex Sans Regular (45KB) and Bold (22KB) woff2 files downloaded to `app/static/fonts/`
- FullCalendar v6.1.15 global JS bundle (276KB) downloaded to `app/static/vendor/`
- `app/main.py`: replaced Google Fonts CDN `<link>` tags with local `@font-face` declarations
- `app/pages/registry.py`: `_ensure_fullcalendar()` now loads from `/static/vendor/` instead of `cdn.jsdelivr.net`

**PROD-03: Pinned dependencies**
- All `>=` replaced with `==` in requirements.txt
- Added `numpy==1.26.4` and `httpx==0.27.0` (were missing)
- Verified actual installed versions for each package

**PROD-04: Local model fixes**
- `OllamaProvider.__init__` now derives URL from `config.llama_server_port` when `base_url` is None (no hardcoded `8080`)
- `verify_metadata()` refactored to accept optional `provider: LLMProvider | None` param; uses `provider.complete()` instead of `_create_client()`
- `verify_api_key()` refactored to accept optional `provider: LLMProvider | None` param; delegates to `provider.verify_key()`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_font_injection failed after CDN → local migration**
- **Found during:** Post-task verification (full test run)
- **Issue:** `test_design_polish.py::test_font_injection` asserted `"IBM+Plex+Sans" in content` — the URL-encoded form only exists in Google Fonts CDN links, which were removed
- **Fix:** Updated assertion to check for `"IBMPlexSans-Regular.woff2"` (local file path) instead
- **Files modified:** `tests/test_design_polish.py`
- **Commit:** 59c58d2

**2. [Rule 3 - Blocking] FullCalendar CSS 404 on jsDelivr**
- **Found during:** Task 1 execution
- **Issue:** `https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.css` returns 404 — FullCalendar v6 bundles CSS into JS (CSS-in-JS injection)
- **Fix:** Created minimal placeholder CSS file at `app/static/vendor/fullcalendar.global.min.css` so the `<link>` href doesn't 404; JS bundle handles all styling
- **Files modified:** `app/static/vendor/fullcalendar.global.min.css`

**3. [Note] python-dotenv version mismatch**
- **Plan suggested:** `python-dotenv==1.0.1`
- **Actual installed:** `0.21.0`
- **Action:** Used actual installed version `0.21.0` (plan specification was aspirational, not the installed version)

**4. [Note] python-dateutil version**
- **Plan suggested:** `2.9.0`
- **Actual installed:** `2.9.0.post0`
- **Action:** Used actual installed version `2.9.0.post0`

## Verification Results

```
All must_have truths verified:
✓ Fonts loaded from local files (no fonts.googleapis.com in app/main.py)
✓ FullCalendar loaded from local vendor/ (no cdn.jsdelivr.net in registry.py)
✓ numpy==1.26.4 and httpx==0.27.0 in requirements.txt
✓ OllamaProvider uses config.llama_server_port (port 8080 in URL confirmed)
✓ verify_metadata() accepts provider param, calls provider.complete()
✓ verify_api_key() accepts provider param, calls provider.verify_key()

Tests: 315 passed, 0 failed (up from 268 passed pre-plan — 47 new tests from plan 23-02)
```

## Known Stubs

None — all changes are complete and functional.

## Self-Check: PASSED

Files verified:
- app/static/fonts/IBMPlexSans-Regular.woff2: FOUND (45KB woff2)
- app/static/fonts/IBMPlexSans-Bold.woff2: FOUND (22KB woff2)
- app/static/vendor/fullcalendar.global.min.js: FOUND (276KB)
- app/static/vendor/fullcalendar.global.min.css: FOUND (placeholder)

Commits verified:
- dd130b4: chore(23-01): bundle offline assets and pin dependencies
- d1f0d2c: feat(23-01): fix OllamaProvider port and refactor verify_metadata to provider system
- 59c58d2: fix(23-01): update test_font_injection to expect local font path
