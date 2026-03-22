"""Исправление ошибочных записей датасета через повторный AI-запрос.

Читает labeled_data_errors.jsonl (с полем error_type),
для каждой записи формирует целенаправленный промпт
и сохраняет исправленные версии.

Запуск:
    cd /path/to/yurteg
    python dataset/fix_errors.py

Результат:
    dataset/labeled_data_fixed.jsonl  — исправленные записи (добавить в обучение)
"""
import re
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

try:
    import pymorphy3
    _morph = pymorphy3.MorphAnalyzer()
    HAS_MORPH = True
except ImportError:
    HAS_MORPH = False

from openai import OpenAI
from config import Config
from modules.ai_extractor import (
    SYSTEM_PROMPT, USER_PROMPT_TEMPLATE,
    _parse_json_response, _json_to_metadata, _create_client,
)

DATASET_DIR = Path(__file__).parent
ERRORS_FILE = DATASET_DIR / "labeled_data_errors.jsonl"
FIXED_FILE  = DATASET_DIR / "labeled_data_fixed.jsonl"
REVIEWED_FILE = DATASET_DIR / "labeled_data_reviewed.jsonl"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Промпты-корректоры по типу ошибки ───────────────────────────────────────

CORRECTION_PROMPTS = {
    "wrong_type": """Предыдущая попытка извлечения метаданных дала НЕВЕРНЫЙ тип документа.

Предыдущий результат (НЕВЕРНЫЙ):
{prev_output}

Перечитай текст внимательно и определи ТОЧНЫЙ тип документа.
Правила:
- Договоры: "Договор поставки", "Договор аренды", "Договор подряда", "Договор оказания услуг"
- ПД: различай "Политика обработки ПД", "Положение об обработке ПД", "Согласие на обработку ПД"
- Корпоративные: "Решение единственного участника", "Протокол общего собрания", "Устав"
- Кадровые: "Приказ о приёме на работу", "Приказ о назначении ответственного"

Верни ПОЛНЫЙ JSON со всеми полями (не только тип), исправив ошибки.

Текст документа:
{text}""",

    "wrong_party": """Предыдущая попытка извлечения метаданных дала НЕВЕРНОГО контрагента или ФИО.

Предыдущий результат (НЕВЕРНЫЙ):
{prev_output}

ГЛАВНОЕ ПРАВИЛО: counterparty — это ДРУГАЯ сторона, не наша.
Наши стороны (НЕ ставь в counterparty):
- Фокина Дарья Владимировна / ИП Фокина / Диджитал Черч / Digital Church
- Файзулина Анастасия Николаевна / ИП Файзулина
- ООО «БУП» / БУП

Если договор между ИП Фокина и ООО «Газпром» → counterparty = "ООО «Газпром»".

Формат ИП: ВСЕГДА "ИП Фамилия Имя Отчество" (не "Индивидуальный предприниматель").
ФИО СТРОГО в именительном падеже.
Если вместо данных стоят пробелы/прочерки — это шаблон, counterparty=null.
В parties перечисляй ВСЕ стороны (включая наших).

Верни ПОЛНЫЙ исправленный JSON.

Текст документа:
{text}""",

    "wrong_data": """Предыдущая попытка извлечения метаданных дала НЕВЕРНЫЕ даты, сумму или предмет.

Предыдущий результат (НЕВЕРНЫЙ):
{prev_output}

Типичные ошибки:
- Даты выдуманы или взяты из другого места документа
- Сумма перепутана (из другого пункта, без валюты)
- Предмет описан неточно

Даты строго YYYY-MM-DD. Сумма с валютой: "500 000 руб."
Если данных нет в тексте — ставь null, не выдумывай.

Верни ПОЛНЫЙ исправленный JSON.

Текст документа:
{text}""",

    "template": """Этот документ — ШАБЛОН (бланк), а не заполненный документ.
В тексте есть пустые поля: _____, пробелы вместо данных, пометки вроде «(ФИО)», «(наименование)».

Правила для шаблонов:
- is_template: true
- counterparty: null
- parties: []
- date_signed, date_start, date_end: null
- amount: null
- confidence: оценивай по качеству определения типа и предмета (может быть высокой!)
- document_type: определи тип шаблона (например "Договор оказания услуг")

Верни JSON.

Текст документа:
{text}""",

    "other": """Предыдущая попытка извлечения метаданных содержала ошибки.

Предыдущий результат (с ошибками):
{prev_output}

Перечитай текст внимательно и извлеки метаданные заново.
ФИО — в именительном падеже. Отсутствующие данные — null.
Если это шаблон (_____, пробелы вместо данных) — counterparty=null, confidence ≤ 0.3.

Верни ПОЛНЫЙ исправленный JSON.

Текст документа:
{text}""",
}

# ─── Группы путаемых типов (для wrong_type) ──────────────────────────────────

CONFUSABLE_GROUPS = [
    {"Договор подряда", "Договор строительного подряда", "Договор бытового подряда",
     "Договор на проведение НИОКР", "Договор на создание научно-технической продукции"},
    {"Договор аренды", "Договор субаренды", "Договор лизинга",
     "Договор финансовой аренды", "Договор финансовой аренды (лизинга)",
     "Договор сублизинга", "Договор найма жилого помещения", "Договор найма",
     "Договор безвозмездного пользования"},
    {"Договор оказания услуг", "Договор возмездного оказания услуг",
     "Договор на проведение аудиторских проверок", "Договор оказания охранных услуг",
     "Агентский договор", "Субагентский договор"},
    {"Договор хранения", "Договор складского хранения"},
    {"Договор страхования", "Договор страхования имущества",
     "Договор ипотечного страхования"},
    {"Договор поручения", "Договор комиссии", "Агентский договор"},
    {"Договор цессии", "Соглашение об уступке права требования",
     "Договор перевода долга", "Договор передачи прав и обязанностей"},
    {"Договор коммерческой концессии", "Договор субконцессии", "Лицензионный договор"},
    {"Договор доверительного управления", "Договор доверительного управления имуществом",
     "Договор коммерческого управления"},
    {"Соглашение о конфиденциальности", "NDA / Соглашение о конфиденциальности",
     "Соглашение о неразглашении конфиденциальной информации"},
    {"Договор о совместной деятельности", "Договор простого товарищества",
     "Договор о сотрудничестве", "Соглашение о сотрудничестве"},
    {"Протокол общего собрания", "Решение единственного участника",
     "Корпоративное решение", "Корпоративный договор"},
    {"Договор перевозки", "Договор перевозки груза",
     "Договор транспортной экспедиции", "Договор транспортно-экспедиционных услуг"},
]

def _build_confusable_map():
    """Строит словарь: тип → множество путаемых типов (включая себя)."""
    m = {}
    for group in CONFUSABLE_GROUPS:
        for t in group:
            if t not in m:
                m[t] = set()
            m[t].update(group)
    return m

_CONFUSABLE_MAP = _build_confusable_map()


# ─── Загрузка одобренных примеров ────────────────────────────────────────────

def load_approved_examples(path: Path = REVIEWED_FILE) -> dict[str, list[dict]]:
    """Загружает одобренные записи, группирует по document_type."""
    by_type: dict[str, list[dict]] = {}
    if not path.exists():
        return by_type
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            doc_type = rec.get("output", {}).get("document_type", "")
            if not doc_type:
                continue
            by_type.setdefault(doc_type, []).append(rec)
    total = sum(len(v) for v in by_type.values())
    logger.info("Загружено одобренных примеров: %d (%d типов)", total, len(by_type))
    return by_type


def find_examples(record: dict, approved: dict[str, list[dict]], n: int = 3) -> list[dict]:
    """Подбирает n релевантных одобренных примеров для ошибочной записи."""
    import random
    error_type = record.get("error_type", "other")
    doc_type = record.get("output", {}).get("document_type", "")

    if error_type == "wrong_type":
        # Для wrong_type: берём примеры из группы путаемых типов
        confusable = _CONFUSABLE_MAP.get(doc_type, {doc_type})
        candidates = []
        for t in confusable:
            candidates.extend(approved.get(t, []))
        # Берём разные типы для наглядности
        by_t = {}
        for c in candidates:
            ct = c["output"]["document_type"]
            by_t.setdefault(ct, []).append(c)
        result = []
        for t, recs in by_t.items():
            result.append(random.choice(recs))
            if len(result) >= n:
                break
        return result[:n]
    else:
        # Для wrong_party/wrong_data/other: берём примеры того же типа
        candidates = approved.get(doc_type, [])
        if not candidates:
            return []
        return random.sample(candidates, min(n, len(candidates)))


def format_examples(examples: list[dict]) -> str:
    """Форматирует примеры для вставки в промпт."""
    if not examples:
        return ""
    parts = ["\n─── ПРИМЕРЫ ПРАВИЛЬНОЙ РАЗМЕТКИ (одобрены человеком) ───"]
    for i, ex in enumerate(examples, 1):
        out = ex.get("output", {})
        parts.append(f"\nПример {i}:")
        parts.append(f"  Текст (начало): {ex.get('text_preview', '')[:200]}...")
        parts.append(f"  Результат: {json.dumps(out, ensure_ascii=False)}")
    parts.append("─── КОНЕЦ ПРИМЕРОВ ───\n")
    return "\n".join(parts)


# ─── Нормализация ИП + ФИО ────────────────────────────────────────────────────

_ORG_PREFIXES = ("ООО", "ОАО", "ЗАО", "АО", "ПАО", "НКО", "ИП", "ФГУП", "МУП", "ГУП")

_IP_PATTERNS = re.compile(
    r'^(?:Индивидуальный[\u0306]?\s+[Пп]редприниматель|индивидуальный[\u0306]?\s+предприниматель|И\.?П\.?)\s+',
    re.IGNORECASE,
)

def _normalize_ip(name):
    if not name:
        return name
    m = _IP_PATTERNS.match(name)
    if m:
        return f"ИП {name[m.end():].strip()}"
    return name

def _looks_like_person(text):
    if not text or len(text) < 3:
        return False
    upper = text.split()[0].upper() if text.split() else ""
    if upper in _ORG_PREFIXES or "«" in text or "\"" in text:
        return False
    parts = text.split()
    return 2 <= len(parts) <= 4 and all(p[0].isupper() and p[0].isalpha() for p in parts)

def _normalize_fio(name):
    if not HAS_MORPH:
        return name
    parts = name.split()
    result = []
    for part in parts:
        parsed = _morph.parse(part)
        best = None
        for p in parsed:
            if {"Name", "Surn", "Patr"} & set(str(p.tag).split(",")):
                best = p
                break
        if best:
            nomn = best.inflect({"nomn"})
            if nomn:
                word = nomn.word
                if part[0].isupper():
                    word = word[0].upper() + word[1:]
                result.append(word)
            else:
                result.append(part)
        else:
            result.append(part)
    return " ".join(result)


# ─── Обработка одной ошибки ───────────────────────────────────────────────────

def fix_one(record: dict, config: Config, approved: dict[str, list[dict]] | None = None) -> dict | None:
    """Отправляет ошибочную запись на повторное извлечение с подсказкой и примерами."""
    error_type = record.get("error_type", "other")
    prompt_template = CORRECTION_PROMPTS.get(error_type, CORRECTION_PROMPTS["other"])

    prev_output = json.dumps(record.get("output", {}), ensure_ascii=False, indent=2)
    text = record.get("input_text", "")[:30_000]

    user_prompt = prompt_template.format(prev_output=prev_output, text=text)

    # Добавляем few-shot примеры из одобренных записей
    if approved:
        examples = find_examples(record, approved, n=3)
        examples_text = format_examples(examples)
        if examples_text:
            user_prompt = examples_text + "\n" + user_prompt

    try:
        client = _create_client(config)
        extra = {}
        if config.ai_disable_thinking:
            extra["extra_body"] = {"thinking": {"type": "disabled"}}

        response = client.chat.completions.create(
            model=config.active_model,
            temperature=0,
            max_tokens=2000,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            **extra,
        )

        raw = response.choices[0].message.content
        if not raw:
            return None

        json_data = _parse_json_response(raw)
        metadata = _json_to_metadata(json_data)

        # Нормализация: ИП формат + ФИО в именительный падеж
        counterparty = _normalize_ip(metadata.counterparty)
        if counterparty and _looks_like_person(counterparty):
            counterparty = _normalize_fio(counterparty)
        parties = [
            _normalize_ip(_normalize_fio(p) if _looks_like_person(p) else _normalize_ip(p))
            for p in metadata.parties
        ]

        fixed = {
            **record,
            "output": {
                "document_type": metadata.contract_type,
                "counterparty": counterparty,
                "subject": metadata.subject,
                "date_signed": metadata.date_signed,
                "date_start": metadata.date_start,
                "date_end": metadata.date_end,
                "amount": metadata.amount,
                "special_conditions": metadata.special_conditions,
                "parties": parties,
                "confidence": metadata.confidence,
                "is_template": metadata.is_template,
            },
            "review_status": "fixed",
            "error_type": error_type,
            "fixed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        }
        return fixed

    except Exception as e:
        logger.error("Ошибка исправления %s: %s", record.get("source_file", "?"), e)
        return None


# ─── Главная функция ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Исправление ошибочных записей датасета")
    parser.add_argument("--input", type=Path, default=ERRORS_FILE,
                        help=f"Файл ошибок (по умолчанию: {ERRORS_FILE.name})")
    parser.add_argument("--output", type=Path, default=FIXED_FILE,
                        help=f"Куда сохранить (по умолчанию: {FIXED_FILE.name})")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--examples", type=Path, default=REVIEWED_FILE,
                        help=f"Файл одобренных записей для few-shot (по умолчанию: {REVIEWED_FILE.name})")
    parser.add_argument("--no-examples", action="store_true",
                        help="Отключить few-shot примеры")
    args = parser.parse_args()

    if not args.input.exists():
        logger.error("Файл не найден: %s", args.input)
        sys.exit(1)

    # Загрузить ошибки
    errors = []
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                errors.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    if not errors:
        logger.error("Нет записей в %s", args.input)
        sys.exit(1)

    # Статистика по типам ошибок
    by_type = {}
    for e in errors:
        t = e.get("error_type", "other")
        by_type[t] = by_type.get(t, 0) + 1
    logger.info("Ошибок: %d", len(errors))
    for t, c in sorted(by_type.items()):
        logger.info("  %s: %d", t, c)

    config = Config()

    # Загрузить одобренные примеры для few-shot
    approved = None
    if not args.no_examples:
        approved = load_approved_examples(args.examples)
        if not approved:
            logger.warning("Нет одобренных примеров — few-shot отключён")

    stats = {"fixed": 0, "failed": 0}

    with open(args.output, "w", encoding="utf-8") as out_f:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(fix_one, rec, config, approved): rec
                for rec in errors
            }
            for future in tqdm(as_completed(futures), total=len(futures), desc="Исправление"):
                rec = futures[future]
                try:
                    fixed = future.result()
                except Exception as e:
                    logger.error("Ошибка: %s", e)
                    stats["failed"] += 1
                    continue

                if fixed is None:
                    stats["failed"] += 1
                    continue

                out_f.write(json.dumps(fixed, ensure_ascii=False) + "\n")
                out_f.flush()
                stats["fixed"] += 1

    logger.info("─" * 40)
    logger.info("Исправлено:  %d", stats["fixed"])
    logger.info("Не удалось:  %d", stats["failed"])
    logger.info("Результат:   %s", args.output)
    logger.info("─" * 40)

    if stats["fixed"] > 0:
        logger.info("")
        logger.info("Исправленные записи нужно проверить в ревьюере.")
        logger.info("Затем одобренные добавить к обучающему датасету.")


if __name__ == "__main__":
    main()
