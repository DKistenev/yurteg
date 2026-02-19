"""Централизованная конфигурация приложения."""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    """Все настройки приложения в одном месте."""

    # Поддерживаемые форматы
    supported_extensions: tuple[str, ...] = (".pdf", ".docx")
    max_file_size_mb: int = 50

    # AI — провайдеры и модели
    # Основной: ZAI Coding Plan Pro (GLM-5)
    ai_base_url: str = "https://api.z.ai/api/coding/paas/v4"
    model_dev: str = "glm-5"
    model_prod: str = "glm-5"
    # Запасной: OpenRouter (бесплатные модели)
    ai_fallback_base_url: str = "https://openrouter.ai/api/v1"
    model_fallback: str = "google/gemma-3-27b-it:free"
    use_prod_model: bool = False
    ai_max_retries: int = 3
    ai_temperature: float = 0
    ai_max_tokens: int = 4000  # Увеличено: thinking-модели используют больше токенов

    # Валидация
    confidence_high: float = 0.8
    confidence_low: float = 0.5
    validation_mode: str = "off"  # "off" | "selective" | "full"

    # Справочник типов договоров
    contract_types: list[str] = field(default_factory=lambda: [
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
    ])

    # Имя выходной папки
    output_folder_name: str = "ЮрТэг_Результат"

    @property
    def active_model(self) -> str:
        return self.model_prod if self.use_prod_model else self.model_dev
