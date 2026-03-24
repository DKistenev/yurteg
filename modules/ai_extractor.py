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
from dataclasses import asdict
from typing import TYPE_CHECKING, Optional

from openai import OpenAI, APIError, APITimeoutError, RateLimitError
from dateutil import parser as dateutil_parser
from dateutil.parser import ParserError

from config import Config
from modules.models import ContractMetadata
from modules.postprocessor import sanitize_metadata
from providers.openrouter import _merge_system_into_user

if TYPE_CHECKING:
    from providers.base import LLMProvider

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
7. Даты строго YYYY-MM-DD.
8. ШАБЛОНЫ: если в тексте есть пустые поля (_____, __________, «_____»), пробелы вместо ФИО/названий, или пометки вроде «(наименование)», «(ФИО)» — это шаблон документа. В таком случае: is_template=true, counterparty=null, parties=[]. Уверенность (confidence) оценивай по качеству извлечения типа и предмета, НЕ снижай из-за того что это шаблон.
9. ФИО пиши СТРОГО в именительном падеже: "Иванов Иван Иванович", НЕ "Иванова Ивана Ивановича". Если в тексте "в лице Петровой Марии Сергеевны" — пиши "Петрова Мария Сергеевна". Организации — как в тексте.
10. document_type: одинаковые документы ВСЕГДА называй одинаково. Правила именования:
    - Договоры: "Договор {чего}" — "Договор поставки", "Договор аренды", "Договор подряда", "Договор оказания услуг"
    - Соглашения: "Соглашение о {чём}" — "Соглашение о конфиденциальности", "Соглашение о расторжении"
    - ПД (различай!): "Политика обработки ПД", "Положение об обработке ПД", "Согласие на обработку ПД", "Приказ о назначении ответственного за ПД" — это РАЗНЫЕ документы
    - Корпоративные: "Решение единственного участника", "Протокол общего собрания", "Устав"
    - Кадровые/приказы: "Приказ о {чём}" — "Приказ о приёме на работу"
    - Акты: "Акт {чего}" — "Акт выполненных работ", "Акт сверки"
    Предпочитай типы из предложенного списка. Если не подходит ни один — создай краткое название в том же стиле.
11. КОНТРАГЕНТ (counterparty) — это ДРУГАЯ сторона договора, а не наша. Наши стороны (НЕ ставь их в counterparty):
    - Фокина Дарья Владимировна / ИП Фокина / Диджитал Черч / Digital Church
    - Файзулина Анастасия Николаевна / ИП Файзулина
    - ООО «БУП» / БУП
    Если договор между ИП Фокина и ООО «Газпром» → counterparty = "ООО «Газпром»", НЕ "ИП Фокина".
    В parties перечисляй ВСЕ стороны (включая наших).
12. Формат ИП: ВСЕГДА пиши "ИП Фамилия Имя Отчество". НЕ "Индивидуальный предприниматель Фамилия...", НЕ "индивидуальный предприниматель", НЕ "И.П.". Примеры: "ИП Фокина Дарья Владимировна", "ИП Кучма Андрей Владимирович"."""

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
- is_template (bool): true если документ — шаблон/бланк с пустыми полями
- payment_terms (string|null): текстовое описание порядка оплаты («ежемесячно до 5-го числа») или null
- payment_amount (number|null): сумма одного платежа — только числовое значение без валюты или null
- payment_frequency (string|null): периодичность платежей — "monthly", "quarterly", "yearly", "once" или null
- payment_direction (string|null): "income" если деньги поступают от контрагента, "expense" если платим мы, или null

Пример ответа:
{{"document_type": "Договор оказания услуг", "counterparty": "ООО \u00abАльфа\u00bb", "subject": "Оказание юридических консультационных услуг", "date_signed": "2024-03-15", "date_start": "2024-04-01", "date_end": "2025-03-31", "amount": "500 000 руб.", "special_conditions": ["Неустойка 0.1% за каждый день просрочки", "Гарантийный срок 12 месяцев"], "parties": ["ООО \u00abАльфа\u00bb", "[ФИО_1]"], "confidence": 0.92, "is_template": false, "payment_terms": "ежемесячно до 5-го числа", "payment_amount": 50000, "payment_frequency": "monthly", "payment_direction": "income"}}

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


# Таблица замены русских названий месяцев на английские для dateutil
_RU_MONTHS: dict[str, str] = {
    "января": "January", "январь": "January",
    "февраля": "February", "февраль": "February",
    "марта": "March", "март": "March",
    "апреля": "April", "апрель": "April",
    "мая": "May", "май": "May",
    "июня": "June", "июнь": "June",
    "июля": "July", "июль": "July",
    "августа": "August", "август": "August",
    "сентября": "September", "сентябрь": "September",
    "октября": "October", "октябрь": "October",
    "ноября": "November", "ноябрь": "November",
    "декабря": "December", "декабрь": "December",
}


def _translate_ru_months(text: str) -> str:
    """Заменяет русские названия месяцев на английские для dateutil."""
    for ru, en in _RU_MONTHS.items():
        text = re.sub(ru, en, text, flags=re.IGNORECASE)
    return text


def _normalize_date(raw: str | None) -> str | None:
    """Нормализует строку с датой в формат YYYY-MM-DD (ISO 8601).

    Возвращает None если строка непарсируема, год-only, или None на входе.
    Логирует оригинальное значение при неудаче.

    Примеры:
        "31 декабря 2025 г." → "2025-12-31"
        "31.12.2025"         → "2025-12-31"
        "31.12.25"           → "2025-12-31"
        "January 1, 2025"    → "2025-01-01"
        "2025-12-31"         → "2025-12-31"  (fast path)
        "бессрочный"         → None
        "2025"               → None  (year-only: dateutil даёт misleading результат)
        None                 → None
    """
    if not raw:
        return None
    raw = raw.strip()
    if not raw or raw.lower() in ("null", "none", ""):
        return None

    # Fast path: уже ISO 8601
    if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        return raw

    # Защита от year-only строк: dateutil.parse("2025") → datetime(2025, today.month, today.day)
    # что создаёт ложную дату. Любая валидная дата содержит день и месяц.
    if len(raw) <= 4 and raw.isdigit():
        logger.warning("Отклонена year-only строка даты: %r", raw)
        return None

    # Перевод русских месяцев и очистка суффиксов для dateutil
    translated = _translate_ru_months(raw)
    translated = re.sub(r"\s*(г\.?|года)\s*$", "", translated).strip()

    try:
        dt = dateutil_parser.parse(translated, dayfirst=True)
        normalized = dt.strftime("%Y-%m-%d")
        # Санитарная проверка: договоры только в диапазоне 1990–2099
        if not (1990 <= dt.year <= 2099):
            logger.warning("Дата вне допустимого диапазона: %r → %s", raw, normalized)
            return None
        return normalized
    except (ParserError, ValueError, OverflowError):
        logger.warning("Не удалось нормализовать дату: %r", raw)
        return None


def _create_client(config: Config, use_fallback: bool = False) -> OpenAI:
    """
    Создаёт клиент OpenAI-совместимого API.

    Основной провайдер: ZAI (ключ ZHIPU_API_KEY или ZAI_API_KEY)
    Запасной: OpenRouter (ключ OPENROUTER_API_KEY)

    # DEPRECATED: используется только в extract_metadata(). Новые функции должны
    # использовать provider.complete() через систему провайдеров.
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


def extract_metadata(
    anonymized_text: str,
    config: Config,
    provider: "LLMProvider | None" = None,
    fallback_provider: "LLMProvider | None" = None,
) -> ContractMetadata:
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
    if provider is not None:
        # Маршрутизация через провайдер (OllamaProvider, ZAIProvider, etc.)
        try:
            raw_text = _try_provider(provider, messages, config.ai_max_retries)
            json_data = _parse_json_response(raw_text)
            result: ContractMetadata | Exception = _json_to_metadata(json_data)
        except Exception as e:
            result = e
    else:
        # Legacy путь для обратной совместимости (прямые вызовы без провайдера)
        result = _try_model(config, messages, config.active_model, use_fallback=False)

    if isinstance(result, ContractMetadata):
        # Post-processing для локальной модели: очистить мусор и строки None
        if config.active_provider == "ollama":
            sanitized = sanitize_metadata(asdict(result))
            result = _json_to_metadata(sanitized)
        # Проверка: если все ключевые поля пустые — пробуем упрощённый промпт
        if not result.contract_type and not result.counterparty and not result.subject:
            logger.info("Все ключевые поля пустые, пробую упрощённый промпт...")
            fallback_msgs = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": FALLBACK_PROMPT_TEMPLATE.format(text=text[:3000])},
            ]
            if provider is not None:
                try:
                    fb_raw = _try_provider(provider, fallback_msgs, config.ai_max_retries)
                    fb_json = _parse_json_response(fb_raw)
                    fb: ContractMetadata | Exception = _json_to_metadata(fb_json)
                except Exception as fb_e:
                    fb = fb_e
            else:
                fb = _try_model(config, fallback_msgs, config.active_model, use_fallback=False)
            if isinstance(fb, ContractMetadata) and (fb.contract_type or fb.counterparty):
                if config.active_provider == "ollama":
                    sanitized = sanitize_metadata(asdict(fb))
                    fb = _json_to_metadata(sanitized)
                return fb
        return result

    last_error = result

    # Этап 2: Fallback провайдер или fallback модель (OpenRouter)
    if fallback_provider is not None:
        logger.info("Основной провайдер недоступен, пробую fallback_provider: %s", fallback_provider.name)
        try:
            fallback_messages = _merge_system_into_user(messages)
            fb_raw = _try_provider(fallback_provider, fallback_messages, config.ai_max_retries)
            fb_json = _parse_json_response(fb_raw)
            fallback_result: ContractMetadata | Exception = _json_to_metadata(fb_json)
        except Exception as e:
            fallback_result = e
        if isinstance(fallback_result, ContractMetadata):
            return fallback_result
        last_error = fallback_result
    elif config.model_fallback and os.environ.get("OPENROUTER_API_KEY"):
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


def _try_provider(
    provider: "LLMProvider",
    messages: list[dict],
    max_retries: int,
) -> str:
    """Вызывает provider.complete() с retry-логикой. Возвращает сырой текст.

    Args:
        provider: реализация LLMProvider (OllamaProvider, ZAIProvider, etc.)
        messages: список сообщений в формате OpenAI
        max_retries: максимальное число попыток

    Returns:
        Сырой текстовый ответ от провайдера.

    Raises:
        RuntimeError: если все попытки исчерпаны.
    """
    last_error: Exception = RuntimeError("Нет попыток")

    for attempt in range(max_retries):
        try:
            logger.info(
                "AI-запрос через провайдер %s: попытка %d/%d",
                provider.name, attempt + 1, max_retries,
            )
            raw_text = provider.complete(messages)
            if not raw_text:
                raise ValueError("Пустой ответ от провайдера")
            logger.debug("Ответ провайдера %s (первые 500 символов): %s", provider.name, raw_text[:500])
            return raw_text

        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            logger.warning(
                "Попытка %d/%d (провайдер %s): невалидный ответ — %s",
                attempt + 1, max_retries, provider.name, e,
            )
            if attempt < max_retries - 1:
                time.sleep(1)

        except Exception as e:
            last_error = e
            logger.warning(
                "Попытка %d/%d (провайдер %s): ошибка — %s",
                attempt + 1, max_retries, provider.name, e,
            )
            if attempt < max_retries - 1:
                time.sleep(1)

    logger.warning("Все попытки исчерпаны для провайдера %s", provider.name)
    raise RuntimeError(
        f"Провайдер {provider.name} не ответил после {max_retries} попыток. "
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
    provider: "LLMProvider | None" = None,
) -> dict:
    """
    AI-валидация L5 (опциональная).

    Отправляет первые 500 символов текста + метаданные на верификацию.
    Использует provider.complete() — если provider не передан, создаётся через get_provider(config).

    Возвращает: {"correct": bool, "corrections": [...], "reasoning": str}
    При ошибке: {"correct": True, "corrections": [], "reasoning": "verification_failed"}
    """
    try:
        if provider is None:
            from providers import get_provider
            provider = get_provider(config)

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

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        raw_text = provider.complete(messages, temperature=0, max_tokens=1000)
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


def verify_api_key(config: Config, provider: "LLMProvider | None" = None) -> bool:
    """
    Проверяет валидность API-ключа через provider.verify_key().
    Возвращает True если ключ рабочий, False если нет.

    Если provider не передан, создаётся через get_provider(config).
    """
    try:
        if provider is None:
            from providers import get_provider
            provider = get_provider(config)
        return provider.verify_key()
    except RuntimeError:
        # Ключ не найден
        return False
    except Exception as e:
        logger.warning("Проверка API-ключа не удалась: %s", e)
        return False


def _safe_float(val) -> Optional[float]:
    """Безопасное приведение к float: None/пустое → None, невалидное → None."""
    try:
        return float(val) if val is not None else None
    except (ValueError, TypeError):
        return None


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
        date_signed=_normalize_date(data.get("date_signed")),
        date_start=_normalize_date(data.get("date_start")),
        date_end=_normalize_date(data.get("date_end")),
        amount=data.get("amount"),
        special_conditions=special_conditions,
        parties=parties,
        confidence=confidence,
        is_template=bool(data.get("is_template", False)),
        payment_terms=data.get("payment_terms"),
        payment_amount=_safe_float(data.get("payment_amount")),
        payment_frequency=data.get("payment_frequency"),
        payment_direction=data.get("payment_direction"),
    )
