"""Абстрактный базовый класс для AI-провайдеров."""
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Контракт для всех LLM-провайдеров.

    Конкретный провайдер реализует complete() и verify_key().
    Retry-логика и fallback-роутинг живут в ai_extractor.py — не здесь.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Идентификатор провайдера для логирования: 'zai', 'openrouter', 'ollama'."""
        ...

    @abstractmethod
    def complete(self, messages: list[dict], **kwargs) -> str:
        """Отправляет запрос к LLM, возвращает текстовый ответ.

        Args:
            messages: список сообщений в формате OpenAI [{role, content}, ...]
            **kwargs: провайдер-специфичные параметры

        Returns:
            Строка с ответом модели.

        Raises:
            RuntimeError: при неустранимой ошибке провайдера.
        """
        ...

    @abstractmethod
    def verify_key(self) -> bool:
        """Проверяет валидность API-ключа. Возвращает True/False, не поднимает исключений."""
        ...

    def get_logprobs(
        self,
        messages: list[dict],
        fields_to_check: list[str],
    ) -> dict[str, float]:
        """Возвращает logprobs для оценки уверенности. По умолчанию — пустой dict."""
        return {}

    def close(self) -> None:
        """Закрывает HTTP-соединения провайдера."""
        client = getattr(self, "_client", None)
        if client is not None and hasattr(client, "close"):
            client.close()
