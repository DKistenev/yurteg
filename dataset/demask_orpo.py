#!/usr/bin/env python3
"""
Убирает маски анонимизации из ORPO-датасета.
Заменяет [ФИО_1], [ТЕЛЕФОН_1] и т.д. на реалистичные русские данные.
"""

import json
import re
import random
import copy
from pathlib import Path

# ─────────────── Данные для замены ───────────────

LAST_NAMES = [
    "Иванов", "Петров", "Сидоров", "Смирнов", "Кузнецов",
    "Попов", "Лебедев", "Новиков", "Морозов", "Козлов",
    "Соколов", "Волков", "Зайцев", "Орлов", "Павлов",
    "Семёнов", "Голубев", "Виноградов", "Богданов", "Воробьёв",
    "Фёдоров", "Михайлов", "Беляев", "Тарасов", "Белов",
    "Комаров", "Киселёв", "Александров", "Макаров", "Андреев",
    "Никитин", "Захаров", "Соловьёв", "Степанов", "Яковлев",
    "Гусев", "Королёв", "Антонов", "Алексеев", "Романов",
    "Медведев", "Громов", "Мельников", "Жуков", "Тихонов",
    "Зуев", "Власов", "Щербаков", "Ершов", "Панов",
]

LAST_NAMES_F = [
    "Иванова", "Петрова", "Сидорова", "Смирнова", "Кузнецова",
    "Попова", "Лебедева", "Новикова", "Морозова", "Козлова",
    "Соколова", "Волкова", "Зайцева", "Орлова", "Павлова",
    "Семёнова", "Голубева", "Виноградова", "Богданова", "Воробьёва",
    "Фёдорова", "Михайлова", "Беляева", "Тарасова", "Белова",
    "Комарова", "Киселёва", "Александрова", "Макарова", "Андреева",
]

FIRST_NAMES_M = [
    "Александр", "Михаил", "Дмитрий", "Иван", "Сергей",
    "Андрей", "Алексей", "Артём", "Максим", "Николай",
    "Владимир", "Евгений", "Денис", "Роман", "Кирилл",
    "Антон", "Игорь", "Павел", "Олег", "Виктор",
]

FIRST_NAMES_F = [
    "Анна", "Мария", "Елена", "Ольга", "Наталья",
    "Светлана", "Татьяна", "Юлия", "Екатерина", "Ирина",
    "Людмила", "Надежда", "Оксана", "Алина", "Марина",
    "Вера", "Валентина", "Галина", "Тамара", "Зоя",
]

PATRONYMICS_M = [
    "Александрович", "Михайлович", "Дмитриевич", "Иванович", "Сергеевич",
    "Андреевич", "Алексеевич", "Артёмович", "Максимович", "Николаевич",
    "Владимирович", "Евгеньевич", "Денисович", "Романович", "Кириллович",
    "Антонович", "Игоревич", "Павлович", "Олегович", "Викторович",
]

PATRONYMICS_F = [
    "Александровна", "Михайловна", "Дмитриевна", "Ивановна", "Сергеевна",
    "Андреевна", "Алексеевна", "Артёмовна", "Максимовна", "Николаевна",
    "Владимировна", "Евгеньевна", "Денисовна", "Романовна", "Кирилловна",
    "Антоновна", "Игоревна", "Павловна", "Олеговна", "Викторовна",
]

ADDRESSES = [
    "г. Москва, ул. Тверская, д. 15, кв. 47",
    "г. Санкт-Петербург, пр. Невский, д. 88, кв. 12",
    "г. Екатеринбург, ул. Малышева, д. 101, кв. 35",
    "г. Новосибирск, ул. Красный проспект, д. 44, кв. 8",
    "г. Казань, ул. Баумана, д. 67, кв. 19",
    "г. Нижний Новгород, ул. Большая Покровская, д. 23, кв. 4",
    "г. Челябинск, ул. Кирова, д. 158, кв. 62",
    "г. Самара, ул. Куйбышева, д. 90, кв. 31",
    "г. Ростов-на-Дону, пр. Буденновский, д. 55, кв. 17",
    "г. Уфа, ул. Ленина, д. 34, кв. 9",
    "г. Красноярск, ул. Мира, д. 78, кв. 56",
    "г. Пермь, ул. Комсомольский проспект, д. 12, кв. 3",
    "г. Воронеж, ул. Плехановская, д. 45, кв. 28",
    "г. Саратов, ул. Московская, д. 118, кв. 41",
    "г. Краснодар, ул. Красная, д. 33, кв. 15",
    "г. Тюмень, ул. Республики, д. 210, кв. 73",
    "г. Тольятти, ул. Победы, д. 65, кв. 22",
    "г. Ижевск, ул. Пушкинская, д. 17, кв. 6",
    "г. Барнаул, пр. Ленина, д. 82, кв. 44",
    "г. Иркутск, ул. Карла Маркса, д. 29, кв. 11",
]

COMPANY_NAMES = [
    "СтройИнвест", "ТехноГрупп", "АльфаТрейд", "МегаСервис", "ПромТехника",
    "ГлобалЛогистик", "РусАктив", "КапиталПарк", "ДельтаТрейд", "ОптимаГрупп",
    "ЛидерТех", "СинтезПро", "АгроКом", "ФинансПартнёр", "БизнесПлюс",
]

# ─────────────── Генераторы ───────────────

def gen_fio() -> tuple[str, str]:
    """Возвращает (ФИО, фамилия) — нужно для email."""
    gender = random.choice(["m", "f"])
    if gender == "m":
        last = random.choice(LAST_NAMES)
        first = random.choice(FIRST_NAMES_M)
        patr = random.choice(PATRONYMICS_M)
    else:
        last = random.choice(LAST_NAMES_F)
        first = random.choice(FIRST_NAMES_F)
        patr = random.choice(PATRONYMICS_F)
    return f"{last} {first} {patr}", last.lower()


def gen_phone() -> str:
    d1 = random.randint(900, 999)
    d2 = random.randint(100, 999)
    d3 = random.randint(10, 99)
    d4 = random.randint(10, 99)
    return f"+7 ({d1}) {d2}-{d3}-{d4}"


def gen_inn_individual() -> str:
    return "".join([str(random.randint(0, 9)) for _ in range(12)])


def gen_inn_company() -> str:
    return "".join([str(random.randint(0, 9)) for _ in range(10)])


def gen_inn() -> str:
    return random.choice([gen_inn_individual, gen_inn_company])()


def gen_ogrn() -> str:
    return "1" + "".join([str(random.randint(0, 9)) for _ in range(12)])


def gen_kpp() -> str:
    return "".join([str(random.randint(0, 9)) for _ in range(9)])


def gen_snils() -> str:
    nums = [str(random.randint(0, 9)) for _ in range(9)]
    s = "".join(nums)
    return f"{s[:3]}-{s[3:6]}-{s[6:9]} 00"


def gen_passport() -> str:
    series = f"{random.randint(10, 99)} {random.randint(10, 99)}"
    number = f"{random.randint(100000, 999999)}"
    return f"серия {series} номер {number}"


def gen_email(last_name: str = "") -> str:
    domains = ["mail.ru", "yandex.ru", "gmail.com", "inbox.ru", "bk.ru"]
    if last_name:
        # транслитерация базовая
        translit = {
            "а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"yo","ж":"zh",
            "з":"z","и":"i","й":"j","к":"k","л":"l","м":"m","н":"n","о":"o",
            "п":"p","р":"r","с":"s","т":"t","у":"u","ф":"f","х":"h","ц":"ts",
            "ч":"ch","ш":"sh","щ":"sch","ъ":"","ы":"y","ь":"","э":"e","ю":"yu","я":"ya",
        }
        name_latin = "".join(translit.get(c, c) for c in last_name.lower())
        suffix = random.randint(10, 99)
        return f"{name_latin}{suffix}@{random.choice(domains)}"
    else:
        words = ["user", "info", "office", "contact", "mail"]
        return f"{random.choice(words)}{random.randint(10,99)}@{random.choice(domains)}"


def gen_address() -> str:
    return random.choice(ADDRESSES)


def gen_date() -> str:
    year = random.randint(2020, 2024)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return f"{day:02d}.{month:02d}.{year}"


def gen_company() -> str:
    return random.choice(COMPANY_NAMES)


# ─────────────── Основная логика ───────────────

MASK_PATTERN = re.compile(r'\[([А-ЯЁа-яё_]+\d*)\]', re.UNICODE)

SYSTEM_MASK_LINE = re.compile(
    r'Маски анонимизации \([^)]+\)[^.\n]*\.\s*\n?'
)


def classify_mask(name: str) -> str:
    """Определяет тип маски по её имени."""
    upper = name.upper()
    if "ФИО" in upper or upper.startswith("ФИ") or upper == "ПРЕДСТАВИТЕЛЬ":
        return "ФИО"
    if "ТЕЛЕФОН" in upper or "ТЕЛ" == upper:
        return "ТЕЛЕФОН"
    if "EMAIL" in upper or "ПОЧТА" in upper or "ИМЕЙЛ" in upper:
        return "EMAIL"
    if upper.startswith("ИНН"):
        return "ИНН"
    if upper.startswith("ОГРН"):
        return "ОГРН"
    if upper.startswith("КПП"):
        return "КПП"
    if upper.startswith("СНИЛС"):
        return "СНИЛС"
    if "АДРЕС" in upper or "АДР" == upper:
        return "АДРЕС"
    if "ПАСПОРТ" in upper:
        return "ПАСПОРТ"
    if "КОМПАНИЯ" in upper or "ОРГАНИЗАЦИЯ" in upper or "НАИМЕНОВАНИЕ" in upper or "ООО" in upper or "АО" in upper:
        return "КОМПАНИЯ"
    if "ДАТА" in upper:
        return "ДАТА"
    return "ПРОЧЕЕ"


def generate_replacement(mask_type: str, context: dict) -> str:
    """Генерирует замену для маски заданного типа."""
    if mask_type == "ФИО":
        fio, last = gen_fio()
        context["last_name"] = last
        return fio
    if mask_type == "ТЕЛЕФОН":
        return gen_phone()
    if mask_type == "EMAIL":
        last = context.get("last_name", "")
        return gen_email(last)
    if mask_type == "ИНН":
        return gen_inn()
    if mask_type == "ОГРН":
        return gen_ogrn()
    if mask_type == "КПП":
        return gen_kpp()
    if mask_type == "СНИЛС":
        return gen_snils()
    if mask_type == "АДРЕС":
        return gen_address()
    if mask_type == "ПАСПОРТ":
        return gen_passport()
    if mask_type == "КОМПАНИЯ":
        return gen_company()
    if mask_type == "ДАТА":
        return gen_date()
    # ПРОЧЕЕ — убираем скобки, оставляем содержимое
    return None  # сигнал — вернуть содержимое как есть


def build_replacements(text: str) -> dict[str, str]:
    """Находит все уникальные маски в тексте и строит словарь замен."""
    masks = set(MASK_PATTERN.findall(text))
    replacements = {}
    context: dict = {}
    for mask_name in sorted(masks):
        mask_type = classify_mask(mask_name)
        replacement = generate_replacement(mask_type, context)
        if replacement is None:
            # ПРОЧЕЕ — убираем скобки
            replacements[f"[{mask_name}]"] = mask_name
        else:
            replacements[f"[{mask_name}]"] = replacement
    return replacements


def apply_replacements(text: str, replacements: dict[str, str]) -> str:
    """Применяет словарь замен к тексту."""
    for mask, value in replacements.items():
        text = text.replace(mask, value)
    return text


def clean_system_prompt(text: str) -> str:
    """Убирает строку про маски анонимизации из system prompt."""
    return SYSTEM_MASK_LINE.sub("", text)


def process_messages(messages: list | None, replacements: dict[str, str], is_system_pass: bool = False) -> list | None:
    if messages is None:
        return None
    result = []
    for msg in messages:
        msg = copy.deepcopy(msg)
        if isinstance(msg.get("content"), str):
            content = msg["content"]
            if is_system_pass and msg.get("role") == "system":
                content = clean_system_prompt(content)
            content = apply_replacements(content, replacements)
            msg["content"] = content
        result.append(msg)
    return result


def collect_all_text(example: dict) -> str:
    """Собирает весь текст примера для поиска масок."""
    parts = []

    def extract(obj):
        if isinstance(obj, str):
            parts.append(obj)
        elif isinstance(obj, list):
            for item in obj:
                extract(item)
        elif isinstance(obj, dict):
            for v in obj.values():
                extract(v)

    extract(example)
    return " ".join(parts)


def process_example(example: dict) -> tuple[dict, int]:
    """Обрабатывает один пример. Возвращает (processed, masks_replaced_count)."""
    all_text = collect_all_text(example)
    replacements = build_replacements(all_text)

    # Считаем только те маски, которые реально заменены (не ПРОЧЕЕ без изменений)
    real_replacements = {k: v for k, v in replacements.items() if k != v}
    count = len(real_replacements)

    if not replacements:
        return example, 0

    result = copy.deepcopy(example)

    # prompt — список сообщений
    if "prompt" in result:
        result["prompt"] = process_messages(result["prompt"], replacements, is_system_pass=True)

    # chosen — список сообщений
    if "chosen" in result and result["chosen"] is not None:
        result["chosen"] = process_messages(result["chosen"], replacements)

    # rejected — список сообщений
    if "rejected" in result and result["rejected"] is not None:
        result["rejected"] = process_messages(result["rejected"], replacements)

    return result, count


def process_file(input_path: Path, output_path: Path) -> dict:
    """Обрабатывает JSONL-файл. Возвращает статистику."""
    stats = {
        "total_examples": 0,
        "examples_with_masks": 0,
        "total_masks_replaced": 0,
        "mask_types_found": {},
    }

    lines = input_path.read_text(encoding="utf-8").splitlines()
    output_lines = []

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        stats["total_examples"] += 1

        try:
            example = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"  [ОШИБКА] строка {i+1}: {e}")
            output_lines.append(line)
            continue

        # Проверяем наличие масок
        all_text = collect_all_text(example)
        found_masks = MASK_PATTERN.findall(all_text)

        if found_masks:
            stats["examples_with_masks"] += 1
            for m in found_masks:
                mask_type = classify_mask(m)
                stats["mask_types_found"][mask_type] = stats["mask_types_found"].get(mask_type, 0) + 1

        processed, count = process_example(example)
        stats["total_masks_replaced"] += count
        output_lines.append(json.dumps(processed, ensure_ascii=False))

    output_path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
    return stats


# ─────────────── Запуск ───────────────

if __name__ == "__main__":
    random.seed(42)  # воспроизводимость

    files = [
        Path("/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/dataset/training/v3_orpo_train.jsonl"),
        Path("/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/dataset/training/v3_orpo_val.jsonl"),
    ]

    for input_path in files:
        if not input_path.exists():
            print(f"[!] Файл не найден: {input_path}")
            continue

        output_path = input_path  # перезаписываем на месте

        print(f"\n{'='*60}")
        print(f"Файл: {input_path.name}")
        print(f"{'='*60}")

        stats = process_file(input_path, output_path)

        print(f"  Всего примеров:           {stats['total_examples']}")
        print(f"  Примеров с масками:       {stats['examples_with_masks']}")
        print(f"  Масок заменено (итого):   {stats['total_masks_replaced']}")

        if stats["mask_types_found"]:
            print(f"  Типы масок:")
            for mtype, cnt in sorted(stats["mask_types_found"].items(), key=lambda x: -x[1]):
                print(f"    {mtype:<20} {cnt}")
        else:
            print("  Маски не найдены.")

    print(f"\n{'='*60}")
    print("Готово. Файлы перезаписаны.")
