"""Тесты для централизованных настроек (config.py) и методов сервисов.

Покрывает:
- load_settings() / save_setting() в config.py
- delete_template() / update_template() в services/review_service.py
- check_connection() в services/telegram_sync.py
"""
import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from modules.database import Database
from services.review_service import (
    add_template,
    delete_template,
    list_templates,
    update_template,
)
from services.telegram_sync import TelegramSync


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db(tmp_path: Path) -> Database:
    """Создаёт in-memory Database с нужной схемой."""
    db = Database(tmp_path / "test.db")
    return db


# ---------------------------------------------------------------------------
# Settings persistence tests (config.py)
# ---------------------------------------------------------------------------

class TestLoadSettings:
    def test_returns_empty_dict_when_file_missing(self, tmp_path: Path, monkeypatch):
        """load_settings() возвращает {} если settings.json не существует."""
        import config as cfg_module
        monkeypatch.setattr(cfg_module, "_SETTINGS_FILE", tmp_path / "nonexistent.json")
        result = cfg_module.load_settings()
        assert result == {}

    def test_save_and_load_string(self, tmp_path: Path, monkeypatch):
        """save_setting() сохраняет строку, load_settings() её возвращает."""
        import config as cfg_module
        settings_file = tmp_path / "settings.json"
        monkeypatch.setattr(cfg_module, "_SETTINGS_FILE", settings_file)

        cfg_module.save_setting("active_provider", "zai")
        result = cfg_module.load_settings()
        assert result == {"active_provider": "zai"}

    def test_save_and_load_integer(self, tmp_path: Path, monkeypatch):
        """save_setting() сохраняет целое число."""
        import config as cfg_module
        settings_file = tmp_path / "settings.json"
        monkeypatch.setattr(cfg_module, "_SETTINGS_FILE", settings_file)

        cfg_module.save_setting("warning_days", 45)
        result = cfg_module.load_settings()
        assert result["warning_days"] == 45

    def test_save_and_load_list(self, tmp_path: Path, monkeypatch):
        """save_setting() сохраняет список."""
        import config as cfg_module
        settings_file = tmp_path / "settings.json"
        monkeypatch.setattr(cfg_module, "_SETTINGS_FILE", settings_file)

        cfg_module.save_setting("anonymize_types", ["ФИО", "ИНН"])
        result = cfg_module.load_settings()
        assert result["anonymize_types"] == ["ФИО", "ИНН"]

    def test_save_merges_not_overwrites(self, tmp_path: Path, monkeypatch):
        """Повторный save_setting() не затирает предыдущие ключи."""
        import config as cfg_module
        settings_file = tmp_path / "settings.json"
        monkeypatch.setattr(cfg_module, "_SETTINGS_FILE", settings_file)

        cfg_module.save_setting("key_a", "value_a")
        cfg_module.save_setting("key_b", "value_b")
        result = cfg_module.load_settings()
        assert result["key_a"] == "value_a"
        assert result["key_b"] == "value_b"


# ---------------------------------------------------------------------------
# Template CRUD tests (services/review_service.py)
# ---------------------------------------------------------------------------

class TestTemplateCrud:
    def test_delete_template_soft_deletes(self, tmp_path: Path):
        """delete_template() устанавливает is_active=0, шаблон пропадает из list_templates()."""
        db = _make_db(tmp_path)
        tmpl_id = add_template(db, "Аренда", "Эталон аренды", "Текст шаблона аренды")
        assert len(list_templates(db)) == 1

        result = delete_template(db, tmpl_id)
        assert result is True
        assert list_templates(db) == []

    def test_delete_template_returns_false_for_missing(self, tmp_path: Path):
        """delete_template() возвращает False если шаблон не найден."""
        db = _make_db(tmp_path)
        result = delete_template(db, 9999)
        assert result is False

    def test_delete_template_returns_false_for_already_deleted(self, tmp_path: Path):
        """delete_template() на уже удалённом шаблоне возвращает False."""
        db = _make_db(tmp_path)
        tmpl_id = add_template(db, "Услуги", "Эталон", "Текст")
        delete_template(db, tmpl_id)
        result = delete_template(db, tmpl_id)
        assert result is False

    def test_update_template_changes_name_and_type(self, tmp_path: Path):
        """update_template() обновляет name и contract_type."""
        db = _make_db(tmp_path)
        tmpl_id = add_template(db, "Услуги", "Старое название", "Текст")

        result = update_template(db, tmpl_id, name="Новое название", contract_type="Аренда")
        assert result is True

        templates = list_templates(db)
        assert len(templates) == 1
        assert templates[0].name == "Новое название"
        assert templates[0].contract_type == "Аренда"

    def test_update_template_returns_false_for_missing(self, tmp_path: Path):
        """update_template() возвращает False если шаблон не найден."""
        db = _make_db(tmp_path)
        result = update_template(db, 9999, name="Что-то", contract_type="Аренда")
        assert result is False


# ---------------------------------------------------------------------------
# Telegram connection check tests (services/telegram_sync.py)
# ---------------------------------------------------------------------------

class TestCheckConnection:
    def test_returns_false_when_base_empty(self):
        """check_connection() возвращает False если server_url не задан."""
        sync = TelegramSync("", 0)
        assert sync.check_connection() is False

    def test_returns_true_on_200(self):
        """check_connection() возвращает True при HTTP 200."""
        sync = TelegramSync("http://localhost:9999", 123)
        mock_response = MagicMock()
        mock_response.status_code = 200
        sync._client = MagicMock()
        sync._client.get.return_value = mock_response

        assert sync.check_connection() is True
        sync._client.get.assert_called_once_with("http://localhost:9999/health", timeout=5)

    def test_returns_false_on_500(self):
        """check_connection() возвращает False при HTTP >= 400."""
        sync = TelegramSync("http://localhost:9999", 123)
        mock_response = MagicMock()
        mock_response.status_code = 500
        sync._client = MagicMock()
        sync._client.get.return_value = mock_response

        assert sync.check_connection() is False

    def test_returns_false_on_network_error(self):
        """check_connection() возвращает False при сетевой ошибке."""
        import httpx
        sync = TelegramSync("http://unreachable.invalid", 123)
        sync._client = MagicMock()
        sync._client.get.side_effect = httpx.ConnectError("Connection refused")

        assert sync.check_connection() is False
