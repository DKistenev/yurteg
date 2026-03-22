"""
Очистка датасета перед обучением 1.5B.

1. Шаблоны (confidence < 0.3, все поля null) → is_template=true, confidence=0.9, оставить 25 штук
2. Дедупликация по тексту документа
3. Ограничение топовых типов до 50 записей
4. Отчёт: какие типы нуждаются в синтетике

Запуск:
    python3 dataset/clean_dataset.py
"""

import json
import random
from collections import Counter, defaultdict
from pathlib import Path

random.seed(42)

DATASET_DIR = Path(__file__).parent
TRAIN_IN = DATASET_DIR / "training" / "train.jsonl"
VAL_IN = DATASET_DIR / "training" / "val.jsonl"
TRAIN_OUT = DATASET_DIR / "training" / "train_clean.jsonl"
VAL_OUT = DATASET_DIR / "training" / "val_clean.jsonl"

MAX_PER_TYPE = 50       # Потолок для перепредставленных типов
MAX_TEMPLATES = 25      # Сколько шаблонов оставить
MIN_PER_TYPE = 5        # Меньше этого — нужна синтетика


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def save_jsonl(records: list[dict], path: Path):
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def is_template_record(resp: dict) -> bool:
    """Шаблон = нет контрагента, нет суммы, нет дат, нет сторон, confidence < 0.3."""
    return (
        resp.get("confidence", 1.0) < 0.3
        and not resp.get("counterparty")
        and not resp.get("amount")
        and not resp.get("date_signed")
        and not resp.get("parties")
    )


def fix_template(resp: dict) -> dict:
    """Помечаем шаблон правильно — это не ошибка, а корректное распознавание."""
    resp["is_template"] = True
    resp["confidence"] = 0.9
    return resp


def get_text_key(record: dict) -> str:
    """Ключ дедупликации — текст документа (без промпта)."""
    user = record["messages"][1]["content"]
    # Берём текст после "Текст документа:"
    if "Текст документа:" in user:
        text = user.split("Текст документа:", 1)[1]
    else:
        text = user
    # Первые 500 символов как ключ
    return text[:500].strip()


def clean_dataset(records: list[dict]) -> tuple[list[dict], dict]:
    stats = {
        "input": len(records),
        "templates_found": 0,
        "templates_fixed": 0,
        "templates_removed": 0,
        "duplicates_removed": 0,
        "capped_removed": 0,
        "output": 0,
    }

    # === Шаг 1: Пометить шаблоны ===
    templates = []
    non_templates = []

    for r in records:
        resp = json.loads(r["messages"][2]["content"])
        if is_template_record(resp):
            stats["templates_found"] += 1
            fix_template(resp)
            r["messages"][2]["content"] = json.dumps(resp, ensure_ascii=False)
            templates.append(r)
        else:
            non_templates.append(r)

    # Оставить MAX_TEMPLATES шаблонов
    random.shuffle(templates)
    kept_templates = templates[:MAX_TEMPLATES]
    stats["templates_fixed"] = len(kept_templates)
    stats["templates_removed"] = len(templates) - len(kept_templates)

    working = non_templates + kept_templates

    # === Шаг 2: Дедупликация ===
    seen_texts = set()
    deduped = []
    for r in working:
        key = get_text_key(r)
        if key not in seen_texts:
            seen_texts.add(key)
            deduped.append(r)
        else:
            stats["duplicates_removed"] += 1

    # === Шаг 3: Ограничить топовые типы ===
    by_type = defaultdict(list)
    for r in deduped:
        resp = json.loads(r["messages"][2]["content"])
        dt = resp.get("document_type", "?")
        by_type[dt].append(r)

    capped = []
    for dt, recs in by_type.items():
        if len(recs) > MAX_PER_TYPE:
            random.shuffle(recs)
            stats["capped_removed"] += len(recs) - MAX_PER_TYPE
            capped.extend(recs[:MAX_PER_TYPE])
        else:
            capped.extend(recs)

    random.shuffle(capped)
    stats["output"] = len(capped)

    # === Статистика по типам после очистки ===
    final_types = Counter()
    for r in capped:
        resp = json.loads(r["messages"][2]["content"])
        final_types[resp.get("document_type", "?")] += 1

    stats["types_total"] = len(final_types)
    stats["types_need_synthetic"] = {
        t: c for t, c in final_types.items() if c < MIN_PER_TYPE
    }
    stats["final_type_distribution"] = final_types

    return capped, stats


def main():
    print("=" * 60)
    print("ОЧИСТКА ДАТАСЕТА")
    print("=" * 60)

    # Загружаем
    train = load_jsonl(TRAIN_IN)
    val = load_jsonl(VAL_IN)
    print(f"\nВход: train={len(train)}, val={len(val)}")

    # Чистим train
    print("\n--- Очистка train ---")
    train_clean, train_stats = clean_dataset(train)

    print(f"  Шаблонов найдено:    {train_stats['templates_found']}")
    print(f"  Шаблонов оставлено:  {train_stats['templates_fixed']}")
    print(f"  Шаблонов убрано:     {train_stats['templates_removed']}")
    print(f"  Дубликатов убрано:   {train_stats['duplicates_removed']}")
    print(f"  Capped (топ типы):   {train_stats['capped_removed']}")
    print(f"  Итого train:         {train_stats['output']}")

    # Чистим val (только дедупликация и шаблоны, без cap)
    print("\n--- Очистка val ---")
    val_clean, val_stats = clean_dataset(val)
    print(f"  Итого val:           {val_stats['output']}")

    # Сохраняем
    save_jsonl(train_clean, TRAIN_OUT)
    save_jsonl(val_clean, VAL_OUT)
    print(f"\nСохранено:")
    print(f"  {TRAIN_OUT}")
    print(f"  {VAL_OUT}")

    # Отчёт по типам
    print("\n" + "=" * 60)
    print("РАСПРЕДЕЛЕНИЕ ТИПОВ (после очистки)")
    print("=" * 60)
    for t, c in train_stats["final_type_distribution"].most_common():
        marker = " ⚠ НУЖНА СИНТЕТИКА" if c < MIN_PER_TYPE else ""
        print(f"  {c:4d}  {t}{marker}")

    # Типы для синтетики
    need_syn = train_stats["types_need_synthetic"]
    if need_syn:
        print(f"\n{'=' * 60}")
        print(f"НУЖНА СИНТЕТИКА ({len(need_syn)} типов)")
        print(f"{'=' * 60}")
        total_needed = 0
        for t, c in sorted(need_syn.items(), key=lambda x: x[1]):
            needed = MIN_PER_TYPE - c
            total_needed += needed
            print(f"  {t}: есть {c}, нужно ещё {needed}")
        print(f"\n  Итого нужно сгенерировать: ~{total_needed} записей")
    else:
        print("\nВсе типы имеют >= 5 примеров — синтетика не нужна!")


if __name__ == "__main__":
    main()
