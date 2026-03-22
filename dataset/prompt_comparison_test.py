#!/usr/bin/env python3
"""
Тест 3 вариантов system prompt на 10 проблемных документах.
Цель: найти вариант с минимальным code-switching.
"""
import json
import re
import time
import urllib.request
from pathlib import Path

STRESS_DIR = Path("/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/tests/test_data/stress")
OUTPUT_FILE = Path("/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/dataset/v2_prompt_comparison.md")
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "yurteg-v2"

DOCS = [
    "03_шаблон.txt",
    "05_трудовой.txt",
    "10_ocr_мусор.txt",
    "11_не_юридический.txt",
    "29_nda.txt",
    "30_иностранный.txt",
    "35_смешанный.txt",
    "40_маркетинг.txt",
    "57_пустой_шаблон.txt",
    "33_оферта.txt",
]

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "document_type": {"type": "string"},
        "counterparty": {"type": ["string", "null"]},
        "subject": {"type": "string"},
        "date_signed": {"type": ["string", "null"]},
        "date_start": {"type": ["string", "null"]},
        "date_end": {"type": ["string", "null"]},
        "amount": {"type": ["string", "null"]},
        "special_conditions": {"type": "array", "items": {"type": "string"}},
        "parties": {"type": "array", "items": {"type": "string"}},
        "is_template": {"type": "boolean"},
        "payment_terms": {"type": ["string", "null"]},
        "payment_amount": {"type": ["number", "null"]},
        "payment_frequency": {"type": ["string", "null"]},
        "payment_direction": {"type": ["string", "null"]},
    },
    "required": ["document_type", "counterparty", "subject", "amount", "is_template", "special_conditions", "parties"],
}

PROMPTS = {
    "A": """Извлеки метаданные из текста юридического документа.

КРИТИЧЕСКИ ВАЖНО: Все поля заполняй ТОЛЬКО на русском языке. ЗАПРЕЩЕНО использовать английские, китайские или любые другие не-русские слова. Даже если в тексте есть иностранные термины — переведи их на русский.

Правила:
- document_type на русском: "Договор займа", "Договор поставки" и т.д.
- amount — сумма с валютой: "2 000 000 руб."
- payment_frequency: "monthly"/"once"/"quarterly"/"yearly"
- payment_direction: "income"/"expense"
- ФИО в именительном падеже
- Контрагент в краткой форме: "ООО", не "Общество с ограниченной ответственностью"

Текст документа:
{text}""",

    "B": """Извлеки метаданные из юридического документа. Отвечай строго на русском языке.

Текст:
{text}""",

    "C": """Извлеки метаданные из текста юридического документа. Все значения ТОЛЬКО на русском.

Пример правильного ответа:
document_type: "Договор оказания услуг"
subject: "Оказание консультационных услуг по вопросам налогообложения"
special_conditions: ["Неустойка 0,1% за каждый день просрочки", "Срок действия 12 месяцев"]

Текст документа:
{text}""",
}

# Enum-значения которые разрешены по-английски
ALLOWED_ENGLISH = {"monthly", "once", "quarterly", "yearly", "income", "expense", "null", "true", "false"}


def count_english_words(text: str) -> tuple[int, list[str]]:
    """Считает английские слова (3+ букв), исключая enum-значения."""
    words = re.findall(r"[a-zA-Z]{3,}", text)
    bad_words = [w for w in words if w.lower() not in ALLOWED_ENGLISH]
    return len(bad_words), bad_words


def call_ollama(prompt: str) -> tuple[str, float, str]:
    """Вызов Ollama. Возвращает (raw_response, elapsed_sec, error)."""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "format": JSON_SCHEMA,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 1024},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8")
            elapsed = time.time() - t0
            result = json.loads(body)
            return result.get("response", ""), elapsed, ""
    except Exception as e:
        return "", time.time() - t0, str(e)


def main():
    results = {}  # {doc: {variant: {"count": int, "words": list, "error": str, "elapsed": float}}}

    for doc_name in DOCS:
        doc_path = STRESS_DIR / doc_name
        if not doc_path.exists():
            print(f"  SKIP (not found): {doc_name}")
            results[doc_name] = {v: {"count": -1, "words": [], "error": "file not found", "elapsed": 0} for v in "ABC"}
            continue

        text = doc_path.read_text(encoding="utf-8", errors="replace")
        # Обрезаем до 3000 символов чтобы не перегружать модель
        text_trimmed = text[:3000]
        results[doc_name] = {}

        for variant, prompt_template in PROMPTS.items():
            prompt = prompt_template.replace("{text}", text_trimmed)
            print(f"  [{doc_name}] Вариант {variant}...", end="", flush=True)
            response, elapsed, error = call_ollama(prompt)

            if error:
                print(f" ОШИБКА: {error}")
                results[doc_name][variant] = {"count": -1, "words": [], "error": error, "elapsed": elapsed}
                continue

            count, words = count_english_words(response)
            print(f" {count} англ. слов ({elapsed:.1f}с)")
            results[doc_name][variant] = {
                "count": count,
                "words": words[:10],  # первые 10
                "error": "",
                "elapsed": elapsed,
                "raw": response[:200],
            }

    # Генерация отчёта
    lines = []
    lines.append("# Сравнение промптов v2 — борьба с code-switching\n")
    lines.append(f"Модель: `{MODEL}` | Дата: 2026-03-21\n")
    lines.append("Метрика: кол-во английских слов (3+ букв) в JSON-ответе, кроме enum-значений (monthly/once/quarterly/yearly/income/expense).\n")

    # Таблица результатов
    lines.append("## Таблица результатов\n")
    lines.append("| Документ | Вариант A | Вариант B | Вариант C | Лучший |")
    lines.append("|----------|-----------|-----------|-----------|--------|")

    totals = {"A": 0, "B": 0, "C": 0}
    errors = {"A": 0, "B": 0, "C": 0}

    for doc_name in DOCS:
        row = results.get(doc_name, {})
        counts = {}
        for v in "ABC":
            d = row.get(v, {})
            if d.get("error"):
                counts[v] = "ERR"
                errors[v] += 1
            else:
                counts[v] = d.get("count", "?")
                if isinstance(counts[v], int) and counts[v] >= 0:
                    totals[v] += counts[v]

        # Определяем лучший
        numeric = {v: counts[v] for v in "ABC" if isinstance(counts[v], int) and counts[v] >= 0}
        best = min(numeric, key=lambda x: numeric[x]) if numeric else "—"

        lines.append(
            f"| `{doc_name}` | {counts['A']} | {counts['B']} | {counts['C']} | **{best}** |"
        )

    # Итого
    lines.append(f"| **ИТОГО** | **{totals['A']}** | **{totals['B']}** | **{totals['C']}** | **{min(totals, key=lambda x: totals[x])}** |")
    lines.append("")

    # Детали по найденным словам
    lines.append("## Найденные английские слова (примеры)\n")
    for doc_name in DOCS:
        row = results.get(doc_name, {})
        has_words = any(row.get(v, {}).get("words") for v in "ABC")
        if has_words:
            lines.append(f"### `{doc_name}`\n")
            for v in "ABC":
                d = row.get(v, {})
                words = d.get("words", [])
                if words:
                    lines.append(f"- Вариант {v}: `{', '.join(words)}`")
            lines.append("")

    # Анализ
    lines.append("## Анализ\n")
    winner = min(totals, key=lambda x: totals[x])
    runner_up = sorted(totals, key=lambda x: totals[x])[1]
    worst = max(totals, key=lambda x: totals[x])

    lines.append(f"**Лучший вариант: {winner}** — {totals[winner]} английских слов суммарно")
    lines.append(f"**Второй: {runner_up}** — {totals[runner_up]} слов")
    lines.append(f"**Худший: {worst}** — {totals[worst]} слов")
    lines.append("")

    descriptions = {
        "A": "«Жёсткие правила» — запрет + подробные инструкции",
        "B": "«Минимальный» — только одна фраза о русском языке",
        "C": "«С примером» — пример правильного ответа",
    }
    for v in "ABC":
        lines.append(f"- Вариант {v} ({descriptions[v]}): **{totals[v]}** англ. слов")
    lines.append("")

    # Рекомендация
    lines.append("## Рекомендация для финального промпта\n")

    if winner == "A":
        lines.append(
            "Использовать **Вариант A** как основу. Явный запрет с перечислением правил даёт модели чёткие ограничения. "
            "Можно дополнить примером из Варианта C для укрепления паттерна."
        )
    elif winner == "B":
        lines.append(
            "Использовать **Вариант B** как основу. Минимальный промпт работает лучше — модель уже обучена на русском "
            "и лишние инструкции создают шум. Рекомендуется не перегружать промпт."
        )
    elif winner == "C":
        lines.append(
            "Использовать **Вариант C** как основу. Few-shot пример оказался эффективнее прямых запретов — "
            "модель учится на образце, а не на правилах. Рекомендуется расширить примеры разными типами документов."
        )

    lines.append("")
    lines.append("### Комбинированный финальный промпт (рекомендуется)\n")
    lines.append("```")
    lines.append("Извлеки метаданные из текста юридического документа. Все значения ТОЛЬКО на русском языке.")
    lines.append("")
    lines.append("Пример правильного ответа:")
    lines.append('document_type: "Договор оказания услуг"')
    lines.append('subject: "Оказание консультационных услуг по вопросам налогообложения"')
    lines.append('special_conditions: ["Неустойка 0,1% за каждый день просрочки"]')
    lines.append("")
    lines.append("Правила:")
    lines.append('- document_type: "Договор займа", "Договор поставки", "Трудовой договор" и т.д.')
    lines.append('- amount: "2 000 000 руб."')
    lines.append('- payment_frequency: "monthly"/"once"/"quarterly"/"yearly"')
    lines.append('- payment_direction: "income"/"expense"')
    lines.append("")
    lines.append("Текст документа:")
    lines.append("{text}")
    lines.append("```")

    report = "\n".join(lines)
    OUTPUT_FILE.write_text(report, encoding="utf-8")
    print(f"\nОтчёт записан: {OUTPUT_FILE}")
    print(f"\nИтого английских слов — A: {totals['A']}, B: {totals['B']}, C: {totals['C']}")
    print(f"Победитель: Вариант {winner}")


if __name__ == "__main__":
    main()
