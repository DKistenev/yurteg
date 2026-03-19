"""Сервис работы с реестром документов.

# NO import streamlit — этот файл должен работать без UI.
"""
from pathlib import Path

from modules.database import Database
from modules.reporter import generate_report as _generate_report


def get_all_contracts(db: Database) -> list[dict]:
    """Все обработанные договоры из базы данных."""
    return db.get_all_results()


def generate_report(db: Database, output_dir: Path) -> Path:
    """Генерировать Excel-реестр. Возвращает путь к созданному файлу."""
    all_data = db.get_all_results()
    return _generate_report(all_data, output_dir)
