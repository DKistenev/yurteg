---
phase: 03-integrations-multitenancy
plan: "04"
subsystem: api
tags: [apscheduler, telegram, notifications, cron, bot-server]

requires:
  - phase: 03-02
    provides: ServerDatabase, bot server FastAPI app, bindings/deadline_sync tables

provides:
  - Daily deadline digest cron job via APScheduler (09:00 UTC)
  - format_digest() for Markdown alert formatting
  - send_deadline_digest() async job that iterates all bound users
  - GET/PUT /api/notifications/{chat_id} REST endpoints
  - POST /api/notify endpoint for processing result cards

affects:
  - 03-06
  - local app TelegramSync client (sends deadlines to /api/deadlines)

tech-stack:
  added: [apscheduler>=3.10.0]
  patterns:
    - "AsyncIOScheduler with CronTrigger — not BackgroundScheduler (async context)"
    - "Per-user error isolation — try/except per binding in digest loop"
    - "Scheduler started only when BOT_TOKEN present — same guard as webhook"
    - "Module-level scheduler variable for lifespan shutdown access"

key-files:
  created:
    - bot_server/scheduler.py
  modified:
    - bot_server/database.py
    - bot_server/main.py
    - requirements.txt

key-decisions:
  - "Single daily cron at 09:00 UTC — per-user digest_hour scheduling is v2; runtime overhead not justified for MVP"
  - "Scheduler started only inside BOT_TOKEN guard — avoids startup crash in dev without token"
  - "get_all_bindings uses threading.Lock for read safety consistency with other write methods"

patterns-established:
  - "Per-user isolation in scheduler: catch Exception per binding, log and continue"
  - "format_digest returns empty string for empty alerts — caller decides not to send"
  - "Module-level scheduler = None pattern for clean lifespan shutdown"

requirements-completed: [INTG-02]

duration: 5min
completed: 2026-03-19
---

# Phase 03 Plan 04: Deadline Notification Scheduler Summary

**APScheduler cron job sending daily Markdown digest of expiring contracts to all bound Telegram users, with REST endpoints for notification settings**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-19T23:44:10Z
- **Completed:** 2026-03-19T23:47:08Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created `bot_server/scheduler.py` with `AsyncIOScheduler` running daily at 09:00 UTC
- `format_digest()` groups expired (red circle) then expiring (warning) alerts into Markdown
- `send_deadline_digest()` iterates all bindings, respects `digest_enabled` flag, catches per-user errors
- Added `get_all_bindings()` to `ServerDatabase` for scheduler user iteration
- Integrated scheduler start/shutdown into FastAPI lifespan (BOT_TOKEN-gated)
- Added `GET/PUT /api/notifications/{chat_id}` and `POST /api/notify` endpoints

## Task Commits

1. **Task 1: Create scheduler with deadline digest cron job** - `efa05ae` (feat)
2. **Task 2: Integrate scheduler into FastAPI lifespan + notification settings endpoints** - `715c5cd` (feat)

## Files Created/Modified

- `bot_server/scheduler.py` — AsyncIOScheduler setup, format_digest, send_deadline_digest
- `bot_server/database.py` — Added get_all_bindings() method
- `bot_server/main.py` — Scheduler in lifespan, notification settings and notify endpoints
- `requirements.txt` — Added apscheduler>=3.10.0

## Decisions Made

- Single daily cron at 09:00 UTC — per-user `digest_hour` scheduling is v2 complexity; single daily run sufficient for MVP
- Scheduler guarded by `BOT_TOKEN` check — avoids startup crash in dev/test environment without Telegram token
- `get_all_bindings` uses `threading.Lock` for read consistency with write methods

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added apscheduler to requirements.txt**
- **Found during:** Task 1 (scheduler.py creation)
- **Issue:** APScheduler was not in requirements.txt — import would fail on fresh install
- **Fix:** Added `apscheduler>=3.10.0` to requirements.txt
- **Files modified:** requirements.txt
- **Verification:** Import succeeds after add
- **Committed in:** efa05ae (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking dependency)
**Impact on plan:** Necessary for runtime correctness. No scope creep.

## Issues Encountered

None — plan executed cleanly.

## Next Phase Readiness

- Scheduler and notification endpoints ready for local app to use via TelegramSync
- `POST /api/notify` endpoint ready for processing completion cards (Phase 03-06)
- `POST /api/deadlines/{chat_id}` (03-02) + scheduler (03-04) form complete deadline notification loop

---
*Phase: 03-integrations-multitenancy*
*Completed: 2026-03-19*
