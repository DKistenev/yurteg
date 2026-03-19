"""FastAPI application for the ЮрТэг Telegram bot server.

Lifespan:
  - Initialises python-telegram-bot Application
  - Sets Telegram webhook to {SERVER_URL}/telegram/webhook
  - Stores ServerDatabase in bot_data["db"]

Endpoints:
  POST /telegram/webhook         — receive Telegram updates
  POST /api/bind                 — exchange binding code for chat_id
  GET  /api/queue/{chat_id}      — return pending files for chat_id
  GET  /api/files/{file_id}      — download a queued file
  DELETE /api/queue/{file_id}    — mark file as fetched
  POST /api/deadlines/{chat_id}  — sync deadline alerts from local app
  GET  /api/health               — liveness probe
"""
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot_server.bot import handle_document, handle_start
from bot_server.config import BOT_TOKEN, DB_PATH, QUEUE_DIR, SERVER_URL
from bot_server.database import ServerDatabase

logger = logging.getLogger(__name__)

# Module-level references populated during lifespan
app_bot: Application | None = None
db: ServerDatabase | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise bot and register webhook on startup; shutdown cleanly."""
    global app_bot, db

    db = ServerDatabase(DB_PATH)
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    if BOT_TOKEN:
        app_bot = Application.builder().token(BOT_TOKEN).build()
        # Store shared DB reference in bot_data so handlers can access it
        app_bot.bot_data["db"] = db

        # Register handlers
        app_bot.add_handler(CommandHandler("start", handle_start))
        app_bot.add_handler(
            MessageHandler(filters.Document.ALL, handle_document)
        )

        await app_bot.initialize()

        # Register webhook
        webhook_url = f"{SERVER_URL}/telegram/webhook"
        await app_bot.bot.set_webhook(webhook_url)
        logger.info("Webhook registered: %s", webhook_url)
    else:
        logger.warning(
            "TELEGRAM_BOT_TOKEN not set — running without Telegram webhook"
        )

    yield

    # Cleanup
    if app_bot is not None:
        await app_bot.shutdown()


app = FastAPI(title="ЮрТэг Bot Server", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Telegram webhook
# ---------------------------------------------------------------------------


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request) -> dict:
    """Forward incoming Telegram updates to python-telegram-bot."""
    if app_bot is None:
        raise HTTPException(status_code=503, detail="Bot not initialised")
    data = await request.json()
    update = Update.de_json(data, app_bot.bot)
    await app_bot.process_update(update)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Binding
# ---------------------------------------------------------------------------


@app.post("/api/bind")
async def api_bind(request: Request) -> dict:
    """Exchange a binding code for a chat_id and confirm the binding."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    body: dict[str, Any] = await request.json()
    code = body.get("code", "")
    result = db.consume_pending_binding(str(code))
    if result is None:
        raise HTTPException(status_code=404, detail="Invalid or expired code")
    chat_id: int = result["chat_id"]
    db.save_binding(chat_id)
    return {"chat_id": chat_id}


# ---------------------------------------------------------------------------
# File queue
# ---------------------------------------------------------------------------


@app.get("/api/queue/{chat_id}")
async def api_get_queue(chat_id: int) -> list[dict]:
    """Return all un-fetched queued files for a bound user."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    return db.fetch_queue(chat_id)


@app.get("/api/files/{file_id}")
async def api_get_file(file_id: int) -> FileResponse:
    """Download the raw file bytes for a queued entry."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    # Retrieve file path from DB — query directly for single row
    row = db._conn.execute(
        "SELECT file_path, filename FROM file_queue WHERE id = ?", (file_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="File not found")
    from pathlib import Path as _Path

    path = _Path(row["file_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(str(path), filename=row["filename"])


@app.delete("/api/queue/{file_id}")
async def api_delete_queue(file_id: int) -> dict:
    """Mark a queued file as fetched (consumed)."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    db.mark_fetched(file_id)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Deadline sync
# ---------------------------------------------------------------------------


@app.post("/api/deadlines/{chat_id}")
async def api_post_deadlines(chat_id: int, request: Request) -> dict:
    """Receive deadline alert list from local app and persist to deadline_sync."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    body = await request.json()
    alerts: list[dict] = body if isinstance(body, list) else body.get("alerts", [])
    db.save_deadlines(chat_id, alerts)
    return {"ok": True, "saved": len(alerts)}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def api_health() -> dict:
    """Liveness probe."""
    return {"status": "ok"}
