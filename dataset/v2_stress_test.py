"""
Stress-тест yurteg-v2 на всех документах в tests/test_data/stress/
Прогоняет через Ollama с constrained decoding, собирает отчёт.
"""

import json
import time
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "yurteg-v2"

PROMPT_TEMPLATE = """Извлеки метаданные из текста юридического документа.

Правила:
- Отвечай ТОЛЬКО на русском языке. Никаких английских или китайских слов.
- document_type на русском: "Договор займа", "Договор поставки", "Доверенность" и т.д.
- amount — сумма с валютой: "2 000 000 руб.", "500 000 EUR". Если нет суммы — null
- payment_frequency: "monthly" если платежи ежемесячные (аренда, кредит, проценты), "once" если разовый, "quarterly"/"yearly" если иное
- payment_direction: "income" если деньги поступают нам, "expense" если платим мы
- ФИО строго в именительном падеже
- Контрагент в краткой форме: "ООО", не "Общество с ограниченной ответственностью"
- Формат ИП: "ИП Фамилия Имя Отчество"

Текст документа:
{text}"""

SCHEMA = {
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
        "payment_direction": {"type": ["string", "null"]}
    },
    "required": ["document_type", "counterparty", "subject", "amount", "is_template", "special_conditions", "parties"]
}


def test_document(filepath: Path) -> dict:
    """Тест одного документа."""
    text = filepath.read_text(encoding="utf-8")
    prompt = PROMPT_TEMPLATE.format(text=text)

    start = time.time()
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "format": SCHEMA,
            "stream": False,
        }, timeout=120)
        elapsed = time.time() - start
        content = resp.json()["message"]["content"]
        parsed = json.loads(content)

        # Проверки
        issues = []

        # Code-switching
        import re
        for key, val in parsed.items():
            val_str = str(val)
            if re.search(r'[a-zA-Z]{3,}', val_str) and key not in ("amount",):
                # Исключаем null, true, false, числа
                if val_str not in ("null", "true", "false", "None", "once", "monthly", "quarterly", "yearly", "income", "expense"):
                    issues.append(f"code-switch в {key}: {val_str[:60]}")
            if re.search(r'[\u4e00-\u9fff]', val_str):
                issues.append(f"китайский в {key}: {val_str[:60]}")

        # Пустой document_type
        if not parsed.get("document_type") or len(parsed["document_type"]) < 3:
            issues.append(f"пустой/мусорный document_type: {parsed.get('document_type')}")

        # Полная форма вместо краткой
        for key in ("counterparty", "parties"):
            val = str(parsed.get(key, ""))
            if "Общество с ограниченной ответственностью" in val:
                issues.append(f"полная форма ООО в {key}")
            if "Индивидуальный предприниматель" in val:
                issues.append(f"полная форма ИП в {key}")
            if "Акционерное общество" in val and "ПАО" not in val and "ЗАО" not in val:
                issues.append(f"полная форма АО в {key}")

        return {
            "file": filepath.name,
            "time": round(elapsed, 1),
            "document_type": parsed.get("document_type", "?"),
            "counterparty": parsed.get("counterparty", "?"),
            "amount": parsed.get("amount"),
            "payment_freq": parsed.get("payment_frequency"),
            "payment_dir": parsed.get("payment_direction"),
            "is_template": parsed.get("is_template"),
            "issues": issues,
            "full_response": parsed,
        }
    except Exception as e:
        return {
            "file": filepath.name,
            "time": round(time.time() - start, 1),
            "error": str(e),
            "issues": [f"CRASH: {e}"],
        }


def main():
    stress_dir = Path("tests/test_data/stress")
    files = sorted(stress_dir.glob("*.txt"))
    print(f"Found {len(files)} stress test documents\n")

    results = []
    for f in files:
        print(f"Testing {f.name}...", end=" ", flush=True)
        result = test_document(f)
        elapsed = result.get("time", "?")
        issues = result.get("issues", [])
        status = "✅" if not issues else f"⚠️ {len(issues)} issues"
        print(f"{elapsed}s — {status}")
        results.append(result)

    # Отчёт
    print(f"\n{'='*70}")
    print(f"ИТОГО: {len(results)} документов")
    print(f"{'='*70}")

    total_issues = sum(len(r.get("issues", [])) for r in results)
    clean = sum(1 for r in results if not r.get("issues"))
    with_issues = len(results) - clean

    print(f"Чистых: {clean}/{len(results)}")
    print(f"С проблемами: {with_issues}/{len(results)}")
    print(f"Всего проблем: {total_issues}")

    # Категоризация
    code_switch = []
    wrong_type = []
    wrong_payment = []
    hallucination = []
    format_issues = []

    for r in results:
        for issue in r.get("issues", []):
            if "code-switch" in issue or "китайский" in issue:
                code_switch.append((r["file"], issue))
            elif "document_type" in issue:
                wrong_type.append((r["file"], issue))
            elif "payment" in issue.lower():
                wrong_payment.append((r["file"], issue))
            elif "форма" in issue:
                format_issues.append((r["file"], issue))
            else:
                hallucination.append((r["file"], issue))

    print(f"\nCode-switching: {len(code_switch)}")
    for f, i in code_switch[:10]:
        print(f"  {f}: {i}")

    print(f"\nНеправильный тип: {len(wrong_type)}")
    for f, i in wrong_type:
        print(f"  {f}: {i}")

    print(f"\nФормат наименований: {len(format_issues)}")
    for f, i in format_issues:
        print(f"  {f}: {i}")

    print(f"\nДругие: {len(hallucination)}")
    for f, i in hallucination[:10]:
        print(f"  {f}: {i}")

    # Среднее время
    times = [r["time"] for r in results if "time" in r]
    print(f"\nСреднее время: {sum(times)/len(times):.1f}с")
    print(f"Мин: {min(times):.1f}с, Макс: {max(times):.1f}с")

    # Сохраняем полный отчёт
    report_path = Path("dataset/v2_stress_report.json")
    with open(report_path, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nПолный отчёт: {report_path}")


if __name__ == "__main__":
    main()
