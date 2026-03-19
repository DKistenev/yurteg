"""Telegram bot handlers for ЮрТэг bot server.

Handlers:
  /start  — generate a 6-digit binding code and send to user
  document — receive PDF/DOCX file, save to queue if user is bound
"""
import logging
import secrets
import string

from telegram import Update
from telegram.ext import ContextTypes

from bot_server.config import BINDING_TTL_MINUTES, MAX_FILE_SIZE_MB, QUEUE_DIR
from bot_server.database import ServerDatabase

logger = logging.getLogger(__name__)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate a 6-digit binding code and send it to the user."""
    chat_id = update.effective_chat.id
    db: ServerDatabase = context.bot_data["db"]
    code = "".join(secrets.choice(string.digits) for _ in range(6))
    db.save_pending_binding(chat_id=chat_id, code=code, ttl_minutes=BINDING_TTL_MINUTES)
    await update.message.reply_text(
        f"Ваш код привязки: *{code}*\n\n"
        f"Введите его в приложении ЮрТэг → Настройки → Telegram.\n"
        f"Код действует {BINDING_TTL_MINUTES} минут.",
        parse_mode="Markdown",
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Receive a document, validate it, and save to queue if user is bound."""
    chat_id = update.effective_chat.id
    db: ServerDatabase = context.bot_data["db"]

    # Require active binding
    binding = db.get_binding(chat_id)
    if not binding:
        await update.message.reply_text(
            "Сначала привяжите аккаунт — введите /start"
        )
        return

    doc = update.message.document
    if not doc:
        await update.message.reply_text(
            "Отправьте документ как файл (PDF или DOCX)."
        )
        return

    # Enforce file size limit
    if doc.file_size and doc.file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        size_mb = doc.file_size // (1024 * 1024)
        await update.message.reply_text(
            f"Файл слишком большой ({size_mb} МБ). "
            f"Максимум: {MAX_FILE_SIZE_MB} МБ."
        )
        return

    # Enforce allowed MIME types
    allowed = (
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    if doc.mime_type not in allowed:
        await update.message.reply_text(
            "Поддерживаются только PDF и DOCX файлы."
        )
        return

    # Save file to queue directory
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    dest = QUEUE_DIR / f"{chat_id}_{doc.file_unique_id}_{doc.file_name}"
    tg_file = await context.bot.get_file(doc.file_id)
    await tg_file.download_to_drive(str(dest))

    db.enqueue_file(
        chat_id=chat_id,
        file_path=str(dest),
        filename=doc.file_name,
        mime_type=doc.mime_type,
    )
    await update.message.reply_text(
        "Получил! Обработаю при следующем запуске приложения."
    )
    logger.info("File queued for chat_id=%s: %s", chat_id, doc.file_name)
