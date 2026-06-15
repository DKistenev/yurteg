"""Сервис обработки архива документов.

# Этот файл должен работать без зависимости от конкретного UI.
# Намеренное ограничение: вызывается Telegram-ботом, CLI, тестами.
"""
from pathlib import Path
from typing import Callable, Optional

from config import Config
from controller import Controller


def process_archive(
    source_dir: Path,
    config: Config,
    grouping: str = "both",
    force_reprocess: bool = False,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
    on_file_done: Optional[Callable] = None,
    output_dir_override: Optional[Path] = None,
    db_path_override: Optional[Path] = None,
) -> dict:
    """Единая точка входа для обработки архива документов.

    Вызывается desktop UI, Telegram-ботом, CLI и тестами.
    Возвращает: dict(total, done, errors, skipped, output_dir, report_path)

    Args:
        source_dir: папка с договорами
        config: конфиг приложения
        grouping: режим группировки ("type" | "counterparty" | "both")
        force_reprocess: игнорировать кэш, обработать все файлы заново
        on_progress: callback(current, total, message) для прогресс-бара
        on_file_done: callback(result) после обработки каждого файла
        output_dir_override: принудительная выходная папка (облачный режим)
    """
    ctrl = Controller(config)
    try:
        return ctrl.process_archive(
            source_dir=source_dir,
            grouping=grouping,
            force_reprocess=force_reprocess,
            on_progress=on_progress,
            on_file_done=on_file_done,
            output_dir_override=output_dir_override,
            db_path_override=db_path_override,
        )
    finally:
        ctrl.close()
