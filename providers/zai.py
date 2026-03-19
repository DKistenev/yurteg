"""ZAI (GLM) провайдер — основной провайдер ЮрТэг."""
import logging
import os

from openai import OpenAI

from config import Config
from providers.base import LLMProvider

logger = logging.getLogger(__name__)


class ZAIProvider(LLMProvider):
    """Провайдер ZAI (api.z.ai) — GLM-4.7 и совместимые модели."""

    name = "zai"

    def __init__(self, config: Config) -> None:
        self._config = config
        api_key = (
            os.environ.get("ZAI_API_KEY", "")
            or os.environ.get("ZHIPU_API_KEY", "")
            or ""
        )
        self._client = OpenAI(
            base_url=config.ai_base_url,
            api_key=api_key,
        )

    def complete(self, messages: list[dict], **kwargs) -> str:
        """Вызов ZAI API. Добавляет extra_body thinking:disabled если включено в конфиге."""
        extra = {}
        if self._config.ai_disable_thinking:
            extra["extra_body"] = {"thinking": {"type": "disabled"}}

        response = self._client.chat.completions.create(
            model=self._config.active_model,
            temperature=self._config.ai_temperature,
            max_tokens=self._config.ai_max_tokens,
            messages=messages,
            **extra,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("ZAI вернул пустой ответ")
        return content

    def verify_key(self) -> bool:
        """Проверяет API-ключ дешёвым запросом."""
        try:
            self._client.models.list()
            return True
        except Exception:
            return False
