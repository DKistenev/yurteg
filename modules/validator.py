"""Модуль валидации метаданных документов.

4 уровня проверки:
- L1: структурная (обязательные поля, формат дат)
- L2: логическая (дата в будущем, start > end, аномальные суммы)
- L3: уверенность AI (пороги, детекция галлюцинаций)
- L4: перекрёстная по всему архиву (дубликаты, аномалии)
"""
import logging
import re
from collections import Counter
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Optional

from config import Config
from modules.models import ContractMetadata, ProcessingResult, ValidationResult

logger = logging.getLogger(__name__)


def validate_metadata(metadata: ContractMetadata, config: Config) -> ValidationResult:
    """
    Валидация L1 + L2 + L3 одного набора метаданных.
    Возвращает ValidationResult со статусом и списком предупреждений.
    """
    warnings: list[str] = []

    # L1: Структурная валидация
    warnings.extend(_validate_l1(metadata))

    # L2: Логическая валидация
    warnings.extend(_validate_l2(metadata, config))

    # L3: Уверенность AI
    l3_status, l3_warnings = _validate_l3(metadata, config)
    warnings.extend(l3_warnings)

    # Итоговый статус: L3 определяет базу, L1/L2 могут понизить
    if any(w.startswith("L1:") for w in warnings):
        status = "error"
    elif l3_status == "unreliable":
        status = "unreliable"
    elif l3_status == "warning" or any(w.startswith("L2:") for w in warnings):
        status = "warning"
    else:
        status = "ok"

    # Итоговый score: начинаем с confidence AI, штрафуем за предупреждения
    score = metadata.confidence
    score -= len([w for w in warnings if w.startswith("L1:")]) * 0.15
    score -= len([w for w in warnings if w.startswith("L2:")]) * 0.1
    score -= len([w for w in warnings if w.startswith("L3:")]) * 0.05
    score = max(0.0, min(1.0, score))

    result = ValidationResult(status=status, warnings=warnings, score=score)

    if warnings:
        logger.info(
            "Валидация: статус=%s, score=%.2f, предупреждений=%d",
            status, score, len(warnings),
        )
    return result


def validate_batch(
    results: list[ProcessingResult], config: Config,
) -> list[ProcessingResult]:
    """
    Валидация L4 — перекрёстная по всему архиву.
    Добавляет предупреждения в validation каждого ProcessingResult.
    """
    successful = [r for r in results if r.status == "done" and r.metadata and r.validation]

    if not successful:
        return results

    # Детекция дубликатов по (контрагент, дата, сумма)
    seen: dict[tuple, str] = {}
    for r in successful:
        m = r.metadata
        key = (
            (m.counterparty or "").lower().strip(),
            m.date_signed or "",
            m.amount or "",
        )
        if key != ("", "", "") and key in seen:
            msg = f"L4: возможный дубликат с файлом «{seen[key]}»"
            r.validation.warnings.append(msg)
            if r.validation.status == "ok":
                r.validation.status = "warning"
        seen[key] = r.file_info.filename

    # Детекция одинаковых дат (copy-paste шаблонов)
    date_ranges: dict[tuple, list[str]] = {}
    for r in successful:
        m = r.metadata
        dr = (m.date_start or "", m.date_end or "")
        if dr != ("", ""):
            date_ranges.setdefault(dr, []).append(r.file_info.filename)
    for dr, filenames in date_ranges.items():
        if len(filenames) > 1:
            for r in successful:
                m = r.metadata
                if (m.date_start or "", m.date_end or "") == dr:
                    others = [f for f in filenames if f != r.file_info.filename]
                    if others:
                        r.validation.warnings.append(
                            f"L4: совпадающие даты с файлами: {', '.join(others[:3])}"
                        )
                        if r.validation.status == "ok":
                            r.validation.status = "warning"

    # Аномалия: >50% одного типа (только при >5 файлов)
    types = [r.metadata.contract_type for r in successful if r.metadata.contract_type]
    if types and len(types) > 5:
        most_common_type, count = Counter(types).most_common(1)[0]
        if count / len(types) > 0.5:
            for r in successful:
                r.validation.warnings.append(
                    f"L4: >{count}/{len(types)} файлов определены как "
                    f"«{most_common_type}» — проверьте классификацию"
                )

    # Аномалия: >30% с предупреждениями (только при >5 файлов)
    if len(successful) > 5:
        warned = sum(1 for r in successful if r.validation.status != "ok")
        if warned / len(successful) > 0.3:
            for r in successful:
                r.validation.warnings.append(
                    f"L4: {warned}/{len(successful)} файлов имеют "
                    f"предупреждения — возможны системные проблемы"
                )

    return results


# --- Внутренние функции ---


def _validate_l1(metadata: ContractMetadata) -> list[str]:
    """L1: Структурная валидация — обязательные поля и формат."""
    warnings: list[str] = []

    # Обязательные поля (включая пустые строки)
    if not metadata.contract_type or not metadata.contract_type.strip():
        warnings.append("L1: отсутствует тип документа (contract_type)")
    if not metadata.counterparty or not metadata.counterparty.strip():
        warnings.append("L1: отсутствует контрагент (counterparty)")
    if not metadata.subject or not metadata.subject.strip():
        warnings.append("L1: отсутствует предмет документа (subject)")

    # Формат дат (ISO: YYYY-MM-DD)
    for field_name in ("date_signed", "date_start", "date_end"):
        value = getattr(metadata, field_name)
        if value is not None:
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                warnings.append(
                    f"L1: некорректный формат даты {field_name}={value}"
                )

    # Confidence в диапазоне
    if not (0 <= metadata.confidence <= 1):
        warnings.append(f"L1: confidence вне диапазона [0,1]: {metadata.confidence}")

    return warnings


def _validate_l2(metadata: ContractMetadata, config: Config) -> list[str]:
    """L2: Логическая валидация — проверка смысла данных."""
    warnings: list[str] = []
    today = datetime.now().date()

    # Дата подписания
    if metadata.date_signed:
        try:
            signed = datetime.strptime(metadata.date_signed, "%Y-%m-%d").date()
            if signed > today + timedelta(days=30):
                warnings.append(
                    f"L2: дата подписания в будущем ({metadata.date_signed})"
                )
            if signed.year < 2000:
                warnings.append(
                    f"L2: дата подписания подозрительно старая ({metadata.date_signed})"
                )
        except ValueError:
            pass  # Уже поймано в L1

    # start > end и срок > 50 лет
    if metadata.date_start and metadata.date_end:
        try:
            start = datetime.strptime(metadata.date_start, "%Y-%m-%d").date()
            end = datetime.strptime(metadata.date_end, "%Y-%m-%d").date()
            if start > end:
                warnings.append(
                    f"L2: дата начала ({metadata.date_start}) позже "
                    f"даты окончания ({metadata.date_end})"
                )
            elif (end - start).days > 50 * 365:
                warnings.append(
                    f"L2: подозрительно долгий срок документа "
                    f"({(end - start).days // 365} лет)"
                )
        except ValueError:
            pass

    # Тип документа — нечёткое сравнение
    if metadata.contract_type:
        _, score = _fuzzy_match(metadata.contract_type, config.document_types_hints)
        if score < 0.6:
            warnings.append(
                f"L2: нестандартный тип документа: «{metadata.contract_type}»"
            )

    # Сумма
    if metadata.amount:
        parsed_amount = _parse_amount(metadata.amount)
        if parsed_amount is None:
            warnings.append(f"L2: сумма не содержит чисел: «{metadata.amount}»")
        else:
            if parsed_amount > 10_000_000_000:
                warnings.append(f"L2: аномально большая сумма: {metadata.amount}")
            if (
                parsed_amount < 1000
                and metadata.contract_type
                and "трудовой" not in metadata.contract_type.lower()
            ):
                warnings.append(f"L2: аномально малая сумма: {metadata.amount}")

    # Предмет договора — длина
    if metadata.subject:
        if len(metadata.subject) < 5:
            warnings.append(
                f"L2: слишком короткий предмет документа ({len(metadata.subject)} символов)"
            )
        if len(metadata.subject) > 500:
            warnings.append(
                f"L2: слишком длинный предмет документа ({len(metadata.subject)} символов)"
            )

    # ИНН в сторонах — проверка контрольной суммы
    for party in (metadata.parties or []):
        if not party or not isinstance(party, str):
            continue
        inn_matches = re.findall(r'ИНН\s*(\d{10,12})', party, re.IGNORECASE)
        for inn in inn_matches:
            if not _validate_inn(inn):
                warnings.append(f"L2: невалидный ИНН {inn} (ошибка контрольной суммы)")

    # Стороны совпадают — подозрительно
    valid_parties = [p for p in (metadata.parties or []) if p and isinstance(p, str)]
    if len(valid_parties) >= 2:
        normalized = [re.sub(r'\s+', ' ', p.lower().strip()) for p in valid_parties]
        if len(set(normalized)) < len(normalized):
            warnings.append("L2: стороны документа совпадают")

    return warnings


def _validate_l3(
    metadata: ContractMetadata, config: Config,
) -> tuple[str, list[str]]:
    """L3: Валидация уверенности AI. Возвращает (статус, предупреждения)."""
    warnings: list[str] = []

    # Порог уверенности
    if metadata.confidence < config.confidence_low:
        status = "unreliable"
        warnings.append(f"L3: низкая уверенность AI ({metadata.confidence:.2f})")
    elif metadata.confidence < config.confidence_high:
        status = "warning"
        warnings.append(
            f"L3: средняя уверенность AI ({metadata.confidence:.2f}), требует проверки"
        )
    else:
        status = "ok"

    # Детекция галлюцинаций — подозрительные контрагенты
    hallucination_names = {
        "ооо ромашка", "ип иванов", "заказчик", "исполнитель",
        "покупатель", "продавец", "арендатор", "арендодатель",
    }
    if metadata.counterparty and metadata.counterparty.lower().strip() in hallucination_names:
        warnings.append(
            f"L3: подозрение на галлюцинацию — контрагент «{metadata.counterparty}»"
        )
        status = "warning"

    # Все три даты одинаковые — подозрительно
    dates = [metadata.date_signed, metadata.date_start, metadata.date_end]
    dates = [d for d in dates if d]
    if len(dates) >= 3 and len(set(dates)) == 1:
        warnings.append("L3: все три даты совпадают — возможная галлюцинация")
        status = "warning"

    return status, warnings


def _fuzzy_match(text: str, candidates: list[str]) -> tuple[str, float]:
    """Нечёткое сравнение строки со списком кандидатов. (best_match, score 0-1)."""
    best = ("", 0.0)
    text_lower = text.lower().strip()
    for candidate in candidates:
        score = SequenceMatcher(None, text_lower, candidate.lower()).ratio()
        if score > best[1]:
            best = (candidate, score)
    return best


def _parse_amount(amount_str: str) -> Optional[float]:
    """Парсит сумму из строки, понимая международные форматы.

    Поддерживает:
    - Русский/пробел:   1 500 000,50 руб.  → 1500000.50
    - Английский:       1,500,000.00 USD   → 1500000.00
    - Европейский:      1.500.000,50 EUR   → 1500000.50
    - Простые:          50000 руб.          → 50000.0
    """
    # Убираем всё кроме цифр, точек, запятых, пробелов
    cleaned = re.sub(r'[^\d.,\s]', '', amount_str).strip()
    if not cleaned:
        return None

    # Убираем пробелы (разделители тысяч в русском формате)
    cleaned = cleaned.replace(' ', '')

    if not re.search(r'\d', cleaned):
        return None

    # Определяем формат по позиции последнего разделителя
    last_dot = cleaned.rfind('.')
    last_comma = cleaned.rfind(',')

    if last_dot == -1 and last_comma == -1:
        # Только цифры: "1500000"
        return float(cleaned)
    elif last_dot != -1 and last_comma == -1:
        # Только точки: может быть "1.500.000" (европейский тысячный) или "1500.50" (десятичная)
        dot_count = cleaned.count('.')
        if dot_count > 1:
            # "1.500.000" — точки как разделители тысяч
            return float(cleaned.replace('.', ''))
        else:
            # "1500.50" — точка как десятичный разделитель
            return float(cleaned)
    elif last_comma != -1 and last_dot == -1:
        # Только запятые: может быть "1,500,000" (англ. тысячный) или "1500,50" (десятичная)
        comma_count = cleaned.count(',')
        if comma_count > 1:
            # "1,500,000" — запятые как разделители тысяч
            return float(cleaned.replace(',', ''))
        else:
            # Одна запятая: проверяем что после неё
            after_comma = cleaned[last_comma + 1:]
            if len(after_comma) == 3 and last_comma > 0:
                # "1,500" — запятая как разделитель тысяч
                return float(cleaned.replace(',', ''))
            else:
                # "1500,50" — запятая как десятичный разделитель
                return float(cleaned.replace(',', '.'))
    else:
        # Есть и точки, и запятые
        if last_dot > last_comma:
            # "1,500,000.50" — запятые тысячные, точка десятичная
            return float(cleaned.replace(',', ''))
        else:
            # "1.500.000,50" — точки тысячные, запятая десятичная
            return float(cleaned.replace('.', '').replace(',', '.'))


def _validate_inn(inn: str) -> bool:
    """
    Проверяет ИНН по контрольной сумме.

    ИНН юрлица (10 цифр): проверяется 10-я цифра.
    ИНН физлица (12 цифр): проверяются 11-я и 12-я цифры.

    Алгоритм: каждая цифра умножается на свой коэффициент,
    сумма делится на 11, остаток — контрольная цифра.
    """
    if not inn.isdigit():
        return False

    digits = [int(d) for d in inn]

    if len(inn) == 10:
        # ИНН юрлица: проверяем 10-ю цифру
        weights = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        checksum = sum(d * w for d, w in zip(digits, weights)) % 11 % 10
        return checksum == digits[9]

    elif len(inn) == 12:
        # ИНН физлица: проверяем 11-ю и 12-ю цифры
        weights_11 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        weights_12 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        check_11 = sum(d * w for d, w in zip(digits, weights_11)) % 11 % 10
        check_12 = sum(d * w for d, w in zip(digits, weights_12)) % 11 % 10
        return check_11 == digits[10] and check_12 == digits[11]

    return False
