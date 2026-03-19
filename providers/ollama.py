"""Ollama провайдер — stub для локальной LLM (Веха 3).

Ollama поддерживает OpenAI-совместимый endpoint на localhost:11434.
Реализация запланирована на Веху 3 (локальная QWEN).
"""
from config import Config
from providers.base import LLMProvider


class OllamaProvider(LLMProvider):
    """Провайдер Ollama — локальная LLM через OpenAI-совместимый endpoint.

    STUB: полная реализация в Вехе 3.
    """

    name = "ollama"

    def __init__(self, config: Config) -> None:
        self._config = config

    def complete(self, messages: list[dict], **kwargs) -> str:
        raise NotImplementedError(
            "Поддержка Ollama запланирована на Веху 3. "
            "Используйте active_provider='zai' или 'openrouter'."
        )

    def verify_key(self) -> bool:
        raise NotImplementedError(
            "Поддержка Ollama запланирована на Веху 3."
        )
