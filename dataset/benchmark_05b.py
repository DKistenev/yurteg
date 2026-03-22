"""
Бенчмарк: Qwen 0.5B (база) vs Qwen 1.5B (дообученная v3)
Прогоняет те же 60 стресс-документов через llama-server + GBNF.

Использование:
  1. Убедиться что llama-server не занят (порт 8080 свободен)
  2. python dataset/benchmark_05b.py

Скрипт сам запустит llama-server с 0.5B, прогонит тесты, остановит сервер.
"""

import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

import requests

# --- Конфиг ---

YURTEG_DIR = Path.home() / ".yurteg"
MODEL_05B = YURTEG_DIR / "qwen2.5-0.5b-q4_k_m.gguf"
MODEL_15B = YURTEG_DIR / "yurteg-v3-Q4_K_M.gguf"
LLAMA_SERVER = YURTEG_DIR / "llama-server"
GRAMMAR_FILE = Path(__file__).parent.parent / "data" / "contract.gbnf"
STRESS_DIR = Path(__file__).parent.parent / "tests" / "test_data" / "stress"
REPORT_DIR = Path(__file__).parent

PORT = 8090  # отдельный порт, чтобы не мешать основному серверу
BASE_URL = f"http://localhost:{PORT}"

# Тот же системный промпт что и в ai_extractor.py
SYSTEM_PROMPT = """Ты — опытный юрист-аналитик. Извлеки структурированные метаданные из юридического документа.

ПРАВИЛА:
1. Текст может содержать маски анонимизации ([ФИО_1], [ТЕЛЕФОН_1] и т.д.) — используй их как есть.
2. Отвечай СТРОГО чистым JSON. Без текста до/после, без обёрток ```json```.
3. Отсутствующую информацию ставь null (не пустую строку "").
4. Списки всегда массивы: parties=[], special_conditions=[]. Никогда не null и не строка.
5. confidence — число от 0.0 до 1.0 (не строка).
6. Сумму пиши с пробелами-разделителями и валютой: "1 500 000 руб.", "25 000 EUR".
7. Даты строго YYYY-MM-DD.
8. ШАБЛОНЫ: если в тексте есть пустые поля — is_template=true, counterparty=null, parties=[].
9. ФИО пиши СТРОГО в именительном падеже.
10. document_type: "Договор поставки", "Договор аренды" и т.д.
11. Формат ИП: ВСЕГДА "ИП Фамилия Имя Отчество"."""

USER_PROMPT_TEMPLATE = """Извлеки метаданные из текста юридического документа.

Верни JSON с полями:
- document_type (string): тип документа
- counterparty (string|null): контрагент
- subject (string): предмет документа
- date_signed (string|null): дата подписания, YYYY-MM-DD
- date_start (string|null): дата начала, YYYY-MM-DD
- date_end (string|null): дата окончания, YYYY-MM-DD
- amount (string|null): сумма с валютой
- special_conditions (array): особые условия
- parties (array): все стороны
- confidence (float): уверенность 0.0–1.0
- is_template (bool): шаблон или нет
- payment_terms (string|null): порядок оплаты
- payment_amount (number|null): сумма платежа
- payment_frequency (string|null): "monthly"/"quarterly"/"yearly"/"once"/null
- payment_direction (string|null): "income"/"expense"/null

Текст документа:
{text}"""


def start_server(model_path: Path) -> subprocess.Popen:
    """Запуск llama-server с указанной моделью."""
    cmd = [
        str(LLAMA_SERVER),
        "-m", str(model_path),
        "-c", "4096",
        "-n", "512",
        "--temp", "0.05",
        "--min-p", "0.05",
        "--top-p", "1.0",
        "--repeat-penalty", "1.1",
        "--grammar-file", str(GRAMMAR_FILE),
        "--port", str(PORT),
    ]
    print(f"Запуск llama-server: {model_path.name} на порту {PORT}...")
    env = os.environ.copy()
    env["DYLD_LIBRARY_PATH"] = str(YURTEG_DIR)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )

    # Ждём готовности (модель грузится на Metal, может занять время)
    for i in range(90):
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=2)
            if r.status_code == 200:
                print(f"  Сервер готов за {i + 1}с")
                return proc
        except requests.ConnectionError:
            pass
        time.sleep(1)

    proc.kill()
    raise RuntimeError("llama-server не запустился за 60 секунд")


def stop_server(proc: subprocess.Popen):
    """Остановка llama-server."""
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("  Сервер остановлен")


def _load_grammar() -> str:
    """Загрузка GBNF грамматики из файла."""
    return GRAMMAR_FILE.read_text(encoding="utf-8")


_GRAMMAR = None


def get_grammar() -> str:
    global _GRAMMAR
    if _GRAMMAR is None:
        _GRAMMAR = _load_grammar()
    return _GRAMMAR


def query_model(text: str) -> tuple[dict | None, float]:
    """Один запрос к модели. Возвращает (parsed_json, время_сек)."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT_TEMPLATE.format(text=text[:30000])},
    ]

    start = time.time()
    try:
        resp = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            json={
                "model": "local",
                "messages": messages,
                "temperature": 0.05,
                "max_tokens": 512,
            },
            timeout=180,
        )
        elapsed = time.time() - start
        content = resp.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return parsed, elapsed
    except Exception as e:
        elapsed = time.time() - start
        return None, elapsed


def check_issues(parsed: dict) -> list[str]:
    """Проверка качества ответа (те же проверки что в v2_stress_test)."""
    issues = []

    # Code-switching: английские слова в русских полях
    for key, val in parsed.items():
        val_str = str(val)
        if re.search(r'[a-zA-Z]{3,}', val_str) and key not in ("amount",):
            if val_str not in (
                "null", "true", "false", "None",
                "once", "monthly", "quarterly", "yearly",
                "income", "expense",
            ):
                # Пропускаем enum-значения внутри списков
                if key in ("payment_frequency", "payment_direction"):
                    continue
                issues.append(f"code-switch в {key}: {val_str[:60]}")
        if re.search(r'[\u4e00-\u9fff]', val_str):
            issues.append(f"китайский в {key}: {val_str[:60]}")

    # Пустой document_type
    if not parsed.get("document_type") or len(str(parsed["document_type"])) < 3:
        issues.append(f"пустой document_type: {parsed.get('document_type')}")

    # Полная форма вместо краткой
    for key in ("counterparty", "parties"):
        val = str(parsed.get(key, ""))
        if "Общество с ограниченной ответственностью" in val:
            issues.append(f"полная форма ООО в {key}")
        if "Индивидуальный предприниматель" in val:
            issues.append(f"полная форма ИП в {key}")

    # Невалидные даты
    for date_key in ("date_signed", "date_start", "date_end"):
        val = parsed.get(date_key)
        if val is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(val)):
            issues.append(f"невалидная дата {date_key}: {val}")

    return issues


def run_benchmark(model_path: Path, label: str) -> list[dict]:
    """Прогон всех стресс-документов через одну модель."""
    print(f"\n{'=' * 60}")
    print(f"  БЕНЧМАРК: {label}")
    print(f"  Модель: {model_path.name} ({model_path.stat().st_size / 1e6:.0f} MB)")
    print(f"{'=' * 60}\n")

    proc = start_server(model_path)
    results = []

    try:
        files = sorted(STRESS_DIR.glob("*.txt"))
        print(f"Документов: {len(files)}\n")

        for i, f in enumerate(files, 1):
            text = f.read_text(encoding="utf-8")
            print(f"  [{i:2d}/{len(files)}] {f.name[:40]:<40s}", end=" ", flush=True)

            parsed, elapsed = query_model(text)

            if parsed is None:
                print(f"  {elapsed:5.1f}с  ❌ CRASH")
                results.append({
                    "file": f.name,
                    "time": round(elapsed, 1),
                    "issues": ["CRASH"],
                    "response": None,
                })
                continue

            issues = check_issues(parsed)
            status = "✅" if not issues else f"⚠️  {len(issues)}"
            print(f"  {elapsed:5.1f}с  {status}")

            results.append({
                "file": f.name,
                "time": round(elapsed, 1),
                "document_type": parsed.get("document_type"),
                "counterparty": parsed.get("counterparty"),
                "amount": parsed.get("amount"),
                "confidence": parsed.get("confidence"),
                "issues": issues,
                "response": parsed,
            })
    finally:
        stop_server(proc)

    return results


def print_summary(results: list[dict], label: str):
    """Вывод сводки по одной модели."""
    total = len(results)
    clean = sum(1 for r in results if not r["issues"])
    crashes = sum(1 for r in results if "CRASH" in r["issues"])
    times = [r["time"] for r in results if r["response"] is not None]
    avg_time = sum(times) / len(times) if times else 0

    all_issues = []
    for r in results:
        all_issues.extend(r["issues"])

    code_switch = sum(1 for i in all_issues if "code-switch" in i)
    chinese = sum(1 for i in all_issues if "китайский" in i)
    format_err = sum(1 for i in all_issues if "форма" in i)
    empty_type = sum(1 for i in all_issues if "document_type" in i)
    bad_date = sum(1 for i in all_issues if "дата" in i)

    print(f"\n{'─' * 50}")
    print(f"  {label}")
    print(f"{'─' * 50}")
    print(f"  Чистых:           {clean}/{total} ({clean / total * 100:.0f}%)")
    print(f"  Крашей:           {crashes}")
    print(f"  Code-switching:   {code_switch}")
    print(f"  Китайский:        {chinese}")
    print(f"  Полная форма:     {format_err}")
    print(f"  Пустой тип:       {empty_type}")
    print(f"  Невалидные даты:  {bad_date}")
    print(f"  Среднее время:    {avg_time:.1f}с")
    if times:
        print(f"  Мин/Макс:         {min(times):.1f}с / {max(times):.1f}с")
    print(f"{'─' * 50}")

    return {
        "label": label,
        "total": total,
        "clean": clean,
        "clean_pct": round(clean / total * 100, 1),
        "crashes": crashes,
        "code_switch": code_switch,
        "chinese": chinese,
        "format_errors": format_err,
        "empty_type": empty_type,
        "bad_date": bad_date,
        "avg_time": round(avg_time, 1),
        "min_time": round(min(times), 1) if times else None,
        "max_time": round(max(times), 1) if times else None,
    }


def main():
    if not MODEL_05B.exists():
        print(f"❌ Модель 0.5B не найдена: {MODEL_05B}")
        print("Скачай: huggingface-cli download Qwen/Qwen2.5-0.5B-Instruct-GGUF "
              "qwen2.5-0.5b-instruct-q4_k_m.gguf --local-dir ~/.yurteg/")
        sys.exit(1)

    if not LLAMA_SERVER.exists():
        print(f"❌ llama-server не найден: {LLAMA_SERVER}")
        sys.exit(1)

    if not GRAMMAR_FILE.exists():
        print(f"❌ GBNF грамматика не найдена: {GRAMMAR_FILE}")
        sys.exit(1)

    # --- Бенчмарк 0.5B ---
    results_05b = run_benchmark(MODEL_05B, "Qwen 0.5B (база, без дообучения)")
    summary_05b = print_summary(results_05b, "Qwen 0.5B (база)")

    # --- Бенчмарк 1.5B ---
    run_15b = input("\nЗапустить тест 1.5B для сравнения? (y/N): ").strip().lower()
    if run_15b == "y":
        results_15b = run_benchmark(MODEL_15B, "Qwen 1.5B v3 (ORPO дообученная)")
        summary_15b = print_summary(results_15b, "Qwen 1.5B v3 (ORPO)")
    else:
        # Используем сохранённые результаты из памяти
        summary_15b = {
            "label": "Qwen 1.5B v3 (ORPO) — из прошлого теста",
            "clean": 51, "total": 60, "clean_pct": 85.0,
            "crashes": 0, "code_switch": 0, "chinese": 0,
            "avg_time": 19.6,
        }
        results_15b = None

    # --- Сравнение ---
    print(f"\n{'=' * 60}")
    print("  СРАВНЕНИЕ")
    print(f"{'=' * 60}")
    print(f"  {'Метрика':<25s} {'0.5B база':>12s} {'1.5B ORPO':>12s}")
    print(f"  {'─' * 49}")
    print(f"  {'Чистых':<25s} {summary_05b['clean_pct']:>11.0f}% {summary_15b['clean_pct']:>11.0f}%")
    print(f"  {'Code-switching':<25s} {summary_05b.get('code_switch', '?'):>12} {summary_15b.get('code_switch', '?'):>12}")
    print(f"  {'Китайский':<25s} {summary_05b.get('chinese', '?'):>12} {summary_15b.get('chinese', '?'):>12}")
    print(f"  {'Среднее время':<25s} {summary_05b['avg_time']:>11.1f}с {summary_15b['avg_time']:>11.1f}с")
    print(f"  {'─' * 49}")

    speedup = summary_15b["avg_time"] / summary_05b["avg_time"] if summary_05b["avg_time"] > 0 else 0
    quality_gap = summary_15b["clean_pct"] - summary_05b["clean_pct"]

    print(f"\n  Ускорение: x{speedup:.1f}")
    print(f"  Разница качества: {quality_gap:+.0f}%")

    if summary_05b["clean_pct"] >= 70:
        print("\n  ✅ 0.5B перспективна! После ORPO дообучения может выйти на уровень 1.5B")
    elif summary_05b["clean_pct"] >= 50:
        print("\n  ⚠️  0.5B средненько. Дообучение поможет, но не факт что догонит 1.5B")
    else:
        print("\n  ❌ 0.5B слишком слабая для этой задачи без дообучения")

    # Сохраняем отчёт
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary_05b": summary_05b,
        "summary_15b": summary_15b,
        "results_05b": results_05b,
        "results_15b": results_15b,
    }
    report_path = REPORT_DIR / "benchmark_05b_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n  Полный отчёт: {report_path}")


if __name__ == "__main__":
    main()
