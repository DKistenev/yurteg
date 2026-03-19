---
phase: 03-integrations-multitenancy
plan: "02"
subsystem: api
tags: [fastapi, telegram, python-telegram-bot, sqlite, webhook, file-queue]

requires:
  - phase: 03-00
    provides: wave-0 xfail skeletons for server/ and services/client_manager interface

provides:
  - bot_server/ package with FastAPI webhook server for Telegram document ingestion
  - ServerDatabase with file_queue, bindings, pending_bindings, deadline_sync, notification_settings
  - 6-digit binding code flow (generate on /start, consume via REST /api/bind)
  - REST API for local app: /api/queue, /api/files, /api/deadlines

affects:
  - 03-03 (Telegram notification service — consumes REST API and bot_data["db"])
  - 03-04 (client_manager — calls /api/bind and /api/queue from local app side)

tech-stack:
  added:
    - python-telegram-bot>=22.7 (webhook-based Telegram bot)
    - fastapi>=0.135 (async REST server)
    - uvicorn>=0.42 (ASGI runner)
    - apscheduler>=3.11 (scheduled digest notifications, next plan)
  patterns:
    - FastAPI lifespan for bot lifecycle management
    - bot_data["db"] for shared database reference in handlers
    - threading.Lock + check_same_thread=False for SQLite thread safety in async context
    - consume_pending_binding: SELECT + DELETE in single locked transaction (atomic one-time use)

key-files:
  created:
    - bot_server/__init__.py
    - bot_server/config.py
    - bot_server/database.py
    - bot_server/bot.py
    - bot_server/main.py
    - bot_server/requirements.txt
  modified: []

key-decisions:
  - "bot_data[db] pattern: ServerDatabase stored in Application.bot_data so handlers access it via context.bot_data['db'] without global imports"
  - "check_same_thread=False + threading.Lock: FastAPI/uvicorn multi-thread context requires this pattern for SQLite safety"
  - "consume_pending_binding is atomic: SELECT + DELETE inside single Lock scope prevents race on double-consume"
  - "File size check uses doc.file_size (Telegram metadata) before downloading — avoids wasted bandwidth for oversized files"

patterns-established:
  - "Pattern: bot_data[db] — shared DB in bot_data, not global variable, consistent with python-telegram-bot best practices"
  - "Pattern: FastAPI lifespan for external service lifecycle (init + cleanup of bot Application)"

requirements-completed:
  - INTG-01

duration: 2min
completed: "2026-03-19"
---

# Phase 03 Plan 02: Telegram Bot Server Summary

**FastAPI + python-telegram-bot webhook server with file-queue SQLite, 6-digit binding codes, and REST API for local app integration**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-19T23:40:23Z
- **Completed:** 2026-03-19T23:42:30Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- bot_server/ package with ServerDatabase: file_queue, bindings, pending_bindings, deadline_sync, notification_settings tables, fully thread-safe
- FastAPI app with lifespan: registers Telegram webhook, initialises bot Application, exposes 7 REST endpoints
- Bot handlers: /start generates 6-digit binding code stored with 15-min TTL; handle_document validates size (20MB) + MIME (PDF/DOCX) before queuing
- All DB CRUD operations verified by plan-provided test suite (enqueue, fetch, pending binding single-use)

## Task Commits

1. **Task 1: Create bot_server config and database layer** - `3237eb1` (feat)
2. **Task 2: Create FastAPI server with webhook + bot handlers + REST API** - `07a03f2` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `bot_server/__init__.py` — Python package marker
- `bot_server/config.py` — BOT_TOKEN, SERVER_URL, DB_PATH, QUEUE_DIR, MAX_FILE_SIZE_MB from env
- `bot_server/database.py` — ServerDatabase: 5 tables, thread-safe CRUD with threading.Lock
- `bot_server/bot.py` — handle_start (binding code), handle_document (size+MIME validation + download)
- `bot_server/main.py` — FastAPI lifespan app with webhook + 7 REST endpoints
- `bot_server/requirements.txt` — python-telegram-bot, fastapi, uvicorn, apscheduler

## Decisions Made

- `bot_data["db"]` pattern: database shared via Application.bot_data so handlers get it through context — avoids global state, consistent with python-telegram-bot best practices
- `consume_pending_binding` is fully atomic (SELECT + DELETE inside single threading.Lock scope) — prevents double-consume race condition
- File size rejection uses Telegram's `doc.file_size` metadata before downloading — avoids bandwidth waste on oversized files

## Deviations from Plan

None - plan executed exactly as written.

Minor: `Application.builder().token(BOT_TOKEN).build()` written on one line to satisfy the acceptance criteria string check (plan required that exact string inline).

## Issues Encountered

- fastapi and python-telegram-bot not pre-installed in environment — installed via pip before final import verification. This is expected for a new bot_server subpackage.

## User Setup Required

**External service requires manual configuration before bot server can run:**

| Variable | Source |
|---|---|
| `TELEGRAM_BOT_TOKEN` | BotFather в Telegram: /newbot → создать @YurTagBot → скопировать token |
| `SERVER_URL` | Публичный HTTPS URL сервера (Railway/Fly.io после деплоя) |

Start server: `uvicorn bot_server.main:app --host 0.0.0.0 --port 8000`

## Next Phase Readiness

- bot_server/ is a standalone deployable package — ready for Railway/Fly.io
- REST API ready for 03-03 (notification scheduler) and 03-04 (local app client_manager)
- APScheduler dependency already listed for 03-03 digest notifications
- No blockers

---
*Phase: 03-integrations-multitenancy*
*Completed: 2026-03-19*
