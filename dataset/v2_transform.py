"""
Датасет v2: конвертация SFT в Qwen tool call формат.

Шаги:
1. Скачать train.jsonl + val.jsonl с HuggingFace
2. Удалить confidence
3. Добавить payment_* = null (заглушки, потом заполнит субагент)
4. Обернуть assistant ответ в <tool_call>...</tool_call>
5. Обновить system/user промпты
6. Сохранить в dataset/training/v2_train.jsonl, v2_val.jsonl
"""

import json
import sys
from pathlib import Path
from huggingface_hub import hf_hub_download

TOKEN = "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"
REPO = "SuperPuperD/yurteg-legal-sft"

NEW_SYSTEM_PROMPT = """Ты — юрист-аналитик. Извлеки метаданные из юридического документа.

Правила:
1. Маски анонимизации ([ФИО_1], [ТЕЛЕФОН_1]) — используй как есть
2. Отсутствующую информацию ставь null
3. Даты строго YYYY-MM-DD
4. ФИО в именительном падеже: "Иванов Иван Иванович"
5. Формат ИП: "ИП Фамилия Имя Отчество"
6. Контрагент — ДРУГАЯ сторона, не наша (Фокина/Файзулина/БУП/Digital Church)
7. Шаблоны (пустые поля _____) → is_template=true, counterparty=null, parties=[]
8. Сумму пиши с пробелами-разделителями и валютой: "1 500 000 руб."
9. document_type: одинаковые документы называй одинаково. Если не из списка — создай краткое название в том же стиле."""


def extract_document_text(user_content: str) -> str:
    """Извлечь текст документа из user prompt."""
    marker = "Текст документа:\n"
    idx = user_content.find(marker)
    if idx != -1:
        return user_content[idx + len(marker):]
    return user_content


def simplify_user_prompt(user_content: str) -> str:
    """Упростить user prompt — убрать инструкции по формату, оставить текст."""
    doc_text = extract_document_text(user_content)
    return f"Извлеки метаданные из текста юридического документа.\n\nТекст документа:\n{doc_text}"


def convert_example(example: dict) -> dict:
    """Конвертировать один SFT-пример в tool call формат."""
    messages = example["messages"]
    system_msg = messages[0]
    user_msg = messages[1]
    assistant_msg = messages[2]

    # Парсим текущий JSON ответ
    try:
        data = json.loads(assistant_msg["content"])
    except json.JSONDecodeError:
        print(f"WARNING: невалидный JSON в ответе, пропускаю", file=sys.stderr)
        return None

    # Удаляем confidence
    data.pop("confidence", None)

    # Добавляем payment_* = null (заглушки)
    for field in ["payment_terms", "payment_amount", "payment_frequency", "payment_direction"]:
        if field not in data:
            data[field] = None

    # Оборачиваем в tool call
    tool_call = {
        "name": "extract_metadata",
        "arguments": data
    }
    tool_call_str = f'<tool_call>\n{json.dumps(tool_call, ensure_ascii=False)}\n</tool_call>'

    return {
        "messages": [
            {"role": "system", "content": NEW_SYSTEM_PROMPT},
            {"role": "user", "content": simplify_user_prompt(user_msg["content"])},
            {"role": "assistant", "content": tool_call_str},
        ]
    }


def main():
    output_dir = Path("dataset/training")
    output_dir.mkdir(parents=True, exist_ok=True)

    for split in ["train", "val"]:
        print(f"\n=== Processing {split} ===")
        filepath = hf_hub_download(REPO, f"{split}.jsonl", token=TOKEN, repo_type="dataset")

        with open(filepath) as f:
            examples = [json.loads(line) for line in f]

        print(f"  Loaded {len(examples)} examples")

        converted = []
        skipped = 0
        for ex in examples:
            result = convert_example(ex)
            if result:
                converted.append(result)
            else:
                skipped += 1

        output_path = output_dir / f"v2_{split}.jsonl"
        with open(output_path, "w") as f:
            for ex in converted:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")

        print(f"  Converted: {len(converted)}, Skipped: {skipped}")
        print(f"  Saved to: {output_path}")

    # Статистика
    print("\n=== Statistics ===")
    for split in ["train", "val"]:
        path = output_dir / f"v2_{split}.jsonl"
        with open(path) as f:
            examples = [json.loads(line) for line in f]

        # Типы документов
        doc_types = {}
        payment_filled = 0
        for ex in examples:
            content = ex["messages"][2]["content"]
            tc = json.loads(content.replace("<tool_call>\n", "").replace("\n</tool_call>", ""))
            args = tc["arguments"]
            dt = args.get("document_type", "?")
            doc_types[dt] = doc_types.get(dt, 0) + 1
            if args.get("payment_terms") is not None:
                payment_filled += 1

        print(f"\n{split}: {len(examples)} examples, {len(doc_types)} doc types")
        print(f"  payment_* filled: {payment_filled}/{len(examples)}")
        # Типы с <=5 примерами
        under5 = [dt for dt, cnt in doc_types.items() if cnt <= 5]
        print(f"  Types with <=5 examples: {len(under5)}")


if __name__ == "__main__":
    main()
