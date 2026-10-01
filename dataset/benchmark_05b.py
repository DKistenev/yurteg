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
MODEL_05B = YURTEG_DIR / "yurteg-0.5b-v1-Q4_K_M.gguf"
MODEL_15B = YURTEG_DIR / "yurteg-v3-Q4_K_M.gguf"
LLAMA_SERVER = YURTEG_DIR / "llama-server"
GRAMMAR_FILE = Path(__file__).parent.parent / "data" / "contract_05b.gbnf"
STRESS_DIR = Path(__file__).parent.parent / "tests" / "test_data" / "stress"
REPORT_DIR = Path(__file__).parent

PORT = 8090  # отдельный порт, чтобы не мешать основному серверу
BASE_URL = f"http://localhost:{PORT}"

# Тот же системный промпт что и в ai_extractor.py
SYSTEM_PROMPT = """Ты — юрист-аналитик. Извлеки метаданные из юридического документа.

ЯЗЫК: Все значения ТОЛЬКО на русском. Запрещены английские и китайские слова.

Правила:
1. Отсутствующую информацию ставь null
2. Даты строго YYYY-MM-DD
3. ФИО в именительном падеже: "Иванов Иван Иванович"
4. Формат ИП: "ИП Фамилия Имя Отчество"
5. Контрагент в краткой форме: "ООО", "АО", "ПАО", "ИП"
6. Сумму с валютой: "1 500 000 руб."
7. Шаблоны (пустые поля _____) → is_template=true, counterparty=null
8. document_type на русском: "Договор аренды", "Акт выполненных работ" и т.д."""

USER_PROMPT_TEMPLATE = """Извлеки метаданные из текста юридического документа.

Текст документа:
{text}"""


# ── Улучшение 7: Очистка OCR-мусора ──────────────────────────────────────────

def clean_text(text: str) -> str:
    """Очистка текста от OCR-артефактов перед отправкой в модель."""
    text = re.sub(r'\n{3,}', '\n\n', text)          # множественные переносы
    text = re.sub(r'[ \t]{2,}', ' ', text)            # множественные пробелы
    text = re.sub(r'^\d+\s*$', '', text, flags=re.M)  # номера страниц
    text = re.sub(r'[-—]{3,}', '', text)              # разделители ---
    return text.strip()


# ── Улучшение 1: Извлечение заголовка документа ──────────────────────────────

TITLE_KEYWORDS = [
    "ДОГОВОР", "СОГЛАШЕНИЕ", "АКТ", "ПРИКАЗ", "ДОВЕРЕННОСТЬ",
    "ПРЕТЕНЗИЯ", "РАСПИСКА", "ПРОТОКОЛ", "СЧЁТ", "СЧЕТ",
    "УВЕДОМЛЕНИЕ", "ОФЕРТА", "УСТАВ", "ПОЛОЖЕНИЕ", "РЕШЕНИЕ",
    "ПОЛИТИКА", "ПРАВИЛА", "ГАРАНТИЙНОЕ", "ИСКОВОЕ", "ОТЗЫВ",
    "СПРАВКА", "СОГЛАСИЕ", "КАРТОЧКА", "КОММЕРЧЕСКОЕ",
]


def extract_title(text: str) -> str | None:
    """Извлечь заголовок документа из первых 500 символов."""
    for line in text[:500].split('\n'):
        line = line.strip()
        if not line or len(line) < 3:
            continue
        upper = line.upper()
        for kw in TITLE_KEYWORDS:
            if kw in upper and len(line) < 120:
                return line
    return None


# ── Улучшение 2+6: Fuzzy matching + нормализация document_type ───────────────

TITLE_TO_TYPE = {
    "ДОГОВОР АРЕНДЫ": "Договор аренды",
    "ДОГОВОР СУБАРЕНДЫ": "Договор субаренды",
    "ДОГОВОР ПОДРЯДА": "Договор подряда",
    "ДОГОВОР КУПЛИ-ПРОДАЖИ": "Договор купли-продажи",
    "ДОГОВОР ОКАЗАНИЯ УСЛУГ": "Договор оказания услуг",
    "ДОГОВОР ПОСТАВКИ": "Договор поставки",
    "ДОГОВОР ЗАЙМА": "Договор займа",
    "ДОГОВОР ДАРЕНИЯ": "Договор дарения",
    "ДОГОВОР КОМИССИИ": "Договор комиссии",
    "ДОГОВОР ХРАНЕНИЯ": "Договор хранения",
    "ДОГОВОР СТРАХОВАНИЯ": "Договор страхования",
    "ДОГОВОР ЛИЗИНГА": "Договор лизинга",
    "ДОГОВОР ПОРУЧИТЕЛЬСТВА": "Договор поручительства",
    "ДОГОВОР ЦЕССИИ": "Договор цессии",
    "КРЕДИТНЫЙ ДОГОВОР": "Кредитный договор",
    "ТРУДОВОЙ ДОГОВОР": "Трудовой договор",
    "ЛИЦЕНЗИОННЫЙ ДОГОВОР": "Лицензионный договор",
    "АГЕНТСКИЙ ДОГОВОР": "Агентский договор",
    "МИРОВОЕ СОГЛАШЕНИЕ": "Мировое соглашение",
    "ДОПОЛНИТЕЛЬНОЕ СОГЛАШЕНИЕ": "Дополнительное соглашение",
    "СОГЛАШЕНИЕ О КОНФИДЕНЦИАЛЬНОСТИ": "Соглашение о конфиденциальности",
    "СОГЛАШЕНИЕ О РАСТОРЖЕНИИ": "Соглашение о расторжении",
    "СОГЛАШЕНИЕ О ЗАЧЁТЕ": "Соглашение о зачёте встречных требований",
    "АКТ ВЫПОЛНЕННЫХ РАБОТ": "Акт выполненных работ",
    "АКТ ПРИЁМА-ПЕРЕДАЧИ": "Акт приема-передачи",
    "АКТ ПРИЕМА-ПЕРЕДАЧИ": "Акт приема-передачи",
    "АКТ СВЕРКИ": "Акт сверки",
    "СЧЁТ НА ОПЛАТУ": "Счёт на оплату",
    "СЧЕТ НА ОПЛАТУ": "Счёт на оплату",
    "СЧЁТ-ФАКТУРА": "Счёт на оплату",
    "КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ": "Коммерческое предложение",
    "ДОВЕРЕННОСТЬ": "Доверенность",
    "РАСПИСКА": "Расписка",
    "ПРЕТЕНЗИЯ": "Претензия",
    "ПРИКАЗ": "Приказ",
    "ПРОТОКОЛ РАЗНОГЛАСИЙ": "Протокол разногласий",
    "ПРОТОКОЛ ОБЩЕГО СОБРАНИЯ": "Протокол общего собрания",
    "ГАРАНТИЙНОЕ ПИСЬМО": "Гарантийное письмо",
    "ИСКОВОЕ ЗАЯВЛЕНИЕ": "Исковое заявление",
    "УВЕДОМЛЕНИЕ О РАСТОРЖЕНИИ": "Уведомление о расторжении",
    "УСТАВ": "Устав",
    "ОФЕРТА": "Оферта на оказание услуг",
    "СОГЛАСИЕ НА ОБРАБОТКУ": "Согласие на обработку ПД",
    "ПОЛИТИКА ОБРАБОТКИ": "Политика обработки ПД",
    "ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ": "Политика конфиденциальности",
    "ПОЛЬЗОВАТЕЛЬСКОЕ СОГЛАШЕНИЕ": "Пользовательское соглашение",
    "РЕШЕНИЕ ЕДИНСТВЕННОГО УЧАСТНИКА": "Решение единственного участника",
    "РАМОЧНЫЙ ДОГОВОР": "Рамочный договор",
    "ДОГОВОР СУБПОДРЯДА": "Договор субподряда",
    "ДОГОВОР ТРАНСПОРТНОЙ ЭКСПЕДИЦИИ": "Договор транспортной экспедиции",
    "БАНКОВСКАЯ ГАРАНТИЯ": "Банковская гарантия",
}

# Нормализация нестандартных типов
TYPE_NORMALIZE = {
    "Субарендная плата": "Договор субаренды",
    "Акт о согласовании сальдо": "Акт сверки",
    "Спецификация": "Дополнительное соглашение",
    "Справка о должности": "Приказ",
    "Договор уборки офисного помещения": "Договор оказания услуг",
    "Договор оказания юридических услуг": "Договор оказания услуг",
}


def fix_document_type(parsed: dict, title: str | None) -> dict:
    """Исправить document_type через заголовок и нормализацию."""
    dt = parsed.get("document_type", "")

    # 1. Нормализация нестандартных типов
    if dt in TYPE_NORMALIZE:
        parsed["document_type"] = TYPE_NORMALIZE[dt]
        return parsed

    # 2. Если модель дефолтнула на "Договор поставки", а заголовок говорит иное
    if title and dt == "Договор поставки":
        title_upper = title.upper()
        for pattern, correct_type in TITLE_TO_TYPE.items():
            if pattern in title_upper and correct_type != "Договор поставки":
                parsed["document_type"] = correct_type
                return parsed

    # 3. Если document_type пустой — попробовать из заголовка
    if not dt or len(dt) < 3:
        if title:
            title_upper = title.upper()
            for pattern, correct_type in TITLE_TO_TYPE.items():
                if pattern in title_upper:
                    parsed["document_type"] = correct_type
                    return parsed

    return parsed


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
        {"role": "user", "content": USER_PROMPT_TEMPLATE.format(text=text[:10000])},
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
            raw_text = f.read_text(encoding="utf-8")
            text = clean_text(raw_text)  # Улучшение 7: очистка OCR
            title = extract_title(text)  # Улучшение 1: заголовок
            print(f"  [{i:2d}/{len(files)}] {f.name[:40]:<40s}", end=" ", flush=True)

            parsed, elapsed = query_model(text)

            # Улучшение 5: retry при краше с урезанным текстом
            if parsed is None and len(text) > 5000:
                parsed, elapsed2 = query_model(text[:5000])
                elapsed += elapsed2

            if parsed is None:
                print(f"  {elapsed:5.1f}с  ❌ CRASH")
                results.append({
                    "file": f.name,
                    "time": round(elapsed, 1),
                    "issues": ["CRASH"],
                    "response": None,
                })
                continue

            # Улучшения 2+6: fuzzy matching + нормализация
            parsed = fix_document_type(parsed, title)

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
