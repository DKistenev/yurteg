"""Deadline notification scheduler for the ЮрТэг bot server.

Runs a daily cron job that sends a digest of expiring/expired documents
to each bound Telegram user who has digest_enabled=True.
"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot_server.database import ServerDatabase

logger = logging.getLogger(__name__)

# Status icons for digest formatting
_STATUS_ICONS: dict[str, str] = {
    "expired": "\U0001f534",   # red circle
    "expiring": "\u26a0\ufe0f",  # warning sign
}


def format_digest(alerts: list[dict]) -> str:
    """Format a list of deadline alerts into a Telegram-ready Markdown string.

    Groups alerts: expired first, then expiring.
    Returns an empty string if alerts is empty (caller must not send).
    """
    if not alerts:
        return ""

    expired = [a for a in alerts if a.get("status") == "expired"]
    expiring = [a for a in alerts if a.get("status") != "expired"]

    lines: list[str] = ["*Дайджест договоров:*"]

    for group in (expired, expiring):
        for a in group:
            icon = _STATUS_ICONS.get(a.get("status", "expiring"), "\u26a0\ufe0f")
            counterparty = a.get("counterparty") or "—"
            contract_ref = a.get("contract_ref") or "—"
            date_end = a.get("date_end") or "—"
            lines.append(f"{icon} {counterparty}: {contract_ref} (до {date_end})")

    return "\n".join(lines)


async def send_deadline_digest(bot, db: ServerDatabase) -> None:
    """Send deadline digest to all bound users with digest_enabled=True.

    Called by the scheduler once per day. Errors for individual users
    are caught and logged — one failure does not block others.
    """
    bindings = db.get_all_bindings()
    sent = 0
    skipped = 0

    for binding in bindings:
        chat_id: int = binding["chat_id"]
        try:
            settings = db.get_notification_settings(chat_id)
            if not settings.get("digest_enabled", 1):
                skipped += 1
                continue

            warning_days: int = settings.get("warning_days", 30)
            alerts = db.get_alerts_for_user(chat_id, warning_days)

            text = format_digest(alerts)
            if not text:
                skipped += 1
                continue

            await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
            sent += 1
            logger.info("Digest sent to chat_id=%s (%d alerts)", chat_id, len(alerts))

        except Exception:
            logger.exception("Failed to send digest to chat_id=%s", chat_id)

    logger.info(
        "Deadline digest complete: sent=%d skipped=%d total=%d",
        sent,
        skipped,
        len(bindings),
    )


def setup_scheduler(bot, db: ServerDatabase) -> AsyncIOScheduler:
    """Create and configure the APScheduler instance.

    Registers a daily CronTrigger at 09:00 UTC to send deadline digests.
    The caller is responsible for calling scheduler.start() and
    scheduler.shutdown() during application lifespan.

    Returns:
        AsyncIOScheduler — not yet started.
    """
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_deadline_digest,
        trigger=CronTrigger(hour=9, minute=0),
        kwargs={"bot": bot, "db": db},
        id="deadline_digest",
        name="Daily deadline digest",
        replace_existing=True,
    )
    logger.info("Scheduler configured: daily digest at 09:00 UTC")
    return scheduler
