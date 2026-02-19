"""Модуль организации файлов по папкам.

Копирует файлы из исходной папки в структурированную директорию
на основе метаданных. Файлы ТОЛЬКО копируются, НИКОГДА не
перемещаются и не удаляются из исходной папки.

Три режима группировки:
- "type": Договоры/{тип}/{файл}
- "counterparty": Договоры/{контрагент}/{файл}
- "both": Договоры/{тип}/{контрагент}/{файл}
"""
import logging
import re
import shutil
from pathlib import Path

from config import Config
from modules.models import ProcessingResult

logger = logging.getLogger(__name__)


def prepare_output_directory(source_dir: Path, config: Config) -> Path:
    """
    Создаёт выходную директорию рядом с исходной папкой.
    Проверяет права на запись и свободное место.
    """
    output_dir = source_dir.parent / config.output_folder_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # Проверка прав на запись
    test_file = output_dir / ".yurteg_test"
    try:
        test_file.write_text("test")
        test_file.unlink()
    except PermissionError:
        raise PermissionError(f"Нет прав на запись в {output_dir}")

    # Проверка свободного места (нужно 2x от исходной папки)
    total_size = sum(f.stat().st_size for f in source_dir.rglob("*") if f.is_file())
    disk_usage = shutil.disk_usage(output_dir)
    if disk_usage.free < total_size * 2:
        raise OSError(
            f"Недостаточно места на диске. "
            f"Требуется: {total_size * 2 / 1024**2:.0f} МБ, "
            f"Свободно: {disk_usage.free / 1024**2:.0f} МБ"
        )

    logger.info("Выходная папка: %s", output_dir)
    return output_dir


def organize_file(
    result: ProcessingResult,
    output_dir: Path,
    grouping: str = "both",
) -> Path:
    """
    Копирует файл в структурированную папку.

    grouping:
    - "type": Договоры/{тип}/{файл}
    - "counterparty": Договоры/{контрагент}/{файл}
    - "both": Договоры/{тип}/{контрагент}/{файл}

    Возвращает путь к скопированному файлу.
    """
    m = result.metadata

    type_dir = _sanitize_name(m.contract_type) if m and m.contract_type else "Неклассифицированные"
    party_dir = _sanitize_name(m.counterparty) if m and m.counterparty else "Неизвестный контрагент"

    # Строим путь в зависимости от режима группировки
    if grouping == "type":
        target_dir = output_dir / "Договоры" / type_dir
    elif grouping == "counterparty":
        target_dir = output_dir / "Договоры" / party_dir
    else:  # "both"
        target_dir = output_dir / "Договоры" / type_dir / party_dir

    target_dir.mkdir(parents=True, exist_ok=True)

    filename = _generate_filename(result)
    target_path = _resolve_conflict(target_dir / filename)

    # Копирование (copy2 сохраняет метаданные файла)
    shutil.copy2(result.file_info.path, target_path)
    logger.info("Скопирован: %s → %s", result.file_info.filename, target_path)

    return target_path


def _sanitize_name(name: str, max_length: int = 80) -> str:
    """Очищает строку для использования как имя файла/папки."""
    clean = re.sub(r'[<>:"/\\|?*]', '_', name)
    clean = re.sub(r'[_\s]+', ' ', clean).strip()
    if len(clean) > max_length:
        clean = clean[:max_length].strip()
    return clean or "Без названия"


def _generate_filename(result: ProcessingResult) -> str:
    """Генерирует имя файла: {тип}_{контрагент}_{дата}.{ext}"""
    m = result.metadata
    parts: list[str] = []

    if m and m.contract_type:
        parts.append(_sanitize_name(m.contract_type, 30))
    if m and m.counterparty:
        parts.append(_sanitize_name(m.counterparty, 30))
    if m and m.date_signed:
        parts.append(m.date_signed)

    if not parts:
        return result.file_info.filename

    name = "_".join(parts)
    ext = result.file_info.extension
    return f"{name}{ext}"


def _resolve_conflict(target_path: Path) -> Path:
    """Если файл существует — добавить суффикс _1, _2, ..."""
    if not target_path.exists():
        return target_path

    stem = target_path.stem
    ext = target_path.suffix
    parent = target_path.parent

    counter = 1
    while True:
        new_path = parent / f"{stem}_{counter}{ext}"
        if not new_path.exists():
            return new_path
        counter += 1
