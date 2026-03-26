"""Ollama провайдер — локальная LLM через llama-server.

Использует OpenAI-совместимый endpoint llama-server на localhost.
Post-processing ответов через modules/postprocessor.sanitize_metadata
подключается в Phase 5 (PROC-01) в ai_extractor.py.

Двухзапросный flow (Phase 29-02):
- complete() принимает grammar= в kwargs и передаёт через extra_body (llama-server extension)
- get_logprobs() делает второй запрос без grammar с logprobs=True для оценки уверенности
"""
import logging

from openai import OpenAI

from config import Config
from providers.base import LLMProvider

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Провайдер для llama-server — локальная QWEN 1.5B через OpenAI API."""

    name = "ollama"

    def __init__(self, config: Config, base_url: str | None = None) -> None:
        self._config = config
        if base_url is None:
            base_url = f"http://localhost:{config.llama_server_port}/v1"
        self._client = OpenAI(
            base_url=base_url,
            api_key="not-needed",  # llama-server не требует ключ
        )

    def complete(self, messages: list[dict], **kwargs) -> str:
        """Отправляет запрос в llama-server, возвращает сырой текст ответа.

        Принимает необязательный kwargs["grammar"] — GBNF-строка, передаётся
        через extra_body (llama-server b5606 extension, параметр "grammar").
        При наличии grammar модель гарантированно возвращает JSON по схеме.

        Post-processing (sanitize_metadata) применяется в ai_extractor.py.
        """
        extra_body: dict = {}
        if "grammar" in kwargs:
            grammar_val = kwargs.pop("grammar")
            if grammar_val:
                extra_body["grammar"] = grammar_val

        response = self._client.chat.completions.create(
            model="local",  # llama-server загружает модель при старте, имя игнорируется
            temperature=kwargs.get("temperature", 0.05),
            max_tokens=kwargs.get("max_tokens", 512),
            messages=messages,
            extra_body=extra_body if extra_body else None,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("llama-server вернул пустой ответ")
        return content

    def get_logprobs(
        self,
        messages: list[dict],
        fields_to_check: list[str],
    ) -> dict[str, float]:
        """Второй запрос без grammar — возвращает агрегированные logprobs.

        Используется для оценки уверенности модели по ключевым полям.
        Делается только для документов с подозрительными null-полями.

        Args:
            messages: исходные сообщения с текстом документа
            fields_to_check: список имён полей для проверки (для формирования промпта)

        Returns:
            dict с "_min" и "_mean" logprob (отрицательные числа, ближе к 0 = увереннее).
            Пустой dict если logprobs недоступны или запрос не удался.
        """
        field_list = ", ".join(fields_to_check)
        probe_user = (
            f"Из этого документа верни ТОЛЬКО JSON с полями: {field_list}. "
            "Без объяснений, только JSON."
        )
        # Берём системный промпт из оригинальных messages (если есть), добавляем probe-запрос
        system_msgs = [m for m in messages if m.get("role") == "system"]
        probe_messages = system_msgs + [{"role": "user", "content": probe_user}]

        # Добавляем текст документа из оригинального user-сообщения
        user_msgs = [m for m in messages if m.get("role") == "user"]
        if user_msgs:
            # Берём первые 2000 символов текста — достаточно для ключевых полей
            original_content = user_msgs[0].get("content", "")
            probe_messages = system_msgs + [
                {"role": "user", "content": original_content[:2000] + f"\n\nВерни ТОЛЬКО JSON с полями: {field_list}."},
            ]

        try:
            response = self._client.chat.completions.create(
                model="local",
                temperature=0.0,  # детерминировано для logprobs
                max_tokens=100,
                messages=probe_messages,
                logprobs=True,
                top_logprobs=1,
            )
        except Exception as exc:
            logger.warning("get_logprobs: запрос не удался — %s", exc)
            return {}

        # Парсим logprobs из ответа
        logprobs_content = getattr(
            getattr(response.choices[0], "logprobs", None), "content", None
        )
        if not logprobs_content:
            logger.debug("get_logprobs: logprobs отсутствуют в ответе")
            return {}

        # Берём min и mean logprob по всем токенам — агрегированная оценка уверенности
        all_logprobs = [
            token.logprob
            for token in logprobs_content
            if token.logprob is not None
        ]
        if not all_logprobs:
            return {}

        result = {
            "_min": min(all_logprobs),
            "_mean": sum(all_logprobs) / len(all_logprobs),
        }
        logger.debug(
            "get_logprobs: %d токенов, min=%.3f mean=%.3f",
            len(all_logprobs), result["_min"], result["_mean"],
        )
        return result

    def verify_key(self) -> bool:
        """Проверяет доступность llama-server через models endpoint."""
        try:
            self._client.models.list()
            return True
        except Exception:
            return False
