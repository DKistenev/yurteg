"""Модуль AI-извлечения метаданных из договоров.

Отправляет анонимизированный текст в LLM, получает структурированные
метаданные в JSON. Поддерживает два провайдера:
- ZAI (GLM-5) — основной, платный
- OpenRouter — запасной, бесплатные модели
"""
import json
import logging
import os
import re
import time
from typing import Optional

from openai import OpenAI, APIError, APITimeoutError, RateLimitError

from config import Config
from modules.models import ContractMetadata

logger = logging.getLogger(__name__)

# --- Промпты ---

SYSTEM_PROMPT = """Ты - опытный юрист-аналитик. Твоя задача - извлечь структурированные метаданные из текста договора.

ВАЖНО:
- Текст может быть частично анонимизирован (содержать маски вида [ФИО_1], [ТЕЛЕФОН_1] и т.д.). Это нормально, используй маски как есть.
- Отвечай СТРОГО в формате JSON. Никакого текста до или после JSON.
- Если информация отсутствует в тексте - ставь null.
- Поле confidence - твоя уверенность в правильности извлечения (0.0-1.0).
- НЕ оборачивай JSON в ```json``` или другие блоки кода. Просто чистый JSON."""

USER_PROMPT_TEMPLATE = """Извлеки метаданные из следующего текста договора.

Известные типы договоров (используй один из них если подходит):
{contract_types}

Верни JSON со следующими полями:
- contract_type (string): тип договора (например: "Договор поставки", "Договор аренды")
- counterparty (string): наименование основного контрагента (организация или маска [ФИО_N] если физлицо)
- subject (string): предмет договора - краткое описание в 1-2 предложения
- date_signed (string|null): дата подписания в формате YYYY-MM-DD
- date_start (string|null): дата начала действия в формате YYYY-MM-DD
- date_end (string|null): дата окончания действия в формате YYYY-MM-DD
- amount (string|null): сумма договора с валютой (например: "1 500 000 руб.")
- special_conditions (array of strings): особые условия (штрафы, неустойки, гарантии)
- parties (array of strings): все стороны договора
- confidence (float): уверенность в правильности извлечения от 0.0 до 1.0

Текст договора:
{text}"""

VERIFY_PROMPT = """Проверь, соответствуют ли эти метаданные тексту договора.

Начало текста договора:
{text_preview}

Извлечённые метаданные:
{metadata_json}

Верни JSON:
- correct (bool): true если метаданные в целом верны
- corrections (array): список исправлений, каждое - объект с полями "field", "current", "suggested"
- reasoning (string): краткое пояснение

Отвечай СТРОГО в формате JSON, без обёрток."""


def _create_client(config: Config, use_fallback: bool = False) -> OpenAI:
    """
    Создаёт клиент OpenAI-совместимого API.

    Основной провайдер: ZAI (ключ ZHIPU_API_KEY или ZAI_API_KEY)
    Запасной: OpenRouter (ключ OPENROUTER_API_KEY)
    """
    if use_fallback:
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            raise RuntimeError("Ключ OpenRouter не найден (OPENROUTER_API_KEY)")
        return OpenAI(
            base_url=config.ai_fallback_base_url,
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://github.com/yurteg",
                "X-Title": "YurTeg",
            },
        )

    # Основной провайдер — ZAI
    api_key = (
        os.environ.get("ZHIPU_API_KEY", "")
        or os.environ.get("ZAI_API_KEY", "")
        or os.environ.get("OPENROUTER_API_KEY", "")
    )
    if not api_key:
        raise RuntimeError(
            "API-ключ не найден. Установите ZHIPU_API_KEY (ZAI) "
            "или OPENROUTER_API_KEY (OpenRouter)."
        )

    # Определяем base_url по типу ключа
    if api_key.startswith("sk-or-"):
        # OpenRouter ключ
        base_url = config.ai_fallback_base_url
        headers = {"HTTP-Referer": "https://github.com/yurteg", "X-Title": "YurTeg"}
    else:
        # ZAI ключ
        base_url = config.ai_base_url
        headers = {}

    return OpenAI(
        base_url=base_url,
        api_key=api_key,
        default_headers=headers,
    )


def extract_metadata(anonymized_text: str, config: Config) -> ContractMetadata:
    """
    Отправляет анонимизированный текст в LLM, парсит JSON-ответ.

    Стратегия:
    1. Основная модель (ZAI GLM-5) — до ai_max_retries попыток
    2. Fallback (OpenRouter, бесплатная) — если основная недоступна

    Текст обрезается до 80K символов (~20K токенов).

    Raises:
        RuntimeError: если все попытки исчерпаны
    """
    # Обрезать текст если слишком длинный
    text = anonymized_text[:80_000]

    # Формируем список типов для промпта
    types_str = ", ".join(f'"{t}"' for t in config.contract_types)

    user_prompt = USER_PROMPT_TEMPLATE.format(
        contract_types=types_str,
        text=text,
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    # Этап 1: Основная модель
    last_error = _try_model(config, messages, config.active_model, use_fallback=False)
    if isinstance(last_error, ContractMetadata):
        return last_error  # Успех

    # Этап 2: Fallback (OpenRouter)
    if config.model_fallback and os.environ.get("OPENROUTER_API_KEY"):
        logger.info("Основная модель недоступна, пробую fallback: %s", config.model_fallback)
        fallback_result = _try_model(
            config, messages, config.model_fallback, use_fallback=True
        )
        if isinstance(fallback_result, ContractMetadata):
            return fallback_result
        last_error = fallback_result

    raise RuntimeError(
        f"Не удалось извлечь метаданные после всех попыток. "
        f"Последняя ошибка: {last_error}"
    )


def _try_model(
    config: Config,
    messages: list[dict],
    model: str,
    use_fallback: bool = False,
) -> "ContractMetadata | Exception":
    """
    Пробует извлечь метаданные с конкретной моделью.
    Возвращает ContractMetadata при успехе, Exception при неудаче.
    """
    try:
        client = _create_client(config, use_fallback=use_fallback)
    except RuntimeError as e:
        return e

    last_error: Exception = RuntimeError("Нет попыток")

    for attempt in range(config.ai_max_retries):
        try:
            logger.info(
                "AI-запрос: модель=%s, попытка %d/%d",
                model, attempt + 1, config.ai_max_retries,
            )

            response = client.chat.completions.create(
                model=model,
                temperature=config.ai_temperature,
                max_tokens=config.ai_max_tokens,
                messages=messages,
            )

            raw_text = response.choices[0].message.content
            if not raw_text:
                raise ValueError("Пустой ответ от модели")

            logger.debug("AI ответ (первые 500 символов): %s", raw_text[:500])

            json_data = _parse_json_response(raw_text)
            metadata = _json_to_metadata(json_data)

            logger.info(
                "Метаданные извлечены: тип=%s, уверенность=%.2f",
                metadata.contract_type, metadata.confidence,
            )
            return metadata

        except (json.JSONDecodeError, ValueError, KeyError, IndexError) as e:
            last_error = e
            logger.warning(
                "Попытка %d/%d (%s): невалидный ответ - %s",
                attempt + 1, config.ai_max_retries, model, e,
            )
            if attempt < config.ai_max_retries - 1:
                time.sleep(2 ** attempt)

        except RateLimitError as e:
            last_error = e
            logger.warning(
                "Попытка %d/%d (%s): лимит запросов - %s",
                attempt + 1, config.ai_max_retries, model, e,
            )
            time.sleep(min(2 ** (attempt + 2), 30))

        except (APIError, APITimeoutError) as e:
            last_error = e
            logger.warning(
                "Попытка %d/%d (%s): ошибка API - %s",
                attempt + 1, config.ai_max_retries, model, e,
            )
            if attempt < config.ai_max_retries - 1:
                time.sleep(2 ** attempt)

    logger.warning("Все попытки исчерпаны для модели %s", model)
    return last_error


def verify_metadata(
    anonymized_text_preview: str,
    metadata: ContractMetadata,
    config: Config,
) -> dict:
    """
    AI-валидация L5 (опциональная).

    Отправляет первые 500 символов текста + метаданные на верификацию.
    Использует fallback-модель (более быструю).

    Возвращает: {"correct": bool, "corrections": [...], "reasoning": str}
    При ошибке: {"correct": True, "corrections": [], "reasoning": "verification_failed"}
    """
    try:
        client = _create_client(config)

        metadata_dict = {
            "contract_type": metadata.contract_type,
            "counterparty": metadata.counterparty,
            "subject": metadata.subject,
            "date_signed": metadata.date_signed,
            "amount": metadata.amount,
            "parties": metadata.parties,
        }

        user_prompt = VERIFY_PROMPT.format(
            text_preview=anonymized_text_preview[:500],
            metadata_json=json.dumps(metadata_dict, ensure_ascii=False, indent=2),
        )

        response = client.chat.completions.create(
            model=config.active_model,
            temperature=0,
            max_tokens=1000,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw_text = response.choices[0].message.content
        if not raw_text:
            raise ValueError("Пустой ответ")

        result = _parse_json_response(raw_text)

        return {
            "correct": result.get("correct", True),
            "corrections": result.get("corrections", []),
            "reasoning": result.get("reasoning", ""),
        }

    except Exception as e:
        logger.warning("AI-верификация не удалась: %s", e)
        return {
            "correct": True,
            "corrections": [],
            "reasoning": "verification_failed",
        }


def verify_api_key(config: Config) -> bool:
    """
    Проверяет валидность API-ключа одним дешёвым запросом.
    Возвращает True если ключ рабочий, False если нет.

    Rate limit (429) считается подтверждением — ключ валиден,
    просто модель перегружена.
    """
    try:
        client = _create_client(config)
        response = client.chat.completions.create(
            model=config.active_model,
            max_tokens=20,
            messages=[{"role": "user", "content": "Ответь одним словом: работает"}],
        )
        # Успех если получили ответ (даже пустой — главное нет ошибки)
        return True
    except RateLimitError:
        # 429 = ключ валиден, но модель перегружена
        logger.info("API-ключ валиден (rate limit — модель временно перегружена)")
        return True
    except RuntimeError:
        # Ключ не найден
        return False
    except Exception as e:
        logger.warning("Проверка API-ключа не удалась: %s", e)
        return False


def _parse_json_response(raw: str) -> dict:
    """Извлекает JSON из ответа модели (может быть обёрнут по-разному)."""
    # Шаг 0: Убрать блоки <think>...</think> (thinking-модели)
    cleaned = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()

    # Попытка 1: прямой парсинг
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Попытка 2: извлечь из ```json ... ```
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Попытка 3: найти первый { ... } блок
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise json.JSONDecodeError("Не найден JSON в ответе модели", raw, 0)


def _json_to_metadata(data: dict) -> ContractMetadata:
    """Конвертирует dict в ContractMetadata с безопасным доступом."""
    return ContractMetadata(
        contract_type=data.get("contract_type"),
        counterparty=data.get("counterparty"),
        subject=data.get("subject"),
        date_signed=data.get("date_signed"),
        date_start=data.get("date_start"),
        date_end=data.get("date_end"),
        amount=data.get("amount"),
        special_conditions=data.get("special_conditions", []),
        parties=data.get("parties", []),
        confidence=float(data.get("confidence", 0.0)),
    )
