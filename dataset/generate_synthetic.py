"""
Генерация синтетических обучающих примеров через локальную 7B (Ollama).

Для каждого целевого типа документа:
1. Просит 7B сгенерировать реалистичный документ
2. Просит 7B извлечь метаданные + написать CoT-рассуждение
3. Сохраняет в формат SFT для обучения 1.5B

Запуск:
    python3 dataset/generate_synthetic.py

Требования:
    pip install openai
    Ollama запущена: ollama serve
    Модель загружена: ollama list (должна быть yurteg или qwen2.5:7b)

Результат:
    dataset/synthetic_sft.jsonl — новые примеры в формате SFT
"""

import json
import os
import time
import random
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from openai import OpenAI
from tqdm import tqdm

# ─── Настройки ───────────────────────────────────────────────────────────────

# ZAI (GLM-4.7) — быстрый облачный вариант
GLM_MODEL = "glm-4.7"
GLM_BASE_URL = "https://api.z.ai/api/coding/paas/v4"
GLM_API_KEY = os.environ.get("ZAI_API_KEY") or os.environ.get("ZHIPU_API_KEY", "")

EXAMPLES_PER_TYPE = 15   # сколько примеров на каждый тип
OUTPUT_FILE = Path(__file__).parent / "synthetic_sft.jsonl"
MAX_WORKERS = 1          # параллельных запросов к GLM

# Синонимы: если GLM возвращает другое название — принимаем и корректируем
TYPE_SYNONYMS = {
    "Договор эскроу": "Эскроу-договор",
    "Эскроу договор": "Эскроу-договор",
    "Договор о вестинге": "Договор вестинга",
    "Договор ДДУ": "Договор долевого участия в строительстве",
    "Договор участия в долевом строительстве": "Договор долевого участия в строительстве",
    "Политика в отношении обработки персональных данных": "Политика обработки ПД",
    "Политика конфиденциальности": "Политика обработки ПД",
    "Оферта": "Оферта на оказание услуг",
}

# Типы которых критически мало (1-3 примера в датасете)
TARGET_TYPES_CRITICAL = [
    "Кредитный договор",
    "Эскроу-договор",
    "Договор вестинга",
    "Договор факторинга",
    "Договор долевого участия в строительстве",
    "Банковская гарантия",
    "Карточка контрагента",
    "Договор контрактации",
    "Апелляционная жалоба",
    "Мировое соглашение",
    "Политика обработки ПД",
    "Пользовательское соглашение",
    "Правила акции",
    "Оферта на оказание услуг",
]

# Типы которых мало (4-7 примеров) — генерируем меньше
TARGET_TYPES_LOW = [
    "Соглашение о конфиденциальности",
    "Лицензионный договор",
    "Договор дарения",
    "Рамочный договор",
    "Договор субаренды",
    "Доверенность",
    "Договор безвозмездного пользования",
]

# Реалистичные российские компании и ФИО для генерации
COMPANIES = [
    "ООО «Ромашка»", "ООО «Альфа-Строй»", "ООО «ТехноГрупп»",
    "АО «Северсталь»", "ООО «Медиасервис»", "ПАО «РосТех»",
    "ООО «Логистик Про»", "ООО «СтройКомплект»", "АО «ФинансГрупп»",
    "ООО «Диджитал Солюшнс»", "ООО «АгроТрейд»", "ООО «МеталлТорг»",
]

INDIVIDUALS = [
    "ИП Петров Алексей Сергеевич", "ИП Сидорова Наталья Владимировна",
    "ИП Козлов Дмитрий Андреевич", "ИП Новикова Елена Михайловна",
    "ИП Морозов Игорь Николаевич", "ИП Волкова Анна Юрьевна",
]

CITIES = ["г. Москва", "г. Санкт-Петербург", "г. Екатеринбург", "г. Новосибирск", "г. Казань"]

# ─── Промпты ─────────────────────────────────────────────────────────────────

GENERATION_SYSTEM = """Ты — опытный юрист, составляющий юридические документы.
Генерируй реалистичные российские юридические документы с конкретными данными.
Документы должны быть полными, профессиональными, на русском языке."""

GENERATION_USER = """Составь реалистичный юридический документ типа "{doc_type}".

Используй эти данные:
- Сторона 1: {party1}
- Сторона 2: {party2}
- Город: {city}
- Год: {year}
- Сумма (если применимо): {amount}

Требования:
- Полный текст документа с номером, датой, реквизитами сторон
- 3-7 разделов с конкретными условиями
- Реалистичные суммы, сроки, условия
- Только текст документа, без пояснений

Документ:"""

# Специальный промпт для карточки контрагента
GENERATION_USER_KARTOCHKA = """Составь реалистичную Карточку контрагента.

ВАЖНО: Карточка контрагента — это НЕ договор. Это анкета-справочник с реквизитами одной организации.
Карточка содержит: наименование, ИНН, КПП, ОГРН, юридический/фактический адрес, банковские реквизиты (р/с, к/с, БИК, банк), контактные данные, ФИО руководителя.
Никаких "сторон", "предметов договора", "обязательств" — только реквизиты одного контрагента.

Контрагент: {party1}
Город: {city}
Год: {year}

Требования к реквизитам:
- ИНН юрлица (ООО/АО/ПАО): ровно 10 цифр (например: 7728123456)
- ИНН ИП: ровно 12 цифр (например: 772812345678)
- КПП: ровно 9 цифр, только у юрлиц, у ИП не указывается (например: 772801001)
- ОГРН юрлица: ровно 13 цифр, начинается с 1 (например: 1027700123456)
- ОГРНИП (для ИП): ровно 15 цифр, начинается с 3 (например: 318774600000123)
- Расчётный счёт: 20 цифр, начинается с 407 или 408 (например: 40702810500000012345)
- БИК: ровно 9 цифр (например: 044525225)
- Корр. счёт: 20 цифр, начинается с 301 (например: 30101810200000000593)

Оформи в виде структурированной таблицы или нумерованных разделов. Только текст карточки, без пояснений.

Карточка контрагента:"""

EXTRACTION_SYSTEM = """Ты — опытный юрист-аналитик. Извлеки структурированные метаданные из юридического документа.

ПРАВИЛА:
1. Отвечай в формате: сначала РАССУЖДЕНИЕ, потом JSON.
2. РАССУЖДЕНИЕ: 2-3 предложения почему ты определил именно этот тип и контрагента.
3. JSON: строго после строки "МЕТАДАННЫЕ:"
4. Отсутствующую информацию ставь null.
5. Даты строго YYYY-MM-DD.
6. Сумму с пробелами и валютой: "1 500 000 руб."
7. parties — массив строк, special_conditions — массив строк."""

EXTRACTION_USER = """Извлеки метаданные из текста юридического документа.

Верни в формате:
РАССУЖДЕНИЕ: [2-3 предложения: почему этот тип, кто контрагент, что является предметом]
МЕТАДАННЫЕ:
{{"document_type": "...", "counterparty": "...", "subject": "...", "date_signed": "...", "date_start": "...", "date_end": "...", "amount": "...", "special_conditions": [...], "parties": [...], "confidence": 0.0, "is_template": false}}

Текст документа:
{text}"""

# ─── Системный промпт для обучения 1.5B (без CoT — финальная версия) ────────

TRAINING_SYSTEM = """Ты — опытный юрист-аналитик. Извлеки структурированные метаданные из юридического документа.

ПРАВИЛА:
1. Отвечай СТРОГО чистым JSON. Без текста до/после, без обёрток ```json```.
2. Отсутствующую информацию ставь null (не пустую строку "").
3. Списки всегда массивы: parties=[], special_conditions=[].
4. confidence — число от 0.0 до 1.0.
5. Сумму пиши с пробелами-разделителями и валютой: "1 500 000 руб.".
6. Даты строго YYYY-MM-DD.
7. ФИО в именительном падеже: "Иванов Иван Иванович".
8. Формат ИП: "ИП Фамилия Имя Отчество"."""

TRAINING_USER = """Извлеки метаданные из текста юридического документа.

Верни JSON с полями: document_type, counterparty, subject, date_signed, date_start, date_end, amount, special_conditions, parties, confidence, is_template

Текст документа:
{text}"""

# ─── Основная логика ─────────────────────────────────────────────────────────

def make_client():
    if not GLM_API_KEY:
        raise ValueError("Не найден API-ключ ZAI. Установи переменную окружения ZAI_API_KEY или ZHIPU_API_KEY")
    return OpenAI(base_url=GLM_BASE_URL, api_key=GLM_API_KEY, timeout=60.0)


def generate_document(client, doc_type: str) -> str | None:
    """Генерирует текст документа через 7B."""
    party1 = random.choice(COMPANIES + INDIVIDUALS)
    party2 = random.choice(COMPANIES + INDIVIDUALS)
    while party2 == party1:
        party2 = random.choice(COMPANIES + INDIVIDUALS)

    amounts = ["500 000 руб.", "1 200 000 руб.", "250 000 руб.", "3 500 000 руб.", "75 000 руб."]

    if doc_type == "Карточка контрагента":
        prompt = GENERATION_USER_KARTOCHKA.format(
            party1=party1,
            city=random.choice(CITIES),
            year=random.choice([2023, 2024, 2025]),
        )
    else:
        prompt = GENERATION_USER.format(
            doc_type=doc_type,
            party1=party1,
            party2=party2,
            city=random.choice(CITIES),
            year=random.choice([2023, 2024, 2025]),
            amount=random.choice(amounts),
        )

    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=GLM_MODEL,
                messages=[
                    {"role": "system", "content": GENERATION_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=2000,
                extra_body={"thinking": {"type": "disabled"}},
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                time.sleep(10 * (attempt + 1))
                continue
            print(f"  Ошибка генерации: {e}")
            return None


def extract_with_cot(client, text: str) -> tuple[str, dict] | None:
    """Извлекает метаданные с CoT-рассуждением. Возвращает (reasoning, metadata)."""
    prompt = EXTRACTION_USER.format(text=text[:4000])

    try:
        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model=GLM_MODEL,
                    messages=[
                        {"role": "system", "content": EXTRACTION_SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0,
                    max_tokens=1000,
                    extra_body={"thinking": {"type": "disabled"}},
                )
                break
            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    time.sleep(10 * (attempt + 1))
                    continue
                raise
        content = resp.choices[0].message.content.strip()

        # Разбираем ответ: РАССУЖДЕНИЕ + МЕТАДАННЫЕ
        reasoning = ""
        metadata = {}

        if "РАССУЖДЕНИЕ:" in content and "МЕТАДАННЫЕ:" in content:
            parts = content.split("МЕТАДАННЫЕ:")
            reasoning = parts[0].replace("РАССУЖДЕНИЕ:", "").strip()
            json_part = parts[1].strip()
        elif "МЕТАДАННЫЕ:" in content:
            json_part = content.split("МЕТАДАННЫЕ:")[1].strip()
        else:
            json_part = content

        # Чистим JSON
        json_part = json_part.strip()
        if json_part.startswith("```"):
            json_part = json_part.split("```")[1]
            if json_part.startswith("json"):
                json_part = json_part[4:]
        json_part = json_part.strip()

        metadata = json.loads(json_part)
        return reasoning, metadata

    except Exception as e:
        print(f"  Ошибка извлечения: {e}")
        print(f"  DEBUG raw content: {repr(content[:500]) if 'content' in dir() else 'нет ответа'}")
        return None


def make_sft_example(doc_text: str, metadata: dict) -> dict:
    """Формирует пример для SFT-обучения в формате messages."""
    user_content = TRAINING_USER.format(text=doc_text[:6000])
    assistant_content = json.dumps(metadata, ensure_ascii=False)

    return {
        "messages": [
            {"role": "system", "content": TRAINING_SYSTEM},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ]
    }


def make_doc_id(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:16]


def process_one(client, doc_type: str) -> tuple[str, dict, str] | None:
    """Генерирует один документ и извлекает метаданные. Возвращает (doc_text, metadata, reasoning) или None."""
    doc_text = generate_document(client, doc_type)
    if not doc_text or len(doc_text) < 200:
        return None

    result = extract_with_cot(client, doc_text)
    if result is None:
        return None

    reasoning, metadata = result
    extracted_type = metadata.get("document_type", "")
    normalized_type = TYPE_SYNONYMS.get(extracted_type, extracted_type)
    if normalized_type != doc_type:
        return None
    metadata["document_type"] = doc_type
    return doc_text, metadata, reasoning


def main():
    client = make_client()

    # Проверяем подключение
    try:
        client.models.list()
        print(f"ZAI подключён, модель: {GLM_MODEL}, воркеров: {MAX_WORKERS}\n")
    except Exception as e:
        print(f"Ошибка подключения к ZAI: {e}")
        print("Проверь API-ключ в переменной окружения ZAI_API_KEY")
        return

    # Добираем только то, чего не хватает после первого запуска
    targets = [
        # Пропущены полностью (0 записей)
        ("Эскроу-договор", 15),
        ("Политика обработки ПД", 15),
        ("Правила акции", 15),
        # Мало
        ("Оферта на оказание услуг", 12),   # было 3, нужно ещё 12
        ("Рамочный договор", 7),             # было 3, нужно ещё 7
        ("Договор дарения", 6),              # было 4, нужно ещё 6
        ("Договор безвозмездного пользования", 8),  # было 2, нужно ещё 8
        # Карточки контрагента — удалили 5 плохих, нужно добрать
        ("Карточка контрагента", 5),
    ]

    total_generated = 0
    total_failed = 0
    write_lock = threading.Lock()

    with open(OUTPUT_FILE, "a", encoding="utf-8") as f_out:
        for doc_type, count in targets:
            print(f"\n{'─'*50}")
            print(f"Тип: {doc_type} (нужно {count} примеров)")
            type_count = 0

            with tqdm(total=count, desc=doc_type[:35], unit="doc") as pbar:
                while type_count < count:
                    result = process_one(client, doc_type)
                    if result is None:
                        total_failed += 1
                        continue
                    doc_text, metadata, reasoning = result
                    example = make_sft_example(doc_text, metadata)
                    record = {
                        "id": make_doc_id(doc_text),
                        "source": "synthetic",
                        "doc_type": doc_type,
                        "cot_reasoning": reasoning,
                        "generated_at": datetime.now().isoformat(),
                        **example,
                    }
                    f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
                    f_out.flush()
                    type_count += 1
                    total_generated += 1
                    pbar.update(1)

            print(f"  Итого для '{doc_type}': {type_count}/{count}")

    print(f"\n{'='*50}")
    print(f"Готово!")
    print(f"  Сгенерировано: {total_generated}")
    print(f"  Ошибок/пропущено: {total_failed}")
    print(f"  Файл: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
