"""OpenRouter провайдер — запасной провайдер ЮрТэг."""
import logging
import os

from openai import OpenAI

from config import Config
from providers.base import LLMProvider

logger = logging.getLogger(__name__)


def _merge_system_into_user(messages: list[dict]) -> list[dict]:
    """Вклеивает system-сообщения в начало первого user-сообщения.

    Нужно для бесплатных моделей OpenRouter, не поддерживающих role='system'
    (gemma, некоторые llama-вариации).
    """
    system_parts: list[str] = []
    other: list[dict] = []
    for msg in messages:
        m = dict(msg)  # defensive copy
        if m["role"] == "system":
            system_parts.append(m["content"])
        else:
            other.append(m)

    if not system_parts or not other:
        return messages

    prefix = "\n\n".join(system_parts)
    merged = []
    injected = False
    for msg in other:
        if msg["role"] == "user" and not injected:
            merged.append({
                "role": "user",
                "content": f"[Инструкция]\n{prefix}\n\n[Задание]\n{msg['content']}",
            })
            injected = True
        else:
            merged.append(msg)
    return merged


class OpenRouterProvider(LLMProvider):
    """Провайдер OpenRouter — бесплатные и платные модели через openrouter.ai."""

    name = "openrouter"

    def __init__(self, config: Config) -> None:
        self._config = config
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY не задан в переменных окружения")
        self._client = OpenAI(
            base_url=config.ai_fallback_base_url,
            api_key=api_key,
            timeout=60.0,
            default_headers={
                "HTTP-Referer": "https://github.com/yurteg",
                "X-Title": "YurTeg",
            },
        )

    def complete(self, messages: list[dict], **kwargs) -> str:
        """Вызов OpenRouter API. Автоматически склеивает system в user для совместимости."""
        merged = _merge_system_into_user(messages)
        response = self._client.chat.completions.create(
            model=self._config.model_fallback,
            temperature=self._config.ai_temperature,
            max_tokens=self._config.ai_max_tokens,
            messages=merged,
        )
        if not response.choices:
            raise RuntimeError("OpenRouter вернул пустой choices")
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("OpenRouter вернул пустой ответ")
        return content

    def verify_key(self) -> bool:
        """Проверяет API-ключ."""
        try:
            self._client.models.list()
            return True
        except Exception as exc:
            logger.warning("OpenRouter verify_key failed: %s", exc)
            return False
