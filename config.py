"""Централизованная конфигурация приложения."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """Все настройки приложения в одном месте."""

    # Поддерживаемые форматы
    supported_extensions: tuple[str, ...] = (".pdf", ".docx")
    max_file_size_mb: int = 50

    # AI — провайдеры и модели
    # Основной: ZAI Coding Plan Pro (GLM-4.7)
    ai_base_url: str = "https://api.z.ai/api/coding/paas/v4"
    model_dev: str = "glm-4.7"
    model_prod: str = "glm-4.7"
    # Запасной: OpenRouter (бесплатные модели)
    ai_fallback_base_url: str = "https://openrouter.ai/api/v1"
    model_fallback: str = "arcee-ai/trinity-large-preview:free"
    use_prod_model: bool = False
    ai_max_retries: int = 2
    ai_temperature: float = 0
    ai_max_tokens: int = 2000
    ai_disable_thinking: bool = True  # отключить thinking mode у GLM (5-7x ускорение)
    max_workers: int = 5  # потоков для параллельных AI-запросов

    # Валидация
    confidence_high: float = 0.8
    confidence_low: float = 0.5
    validation_mode: str = "off"  # "off" | "selective" | "full"

    # Справочник типов документов (подсказки для AI, не ограничения)
    document_types_hints: list[str] = field(default_factory=lambda: [
        # Договоры
        "Договор поставки",
        "Договор оказания услуг",
        "Договор подряда",
        "Договор аренды",
        "Договор займа",
        "Договор купли-продажи",
        "Трудовой договор",
        "Договор цессии",
        "Лицензионный договор",
        "Агентский договор",
        "Договор хранения",
        "Договор комиссии",
        "Дополнительное соглашение",
        "Рамочный договор",
        "NDA / Соглашение о конфиденциальности",
        # Финансовые документы
        "Счёт на оплату",
        "Счёт-фактура",
        "Акт выполненных работ",
        "Акт сверки",
        "Товарная накладная",
        # Коммерческие / иные
        "Коммерческое предложение",
        "Протокол разногласий",
        "Протокол согласования",
        "Доверенность",
        "Гарантийное письмо",
    ])

    # Анонимизация: какие типы ПД маскировать (None = все)
    anonymize_types: Optional[set[str]] = None

    # Имя выходной папки
    output_folder_name: str = "ЮрТэг_Результат"

    @property
    def active_model(self) -> str:
        return self.model_prod if self.use_prod_model else self.model_dev
