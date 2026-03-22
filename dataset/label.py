"""Скрипт разметки датасета юридических документов для файнтюнинга.

Обходит указанные папки → извлекает текст (extractor.py) →
отправляет в GLM-4.7 → сохраняет результаты в dataset/labeled_data.jsonl.

Без анонимизации — для файнтюнинга нужны реальные имена и реквизиты
(данные не покидают мак при локальном обучении).

Запуск:
    cd /path/to/yurteg
    python dataset/label.py /path/to/DC /path/to/BUP

Флаги:
    --output PATH     куда писать JSONL (по умолчанию: dataset/labeled_data.jsonl)
    --workers N       параллельных AI-запросов (по умолчанию: 5)
    --resume          дописать в существующий файл, пропуская уже размеченные
"""
import re
import sys
import json
import hashlib
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

# Добавляем корень yurteg/ в sys.path для импорта модулей
sys.path.insert(0, str(Path(__file__).parent.parent))

# Загружаем .env с API-ключами из корня проекта
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):  # заглушка если tqdm не стоит
        return iterable

import pymorphy3

from modules.extractor import extract_text
from modules.models import FileInfo
from modules.ai_extractor import extract_metadata
from config import Config

_morph = pymorphy3.MorphAnalyzer()

# ─── Настройки ───────────────────────────────────────────────────────────────

DATASET_DIR = Path(__file__).parent
OUTPUT_FILE = DATASET_DIR / "labeled_data.jsonl"

# Примерные токены на документ: вход ~8K + выход ~300
APPROX_TOKENS_PER_DOC = 8_300

# Расширенный список типов для БУП/корпоративных документов
EXTRA_DOCUMENT_TYPES = [
    "Приказ",
    "Положение",
    "Политика обработки персональных данных",
    "Корпоративное решение",
    "Договор вестинга",
    "Устав",
    "Протокол общего собрания",
    "Решение единственного участника",
    "Корпоративный договор",
    "Инструкция",
    "Регламент",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Нормализация ФИО ─────────────────────────────────────────────────────────

_ORG_PREFIXES = ("ООО", "ОАО", "ЗАО", "АО", "ПАО", "НКО", "ИП", "ФГУП", "МУП", "ГУП")


def _looks_like_person(text: str) -> bool:
    """Проверяет, похоже ли на ФИО (а не на организацию)."""
    if not text or len(text) < 3:
        return False
    # Организации: ООО «...», ИП ..., и т.п.
    upper = text.upper().split()[0] if text.split() else ""
    if upper in _ORG_PREFIXES or "«" in text or "\"" in text:
        return False
    # ФИО: 2-3 слова, все начинаются с заглавной, кириллица
    parts = text.split()
    if not (2 <= len(parts) <= 4):
        return False
    return all(p[0].isupper() and p[0].isalpha() for p in parts)


def _normalize_fio(name: str) -> str:
    """Приводит ФИО к именительному падежу через pymorphy2."""
    parts = name.split()
    result = []
    for part in parts:
        parsed = _morph.parse(part)
        # Ищем разбор как имя/фамилия/отчество
        best = None
        for p in parsed:
            if {"Name", "Surn", "Patr"} & set(str(p.tag).split(",")):
                best = p
                break
        if best:
            nomn = best.inflect({"nomn"})
            if nomn:
                word = nomn.word
                # Сохраняем оригинальную капитализацию
                if part[0].isupper():
                    word = word[0].upper() + word[1:]
                result.append(word)
            else:
                result.append(part)
        else:
            result.append(part)
    return " ".join(result)


_IP_PATTERNS = re.compile(
    r'^(?:Индивидуальный[\u0306]?\s+[Пп]редприниматель|индивидуальный[\u0306]?\s+предприниматель|И\.?П\.?)\s+',
    re.IGNORECASE,
)

def _normalize_ip(name: str) -> str:
    """Приводит формат ИП к единому: 'ИП Фамилия Имя Отчество'."""
    if not name:
        return name
    m = _IP_PATTERNS.match(name)
    if m:
        fio_part = name[m.end():].strip()
        return f"ИП {fio_part}"
    return name


# ─── Вспомогательные функции ──────────────────────────────────────────────────

def _text_hash(text: str) -> str:
    """SHA-256 от первых 5000 символов — ID для дедупликации содержимого."""
    return hashlib.sha256(text[:5000].encode("utf-8", errors="replace")).hexdigest()[:16]


def _file_hash(path: Path) -> str:
    """Быстрый хеш по имени + размеру файла (для FileInfo)."""
    h = hashlib.sha256()
    h.update(path.name.encode())
    h.update(str(path.stat().st_size).encode())
    return h.hexdigest()[:16]


def collect_files(source_dirs: list[Path]) -> list[tuple[Path, str]]:
    """
    Рекурсивно собирает PDF/DOCX из папок.
    Возвращает список (путь, относительная_метка).

    Метка вида: "DC/Договоры/файл.pdf" — имя папки-источника + путь внутри неё.
    Пропускает ~$... (MS Office lock-файлы).
    """
    found: list[tuple[Path, str]] = []
    for src in source_dirs:
        if not src.exists():
            logger.warning("Папка не найдена: %s", src)
            continue
        for f in src.rglob("*"):
            if not f.is_file():
                continue
            if f.suffix.lower() not in (".pdf", ".docx", ".doc"):
                continue
            if f.name.startswith("~$"):
                continue
            rel_label = str(Path(src.name) / f.relative_to(src))
            found.append((f, rel_label))
    logger.info("Найдено файлов: %d", len(found))
    return found


# ─── Обработка одного файла ───────────────────────────────────────────────────

def process_one(path: Path, rel_label: str, config: Config) -> dict | None:
    """
    Извлекает текст и запрашивает AI-метаданные для одного файла.
    Возвращает dict-запись для JSONL или None если файл нужно пропустить.
    """
    file_info = FileInfo(
        path=path,
        filename=path.name,
        extension=path.suffix.lower(),
        size_bytes=path.stat().st_size,
        file_hash=_file_hash(path),
    )
    extracted = extract_text(file_info)

    if extracted.extraction_method == "failed":
        logger.warning("Нет текста: %s", path.name)
        return None
    if extracted.is_scanned:
        logger.info("Пропуск скана (нет OCR): %s", path.name)
        return None
    if len(extracted.text.strip()) < 100:
        logger.info("Мало текста: %s", path.name)
        return None

    try:
        metadata = extract_metadata(extracted.text, config)
    except RuntimeError as e:
        logger.error("AI-ошибка %s: %s", path.name, e)
        return None

    # Нормализация: ИП формат + ФИО в именительный падеж
    counterparty = _normalize_ip(metadata.counterparty)
    if counterparty and _looks_like_person(counterparty):
        counterparty = _normalize_fio(counterparty)

    parties = [
        _normalize_ip(_normalize_fio(p) if _looks_like_person(p) else _normalize_ip(p))
        for p in metadata.parties
    ]

    return {
        "id": _text_hash(extracted.text),
        "source_file": rel_label,
        "text_preview": extracted.text[:300].replace("\n", " ").strip(),
        "text_length": len(extracted.text),
        "input_text": extracted.text[:30_000],
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
        "model_used": config.active_model,
        "labeled_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "review_status": "pending",
    }


# ─── Главная функция ──────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Разметка датасета юридических документов для файнтюнинга"
    )
    parser.add_argument("sources", nargs="+", type=Path, help="Папки с документами")
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE,
                        help=f"Куда писать JSONL (по умолчанию: {OUTPUT_FILE})")
    parser.add_argument("--workers", type=int, default=5,
                        help="Параллельных AI-запросов (по умолчанию: 5)")
    parser.add_argument("--resume", action="store_true",
                        help="Дописать в существующий файл, пропуская уже размеченные")
    args = parser.parse_args()

    # Конфигурация с расширенным списком типов документов
    config = Config()
    config.document_types_hints = config.document_types_hints + EXTRA_DOCUMENT_TYPES

    # Собрать файлы
    file_pairs = collect_files([Path(s) for s in args.sources])
    if not file_pairs:
        logger.error("Нет файлов для обработки")
        sys.exit(1)

    # Загрузить ID уже размеченных (для --resume)
    seen_ids: set[str] = set()
    if args.resume and args.output.exists():
        with open(args.output, encoding="utf-8") as f:
            for line in f:
                try:
                    seen_ids.add(json.loads(line)["id"])
                except (json.JSONDecodeError, KeyError):
                    pass
        logger.info("Уже в датасете: %d записей", len(seen_ids))

    stats = {"ok": 0, "skip": 0, "dup": 0, "error": 0}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.resume else "w"

    with open(args.output, mode, encoding="utf-8") as out_f:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(process_one, path, label, config): (path, label)
                for path, label in file_pairs
            }
            for future in tqdm(as_completed(futures), total=len(futures), desc="Разметка"):
                path, label = futures[future]
                try:
                    record = future.result()
                except Exception as e:
                    logger.error("Ошибка %s: %s", path.name, e)
                    stats["error"] += 1
                    continue

                if record is None:
                    stats["skip"] += 1
                    continue

                if record["id"] in seen_ids:
                    logger.debug("Дубль пропущен: %s", path.name)
                    stats["dup"] += 1
                    continue

                seen_ids.add(record["id"])
                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                out_f.flush()
                stats["ok"] += 1

    total = sum(stats.values())
    logger.info("─" * 50)
    logger.info("Файлов:      %d", total)
    logger.info("Размечено:   %d", stats["ok"])
    logger.info("Пропущено:   %d  (сканы, нет текста)", stats["skip"])
    logger.info("Дублей:      %d", stats["dup"])
    logger.info("Ошибок:      %d", stats["error"])
    logger.info("Датасет:     %s", args.output)
    logger.info("Токенов ≈    %s", f"{stats['ok'] * APPROX_TOKENS_PER_DOC:,}")
    logger.info("─" * 50)


if __name__ == "__main__":
    main()
