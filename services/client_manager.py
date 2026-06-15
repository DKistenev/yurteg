"""Управление мультиклиентскими реестрами. Каждый клиент = отдельный .db файл."""
import atexit
import json
import logging
import re
import threading
from pathlib import Path
from typing import Optional

from modules.database import Database

logger = logging.getLogger(__name__)


class ClientManager:
    """Управление мультиклиентскими реестрами. Каждый клиент = отдельный .db файл."""

    DEFAULT_CLIENT = "Основной реестр"
    _db_cache: dict[Path, Database] = {}
    _db_cache_lock = threading.Lock()
    _atexit_registered = False

    def __init__(self, data_dir: Optional[Path] = None):
        self._data_dir = data_dir or (Path.home() / ".yurteg")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._meta_file = self._data_dir / "clients.json"
        self._clients: dict[str, Path] = self._load()
        if not ClientManager._atexit_registered:
            atexit.register(ClientManager.close_all)
            ClientManager._atexit_registered = True

    def _load(self) -> dict[str, Path]:
        if self._meta_file.exists():
            try:
                data = json.loads(self._meta_file.read_text(encoding="utf-8"))
                return {name: Path(p) for name, p in data.items()}
            except (json.JSONDecodeError, ValueError):
                logger.warning("Corrupted clients.json, starting fresh")
        return {self.DEFAULT_CLIENT: self._data_dir / "yurteg.db"}

    def _save(self) -> None:
        data = {name: str(p) for name, p in self._clients.items()}
        self._meta_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def list_clients(self) -> list[str]:
        return list(self._clients.keys())

    def get_db_path(self, name: str) -> Path:
        if name not in self._clients:
            raise KeyError(f"Client not found: {name}")
        return self._clients[name]

    def get_db(self, name: str) -> Database:
        db_path = self.get_db_path(name)
        with self._db_cache_lock:
            db = self._db_cache.get(db_path)
            if db is None:
                db = Database(db_path)
                self._db_cache[db_path] = db
            return db

    @classmethod
    def close_all(cls) -> None:
        """Закрывает все кэшированные sqlite-соединения."""
        with cls._db_cache_lock:
            for db in cls._db_cache.values():
                db.close()
            cls._db_cache.clear()

    def add_client(self, name: str) -> Path:
        if name in self._clients:
            return self._clients[name]
        slug = re.sub(r'[^\w\s-]', '', name.lower()).strip()
        slug = re.sub(r'[\s]+', '_', slug)
        if not slug:
            slug = "client"
        path = self._data_dir / f"client_{slug}.db"
        # Avoid path collisions
        existing_paths = {str(p) for p in self._clients.values()}
        counter = 1
        while path.exists() or str(path) in existing_paths:
            path = self._data_dir / f"client_{slug}_{counter}.db"
            counter += 1
        self._clients[name] = path
        self._save()
        return path

    def remove_client(self, name: str) -> bool:
        if name == self.DEFAULT_CLIENT:
            return False  # Cannot remove default
        if name in self._clients:
            del self._clients[name]
            self._save()
            return True
        return False

    def find_client_by_counterparty(
        self, counterparty: str, threshold: int = 85
    ) -> Optional[str]:
        """Fuzzy match counterparty name against client names.

        Uses rapidfuzz token_sort_ratio — handles word reordering:
        'ООО Рога и Копыта' matches 'Рога и Копыта ООО'.
        Returns client name or None if no match above threshold.
        """
        if not counterparty:
            return None
        try:
            from rapidfuzz import process, fuzz
        except ImportError:
            logger.warning("rapidfuzz not installed, fuzzy matching disabled")
            return None

        client_names = [n for n in self._clients.keys() if n != self.DEFAULT_CLIENT]
        if not client_names:
            return None

        result = process.extractOne(
            counterparty,
            client_names,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=threshold,
        )
        return result[0] if result else None
