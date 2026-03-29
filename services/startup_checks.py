"""Проверки перед скачиванием модели: интернет и место на диске.

Используется в splash.py для показа понятных предупреждений
вместо крашей при первом запуске без интернета или с полным диском.
"""
import logging
import shutil
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

# Минимум свободного места для модели (~940 МБ) + llama-server (~100 МБ) + запас
REQUIRED_SPACE_GB: float = 1.5

# Хосты для проверки — те же, откуда скачиваются модель и бинарник
_CHECK_HOSTS: list[str] = [
    "https://huggingface.co",
    "https://github.com",
]

_TIMEOUT_S: int = 5


def check_internet() -> bool:
    """Проверяет доступность интернета через HEAD-запрос к хостам скачивания.

    Возвращает True если хотя бы один хост отвечает.
    Таймаут — 5 секунд на каждый хост.
    """
    for host in _CHECK_HOSTS:
        try:
            req = urllib.request.Request(host, method="HEAD")
            with urllib.request.urlopen(req, timeout=_TIMEOUT_S):  # noqa: S310
                logger.debug("Интернет доступен (ответил %s)", host)
                return True
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            logger.debug("Хост %s недоступен: %s", host, exc)
            continue

    logger.debug("Интернет недоступен — все хосты не ответили")
    return False


def check_disk_space(target_dir: Path) -> tuple[bool, float]:
    """Проверяет свободное место на диске для целевой директории.

    Создаёт директорию если не существует (нужна для shutil.disk_usage).

    Returns:
        (достаточно_места, свободно_гб) — например (True, 3.2) или (False, 0.8)
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(target_dir)
    free_gb = round(usage.free / (1024**3), 1)

    ok = free_gb >= REQUIRED_SPACE_GB
    logger.debug(
        "Место на диске: %.1f ГБ свободно, нужно %.1f ГБ — %s",
        free_gb, REQUIRED_SPACE_GB, "ОК" if ok else "недостаточно",
    )
    return (ok, free_gb)
