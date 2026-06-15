"""Модуль сканирования директории — находит PDF/DOCX файлы и вычисляет хеши."""
import hashlib
import logging
from pathlib import Path

from config import Config
from modules.models import FileInfo

logger = logging.getLogger(__name__)


def compute_file_hash(file_path: Path) -> str:
    """Вычисляет SHA-256 хеш файла. Читает файл блоками по 8192 байта."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def scan_directory(directory: Path, config: Config) -> list[FileInfo]:
    """
    Рекурсивно сканирует директорию.

    Аргументы:
        directory: путь к папке с договорами
        config: конфигурация (расширения, макс. размер)

    Возвращает:
        Список FileInfo для всех найденных файлов поддерживаемых форматов.
        Файлы, превышающие max_file_size_mb, пропускаются (логируются как WARNING).

    Raises:
        FileNotFoundError: если directory не существует или не является директорией
    """
    if not directory.exists():
        raise FileNotFoundError(f"Директория не найдена: {directory}")
    if not directory.is_dir():
        raise FileNotFoundError(f"Путь не является директорией: {directory}")

    max_size_bytes = config.max_file_size_mb * 1024 * 1024
    files: list[FileInfo] = []
    counts: dict[str, int] = {}

    for path in directory.rglob("*"):
        if not path.is_file():
            continue

        extension = path.suffix.lower()
        if extension not in config.supported_extensions:
            continue

        size_bytes = path.stat().st_size

        if size_bytes > max_size_bytes:
            logger.warning(
                "Файл пропущен (размер %d МБ > %d МБ): %s",
                size_bytes // (1024 * 1024),
                config.max_file_size_mb,
                path.name,
            )
            continue

        file_hash = compute_file_hash(path)

        file_info = FileInfo(
            path=path,
            filename=path.name,
            extension=extension,
            size_bytes=size_bytes,
            file_hash=file_hash,
        )
        files.append(file_info)
        counts[extension] = counts.get(extension, 0) + 1

    files.sort(key=lambda f: f.filename)

    parts = [f"{count} {ext.upper().lstrip('.')}" for ext, count in sorted(counts.items())]
    logger.info("Найдено %d файлов (%s)", len(files), ", ".join(parts) if parts else "0")

    return files
