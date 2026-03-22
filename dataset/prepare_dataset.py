"""
Подготовка финального датасета для обучения 1.5B.

1. Конвертирует labeled_data_normalized.jsonl → формат messages
2. Объединяет с synthetic_sft.jsonl
3. Дедуплицирует по id
4. Делает train/val split (90/10)
5. Сохраняет в dataset/training/

Запуск:
    python3 dataset/prepare_dataset.py
"""

import json
import random
import hashlib
from pathlib import Path
from collections import Counter

random.seed(42)

DATASET_DIR = Path(__file__).parent
OUTPUT_DIR = DATASET_DIR / "training"
OUTPUT_DIR.mkdir(exist_ok=True)

VAL_RATIO = 0.1

SYSTEM_PROMPT = """Ты — опытный юрист-аналитик. Извлеки структурированные метаданные из юридического документа.

ПРАВИЛА:
1. Отвечай СТРОГО чистым JSON. Без текста до/после, без обёрток ```json```.
2. Отсутствующую информацию ставь null (не пустую строку "").
3. Списки всегда массивы: parties=[], special_conditions=[].
4. confidence — число от 0.0 до 1.0.
5. Сумму пиши с пробелами-разделителями и валютой: "1 500 000 руб.".
6. Даты строго YYYY-MM-DD.
7. ФИО в именительном падеже: "Иванов Иван Иванович".
8. Формат ИП: "ИП Фамилия Имя Отчество"."""

USER_TEMPLATE = """Извлеки метаданные из текста юридического документа.

Верни JSON с полями: document_type, counterparty, subject, date_signed, date_start, date_end, amount, special_conditions, parties, confidence, is_template

Текст документа:
{text}"""


def make_id(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:16]


def convert_real(record: dict) -> dict | None:
    """Конвертирует запись из labeled_data_normalized в формат messages."""
    input_text = record.get("input_text", "").strip()
    output = record.get("output", {})

    if not input_text or not output:
        return None

    if isinstance(output, str):
        try:
            output = json.loads(output)
        except Exception:
            return None

    # Добавляем is_template если нет
    if "is_template" not in output:
        output["is_template"] = False

    # Добавляем parties если нет
    if "parties" not in output:
        output["parties"] = []

    # Чистим плохие даты
    for date_field in ["date_signed", "date_start", "date_end"]:
        val = output.get(date_field)
        if val and ("00-00" in str(val) or len(str(val)) != 10):
            output[date_field] = None

    # Пустые строки → null
    for field in ["counterparty", "subject", "amount", "date_signed", "date_start", "date_end"]:
        if output.get(field) == "":
            output[field] = None

    # parties и special_conditions всегда массивы
    if not isinstance(output.get("parties"), list):
        output["parties"] = []
    if not isinstance(output.get("special_conditions"), list):
        output["special_conditions"] = []

    user_content = USER_TEMPLATE.format(text=input_text[:6000])
    assistant_content = json.dumps(output, ensure_ascii=False)

    return {
        "id": record.get("id") or make_id(input_text),
        "source": "real",
        "doc_type": output.get("document_type", ""),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ],
    }


def load_real() -> list[dict]:
    records = []
    with open(DATASET_DIR / "labeled_data_normalized.jsonl", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = convert_real(json.loads(line))
                if r:
                    records.append(r)
            except Exception as e:
                print(f"  Пропущена запись: {e}")
    return records


def load_synthetic() -> list[dict]:
    records = []
    with open(DATASET_DIR / "synthetic_sft.jsonl", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception as e:
                print(f"  Пропущена запись: {e}")
    return records


def deduplicate(records: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for r in records:
        rid = r.get("id", make_id(str(r)))
        if rid not in seen:
            seen.add(rid)
            result.append(r)
    return result


def main():
    print("Загружаем реальные данные...")
    real = load_real()
    print(f"  Загружено: {len(real)}")

    print("Загружаем синтетику...")
    synthetic = load_synthetic()
    print(f"  Загружено: {len(synthetic)}")

    print("Объединяем и дедуплицируем...")
    all_records = real + synthetic
    all_records = deduplicate(all_records)
    print(f"  Итого после дедупликации: {len(all_records)}")

    # Статистика по типам
    type_counts = Counter(r.get("doc_type", "?") for r in all_records)
    print(f"\nТипов документов: {len(type_counts)}")
    print("Топ-10 по количеству:")
    for t, c in type_counts.most_common(10):
        print(f"  {c:4d}  {t}")

    # Перемешиваем и делим
    random.shuffle(all_records)
    val_size = max(1, int(len(all_records) * VAL_RATIO))
    val_records = all_records[:val_size]
    train_records = all_records[val_size:]

    print(f"\nTrain: {len(train_records)}, Val: {len(val_records)}")

    # Сохраняем только поле messages (формат для обучения)
    train_file = OUTPUT_DIR / "train.jsonl"
    val_file = OUTPUT_DIR / "val.jsonl"

    with open(train_file, "w", encoding="utf-8") as f:
        for r in train_records:
            f.write(json.dumps({"messages": r["messages"]}, ensure_ascii=False) + "\n")

    with open(val_file, "w", encoding="utf-8") as f:
        for r in val_records:
            f.write(json.dumps({"messages": r["messages"]}, ensure_ascii=False) + "\n")

    print(f"\nГотово!")
    print(f"  {train_file}")
    print(f"  {val_file}")


if __name__ == "__main__":
    main()
