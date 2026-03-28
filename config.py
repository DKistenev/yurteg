"""Централизованная конфигурация приложения."""
import json
import logging
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

logger = logging.getLogger(__name__)

APP_VERSION = "1.0.0-beta"


@dataclass
class Config:
    """Все настройки приложения в одном месте."""

    # Поддерживаемые форматы
    supported_extensions: tuple[str, ...] = (".pdf", ".docx")
    max_file_size_mb: int = 50

    # AI — провайдеры и модели
    # Основной: ZAI Coding Plan Pro (GLM-4.7)
    ai_base_url: str = "https://api.z.ai/api/coding/paas/v4"
    # Запасной: OpenRouter (бесплатные модели)
    ai_fallback_base_url: str = "https://openrouter.ai/api/v1"
    model_fallback: str = "arcee-ai/trinity-large-preview:free"
    ai_max_retries: int = 2
    ai_temperature: float = 0
    ai_max_tokens: int = 2000
    active_provider: str = "ollama"        # "zai" | "openrouter" | "ollama"
    fallback_provider: str = "zai"         # автофallback при недоступности active_provider

    # Локальная LLM (llama-server)
    llama_server_port: int = 8080
    llama_model_repo: str = "SuperPuperD/yurteg-1.5b-v3-gguf"
    llama_model_filename: str = "yurteg-v3-Q4_K_M.gguf"
    max_workers: int = 5  # потоков для параллельных AI-запросов
    warning_days_threshold: int = 30  # порог предупреждения о сроках (дней)

    # Валидация
    confidence_high: float = 0.8
    confidence_low: float = 0.5
    validation_mode: Literal["off", "selective", "full"] = "off"

    # Справочник типов документов (подсказки для AI, не ограничения)
    document_types_hints: list[str] = field(default_factory=lambda: [
        # Договоры
        "Договор оказания услуг",
        "Договор купли-продажи",
        "Договор поставки",
        "Договор аренды",
        "Договор подряда",
        "Договор займа",
        "Договор лизинга",
        "Договор комиссии",
        "Договор хранения",
        "Договор цессии",
        "Договор безвозмездного пользования",
        "Договор страхования",
        "Договор транспортной экспедиции",
        "Договор коммерческой концессии",
        "Агентский договор",
        "Лицензионный договор",
        "Договор мены",
        "Договор найма жилого помещения",
        "Договор субаренды",
        "Субагентский договор",
        "Договор простого товарищества",
        "Договор о совместной деятельности",
        "Договор дарения",
        "Договор поручения",
        "Договор банковского вклада",
        "Договор банковского счета",
        "Брачный договор",
        "Договор вестинга",
        "Эскроу-договор",
        "Договор контрактации",
        "Договор долевого участия в строительстве",
        "Договор перевозки",
        "Договор поручительства",
        "Договор перевода долга",
        "Кредитный договор",
        "Договор факторинга",
        "Трудовой договор",
        # Дополнительные соглашения
        "Дополнительное соглашение",
        "Рамочный договор",
        "Соглашение о расторжении",
        # Финансовые / бухгалтерские
        "Счёт на оплату",
        "Счёт-фактура",
        "УПД",
        "Акт выполненных работ",
        "Акт сверки",
        "Акт приема-передачи",
        "Товарная накладная",
        # Корпоративные
        "Протокол общего собрания",
        "Решение единственного участника",
        "Устав",
        "Корпоративный договор",
        "Соглашение о предоставлении опциона",
        "Передаточный акт",
        # Персональные данные
        "Согласие на обработку ПД",
        "Согласие на обработку биометрических ПД",
        "Политика обработки ПД",
        "Политика конфиденциальности",
        "Положение об обработке ПД",
        "Уведомление об обработке ПД",
        "Уведомление об уничтожении ПД",
        "Приказ о назначении ответственного за ПД",
        # Трудовые
        "Приказ",
        "Должностная инструкция",
        "Уведомление о расторжении трудового договора",
        # Судебные
        "Исковое заявление",
        "Претензия",
        "Протокол разногласий",
        "Апелляционная жалоба",
        "Кассационная жалоба",
        "Мировое соглашение",
        "Отзыв на исковое заявление",
        # Прочие
        "Доверенность",
        "Банковская гарантия",
        "Коммерческое предложение",
        "Соглашение о конфиденциальности",
        "Оферта на оказание услуг",
        "Пользовательское соглашение",
        "Правила акции",
        "Гарантийное письмо",
        "Карточка контрагента",
        "Расписка",
        "Положение",
    ])

    # Анонимизация: какие типы ПД маскировать (None = все)
    anonymize_types: Optional[set[str]] = None

    # Telegram-интеграция
    telegram_server_url: str = ""  # URL сервера бота (e.g., "https://yurteg-bot.railway.app")
    telegram_chat_id: Optional[int] = None  # привязанный Telegram chat_id (None = не привязан)

    # Имя выходной папки
    output_folder_name: str = "ЮрТэг_Результат"

    def __post_init__(self) -> None:
        """Graceful validation — исправляет невалидные значения, не падает."""
        _valid_providers = {"zai", "openrouter", "ollama"}
        if self.active_provider not in _valid_providers:
            logger.warning("Неизвестный провайдер %r, использую ollama", self.active_provider)
            self.active_provider = "ollama"

        if self.fallback_provider not in _valid_providers:
            logger.warning("Неизвестный fallback провайдер %r, использую zai", self.fallback_provider)
            self.fallback_provider = "zai"

        if not (0 < self.llama_server_port <= 65535):
            logger.warning("Неверный порт %d, использую 8080", self.llama_server_port)
            self.llama_server_port = 8080

        if self.validation_mode not in {"off", "selective", "full"}:
            logger.warning("Неверный validation_mode %r, использую off", self.validation_mode)
            self.validation_mode = "off"

        if self.max_workers < 1:
            logger.warning("max_workers < 1, использую 1")
            self.max_workers = 1

        if self.confidence_high <= self.confidence_low:
            raise ValueError(
                f"confidence_high ({self.confidence_high}) должен быть > confidence_low ({self.confidence_low})"
            )

    @property
    def active_model(self) -> str:
        """Возвращает имя модели для текущего active_provider."""
        if self.active_provider == "ollama":
            return "local"
        if self.active_provider == "openrouter":
            return self.model_fallback
        return "glm-4.7"


# ---------------------------------------------------------------------------
# Settings persistence — централизованное хранение настроек
# ---------------------------------------------------------------------------

_SETTINGS_FILE = Path.home() / ".yurteg" / "settings.json"
_settings_lock = threading.Lock()


def load_settings() -> dict:
    """Загружает персистентные настройки из ~/.yurteg/settings.json."""
    try:
        if _SETTINGS_FILE.exists():
            return json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        logger.warning("settings.json повреждён: %s — используются дефолты", e)
    except OSError as e:
        logger.warning("Не удалось прочитать settings.json: %s — используются дефолты", e)
    return {}


def save_setting(key: str, value) -> None:
    """Сохраняет один ключ в ~/.yurteg/settings.json (merge, thread-safe)."""
    with _settings_lock:
        s = load_settings()
        s[key] = value
        _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _SETTINGS_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            os.chmod(_SETTINGS_FILE, 0o600)
        except OSError:
            pass  # Windows не поддерживает POSIX chmod
