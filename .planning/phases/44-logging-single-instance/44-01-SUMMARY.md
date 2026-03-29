---
phase: 44-logging-single-instance
plan: 01
subsystem: infra
tags: [logging, betterstack, logtail, rotating-file, security]

# Dependency graph
requires: []
provides:
  - "setup_logging() — centralized logging configuration for the app"
  - "RotatingFileHandler at ~/.yurteg/logs/yurteg.log"
  - "BetterStack Logtail remote logging with machine_id"
  - "_ContentFilter preventing document content in remote logs"
  - "_get_storage_secret() — dynamic persistent storage secret"
affects: [44-02-single-instance, desktop-build]

# Tech tracking
tech-stack:
  added: [logtail-python]
  patterns: [setup_logging before any logger usage, content filtering for remote handlers]

key-files:
  created: [services/log_setup.py]
  modified: [app/main.py, requirements.txt]

key-decisions:
  - "logtail-python for BetterStack integration (official SDK, simple API)"
  - "Content filter rejects DEBUG from sensitive modules + messages >500 chars"
  - "storage_secret generated via secrets.token_hex(32) and persisted in settings.json"
  - "setup_logging() is idempotent — checks root.handlers before adding"

patterns-established:
  - "setup_logging() called at module level before logger = logging.getLogger()"
  - "_ContentFilter pattern for PII/content protection in remote logging"

requirements-completed: [LOG-01, LOG-02, LOG-03, LOG-04]

# Metrics
duration: 2min
completed: 2026-03-30
---

# Phase 44 Plan 01: Logging & Storage Secret Summary

**Structured logging with 5MB rotating file + BetterStack Logtail remote handler with machine_id and content filter; dynamic storage_secret replacing hardcoded value**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-29T22:18:41Z
- **Completed:** 2026-03-29T22:20:37Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Local file logging at ~/.yurteg/logs/yurteg.log with 5MB rotation and 3 backups
- BetterStack Logtail integration with machine_id and app_version context for beta monitoring
- Content filter prevents document text from leaking to remote logs
- Replaced hardcoded storage_secret with dynamically generated persistent secret

## Task Commits

Each task was committed atomically:

1. **Task 1: Create services/log_setup.py with file + BetterStack logging** - `35e2548` (feat)
2. **Task 2: Wire logging into main.py and replace hardcoded storage_secret** - `66a7f04` (feat)

## Files Created/Modified
- `services/log_setup.py` - Logging configuration: RotatingFileHandler + LogtailHandler + _ContentFilter
- `app/main.py` - Added setup_logging() call, _get_storage_secret(), removed hardcoded secret
- `requirements.txt` - Added logtail-python>=0.3.0

## Decisions Made
- Used logtail-python official SDK for BetterStack (simplest integration, handles batching)
- Content filter blocks DEBUG from text_extractor/anonymizer and messages >500 chars from remote logs
- storage_secret uses secrets.token_hex(32) — 256 bits of entropy, persisted in settings.json
- setup_logging() is idempotent (safe to call multiple times)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

BetterStack Logtail requires a source token. Set `BETTERSTACK_SOURCE_TOKEN` env var or add `betterstack_token` to ~/.yurteg/settings.json. Without it, remote logging is gracefully skipped (local file logging works regardless).

## Known Stubs

None - all functionality is fully wired.

## Next Phase Readiness
- Logging infrastructure ready for all modules
- Phase 44-02 (single instance lock) can proceed independently
- BetterStack will activate automatically once token is configured

---
*Phase: 44-logging-single-instance*
*Completed: 2026-03-30*
