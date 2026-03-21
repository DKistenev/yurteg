"""Ollama провайдер — локальная LLM через llama-server.

Использует OpenAI-совместимый endpoint llama-server на localhost.
Post-processing ответов через modules/postprocessor.sanitize_metadata
подключается в Phase 5 (PROC-01) в ai_extractor.py.
"""
import logging

from openai import OpenAI

from config import Config
from providers.base import LLMProvider

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Провайдер для llama-server — локальная QWEN 1.5B через OpenAI API."""

    name = "ollama"

    def __init__(self, config: Config, base_url: str = "http://localhost:8080/v1") -> None:
        self._config = config
        self._client = OpenAI(
            base_url=base_url,
            api_key="not-needed",  # llama-server не требует ключ
        )

    def complete(self, messages: list[dict], **kwargs) -> str:
        """Отправляет запрос в llama-server, возвращает сырой текст ответа.

        Post-processing (sanitize_metadata) применяется в ai_extractor.py.
        """
        response = self._client.chat.completions.create(
            model="local",  # llama-server загружает модель при старте, имя игнорируется
            temperature=0.05,  # из Modelfile
            max_tokens=512,    # num_predict из Modelfile
            messages=messages,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("llama-server вернул пустой ответ")
        return content

    def verify_key(self) -> bool:
        """Проверяет доступность llama-server через models endpoint."""
        try:
            self._client.models.list()
            return True
        except Exception:
            return False
