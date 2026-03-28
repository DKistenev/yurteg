"""Синхронизация локального приложения с сервером Telegram-бота.

# NO import streamlit — этот файл должен работать без UI.
# Вызывается из main.py, CLI и тестов.
"""
import logging
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class TelegramSync:
    """Клиент для взаимодействия с REST API сервера Telegram-бота."""

    def __init__(self, server_url: str, chat_id: int) -> None:
        self.base = server_url.rstrip("/")
        self.chat_id = chat_id
        self._client = httpx.Client(timeout=30)

    def is_configured(self) -> bool:
        """True, если сервер задан и аккаунт привязан."""
        return bool(self.base) and self.chat_id > 0

    def check_connection(self) -> bool:
        """Проверяет доступность сервера Telegram-бота. GET {base}/health, timeout=5s."""
        if not self.base:
            return False
        try:
            r = self._client.get(f"{self.base}/health", timeout=5)
            return r.status_code < 400
        except Exception:
            return False

    def bind(self, code: str) -> Optional[int]:
        """Отправить код привязки на сервер, вернуть chat_id при успехе.

        POST /api/bind  — тело JSON {"code": code}
        Сервер ожидает JSON, не query-параметры.
        """
        try:
            r = self._client.post(
                f"{self.base}/api/bind",
                json={"code": code},
            )
            r.raise_for_status()
            data = r.json()
            return data.get("chat_id")
        except httpx.HTTPError as e:
            logger.warning("Привязка не удалась: %s", e)
            return None

    def fetch_queue(self, dest_dir: Path) -> list[Path]:
        """Скачать все файлы из очереди сервера, сохранить в dest_dir.

        GET /api/queue/{chat_id} — возвращает list[dict] напрямую
        (каждый элемент содержит id, filename, file_path, ...).
        GET /api/files/{file_id} — скачать байты файла
        DELETE /api/queue/{file_id} — подтвердить получение
        """
        if not self.is_configured():
            return []
        try:
            r = self._client.get(f"{self.base}/api/queue/{self.chat_id}")
            r.raise_for_status()
            files_data: list[dict] = r.json()
            if not isinstance(files_data, list):
                # На случай если сервер вернёт обёртку {"files": [...]}
                files_data = files_data.get("files", [])  # type: ignore[union-attr]
        except httpx.HTTPError as e:
            logger.warning("Не удалось получить очередь: %s", e)
            return []

        dest_dir.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        for item in files_data:
            if "id" not in item or "filename" not in item:
                logger.warning("Пропущен элемент очереди без id/filename: %s", item)
                continue
            try:
                fr = self._client.get(f"{self.base}/api/files/{item['id']}")
                fr.raise_for_status()
                dest = dest_dir / item["filename"]
                dest.write_bytes(fr.content)
                # Подтвердить получение только после успешной записи
                self._client.delete(f"{self.base}/api/queue/{item['id']}")
                paths.append(dest)
                logger.info("Скачан файл из Telegram: %s", item["filename"])
            except httpx.HTTPError as e:
                logger.warning(
                    "Не удалось скачать файл %s: %s", item.get("filename"), e
                )
        return paths

    def push_deadlines(self, alerts: list[dict]) -> bool:
        """Передать метаданные дедлайнов на сервер для cron-уведомлений.

        POST /api/deadlines/{chat_id}  — тело JSON {"alerts": [...]}
        """
        if not self.is_configured():
            return False
        try:
            r = self._client.post(
                f"{self.base}/api/deadlines/{self.chat_id}",
                json={"alerts": alerts},
            )
            r.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.warning("Не удалось передать дедлайны: %s", e)
            return False

    def notify_processed(self, chat_id: int, summary: str) -> bool:
        """Попросить сервер отправить карточку с результатами обработки пользователю.

        POST /api/notify  — тело JSON {"chat_id": chat_id, "text": summary}
        """
        if not self.is_configured():
            return False
        try:
            r = self._client.post(
                f"{self.base}/api/notify",
                json={"chat_id": chat_id, "text": summary},
            )
            r.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.warning("Не удалось отправить уведомление: %s", e)
            return False
