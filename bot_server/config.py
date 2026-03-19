"""Bot server configuration — loaded from environment variables."""
import os
from pathlib import Path

BOT_TOKEN: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")
SERVER_URL: str = os.environ.get("SERVER_URL", "http://localhost:8000")
DB_PATH: Path = Path(os.environ.get("BOT_DB_PATH", "bot_server/bot.db"))
QUEUE_DIR: Path = Path(os.environ.get("BOT_QUEUE_DIR", "bot_server/queue"))
BINDING_TTL_MINUTES: int = 15
MAX_FILE_SIZE_MB: int = 20  # Maximum file size in MB accepted from Telegram
