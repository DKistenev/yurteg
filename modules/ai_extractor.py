"""Модуль AI-извлечения метаданных из юридических документов.

Отправляет анонимизированный текст в LLM, получает структурированные
метаданные в JSON. Поддерживает два провайдера:
- ZAI (GLM-4.7) — основной, платный
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

SYSTEM_PROMPT = """Ты — опытный юрист-аналитик. Извлеки структурированные метаданные из юридического документа.

ПРАВИЛА:
1. Текст может содержать маски анонимизации ([ФИО_1], [ТЕЛЕФОН_1] и т.д.) — используй их как есть.
2. Отвечай СТРОГО чистым JSON. Без текста до/после, без обёрток ```json```.
3. Отсутствующую информацию ставь null (не пустую строку "").
4. Списки всегда массивы: parties=[], special_conditions=[]. Никогда не null и не строка.
5. confidence — число от 0.0 до 1.0 (не строка).
6. Сумму пиши с пробелами-разделителями и валютой: "1 500 000 руб.", "25 000 EUR".
7. Даты строго YYYY-MM-DD."""

USER_PROMPT_TEMPLATE = """Извлеки метаданные из текста юридического документа.

Известные типы документов (используй подходящий из списка или определи свой):
{document_types}

Верни JSON с полями:
- document_type (string): тип документа. Примеры: "Договор поставки", "Счёт на оплату", "Акт выполненных работ", "Коммерческое предложение"
- counterparty (string): основной контрагент (организация или маска [ФИО_N])
- subject (string): предмет документа — 1-2 предложения
- date_signed (string|null): дата подписания, YYYY-MM-DD
- date_start (string|null): дата начала действия, YYYY-MM-DD
- date_end (string|null): дата окончания, YYYY-MM-DD
- amount (string|null): сумма с валютой, пробелы-разделители (пример: "1 500 000 руб.")
- special_conditions (array of strings): особые условия (штрафы, неустойки, гарантии). Пустой массив [] если нет
- parties (array of strings): все стороны документа. Пустой массив [] если не определены
- confidence (float): уверенность 0.0–1.0

Пример ответа:
{{"document_type": "Договор оказания услуг", "counterparty": "ООО \u00abАльфа\u00bb", "subject": "Оказание юридических консультационных услуг", "date_signed": "2024-03-15", "date_start": "2024-04-01", "date_end": "2025-03-31", "amount": "500 000 руб.", "special_conditions": ["Неустойка 0.1% за каждый день просрочки", "Гарантийный срок 12 месяцев"], "parties": ["ООО \u00abАльфа\u00bb", "[ФИО_1]"], "confidence": 0.92}}

Текст документа:
{text}"""

FALLBACK_PROMPT_TEMPLATE = """Текст документа не удалось обработать полностью. Извлеки базовую информацию.

Определи:
- document_type (string): тип документа
- counterparty (string): контрагент
- subject (string): предмет (кратко)
- confidence (float): уверенность 0.0-1.0

Верни ТОЛЬКО JSON с этими 4 полями.

Текст (первые 3000 символов):
{text}"""

VERIFY_PROMPT = """Проверь, соответствуют ли эти метаданные тексту документа.

Начало текста документа:
{text_preview}

Извлечённые метаданные:
{metadata_json}

Верни JSON:
- correct (bool): true если метаданные в целом верны
- corrections (array): список исправлений, каждое — объект с полями "field", "current", "suggested"
- reasoning (string): краткое пояснение

Отвечай СТРОГО в формате JSON, без обёрток."""


def _merge_system_into_user(messages: list[dict]) -> list[dict]:
    """Вклеивает system-сообщения в начало первого user-сообщения.

    Нужно для моделей, не поддерживающих role='system'
    (gemma, некоторые бесплатные модели на OpenRouter).
    """
    system_parts: list[str] = []
    other: list[dict] = []
    for msg in messages:
        if msg["role"] == "system":
            system_parts.append(msg["content"])
        else:
            other.append(msg)

    if not system_parts or not other:
        return messages

    # Вклеиваем system prompt как инструкцию в начало user-сообщения
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

    Текст обрезается до 30K символов (~7.5K токенов).

    Raises:
        RuntimeError: если все попытки исчерпаны
    """
    # Обрезать текст если слишком длинный (30K достаточно для 95% документов)
    text = anonymized_text[:30_000]

    # Формируем список типов для промпта
    types_str = ", ".join(f'"{t}"' for t in config.document_types_hints)

    user_prompt = USER_PROMPT_TEMPLATE.format(
        document_types=types_str,
        text=text,
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    # Этап 1: Основная модель
    result = _try_model(config, messages, config.active_model, use_fallback=False)
    if isinstance(result, ContractMetadata):
        # Проверка: если все ключевые поля пустые — пробуем упрощённый промпт
        if not result.contract_type and not result.counterparty and not result.subject:
            logger.info("Все ключевые поля пустые, пробую упрощённый промпт...")
            fallback_msgs = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": FALLBACK_PROMPT_TEMPLATE.format(text=text[:3000])},
            ]
            fb = _try_model(config, fallback_msgs, config.active_model, use_fallback=False)
            if isinstance(fb, ContractMetadata) and (fb.contract_type or fb.counterparty):
                return fb
        return result

    last_error = result

    # Этап 2: Fallback модель (OpenRouter)
    if config.model_fallback and os.environ.get("OPENROUTER_API_KEY"):
        logger.info("Основная модель недоступна, пробую fallback: %s", config.model_fallback)
        # Некоторые бесплатные модели не поддерживают system role —
        # вклеиваем system prompt в начало user-сообщения для надёжности
        fallback_messages = _merge_system_into_user(messages)
        fallback_result = _try_model(
            config, fallback_messages, config.model_fallback, use_fallback=True
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

            # Отключаем thinking mode для ZAI (5-7x ускорение)
            extra = {}
            if config.ai_disable_thinking and not use_fallback:
                extra["extra_body"] = {"thinking": {"type": "disabled"}}

            response = client.chat.completions.create(
                model=model,
                temperature=config.ai_temperature,
                max_tokens=config.ai_max_tokens,
                messages=messages,
                **extra,
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
                time.sleep(1)

        except RateLimitError as e:
            last_error = e
            logger.warning(
                "Попытка %d/%d (%s): лимит запросов - %s",
                attempt + 1, config.ai_max_retries, model, e,
            )
            time.sleep(min(2 ** (attempt + 1), 10))

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

        extra = {}
        if config.ai_disable_thinking:
            extra["extra_body"] = {"thinking": {"type": "disabled"}}

        response = client.chat.completions.create(
            model=config.active_model,
            temperature=0,
            max_tokens=1000,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            **extra,
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
        # Определить модель по тому же ключу, что использует _create_client
        active_key = (
            os.environ.get("ZHIPU_API_KEY", "")
            or os.environ.get("ZAI_API_KEY", "")
            or os.environ.get("OPENROUTER_API_KEY", "")
        )
        if active_key.startswith("sk-or-"):
            model = config.model_fallback
        else:
            model = config.active_model
        response = client.chat.completions.create(
            model=model,
            max_tokens=50,
            messages=[{"role": "user", "content": "Ответь: ok"}],
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
    # Безопасное извлечение списковых полей: null → [], строка → [строка]
    raw_conditions = data.get("special_conditions")
    if raw_conditions is None:
        special_conditions = []
    elif isinstance(raw_conditions, str):
        special_conditions = [raw_conditions]
    elif isinstance(raw_conditions, list):
        special_conditions = raw_conditions
    else:
        special_conditions = []

    raw_parties = data.get("parties")
    if raw_parties is None:
        parties = []
    elif isinstance(raw_parties, list):
        parties = [str(p) for p in raw_parties if p is not None]
    else:
        parties = []

    # Безопасное извлечение confidence: null, строка, невалидное → 0.0
    raw_conf = data.get("confidence")
    try:
        confidence = float(raw_conf) if raw_conf is not None else 0.0
        if not (0.0 <= confidence <= 1.0):
            confidence = max(0.0, min(1.0, confidence))
    except (ValueError, TypeError):
        confidence = 0.0

    return ContractMetadata(
        contract_type=data.get("document_type") or data.get("contract_type"),
        counterparty=data.get("counterparty"),
        subject=data.get("subject"),
        date_signed=data.get("date_signed"),
        date_start=data.get("date_start"),
        date_end=data.get("date_end"),
        amount=data.get("amount"),
        special_conditions=special_conditions,
        parties=parties,
        confidence=confidence,
    )
