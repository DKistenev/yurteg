"""
Датасет v2: генерация DPO-пар и edge cases.

75 DPO-пар по 5 категориям:
1. Невалидный JSON (15)
2. Кривые даты (15)
3. Пустые массивы (15)
4. Краткий subject (15)
5. Ошибки ФИО/падежей (15)

+ Edge cases для train:
- 15 negative examples (не-юридические тексты)
- 10 нестандартных типов документов
"""

import json
import random
import re
from pathlib import Path

random.seed(42)

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


def make_tool_call(args: dict) -> str:
    tc = {"name": "extract_metadata", "arguments": args}
    return f'<tool_call>\n{json.dumps(tc, ensure_ascii=False)}\n</tool_call>'


def load_train():
    with open("dataset/training/v2_train.jsonl") as f:
        return [json.loads(line) for line in f]


def parse_tool_call(content: str) -> dict:
    clean = content.replace("<tool_call>\n", "").replace("\n</tool_call>", "")
    return json.loads(clean)


def make_dpo_pair(system_msg, user_msg, chosen_content, rejected_content):
    return {
        "prompt": [system_msg, user_msg],
        "chosen": [{"role": "assistant", "content": chosen_content}],
        "rejected": [{"role": "assistant", "content": rejected_content}],
    }


def generate_invalid_json_pairs(examples, n=15):
    """Категория 1: невалидный JSON."""
    pairs = []
    selected = random.sample(examples, min(n, len(examples)))

    corruptions = [
        lambda s: s.replace('"document_type"', "document_type"),  # unquoted key
        lambda s: s.replace('": "', "': '"),  # single quotes
        lambda s: s + ",}",  # trailing comma
        lambda s: s.replace("null", "None"),  # Python None
        lambda s: "```json\n" + s + "\n```",  # markdown wrapper
        lambda s: "Вот результат:\n" + s,  # text before JSON
        lambda s: s[:-1],  # missing closing brace
        lambda s: re.sub(r'"(\d[\d ]*)\s*руб\."', r'\1 руб.', s),  # unquoted amount
    ]

    for i, ex in enumerate(selected):
        system_msg = ex["messages"][0]
        user_msg = ex["messages"][1]
        chosen = ex["messages"][2]["content"]

        # Parse and get raw JSON for corruption
        tc = parse_tool_call(chosen)
        raw_json = json.dumps(tc["arguments"], ensure_ascii=False)

        # Apply random corruption
        corruption = corruptions[i % len(corruptions)]
        corrupted = corruption(raw_json)

        # Rejected: plain text (no tool_call tags) with corrupted JSON
        pairs.append(make_dpo_pair(system_msg, user_msg, chosen, corrupted))

    return pairs


def generate_bad_dates_pairs(examples, n=15):
    """Категория 2: кривые даты."""
    pairs = []
    # Filter examples with dates
    with_dates = [ex for ex in examples if '"date_signed"' in ex["messages"][2]["content"]
                  and '"2' in ex["messages"][2]["content"]]
    selected = random.sample(with_dates, min(n, len(with_dates)))

    for ex in selected:
        system_msg = ex["messages"][0]
        user_msg = ex["messages"][1]
        chosen = ex["messages"][2]["content"]

        tc = parse_tool_call(chosen)
        args = tc["arguments"].copy()

        # Corrupt dates
        for field in ["date_signed", "date_start", "date_end"]:
            if args.get(field) and re.match(r"\d{4}-\d{2}-\d{2}", str(args[field])):
                y, m, d = args[field].split("-")
                # Random corruption
                corruption_type = random.choice(["ddmmyyyy", "russian", "swap", "year_only"])
                if corruption_type == "ddmmyyyy":
                    args[field] = f"{d}.{m}.{y}"
                elif corruption_type == "russian":
                    months = ["января", "февраля", "марта", "апреля", "мая", "июня",
                              "июля", "августа", "сентября", "октября", "ноября", "декабря"]
                    args[field] = f"{int(d)} {months[int(m)-1]} {y}"
                elif corruption_type == "swap":
                    # Swap signed and start
                    if field == "date_signed" and args.get("date_start"):
                        args["date_signed"], args["date_start"] = args["date_start"], args["date_signed"]
                elif corruption_type == "year_only":
                    args[field] = y

        rejected_tc = {"name": "extract_metadata", "arguments": args}
        rejected = f'<tool_call>\n{json.dumps(rejected_tc, ensure_ascii=False)}\n</tool_call>'
        pairs.append(make_dpo_pair(system_msg, user_msg, chosen, rejected))

    return pairs


def generate_empty_arrays_pairs(examples, n=15):
    """Категория 3: пустые массивы когда данные есть."""
    pairs = []
    # Filter examples with filled arrays
    with_arrays = []
    for ex in examples:
        tc = parse_tool_call(ex["messages"][2]["content"])
        args = tc["arguments"]
        if (args.get("special_conditions") and len(args["special_conditions"]) > 0 and
                args.get("parties") and len(args["parties"]) > 0):
            with_arrays.append(ex)

    selected = random.sample(with_arrays, min(n, len(with_arrays)))

    for ex in selected:
        system_msg = ex["messages"][0]
        user_msg = ex["messages"][1]
        chosen = ex["messages"][2]["content"]

        tc = parse_tool_call(chosen)
        args = tc["arguments"].copy()

        # Empty out arrays
        corruption = random.choice(["both", "conditions", "parties"])
        if corruption in ("both", "conditions"):
            args["special_conditions"] = []
        if corruption in ("both", "parties"):
            args["parties"] = []

        rejected_tc = {"name": "extract_metadata", "arguments": args}
        rejected = f'<tool_call>\n{json.dumps(rejected_tc, ensure_ascii=False)}\n</tool_call>'
        pairs.append(make_dpo_pair(system_msg, user_msg, chosen, rejected))

    return pairs


def generate_short_subject_pairs(examples, n=15):
    """Категория 4: краткий subject."""
    pairs = []
    # Filter examples with long subjects
    with_subject = [ex for ex in examples
                    if len(parse_tool_call(ex["messages"][2]["content"])["arguments"].get("subject", "")) > 30]
    selected = random.sample(with_subject, min(n, len(with_subject)))

    short_subjects = {
        "Договор": "Оказание услуг",
        "Кредит": "Выдача кредита",
        "Поставка": "Поставка товара",
        "Аренда": "Аренда помещения",
        "Подряд": "Выполнение работ",
        "Купля": "Купля-продажа",
        "Лицензи": "Предоставление лицензии",
        "Страхов": "Страхование",
        "Факторинг": "Факторинг",
        "Займ": "Предоставление займа",
    }

    for ex in selected:
        system_msg = ex["messages"][0]
        user_msg = ex["messages"][1]
        chosen = ex["messages"][2]["content"]

        tc = parse_tool_call(chosen)
        args = tc["arguments"].copy()

        # Shorten subject
        original = args["subject"]
        short = "Документ"
        for key, val in short_subjects.items():
            if key.lower() in original.lower():
                short = val
                break
        args["subject"] = short

        rejected_tc = {"name": "extract_metadata", "arguments": args}
        rejected = f'<tool_call>\n{json.dumps(rejected_tc, ensure_ascii=False)}\n</tool_call>'
        pairs.append(make_dpo_pair(system_msg, user_msg, chosen, rejected))

    return pairs


def generate_fio_errors_pairs(examples, n=15):
    """Категория 5: ошибки ФИО/падежей."""
    pairs = []
    # Filter examples with ФИО in parties
    fio_pattern = re.compile(r'[А-ЯЁ][а-яё]+\s[А-ЯЁ][а-яё]+\s[А-ЯЁ][а-яё]+')
    with_fio = [ex for ex in examples
                if fio_pattern.search(str(parse_tool_call(ex["messages"][2]["content"])["arguments"].get("parties", [])))]
    selected = random.sample(with_fio, min(n, len(with_fio)))

    def corrupt_fio(name: str) -> str:
        """Перевести ФИО в родительный падеж (упрощённо)."""
        parts = name.split()
        if len(parts) >= 3:
            # Упрощённое склонение
            if parts[0].endswith("ов") or parts[0].endswith("ев"):
                parts[0] = parts[0] + "а"
            elif parts[0].endswith("а"):
                parts[0] = parts[0][:-1] + "ой"
            elif parts[0].endswith("ая"):
                parts[0] = parts[0][:-2] + "ой"
            # Имя
            if len(parts) > 1:
                if parts[1].endswith("й"):
                    parts[1] = parts[1][:-1] + "я"
                elif parts[1].endswith("а"):
                    parts[1] = parts[1][:-1] + "ы"
            # Отчество
            if len(parts) > 2:
                if parts[2].endswith("ич"):
                    parts[2] = parts[2] + "а"
                elif parts[2].endswith("на"):
                    parts[2] = parts[2][:-1] + "ы"
        return " ".join(parts)

    for ex in selected:
        system_msg = ex["messages"][0]
        user_msg = ex["messages"][1]
        chosen = ex["messages"][2]["content"]

        tc = parse_tool_call(chosen)
        args = tc["arguments"].copy()

        # Corrupt ФИО in parties
        if args.get("parties"):
            new_parties = []
            for p in args["parties"]:
                if fio_pattern.search(p):
                    new_parties.append(corrupt_fio(p))
                else:
                    new_parties.append(p)
            args["parties"] = new_parties

        # Also corrupt counterparty if it's a person
        if args.get("counterparty") and fio_pattern.search(args["counterparty"]):
            args["counterparty"] = corrupt_fio(args["counterparty"])

        rejected_tc = {"name": "extract_metadata", "arguments": args}
        rejected = f'<tool_call>\n{json.dumps(rejected_tc, ensure_ascii=False)}\n</tool_call>'
        pairs.append(make_dpo_pair(system_msg, user_msg, chosen, rejected))

    return pairs


def generate_edge_cases():
    """Генерация edge case примеров для train."""
    edge_cases = []

    # Negative examples — не-юридические тексты
    non_legal_texts = [
        "Рецепт борща\n\nИнгредиенты: свёкла, картофель, капуста, морковь, лук.\nПорезать овощи, варить 40 минут. Подавать со сметаной.",
        "Прогноз погоды на завтра\n\nМосква: облачно, +15°C, ветер юго-западный 5 м/с. Осадки не ожидаются.",
        "Список покупок:\n- Молоко 2 литра\n- Хлеб белый\n- Яйца 10 шт\n- Масло сливочное\n- Сыр 300г",
        "Дорогая Мария Ивановна!\n\nПоздравляю Вас с днём рождения! Желаю здоровья, счастья и благополучия.\n\nС уважением, Пётр",
        "МЕНЮ РЕСТОРАНА «ОГОНЁК»\n\nСалат Цезарь — 450 руб.\nБорщ — 350 руб.\nСтейк рибай — 1 800 руб.\nТирамису — 550 руб.",
        "Инструкция по эксплуатации стиральной машины\n\n1. Загрузите бельё\n2. Добавьте порошок\n3. Выберите программу\n4. Нажмите Старт",
        "Расписание электричек Москва — Тверь\n\n06:15 — все остановки\n07:30 — экспресс\n08:45 — все остановки\n10:00 — экспресс",
        "Описание вакансии\n\nМенеджер по продажам\nЗарплата: от 80 000 руб.\nОпыт: от 2 лет\nГрафик: 5/2",
        "Отзыв о товаре\n\nКупил этот пылесос месяц назад. Работает отлично, тихий, мощный. Рекомендую! 5/5 звёзд.",
        "Новости спорта\n\nСборная России по футболу одержала победу со счётом 3:1 в матче отборочного турнира.",
        "Статья в блоге\n\n10 способов сэкономить на коммунальных услугах\n\n1. Установите счётчики воды\n2. Используйте LED-лампы...",
        "Техническое задание на разработку сайта\n\nСтраницы: главная, о нас, услуги, контакты.\nCMS: WordPress\nСрок: 2 недели",
        "SMS-уведомление\n\nВаш заказ №12345 отправлен. Ожидаемая дата доставки: 25.03.2026. Трек-номер: RU123456789",
        "Конспект лекции по физике\n\nЗакон Ньютона: F = ma\nСила равна произведению массы на ускорение.",
        "Пост в социальной сети\n\nСегодня прекрасный день! Гуляли в парке, пили кофе. #москва #весна #настроение",
    ]

    null_args = {
        "document_type": "Нераспознанный документ",
        "counterparty": None,
        "subject": "Документ не является юридическим",
        "date_signed": None, "date_start": None, "date_end": None,
        "amount": None,
        "special_conditions": [], "parties": [],
        "is_template": False,
        "payment_terms": None, "payment_amount": None,
        "payment_frequency": None, "payment_direction": None,
    }

    for text in non_legal_texts:
        edge_cases.append({
            "messages": [
                {"role": "system", "content": NEW_SYSTEM_PROMPT},
                {"role": "user", "content": f"Извлеки метаданные из текста юридического документа.\n\nТекст документа:\n{text}"},
                {"role": "assistant", "content": make_tool_call(null_args)},
            ]
        })

    # Нестандартные типы документов
    unusual_docs = [
        {
            "text": "ПРОТОКОЛ РАЗНОГЛАСИЙ\nк Договору поставки № 45 от 10.01.2025\n\nООО «ТехноПром» предлагает изменить п. 3.2: срок поставки 30 дней вместо 14.",
            "args": {"document_type": "Протокол разногласий", "counterparty": 'ООО «ТехноПром»', "subject": "Разногласия к договору поставки № 45 по срокам поставки", "date_signed": None, "date_start": None, "date_end": None, "amount": None, "special_conditions": ["Предложение изменить срок поставки с 14 до 30 дней"], "parties": ['ООО «ТехноПром»'], "is_template": False, "payment_terms": None, "payment_amount": None, "payment_frequency": None, "payment_direction": None},
        },
        {
            "text": "АКТ ИНВЕНТАРИЗАЦИИ ОСНОВНЫХ СРЕДСТВ\n№ 7 от 01.03.2025\n\nИнвентаризационная комиссия в составе: председатель Козлов А.В., члены: Семёнова Е.П., Волков Д.И.\nОбъект: офис по адресу г. Москва, ул. Тверская, д. 12.\nВыявлено: 45 ед. мебели, 23 компьютера, 5 принтеров.",
            "args": {"document_type": "Акт инвентаризации", "counterparty": None, "subject": "Инвентаризация основных средств офиса на ул. Тверская, д. 12", "date_signed": "2025-03-01", "date_start": None, "date_end": None, "amount": None, "special_conditions": [], "parties": ["Козлов Артём Владимирович", "Семёнова Екатерина Петровна", "Волков Дмитрий Игоревич"], "is_template": False, "payment_terms": None, "payment_amount": None, "payment_frequency": None, "payment_direction": None},
        },
        {
            "text": "ГАРАНТИЙНОЕ ПИСЬМО\n\nООО «СтройМастер» гарантирует оплату задолженности в размере 350 000 руб. перед ООО «Бетон-Плюс» в срок до 15.04.2025.\n\nГенеральный директор Николаев С.А.",
            "args": {"document_type": "Гарантийное письмо", "counterparty": 'ООО «Бетон-Плюс»', "subject": "Гарантия оплаты задолженности 350 000 руб. в срок до 15.04.2025", "date_signed": None, "date_start": None, "date_end": "2025-04-15", "amount": "350 000 руб.", "special_conditions": [], "parties": ['ООО «СтройМастер»', 'ООО «Бетон-Плюс»'], "is_template": False, "payment_terms": "до 15.04.2025", "payment_amount": 350000, "payment_frequency": "once", "payment_direction": "expense"},
        },
        {
            "text": "РАСПИСКА\n\nЯ, Фёдоров Алексей Николаевич, получил от Петрова Ивана Сергеевича денежные средства в размере 100 000 (сто тысяч) рублей.\n\n20 февраля 2025 г.",
            "args": {"document_type": "Расписка", "counterparty": "Петров Иван Сергеевич", "subject": "Получение денежных средств в размере 100 000 руб.", "date_signed": "2025-02-20", "date_start": None, "date_end": None, "amount": "100 000 руб.", "special_conditions": [], "parties": ["Фёдоров Алексей Николаевич", "Петров Иван Сергеевич"], "is_template": False, "payment_terms": None, "payment_amount": 100000, "payment_frequency": "once", "payment_direction": "income"},
        },
        {
            "text": "УВЕДОМЛЕНИЕ О РАСТОРЖЕНИИ ДОГОВОРА\n\nООО «Альфа-Строй» уведомляет ИП Сидорова М.А. о расторжении Договора аренды № 18 от 01.06.2024 с 01.04.2025 в связи с систематическим нарушением условий оплаты.",
            "args": {"document_type": "Уведомление о расторжении", "counterparty": "ИП Сидоров Михаил Александрович", "subject": "Расторжение договора аренды № 18 в связи с нарушением условий оплаты", "date_signed": None, "date_start": None, "date_end": "2025-04-01", "amount": None, "special_conditions": ["Причина: систематическое нарушение условий оплаты"], "parties": ['ООО «Альфа-Строй»', "ИП Сидоров Михаил Александрович"], "is_template": False, "payment_terms": None, "payment_amount": None, "payment_frequency": None, "payment_direction": None},
        },
        {
            "text": "СПРАВКА\nВыдана Морозовой Ольге Дмитриевне в том, что она работает в ООО «ГринТех» на должности бухгалтера с окладом 75 000 руб.\nДата выдачи: 10.03.2025",
            "args": {"document_type": "Справка о доходах", "counterparty": None, "subject": "Подтверждение трудоустройства и оклада Морозовой О.Д. в ООО «ГринТех»", "date_signed": "2025-03-10", "date_start": None, "date_end": None, "amount": "75 000 руб.", "special_conditions": [], "parties": ["Морозова Ольга Дмитриевна", 'ООО «ГринТех»'], "is_template": False, "payment_terms": None, "payment_amount": 75000, "payment_frequency": "monthly", "payment_direction": "income"},
        },
        {
            "text": "СОГЛАШЕНИЕ О ЗАЧЁТЕ ВСТРЕЧНЫХ ТРЕБОВАНИЙ\n\nООО «Восток» и ООО «Запад» договорились о зачёте взаимных требований на сумму 200 000 руб.\nОсновные обязательства по Договору поставки № 15 и Договору оказания услуг № 22.",
            "args": {"document_type": "Соглашение о зачёте встречных требований", "counterparty": 'ООО «Запад»', "subject": "Зачёт взаимных требований по договорам поставки и оказания услуг на 200 000 руб.", "date_signed": None, "date_start": None, "date_end": None, "amount": "200 000 руб.", "special_conditions": ["По Договору поставки № 15", "По Договору оказания услуг № 22"], "parties": ['ООО «Восток»', 'ООО «Запад»'], "is_template": False, "payment_terms": None, "payment_amount": 200000, "payment_frequency": "once", "payment_direction": None},
        },
        {
            "text": "ТЕХНИЧЕСКИЙ ПАСПОРТ ОБЪЕКТА\n\nЗдание по адресу: г. Казань, ул. Баумана, д. 5\nГод постройки: 1985\nПлощадь: 1 200 кв.м.\nЭтажность: 3\nМатериал стен: кирпич",
            "args": {"document_type": "Технический паспорт", "counterparty": None, "subject": "Техническое описание здания по ул. Баумана, д. 5, г. Казань", "date_signed": None, "date_start": None, "date_end": None, "amount": None, "special_conditions": ["Год постройки: 1985", "Площадь: 1 200 кв.м.", "Этажность: 3"], "parties": [], "is_template": False, "payment_terms": None, "payment_amount": None, "payment_frequency": None, "payment_direction": None},
        },
        {
            "text": "АКТ СВЕРКИ ВЗАИМОРАСЧЁТОВ\nза период с 01.01.2025 по 31.03.2025\n\nМежду ООО «Логистик» и ООО «ТрансКарго»\n\nПо данным ООО «Логистик»: задолженность в пользу ООО «ТрансКарго» — 145 000 руб.\nПо данным ООО «ТрансКарго»: задолженность в пользу ООО «ТрансКарго» — 145 000 руб.\nРасхождений нет.",
            "args": {"document_type": "Акт сверки взаиморасчётов", "counterparty": 'ООО «ТрансКарго»', "subject": "Сверка взаиморасчётов за Q1 2025, задолженность 145 000 руб.", "date_signed": None, "date_start": "2025-01-01", "date_end": "2025-03-31", "amount": "145 000 руб.", "special_conditions": ["Расхождений нет"], "parties": ['ООО «Логистик»', 'ООО «ТрансКарго»'], "is_template": False, "payment_terms": None, "payment_amount": 145000, "payment_frequency": None, "payment_direction": "expense"},
        },
        {
            "text": "ПИСЬМО-ОТКАЗ\n\nООО «МедиаГрупп» сообщает об отказе от заключения Договора на оказание рекламных услуг с ИП Кузнецовым А.В. в связи с несоответствием технического задания нашим стандартам качества.",
            "args": {"document_type": "Письмо-отказ", "counterparty": "ИП Кузнецов Андрей Владимирович", "subject": "Отказ от заключения договора на рекламные услуги из-за несоответствия ТЗ", "date_signed": None, "date_start": None, "date_end": None, "amount": None, "special_conditions": ["Причина: несоответствие технического задания стандартам качества"], "parties": ['ООО «МедиаГрупп»', "ИП Кузнецов Андрей Владимирович"], "is_template": False, "payment_terms": None, "payment_amount": None, "payment_frequency": None, "payment_direction": None},
        },
    ]

    for doc in unusual_docs:
        edge_cases.append({
            "messages": [
                {"role": "system", "content": NEW_SYSTEM_PROMPT},
                {"role": "user", "content": f"Извлеки метаданные из текста юридического документа.\n\nТекст документа:\n{doc['text']}"},
                {"role": "assistant", "content": make_tool_call(doc["args"])},
            ]
        })

    return edge_cases


def main():
    output_dir = Path("dataset/training")

    # Load train data
    examples = load_train()
    print(f"Loaded {len(examples)} train examples")

    # Generate DPO pairs
    print("\n=== Generating DPO pairs ===")
    all_dpo = []

    pairs_1 = generate_invalid_json_pairs(examples, 15)
    print(f"  Cat 1 (invalid JSON): {len(pairs_1)} pairs")
    all_dpo.extend(pairs_1)

    pairs_2 = generate_bad_dates_pairs(examples, 15)
    print(f"  Cat 2 (bad dates): {len(pairs_2)} pairs")
    all_dpo.extend(pairs_2)

    pairs_3 = generate_empty_arrays_pairs(examples, 15)
    print(f"  Cat 3 (empty arrays): {len(pairs_3)} pairs")
    all_dpo.extend(pairs_3)

    pairs_4 = generate_short_subject_pairs(examples, 15)
    print(f"  Cat 4 (short subject): {len(pairs_4)} pairs")
    all_dpo.extend(pairs_4)

    pairs_5 = generate_fio_errors_pairs(examples, 15)
    print(f"  Cat 5 (FIO errors): {len(pairs_5)} pairs")
    all_dpo.extend(pairs_5)

    print(f"\n  Total DPO: {len(all_dpo)} pairs")

    # Split 90/10
    random.shuffle(all_dpo)
    split_idx = int(len(all_dpo) * 0.9)
    dpo_train = all_dpo[:split_idx]
    dpo_val = all_dpo[split_idx:]

    with open(output_dir / "v2_dpo_train.jsonl", "w") as f:
        for pair in dpo_train:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    with open(output_dir / "v2_dpo_val.jsonl", "w") as f:
        for pair in dpo_val:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    print(f"  DPO train: {len(dpo_train)}, DPO val: {len(dpo_val)}")

    # Generate edge cases
    print("\n=== Generating edge cases ===")
    edge_cases = generate_edge_cases()
    print(f"  Generated: {len(edge_cases)} edge cases")

    # Append edge cases to v2_train
    with open(output_dir / "v2_train.jsonl") as f:
        train_examples = [json.loads(line) for line in f]

    train_examples.extend(edge_cases)

    with open(output_dir / "v2_train.jsonl", "w") as f:
        for ex in train_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"  v2_train.jsonl updated: {len(train_examples)} total examples")

    # Final stats
    print("\n=== Final Statistics ===")
    print(f"  SFT train: {len(train_examples)}")
    with open(output_dir / "v2_val.jsonl") as f:
        val_count = sum(1 for _ in f)
    print(f"  SFT val: {val_count}")
    print(f"  DPO train: {len(dpo_train)}")
    print(f"  DPO val: {len(dpo_val)}")


if __name__ == "__main__":
    main()
