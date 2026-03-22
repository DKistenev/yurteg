#!/usr/bin/env python3
"""
Подготовка ORPO датасета v3 для Qwen 2.5 1.5B.
ORPO = SFT + Preference в одну фазу.

Формат каждого примера:
  {"prompt": [system_msg, user_msg], "chosen": [assistant_msg], "rejected": [assistant_msg] | null}
"""

import json
import re
import os
from pathlib import Path
from typing import Optional

BASE = Path("/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg")
TRAINING = BASE / "dataset/training"
STRESS_DIR = BASE / "tests/test_data/stress"
STRESS_REPORT = BASE / "dataset/v2_stress_report.json"

# ── Новый system prompt ────────────────────────────────────────────────────────
NEW_SYSTEM_PROMPT = """Ты — юрист-аналитик. Извлеки метаданные из юридического документа.
ЯЗЫК: Все значения ТОЛЬКО на русском. Запрещены английские и китайские слова.

Правила:
1. Отсутствующую информацию ставь null
2. Даты строго YYYY-MM-DD
3. ФИО в именительном падеже: "Иванов Иван Иванович"
4. Формат ИП: "ИП Фамилия Имя Отчество"
5. Контрагент — ДРУГАЯ сторона, не наша (Фокина/Файзулина/БУП/Digital Church)
6. Шаблоны (пустые поля _____) → is_template=true, counterparty=null, parties=[]
7. Сумму с валютой: "1 500 000 руб."
8. document_type: одинаковые документы называй одинаково
9. Контрагент в краткой форме: "ООО", "АО", "ПАО", "ИП" """.strip()

# ── Замены для payment_frequency / payment_direction ─────────────────────────
PF_FIXES = {
    "ежемесячно": "monthly",
    "единоразово": "once",
    "ежеквартально": "quarterly",
    "ежегодно": "yearly",
}
PD_FIXES = {
    "расход": "expense",
    "доход": "income",
}


def fix_enum_values(content: str) -> str:
    """Исправить payment_frequency и payment_direction в JSON-строке."""
    for ru, en in PF_FIXES.items():
        content = re.sub(
            rf'("payment_frequency"\s*:\s*"){ru}"',
            lambda m, en=en: m.group(0).replace(ru, en),
            content,
        )
    for ru, en in PD_FIXES.items():
        content = re.sub(
            rf'("payment_direction"\s*:\s*"){ru}"',
            lambda m, en=en: m.group(0).replace(ru, en),
            content,
        )
    return content


def update_system_in_prompt(prompt: list) -> list:
    """Заменить system-сообщение на новый system prompt."""
    result = []
    for msg in prompt:
        if msg["role"] == "system":
            result.append({"role": "system", "content": NEW_SYSTEM_PROMPT})
        else:
            result.append(msg)
    return result


def fix_payment_freq_in_sft(content: str, doc_type: Optional[str]) -> str:
    """
    Эвристически исправить payment_frequency в SFT примерах.
    Аренда → monthly, купля-продажа/поставка → once.
    """
    if doc_type is None:
        return content
    dt = doc_type.lower()
    if any(w in dt for w in ("аренд", "субаренд", "найм")):
        # payment_frequency должен быть monthly
        content = re.sub(
            r'"payment_frequency"\s*:\s*"once"',
            '"payment_frequency": "monthly"',
            content,
        )
    if any(w in dt for w in ("кредит", "займ", "заём")):
        # Проценты ежемесячно
        content = re.sub(
            r'"payment_frequency"\s*:\s*"once"',
            '"payment_frequency": "monthly"',
            content,
        )
    if any(w in dt for w in ("купл", "поставк", "продаж")):
        # Разовая оплата
        content = re.sub(
            r'"payment_frequency"\s*:\s*"monthly"',
            '"payment_frequency": "once"',
            content,
        )
    return content


def extract_doc_type_from_tool_call(content: str) -> Optional[str]:
    """Достать document_type из tool_call контента."""
    m = re.search(r'"document_type"\s*:\s*"([^"]+)"', content)
    return m.group(1) if m else None


# ── Загрузка файлов ──────────────────────────────────────────────────────────

def load_sft(path: Path) -> list:
    examples = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            msgs = obj["messages"]
            system_msg = next((m for m in msgs if m["role"] == "system"), None)
            user_msg = next((m for m in msgs if m["role"] == "user"), None)
            asst_msg = next((m for m in msgs if m["role"] == "assistant"), None)
            if not (user_msg and asst_msg):
                continue

            # Построить prompt
            prompt = []
            if system_msg:
                prompt.append({"role": "system", "content": NEW_SYSTEM_PROMPT})
            prompt.append(user_msg)

            # Исправить enum-значения и document-type эвристики в chosen
            chosen_content = fix_enum_values(asst_msg["content"])
            doc_type = extract_doc_type_from_tool_call(chosen_content)
            chosen_content = fix_payment_freq_in_sft(chosen_content, doc_type)

            examples.append({
                "prompt": prompt,
                "chosen": [{"role": "assistant", "content": chosen_content}],
                "rejected": None,
                "_source": "sft",
            })
    return examples


def load_dpo(path: Path, fix_enums: bool = False) -> list:
    examples = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            prompt = update_system_in_prompt(obj["prompt"])

            chosen_msgs = obj["chosen"]
            rejected_msgs = obj["rejected"]

            if fix_enums:
                chosen_msgs = [
                    {**m, "content": fix_enum_values(m["content"])}
                    for m in chosen_msgs
                ]
                rejected_msgs = [
                    {**m, "content": fix_enum_values(m["content"])}
                    for m in rejected_msgs
                ]

            examples.append({
                "prompt": prompt,
                "chosen": chosen_msgs,
                "rejected": rejected_msgs,
                "_source": "dpo",
            })
    return examples


# ── Генерация chosen из stress-report ────────────────────────────────────────

# Правила перевода полей
FIELD_TRANSLATIONS = {
    # document_type патчи
    "Contract": "Договор",
    "DocumentType": None,  # None = использовать как null в document_type
}

# Паттерны для детектирования code-switching в строках
EN_PATTERN = re.compile(r'[a-zA-Z]{4,}')
ZH_PATTERN = re.compile(r'[\u4e00-\u9fff]')


def has_foreign(s: str) -> bool:
    """Есть ли в строке ≥4 латинских букв подряд или китайские символы."""
    return bool(EN_PATTERN.search(s)) or bool(ZH_PATTERN.search(s))


# Известные допустимые иностранные слова/имена (enum-значения и имена)
ALLOWED_FOREIGN_SUBSTRINGS = [
    # Иностранные компании — их оставляем
    r'[A-Z][a-zA-Z]+ (LLC|GmbH|Ltd\.?|Inc\.?|GmbH|AG|Corp\.?)',
    r'(LLC|GmbH|Ltd\.?|Inc\.?|AG|Corp\.?) [A-Z]',
    # Apple, Microsoft и подобные имена собственные
    r'Apple|Microsoft|Google|Amazon|Samsung',
    # Аббревиатуры ПО версии
    r'v\d+\.\d+',
]
ALLOWED_FOREIGN_RE = re.compile("|".join(ALLOWED_FOREIGN_SUBSTRINGS), re.IGNORECASE)


def translate_condition(s: str) -> str:
    """
    Перевести/исправить одну строку special_condition или subject.
    Убираем english/китайские вставки, оставляем разрешённые имена.
    """
    # Заменим известные английские паттерны на русские
    replacements = [
        (r'\bof goods from\b', "товаров из"),
        (r'\bfrom Moscow to St\. Petersburg\b', "из Москвы в Санкт-Петербург"),
        (r'\bTransport will occur during off-peak hours\b',
         "Транспортировка осуществляется в нерабочие часы"),
        (r'\bGoods will be transported using specialized tugs\b',
         "Грузы перевозятся с использованием специализированных буксиров"),
        (r'\bPayment terms: invoice \+ 10 days\b',
         "Срок оплаты: счёт + 10 дней"),
        (r'\bNDA required\b', "Требуется соглашение о неразглашении"),
        (r'\bNDS \(value-added tax\) rate is 20%\b', "НДС составляет 20%"),
        (r'\bPayment is due on 10\.\b', "Оплата до 10-го числа"),
        (r'\bTransport will occur during off-peak hours\b',
         "Транспортировка в нерабочие часы"),
        (r'\bGoods will be transported using specialized tugs\b',
         "Грузы перевозятся с использованием специализированных буксиров"),
        (r'\bWork only with approved contractors\b',
         "Работа только с одобренными подрядчиками"),
        (r'\bVested interest действует\b', "Запрет на разглашение действует"),
        (r'\bVESTED INTEREST\b', "запрет на разглашение"),
        (r'\bvested interest\b', "запрет на разглашение"),
        (r'\bUDF\b', "Пользовательские данные"),
        (r'\bSaaS\b', "SaaS"),  # оставим как есть — это бренд
        (r'\bIT-услуг\b', "ИТ-услуг"),
        (r'\bdevelopment и hosting\b', "разработку и хостинг"),
        (r'\bhosting\b', "хостинг"),
        (r'\bdevelopment\b', "разработку"),
        (r'\bSLA\b', "SLA"),  # оставим
        (r'\bAPI\b', "API"),  # оставим
        (r'\bKPI\b', "КПЭ"),
        (r'\bCPL\b', "стоимость лида"),
        (r'\bROI\b', "рентабельность инвестиций"),
        (r'\bNDA\b', "СНР"),  # Соглашение о неразглашении
        (r'\bSPA\b', "договор купли-продажи"),
        (r'\bLOI\b', "письмо о намерениях"),
        (r'\bNDA required\b', "Требуется соглашение о неразглашении"),
        (r'\b24-hour\b', "24-часовой"),
        (r'\bsqm\b', "кв.м."),
        (r'\bRequirements for extraction metadata from a legal document:\s*', ""),
        (r'\bPayment terms: 30% down deposit upon signing, remaining amount upon completion\b',
         "Оплата: 30% аванс при подписании, остаток после завершения"),
        (r'\buntil 28 February 2026\b', "до 28 февраля 2026"),
        (r'\bSrок complete payment is\b', "Срок полной оплаты"),
        (r'\bSrок\b', "Срок"),
        (r'\bInterest is 1\b', "Процентная ставка 1"),
        (r'\bonce, once, monthly\b', "разовая"),
        (r'\bExclusivity of damage\b', "Исключительность ущерба"),
        (r'\bwithin 30 days\b', "в течение 30 дней"),
        (r'\bin amounts of\b', "на сумму"),
        (r'\bamounts of\b', "на сумму"),
        (r'\bNDS\b', "НДС"),
        (r'\bMacBook Pro\b', "MacBook Pro"),  # имя собственное — оставляем
        (r'\b16"\b', '16"'),
        (r'\bnot specified\b', "не указано"),
        (r'\bannual\b', ""),  # payment_frequency исправится ниже
        (r'\bContract\b', "Договор"),
        (r'\bDocumentType\b', "Договор"),
        (r'\bPaying for goods supplied:\b', "Оплата за поставленные товары:"),
        (r'\bcompressors, filters, oil\.\b', "компрессоры, фильтры, масло"),
        (r'\bPaying for goods supplied: compressors, filters, oil\.\b',
         "Оплата за поставленные товары: компрессоры, фильтры, масло"),
        (r'\bнайм осуществляется на т\b', "Найм осуществляется на т"),
        (r'\boperation in Ukraine\b', "эксплуатации на территории Украины"),
        (r'\bvehicle для operation in Ukraine\b',
         "транспортного средства для эксплуатации на территории Украины"),
        (r'\bvehicle\b', "транспортное средство"),
        (r'\bNайм vehicle\b', "Найм транспортного средства"),
        (r'\bv\d+\.\d+\b', lambda m: m.group()),  # версии ПО оставляем
        (r'\barbitr\b', "арбитр"),
        (r'\bгосregi', "госрег"),
    ]

    result = s
    for pattern, replacement in replacements:
        if callable(replacement):
            result = re.sub(pattern, replacement, result)
        else:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    # Убираем оставшиеся китайские символы (заменяем на пустую строку или [?])
    result = ZH_PATTERN.sub("", result)

    # Убираем латинские фрагменты >= 4 букв, если не в списке разрешённых
    def clean_latin(text: str) -> str:
        def replace_if_foreign(m):
            word = m.group()
            # Проверяем разрешённые паттерны
            if ALLOWED_FOREIGN_RE.search(word):
                return word
            # Короткие аббревиатуры оставляем: API, SLA, SaaS, MacBook и т.д.
            if len(word) <= 5:
                return word
            return word  # оставим — лучше не рушить текст автоматически

        return re.sub(r'[A-Za-z]{4,}', replace_if_foreign, text)

    result = clean_latin(result)
    return result.strip()


def make_chosen_from_stress(item: dict, doc_text: Optional[str]) -> dict:
    """
    Создать chosen-ответ из full_response, исправив все code-switching проблемы.
    """
    fr = dict(item["full_response"])  # копия

    # Исправить document_type
    if "document_type" in fr and fr["document_type"]:
        dt = fr["document_type"]
        dt = re.sub(r'\bContract\b', 'Договор', dt)
        dt = re.sub(r'\bDocumentType\b', 'Договор', dt)
        dt = re.sub(r'\bоказania\b', 'оказания', dt)
        dt = re.sub(r'\buslug\b', 'услуг', dt)
        dt = re.sub(r'\bвайм\b', 'найм', dt, flags=re.IGNORECASE)
        dt = re.sub(r'\bvehicles\b', 'транспортных средств', dt, flags=re.IGNORECASE)
        dt = re.sub(r'\bmedicinskikh\b', 'медицинских', dt, flags=re.IGNORECASE)
        dt = re.sub(r'\bLицензий onus\b', 'Лицензионный договор', dt)
        dt = re.sub(r'\bСоглашение о неразглашении и не.*$', 'Соглашение о неразглашении', dt)
        dt = re.sub(r'\bСчёт-на-payable-for-service\b', 'Счёт на оплату услуг', dt)
        dt = ZH_PATTERN.sub("", dt).strip()
        fr["document_type"] = dt

    # Исправить subject
    if "subject" in fr and fr["subject"]:
        fr["subject"] = translate_condition(fr["subject"])

    # Исправить special_conditions
    if "special_conditions" in fr and isinstance(fr["special_conditions"], list):
        fr["special_conditions"] = [
            translate_condition(c) for c in fr["special_conditions"]
            if c  # не None
        ]
        # Убираем пустые строки
        fr["special_conditions"] = [c for c in fr["special_conditions"] if c.strip()]

    # Исправить parties
    if "parties" in fr and isinstance(fr["parties"], list):
        clean_parties = []
        for p in fr["parties"]:
            p_clean = re.sub(r'\bООО «Пierrus\'\"\b', 'ООО «Пьерус»', p)
            p_clean = re.sub(r'\bИП Пупkin Maxim Maximovich\b', 'ИП Пупкин Максим Максимович', p_clean)
            p_clean = re.sub(r'\bПАО «СeverBank»\b', 'ПАО «СеверБанк»', p_clean)
            p_clean = re.sub(r'\bВolgаТранс\b', 'ВолгаТранс', p_clean)
            # Если это иностранная компания — оставляем
            clean_parties.append(p_clean)
        fr["parties"] = clean_parties

    # Исправить counterparty
    if "counterparty" in fr and fr["counterparty"]:
        cp = fr["counterparty"]
        # Компания XYZ Ltd. и подобные — оставляем как есть
        # ИП Пупkin → ИП Пупкин
        cp = re.sub(r'ИП Пупkin Maxim Maximovich', 'ИП Пупкин Максим Максимович', cp)
        # АО полная форма → оставляем
        fr["counterparty"] = cp

    # Исправить is_template — всегда bool
    if "is_template" in fr:
        val = fr["is_template"]
        if isinstance(val, str):
            fr["is_template"] = val.lower() in ("true", "1", "yes")

    # Исправить payment_frequency
    if "payment_frequency" in fr and fr["payment_frequency"]:
        pf = str(fr["payment_frequency"]).strip().strip('"').strip("'")
        pf_map = {
            "annual": "yearly",
            "annually": "yearly",
            "monthly": "monthly",
            "once": "once",
            "quarterly": "quarterly",
            "yearly": "yearly",
            "ежемесячно": "monthly",
            "единоразово": "once",
            "ежеквартально": "quarterly",
            "ежегодно": "yearly",
        }
        fr["payment_frequency"] = pf_map.get(pf.lower(), pf)

    # Исправить payment_direction
    if "payment_direction" in fr and fr["payment_direction"]:
        pd = str(fr["payment_direction"]).strip().strip('"').strip("'").rstrip('", ')
        pd_map = {
            "expense": "expense",
            "income": "income",
            "расход": "expense",
            "доход": "income",
        }
        fr["payment_direction"] = pd_map.get(pd.lower(), pd)

    # Исправить date_end
    if "date_end" in fr and fr["date_end"]:
        de = str(fr["date_end"])
        if "not specified" in de.lower() or not re.match(r'\d{4}-\d{2}-\d{2}', de):
            fr["date_end"] = None

    # Собрать tool_call
    tool_call_content = (
        "<tool_call>\n"
        + json.dumps({"name": "extract_metadata", "arguments": fr},
                     ensure_ascii=False)
        + "\n</tool_call>"
    )

    return {"role": "assistant", "content": tool_call_content}


def make_rejected_from_stress(item: dict) -> dict:
    """Взять full_response как есть — это rejected (с ошибками)."""
    fr = item["full_response"]
    tool_call_content = (
        "<tool_call>\n"
        + json.dumps({"name": "extract_metadata", "arguments": fr},
                     ensure_ascii=False)
        + "\n</tool_call>"
    )
    return {"role": "assistant", "content": tool_call_content}


def load_stress_text(filename: str) -> Optional[str]:
    p = STRESS_DIR / filename
    if p.exists():
        return p.read_text(encoding="utf-8")
    return None


def generate_stress_dpo_pairs() -> list:
    """Генерация DPO пар из stress-report для всех 60 документов."""
    with open(STRESS_REPORT, encoding="utf-8") as f:
        stress_data = json.load(f)

    pairs = []
    for item in stress_data:
        doc_text = load_stress_text(item["file"])

        # User message
        user_content = "Извлеки метаданные из текста юридического документа."
        if doc_text:
            user_content += f"\n\nТекст документа:\n{doc_text}"

        prompt = [
            {"role": "system", "content": NEW_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        chosen = make_chosen_from_stress(item, doc_text)
        rejected = make_rejected_from_stress(item)

        # Если chosen и rejected одинаковые — пропускаем (нет смысла)
        if chosen["content"] == rejected["content"]:
            continue

        pairs.append({
            "prompt": prompt,
            "chosen": [chosen],
            "rejected": [rejected],
            "_source": "stress_dpo",
        })

    return pairs


# ── EN→RU SFT аугментации ─────────────────────────────────────────────────────

EN_RU_AUGMENTATIONS = [
    # 1. IT-контракт с SLA
    {
        "doc_text": """ДОГОВОР НА ОКАЗАНИЕ IT-УСЛУГ № IT-2024/001

г. Москва                                    15 января 2024 года

ООО «ТехПартнёр», именуемое в дальнейшем «Исполнитель», и ООО «БизнесСофт», именуемое в дальнейшем «Заказчик», заключили настоящий договор:

1. ПРЕДМЕТ ДОГОВОРА
Исполнитель обязуется оказывать услуги по разработке (development) и сопровождению программного обеспечения, включая hosting на серверах Исполнителя, техническую поддержку с соблюдением SLA: uptime 99,9%, время отклика на инциденты priority 1 — не более 2 часов.

2. СТОИМОСТЬ УСЛУГ
Ежемесячная абонентская плата составляет 85 000 (восемьдесят пять тысяч) рублей.

3. СРОК ДЕЙСТВИЯ
Договор заключён сроком на 1 (один) год с 01.02.2024 по 31.01.2025.
""",
        "answer": {
            "document_type": "Договор на оказание ИТ-услуг",
            "counterparty": "ООО «БизнесСофт»",
            "subject": "Оказание услуг по разработке и сопровождению программного обеспечения с хостингом",
            "date_signed": "2024-01-15",
            "date_start": "2024-02-01",
            "date_end": "2025-01-31",
            "amount": "85 000 руб.",
            "special_conditions": [
                "Уровень доступности 99,9% (SLA)",
                "Время реагирования на инциденты критического уровня — не более 2 часов",
            ],
            "parties": ["ООО «ТехПартнёр»", "ООО «БизнесСофт»"],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": "monthly",
            "payment_direction": "income",
        },
    },
    # 2. Договор с иностранным контрагентом (GmbH)
    {
        "doc_text": """ДОГОВОР ПОСТАВКИ ПРОГРАММНОГО ОБЕСПЕЧЕНИЯ

г. Москва                                    10 февраля 2024 года

ООО «ИнтегральСофт», далее «Покупатель», и SoftWare Solutions GmbH (Германия), далее «Поставщик», заключили настоящий договор:

1. Поставщик передаёт неисключительные лицензионные права на программное обеспечение «DataBridge Enterprise» v2.5.

2. Стоимость: 120 000 (сто двадцать тысяч) евро, НДС не облагается.

3. Оплата единоразово в течение 30 дней с момента подписания.

4. Срок договора не установлен (бессрочно).
""",
        "answer": {
            "document_type": "Договор поставки программного обеспечения",
            "counterparty": "SoftWare Solutions GmbH",
            "subject": "Передача неисключительных лицензионных прав на программное обеспечение «DataBridge Enterprise» v2.5",
            "date_signed": "2024-02-10",
            "date_start": None,
            "date_end": None,
            "amount": "120 000 евро",
            "special_conditions": [
                "НДС не облагается",
                "Срок оплаты — 30 дней с момента подписания",
            ],
            "parties": ["ООО «ИнтегральСофт»", "SoftWare Solutions GmbH"],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": "once",
            "payment_direction": "expense",
        },
    },
    # 3. Маркетинговый договор с KPI/CPL
    {
        "doc_text": """ДОГОВОР НА ОКАЗАНИЕ МАРКЕТИНГОВЫХ УСЛУГ № МКТ-456

г. Санкт-Петербург                           1 марта 2024 года

ООО «Маркетинг Про», в лице директора Соколова Игоря Анатольевича, и ООО «РитейлГрупп», заключили договор на продвижение:

1. Исполнитель обязуется организовать рекламные кампании с KPI: CPL не более 2 500 руб., ROI не менее 150%.

2. Стоимость услуг: 350 000 (триста пятьдесят тысяч) рублей в месяц.

3. Срок: 6 месяцев, с 01.03.2024 по 31.08.2024.

4. Отчёт по KPI предоставляется ежемесячно.
""",
        "answer": {
            "document_type": "Договор на оказание маркетинговых услуг",
            "counterparty": "ООО «РитейлГрупп»",
            "subject": "Оказание услуг по продвижению и рекламным кампаниям",
            "date_signed": "2024-03-01",
            "date_start": "2024-03-01",
            "date_end": "2024-08-31",
            "amount": "350 000 руб.",
            "special_conditions": [
                "Стоимость лида (CPL) не более 2 500 руб.",
                "Рентабельность инвестиций (ROI) не менее 150%",
                "Ежемесячные отчёты по показателям эффективности",
            ],
            "parties": ["ООО «Маркетинг Про»", "ООО «РитейлГрупп»"],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": "monthly",
            "payment_direction": "income",
        },
    },
    # 4. NDA
    {
        "doc_text": """СОГЛАШЕНИЕ О НЕРАЗГЛАШЕНИИ КОНФИДЕНЦИАЛЬНОЙ ИНФОРМАЦИИ (NDA)

г. Екатеринбург                              5 апреля 2024 года

ООО «УралТехно» и ИП Кузнецов Дмитрий Сергеевич заключили настоящее NDA.

1. Стороны обязуются не раскрывать третьим лицам конфиденциальную информацию, переданную в рамках переговоров о возможном сотрудничестве.

2. Срок действия NDA: 3 года с даты подписания.

3. В случае нарушения: штраф 500 000 (пятьсот тысяч) рублей.
""",
        "answer": {
            "document_type": "Соглашение о неразглашении",
            "counterparty": "ИП Кузнецов Дмитрий Сергеевич",
            "subject": "Неразглашение конфиденциальной информации в рамках переговоров о сотрудничестве",
            "date_signed": "2024-04-05",
            "date_start": "2024-04-05",
            "date_end": "2027-04-05",
            "amount": None,
            "special_conditions": [
                "Штраф за нарушение — 500 000 руб.",
                "Срок действия — 3 года",
            ],
            "parties": ["ООО «УралТехно»", "ИП Кузнецов Дмитрий Сергеевич"],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": None,
            "payment_direction": None,
        },
    },
    # 5. SPA (договор купли-продажи доли)
    {
        "doc_text": """ДОГОВОР КУПЛИ-ПРОДАЖИ ДОЛИ В УСТАВНОМ КАПИТАЛЕ (SPA)

г. Москва                                    20 мая 2024 года

Сидоров Антон Викторович, именуемый «Продавец», и ООО «ИнвестКапитал», именуемое «Покупатель», заключили настоящий договор:

1. Продавец продаёт 30% доли в уставном капитале ООО «ТехСтарт» за 4 500 000 (четыре миллиона пятьсот тысяч) рублей.

2. Оплата производится единоразово не позднее 5 рабочих дней со дня подписания.
""",
        "answer": {
            "document_type": "Договор купли-продажи доли в уставном капитале",
            "counterparty": "ООО «ИнвестКапитал»",
            "subject": "Продажа 30% доли в уставном капитале ООО «ТехСтарт»",
            "date_signed": "2024-05-20",
            "date_start": None,
            "date_end": None,
            "amount": "4 500 000 руб.",
            "special_conditions": [
                "Оплата в течение 5 рабочих дней с даты подписания",
            ],
            "parties": ["Сидоров Антон Викторович", "ООО «ИнвестКапитал»"],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": "once",
            "payment_direction": "income",
        },
    },
    # 6. LOI (письмо о намерениях)
    {
        "doc_text": """ПИСЬМО О НАМЕРЕНИЯХ (LOI)

г. Москва                                    3 июня 2024 года

ПАО «РусИнвест» направляет настоящее LOI ООО «ГринТех» о намерении приобрести 51% акций компании по ориентировочной стоимости 250 000 000 (двести пятьдесят миллионов) рублей.

Стороны договорились провести due diligence в течение 60 дней.
""",
        "answer": {
            "document_type": "Письмо о намерениях",
            "counterparty": "ООО «ГринТех»",
            "subject": "Намерение о приобретении 51% акций ООО «ГринТех»",
            "date_signed": "2024-06-03",
            "date_start": None,
            "date_end": None,
            "amount": "250 000 000 руб.",
            "special_conditions": [
                "Проведение юридической проверки (due diligence) в течение 60 дней",
            ],
            "parties": ["ПАО «РусИнвест»", "ООО «ГринТех»"],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": "once",
            "payment_direction": "expense",
        },
    },
    # 7. Договор аренды с Microsoft
    {
        "doc_text": """ДОГОВОР ПОСТАВКИ ПРОГРАММНОГО ОБЕСПЕЧЕНИЯ И ЛИЦЕНЗИЙ

г. Москва                                    15 июля 2024 года

ООО «Офис-Центр» и Microsoft LLC заключили договор:

1. Microsoft LLC поставляет лицензии Microsoft Office 365 Business Premium для 50 пользователей.

2. Стоимость: 1 200 000 (один миллион двести тысяч) рублей в год.

3. Срок: 01.08.2024 – 31.07.2025.
""",
        "answer": {
            "document_type": "Договор поставки программного обеспечения",
            "counterparty": "Microsoft LLC",
            "subject": "Поставка лицензий Microsoft Office 365 Business Premium для 50 пользователей",
            "date_signed": "2024-07-15",
            "date_start": "2024-08-01",
            "date_end": "2025-07-31",
            "amount": "1 200 000 руб.",
            "special_conditions": [
                "Лицензии для 50 пользователей",
            ],
            "parties": ["ООО «Офис-Центр»", "Microsoft LLC"],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": "yearly",
            "payment_direction": "expense",
        },
    },
    # 8. Договор на хостинг с API
    {
        "doc_text": """ДОГОВОР НА ОКАЗАНИЕ УСЛУГ ХОСТИНГА № ХСТ-789

г. Новосибирск                               2 августа 2024 года

ООО «ХостПро» (Исполнитель) и ИП Миронов Алексей Владимирович (Заказчик):

1. Исполнитель предоставляет услуги хостинга: VPS-сервер, доступ к API управления, автобэкап.

2. Uptime: 99,95% согласно SLA.

3. Ежемесячная плата: 12 000 (двенадцать тысяч) рублей.

4. Срок: с 01.09.2024 бессрочно.
""",
        "answer": {
            "document_type": "Договор на оказание услуг хостинга",
            "counterparty": "ИП Миронов Алексей Владимирович",
            "subject": "Оказание услуг хостинга: предоставление виртуального сервера, программного интерфейса управления, автоматического резервного копирования",
            "date_signed": "2024-08-02",
            "date_start": "2024-09-01",
            "date_end": None,
            "amount": "12 000 руб.",
            "special_conditions": [
                "Уровень доступности 99,95% (SLA)",
            ],
            "parties": ["ООО «ХостПро»", "ИП Миронов Алексей Владимирович"],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": "monthly",
            "payment_direction": "income",
        },
    },
    # 9. IT-аутсорс с Inc.
    {
        "doc_text": """ДОГОВОР ОБ АУТСОРСИНГЕ РАЗРАБОТКИ ПРОГРАММНОГО ОБЕСПЕЧЕНИЯ

г. Москва                                    10 сентября 2024 года

ООО «ЦифраТех» и DataSoft Inc. (США) заключили договор:

1. DataSoft Inc. оказывает услуги по разработке backend-модуля системы управления складом.

2. Стоимость работ: 280 000 USD.

3. Оплата поэтапно: 40% — аванс, 60% — после сдачи.

4. Срок выполнения: 01.10.2024 – 31.03.2025.
""",
        "answer": {
            "document_type": "Договор об аутсорсинге разработки программного обеспечения",
            "counterparty": "DataSoft Inc.",
            "subject": "Разработка серверного модуля системы управления складом",
            "date_signed": "2024-09-10",
            "date_start": "2024-10-01",
            "date_end": "2025-03-31",
            "amount": "280 000 USD",
            "special_conditions": [
                "Оплата поэтапно: 40% аванс, 60% после сдачи результата",
            ],
            "parties": ["ООО «ЦифраТех»", "DataSoft Inc."],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": "once",
            "payment_direction": "expense",
        },
    },
    # 10. Договор технической поддержки (support SLA)
    {
        "doc_text": """ДОГОВОР ТЕХНИЧЕСКОЙ ПОДДЕРЖКИ ПРОГРАММНОГО ОБЕСПЕЧЕНИЯ

г. Казань                                    1 октября 2024 года

ООО «СервисДата» и АО «ПромышленникЪ»:

1. Исполнитель оказывает поддержку ERP-системы: helpdesk 8/5, реагирование на критические инциденты — 4 часа.

2. Ежеквартальная оплата: 180 000 (сто восемьдесят тысяч) рублей.

3. Срок: 01.10.2024 – 30.09.2025.
""",
        "answer": {
            "document_type": "Договор технической поддержки программного обеспечения",
            "counterparty": "АО «ПромышленникЪ»",
            "subject": "Оказание технической поддержки системы планирования ресурсов предприятия (ERP)",
            "date_signed": "2024-10-01",
            "date_start": "2024-10-01",
            "date_end": "2025-09-30",
            "amount": "180 000 руб.",
            "special_conditions": [
                "Поддержка в режиме 8 часов в сутки / 5 дней в неделю",
                "Время реагирования на критические инциденты — 4 часа",
            ],
            "parties": ["ООО «СервисДата»", "АО «ПромышленникЪ»"],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": "quarterly",
            "payment_direction": "income",
        },
    },
    # 11. Договор с GmbH (консалтинг)
    {
        "doc_text": """КОНСУЛЬТАЦИОННЫЙ ДОГОВОР № КОН-2024/11

г. Москва                                    20 ноября 2024 года

ООО «РосКонсалт» и Beratung GmbH (Австрия) заключили договор:

1. Beratung GmbH оказывает консультационные услуги по реструктуризации бизнеса.

2. Стоимость: 95 000 евро единовременно.

3. Срок: декабрь 2024 – март 2025.
""",
        "answer": {
            "document_type": "Консультационный договор",
            "counterparty": "Beratung GmbH",
            "subject": "Оказание консультационных услуг по реструктуризации бизнеса",
            "date_signed": "2024-11-20",
            "date_start": "2024-12-01",
            "date_end": "2025-03-31",
            "amount": "95 000 евро",
            "special_conditions": [],
            "parties": ["ООО «РосКонсалт»", "Beratung GmbH"],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": "once",
            "payment_direction": "expense",
        },
    },
    # 12. Договор Amazon AWS
    {
        "doc_text": """СОГЛАШЕНИЕ ОБ ИСПОЛЬЗОВАНИИ ОБЛАЧНЫХ СЕРВИСОВ

г. Москва                                    5 декабря 2024 года

ООО «КлаудРус» и Amazon Web Services, Inc. (AWS):

1. AWS предоставляет доступ к облачной инфраструктуре: EC2, S3, RDS.

2. Оплата ежемесячно по факту потребления, предоплата не требуется.

3. Ориентировочный ежемесячный бюджет: 150 000 (сто пятьдесят тысяч) рублей.
""",
        "answer": {
            "document_type": "Соглашение об использовании облачных сервисов",
            "counterparty": "Amazon Web Services, Inc.",
            "subject": "Предоставление доступа к облачной инфраструктуре (виртуальные серверы, хранилище, управляемые базы данных)",
            "date_signed": "2024-12-05",
            "date_start": None,
            "date_end": None,
            "amount": "150 000 руб.",
            "special_conditions": [
                "Оплата по факту потребления без предоплаты",
            ],
            "parties": ["ООО «КлаудРус»", "Amazon Web Services, Inc."],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": "monthly",
            "payment_direction": "expense",
        },
    },
    # 13. Рамочный договор с Ltd. (поставки)
    {
        "doc_text": """РАМОЧНЫЙ ДОГОВОР ПОСТАВКИ ТОВАРОВ № РМК-2024/5

г. Ростов-на-Дону                            10 января 2025 года

ООО «ЮгТорг» и TechSupply Ltd. (Великобритания) заключили рамочный договор:

1. TechSupply Ltd. осуществляет поставку электронных компонентов по заявкам Покупателя.

2. Цена определяется в каждой спецификации отдельно.

3. Условия Incoterms: DAP Ростов-на-Дону.

4. Срок договора: 2 года.
""",
        "answer": {
            "document_type": "Рамочный договор поставки",
            "counterparty": "TechSupply Ltd.",
            "subject": "Поставка электронных компонентов по заявкам Покупателя",
            "date_signed": "2025-01-10",
            "date_start": "2025-01-10",
            "date_end": "2027-01-10",
            "amount": None,
            "special_conditions": [
                "Цена определяется в каждой спецификации отдельно",
                "Условия поставки: DAP Ростов-на-Дону",
            ],
            "parties": ["ООО «ЮгТорг»", "TechSupply Ltd."],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": "once",
            "payment_direction": "expense",
        },
    },
    # 14. Лицензионное соглашение на ПО Samsung
    {
        "doc_text": """ЛИЦЕНЗИОННОЕ СОГЛАШЕНИЕ НА ИСПОЛЬЗОВАНИЕ ПРОГРАММНОГО ОБЕСПЕЧЕНИЯ

г. Санкт-Петербург                           1 февраля 2025 года

ООО «Дистрибьютор» и Samsung Electronics Co., Ltd.:

1. Samsung Electronics Co., Ltd. предоставляет неисключительную лицензию на использование системы управления устройствами Samsung Knox для 200 устройств.

2. Стоимость лицензии: 600 000 (шестьсот тысяч) рублей ежегодно.

3. Срок: бессрочно при условии ежегодной оплаты.
""",
        "answer": {
            "document_type": "Лицензионный договор",
            "counterparty": "Samsung Electronics Co., Ltd.",
            "subject": "Предоставление неисключительной лицензии на систему управления устройствами Samsung Knox для 200 устройств",
            "date_signed": "2025-02-01",
            "date_start": "2025-02-01",
            "date_end": None,
            "amount": "600 000 руб.",
            "special_conditions": [
                "Лицензия для 200 устройств",
                "Условие сохранения лицензии — ежегодная оплата",
            ],
            "parties": ["ООО «Дистрибьютор»", "Samsung Electronics Co., Ltd."],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": "yearly",
            "payment_direction": "expense",
        },
    },
    # 15. Договор на разработку (Corp.)
    {
        "doc_text": """ДОГОВОР ПОДРЯДА НА РАЗРАБОТКУ МОБИЛЬНОГО ПРИЛОЖЕНИЯ

г. Москва                                    15 марта 2025 года

ООО «МобильТех» и AppDev Corp. (Канада):

1. AppDev Corp. разрабатывает мобильное приложение для iOS и Android.

2. Стоимость: 3 500 000 (три миллиона пятьсот тысяч) рублей.

3. Оплата: аванс 30% — 1 050 000 руб., остаток — после сдачи.

4. Срок: 01.04.2025 – 30.09.2025.
""",
        "answer": {
            "document_type": "Договор подряда на разработку программного обеспечения",
            "counterparty": "AppDev Corp.",
            "subject": "Разработка мобильного приложения для платформ iOS и Android",
            "date_signed": "2025-03-15",
            "date_start": "2025-04-01",
            "date_end": "2025-09-30",
            "amount": "3 500 000 руб.",
            "special_conditions": [
                "Аванс 30% — 1 050 000 руб. при подписании",
                "Остаток — после сдачи результата",
            ],
            "parties": ["ООО «МобильТех»", "AppDev Corp."],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": "once",
            "payment_direction": "expense",
        },
    },
    # 16. Договор API-интеграции
    {
        "doc_text": """ДОГОВОР НА ОКАЗАНИЕ УСЛУГ API-ИНТЕГРАЦИИ

г. Уфа                                       5 апреля 2025 года

ООО «СвязьТех» и ИП Волков Константин Юрьевич:

1. Исполнитель разрабатывает REST API для интеграции с платёжной системой.

2. Стоимость: 220 000 (двести двадцать тысяч) рублей.

3. Срок выполнения: 60 календарных дней.
""",
        "answer": {
            "document_type": "Договор на оказание услуг по программной интеграции",
            "counterparty": "ИП Волков Константин Юрьевич",
            "subject": "Разработка программного интерфейса (REST API) для интеграции с платёжной системой",
            "date_signed": "2025-04-05",
            "date_start": "2025-04-05",
            "date_end": None,
            "amount": "220 000 руб.",
            "special_conditions": [
                "Срок выполнения — 60 календарных дней",
            ],
            "parties": ["ООО «СвязьТех»", "ИП Волков Константин Юрьевич"],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": "once",
            "payment_direction": "income",
        },
    },
    # 17. Субподряд с Ltd.
    {
        "doc_text": """ДОГОВОР СУБПОДРЯДА № СУБ-2025/03

г. Москва                                    20 апреля 2025 года

ООО «СтройПроект» (Подрядчик) и BuildTech Ltd. (Субподрядчик):

1. Субподрядчик выполняет монтаж инженерных систем по адресу: г. Москва, ул. Ленина, д. 15.

2. Стоимость работ: 8 700 000 (восемь миллионов семьсот тысяч) рублей.

3. Срок: 01.05.2025 – 30.11.2025.

4. Оплата: 25% аванс, 75% — по актам выполненных работ.
""",
        "answer": {
            "document_type": "Договор субподряда",
            "counterparty": "BuildTech Ltd.",
            "subject": "Монтаж инженерных систем по адресу: г. Москва, ул. Ленина, д. 15",
            "date_signed": "2025-04-20",
            "date_start": "2025-05-01",
            "date_end": "2025-11-30",
            "amount": "8 700 000 руб.",
            "special_conditions": [
                "Аванс 25%, остаток — по актам выполненных работ",
            ],
            "parties": ["ООО «СтройПроект»", "BuildTech Ltd."],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": "once",
            "payment_direction": "expense",
        },
    },
    # 18. Договор аренды оборудования (AG)
    {
        "doc_text": """ДОГОВОР АРЕНДЫ ПРОМЫШЛЕННОГО ОБОРУДОВАНИЯ

г. Самара                                    2 мая 2025 года

ООО «СамараИнвест» и Technik AG (Швейцария):

1. Арендодатель предоставляет в аренду промышленное оборудование: фрезерные станки ЧПУ — 3 ед.

2. Арендная плата: 450 000 (четыреста пятьдесят тысяч) рублей в месяц.

3. Срок аренды: 12 месяцев, с 01.06.2025 по 31.05.2026.
""",
        "answer": {
            "document_type": "Договор аренды оборудования",
            "counterparty": "Technik AG",
            "subject": "Аренда промышленных фрезерных станков с числовым программным управлением — 3 единицы",
            "date_signed": "2025-05-02",
            "date_start": "2025-06-01",
            "date_end": "2026-05-31",
            "amount": "450 000 руб.",
            "special_conditions": [],
            "parties": ["ООО «СамараИнвест»", "Technik AG"],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": "monthly",
            "payment_direction": "expense",
        },
    },
    # 19. Рекламный договор (ROI/KPI/CPL)
    {
        "doc_text": """ДОГОВОР НА ОКАЗАНИЕ РЕКЛАМНЫХ УСЛУГ В ИНТЕРНЕТЕ № РЕК-2025/07

г. Краснодар                                 1 июня 2025 года

ООО «Агентство Рост» и ООО «Продажа.ру»:

1. Исполнитель размещает контекстную рекламу в Яндекс.Директ и Google Ads.

2. Ключевые показатели: CPL ≤ 1 200 руб., конверсия ≥ 3%, ROI ≥ 200%.

3. Бюджет на рекламу: 500 000 (пятьсот тысяч) рублей в месяц + вознаграждение агентства 15%.

4. Отчётность: еженедельные KPI-отчёты.
""",
        "answer": {
            "document_type": "Договор на оказание рекламных услуг",
            "counterparty": "ООО «Продажа.ру»",
            "subject": "Размещение контекстной рекламы в поисковых системах",
            "date_signed": "2025-06-01",
            "date_start": "2025-06-01",
            "date_end": None,
            "amount": "500 000 руб.",
            "special_conditions": [
                "Стоимость лида (CPL) не более 1 200 руб.",
                "Конверсия не менее 3%",
                "Рентабельность инвестиций (ROI) не менее 200%",
                "Вознаграждение агентства — 15% от рекламного бюджета",
                "Еженедельные отчёты по показателям эффективности",
            ],
            "parties": ["ООО «Агентство Рост»", "ООО «Продажа.ру»"],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": "monthly",
            "payment_direction": "income",
        },
    },
    # 20. GDPR / персональные данные (Inc.)
    {
        "doc_text": """СОГЛАШЕНИЕ ОБ ОБРАБОТКЕ ПЕРСОНАЛЬНЫХ ДАННЫХ (DPA)

г. Москва                                    10 июля 2025 года

ООО «ДатаСервис» и GlobalData Inc. (США):

1. Стороны договорились о порядке обработки персональных данных пользователей в соответствии с GDPR и Федеральным законом № 152-ФЗ.

2. GlobalData Inc. выступает оператором данных, ООО «ДатаСервис» — обработчиком.

3. Срок хранения данных: не более 3 лет.
""",
        "answer": {
            "document_type": "Соглашение об обработке персональных данных",
            "counterparty": "GlobalData Inc.",
            "subject": "Определение порядка обработки персональных данных пользователей",
            "date_signed": "2025-07-10",
            "date_start": "2025-07-10",
            "date_end": None,
            "amount": None,
            "special_conditions": [
                "Соответствие требованиям европейского регламента о защите данных (GDPR) и Федерального закона № 152-ФЗ",
                "Срок хранения персональных данных — не более 3 лет",
                "GlobalData Inc. — оператор данных, ООО «ДатаСервис» — обработчик",
            ],
            "parties": ["ООО «ДатаСервис»", "GlobalData Inc."],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": None,
            "payment_direction": None,
        },
    },
    # 21. Договор с [ФИО_1] (маски анонимизации)
    {
        "doc_text": """ТРУДОВОЙ ДОГОВОР № ТД-2025/88

г. Санкт-Петербург                           [ДАТА_1]

ООО «ЮрТэг», в лице генерального директора [ФИО_1], и [ФИО_2], именуемый(-ая) «Работник»:

1. Работник принимается на должность: ведущий разработчик backend.

2. Заработная плата: [СУММА_1] в месяц.

3. Испытательный срок: 3 (три) месяца.

4. Место работы: г. Санкт-Петербург, ул. [АДРЕС_1].
""",
        "answer": {
            "document_type": "Трудовой договор",
            "counterparty": "[ФИО_2]",
            "subject": "Приём на работу на должность ведущего разработчика серверной части",
            "date_signed": "[ДАТА_1]",
            "date_start": None,
            "date_end": None,
            "amount": "[СУММА_1]",
            "special_conditions": [
                "Испытательный срок — 3 месяца",
                "Место работы: г. Санкт-Петербург, ул. [АДРЕС_1]",
            ],
            "parties": ["ООО «ЮрТэг»", "[ФИО_2]"],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": "monthly",
            "payment_direction": "expense",
        },
    },
    # 22. Договор на маркетинговые KPI-услуги (шаблон)
    {
        "doc_text": """ДОГОВОР НА ПРОДВИЖЕНИЕ В СОЦИАЛЬНЫХ СЕТЯХ (SMM)

г. ________                                  «___» _______ 20__ г.

_________ (Исполнитель) и _________ (Заказчик):

1. Исполнитель ведёт социальные сети Заказчика: ВКонтакте, Telegram.

2. KPI: охват ≥ 10 000 в месяц, engagement rate ≥ 5%.

3. Вознаграждение: _________ рублей в месяц.
""",
        "answer": {
            "document_type": "Договор на продвижение в социальных сетях",
            "counterparty": None,
            "subject": "Ведение социальных сетей Заказчика",
            "date_signed": None,
            "date_start": None,
            "date_end": None,
            "amount": None,
            "special_conditions": [
                "Охват не менее 10 000 пользователей в месяц",
                "Показатель вовлечённости аудитории не менее 5%",
            ],
            "parties": [],
            "is_template": True,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": "monthly",
            "payment_direction": None,
        },
    },
    # 23. Дополнительное соглашение о смене контрагента (Ltd.)
    {
        "doc_text": """ДОПОЛНИТЕЛЬНОЕ СОГЛАШЕНИЕ № 2 К ДОГОВОРУ № ОС-2024/12

г. Волгоград                                 30 июня 2025 года

ООО «ЭнергоСтрой» и LogisticPro Ltd. к Договору транспортной экспедиции от 01.01.2025:

1. Увеличить стоимость услуг на 10% в связи с ростом топливных расходов.

2. Новая ежемесячная стоимость: 275 000 (двести семьдесят пять тысяч) рублей.

3. Изменения вступают в силу с 01.07.2025.
""",
        "answer": {
            "document_type": "Дополнительное соглашение к договору транспортной экспедиции",
            "counterparty": "LogisticPro Ltd.",
            "subject": "Изменение стоимости услуг транспортной экспедиции в связи с ростом топливных расходов",
            "date_signed": "2025-06-30",
            "date_start": "2025-07-01",
            "date_end": None,
            "amount": "275 000 руб.",
            "special_conditions": [
                "Увеличение стоимости услуг на 10%",
                "Изменения вступают в силу с 01.07.2025",
            ],
            "parties": ["ООО «ЭнергоСтрой»", "LogisticPro Ltd."],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": "monthly",
            "payment_direction": "expense",
        },
    },
    # 24. Лицензия на ПО (AG)
    {
        "doc_text": """ЛИЦЕНЗИОННЫЙ ДОГОВОР НА ПРОГРАММНОЕ ОБЕСПЕЧЕНИЕ «LEGALIS PRO»

г. Москва                                    15 августа 2025 года

ООО «ЛегалИС» и Recht AG (Австрия):

1. Recht AG предоставляет лицензию на использование системы автоматизации юридического документооборота «Legalis Pro» v4.1.

2. Лицензия: неисключительная, для 10 рабочих мест.

3. Стоимость: 2 400 000 (два миллиона четыреста тысяч) рублей единовременно.

4. Техническая поддержка: 1 год включена в стоимость.
""",
        "answer": {
            "document_type": "Лицензионный договор на программное обеспечение",
            "counterparty": "Recht AG",
            "subject": "Предоставление неисключительной лицензии на систему автоматизации юридического документооборота «Legalis Pro» v4.1 для 10 рабочих мест",
            "date_signed": "2025-08-15",
            "date_start": None,
            "date_end": None,
            "amount": "2 400 000 руб.",
            "special_conditions": [
                "Неисключительная лицензия для 10 рабочих мест",
                "Техническая поддержка включена на 1 год",
            ],
            "parties": ["ООО «ЛегалИС»", "Recht AG"],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": "once",
            "payment_direction": "expense",
        },
    },
    # 25. ИТ-договор с маскированными данными
    {
        "doc_text": """ДОГОВОР НА РАЗРАБОТКУ КОРПОРАТИВНОГО ПОРТАЛА

г. [ГОРОД_1]                                 [ДАТА_1]

[ОРГАНИЗАЦИЯ_1] (Заказчик) и ООО «ДевЛаб» (Исполнитель):

1. Исполнитель разрабатывает корпоративный портал с HR-модулем, CRM и аналитикой.

2. Стоимость: [СУММА_1] рублей.

3. Срок: 4 месяца с даты подписания.

4. Оплата: 50% аванс, 50% по завершении.
""",
        "answer": {
            "document_type": "Договор на разработку программного обеспечения",
            "counterparty": "[ОРГАНИЗАЦИЯ_1]",
            "subject": "Разработка корпоративного портала с модулями управления персоналом, управления клиентами и аналитики",
            "date_signed": "[ДАТА_1]",
            "date_start": None,
            "date_end": None,
            "amount": "[СУММА_1] руб.",
            "special_conditions": [
                "Срок выполнения — 4 месяца с даты подписания",
                "Оплата поэтапно: 50% аванс, 50% по завершении",
            ],
            "parties": ["[ОРГАНИЗАЦИЯ_1]", "ООО «ДевЛаб»"],
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": "once",
            "payment_direction": "income",
        },
    },
]

# Дополним до 50 примеров вариациями на основе существующих
ADDITIONAL_AUGMENTATIONS_COUNT = 25  # Будет сгенерировано программно

def generate_en_ru_augmentations() -> list:
    """Создать SFT примеры из EN→RU аугментаций."""
    examples = []
    for item in EN_RU_AUGMENTATIONS:
        user_content = (
            "Извлеки метаданные из текста юридического документа.\n\n"
            f"Текст документа:\n{item['doc_text'].strip()}"
        )
        answer = item["answer"]

        tool_call = json.dumps(
            {"name": "extract_metadata", "arguments": answer},
            ensure_ascii=False,
        )
        chosen_content = f"<tool_call>\n{tool_call}\n</tool_call>"

        examples.append({
            "prompt": [
                {"role": "system", "content": NEW_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "chosen": [{"role": "assistant", "content": chosen_content}],
            "rejected": None,
            "_source": "sft_en_ru",
        })
    return examples


# ── Вариации для дополнения до 50 примеров ────────────────────────────────────

def make_variations() -> list:
    """Генерировать дополнительные вариации на основе базовых шаблонов."""
    variations = [
        # 26. Договор SaaS-подписки
        {
            "doc_text": """ДОГОВОР-ОФЕРТА НА ИСПОЛЬЗОВАНИЕ SAAS-СЕРВИСА

Принят в публичной оферте, опубликован 01.09.2025.

ООО «КлаудБаза» предлагает неограниченному кругу лиц (Пользователей) доступ к SaaS-платформе документооборота.

Тариф «Бизнес»: 4 900 (четыре тысячи девятьсот) рублей в месяц за организацию.

Бесплатный пробный период: 14 дней.
""",
            "answer": {
                "document_type": "Договор-оферта на использование облачного сервиса",
                "counterparty": None,
                "subject": "Предоставление доступа к облачной платформе электронного документооборота",
                "date_signed": "2025-09-01",
                "date_start": "2025-09-01",
                "date_end": None,
                "amount": "4 900 руб.",
                "special_conditions": [
                    "Бесплатный пробный период — 14 дней",
                ],
                "parties": [],
                "is_template": False,
                "payment_terms": None,
                "payment_amount": None,
                "payment_frequency": "monthly",
                "payment_direction": "income",
            },
        },
        # 27. Договор с Apple Inc.
        {
            "doc_text": """ДОГОВОР ПОСТАВКИ ТЕХНИКИ И ПРОГРАММНОГО ОБЕСПЕЧЕНИЯ

г. Москва                                    10 октября 2025 года

ООО «АйТи-Решения» и Apple Inc.:

1. Apple Inc. поставляет MacBook Pro 16" M4 Pro — 20 штук и MacBook Air M3 — 30 штук.

2. Стоимость поставки: 18 500 000 (восемнадцать миллионов пятьсот тысяч) рублей.

3. Оплата единовременно в течение 10 дней с момента поставки.
""",
            "answer": {
                "document_type": "Договор поставки техники",
                "counterparty": "Apple Inc.",
                "subject": "Поставка ноутбуков MacBook Pro 16\" M4 Pro (20 шт.) и MacBook Air M3 (30 шт.)",
                "date_signed": "2025-10-10",
                "date_start": None,
                "date_end": None,
                "amount": "18 500 000 руб.",
                "special_conditions": [
                    "Срок оплаты — 10 дней с момента поставки",
                ],
                "parties": ["ООО «АйТи-Решения»", "Apple Inc."],
                "is_template": False,
                "payment_terms": None,
                "payment_amount": None,
                "payment_frequency": "once",
                "payment_direction": "expense",
            },
        },
        # 28. Агентский договор (LLC иностранный)
        {
            "doc_text": """АГЕНТСКИЙ ДОГОВОР № АГ-2025/15

г. Москва                                    1 ноября 2025 года

ООО «МедиаГрупп» (Принципал) и MediaSolutions LLC (Агент):

1. Агент от имени и за счёт Принципала заключает договоры с рекламодателями.

2. Агентское вознаграждение: 12% от суммы привлечённых договоров.

3. Минимальный ежемесячный оборот: 2 000 000 (два миллиона) рублей.

4. Срок: 01.11.2025 – 31.10.2026.
""",
            "answer": {
                "document_type": "Агентский договор",
                "counterparty": "MediaSolutions LLC",
                "subject": "Заключение договоров с рекламодателями от имени и за счёт Принципала",
                "date_signed": "2025-11-01",
                "date_start": "2025-11-01",
                "date_end": "2026-10-31",
                "amount": None,
                "special_conditions": [
                    "Агентское вознаграждение — 12% от суммы привлечённых договоров",
                    "Минимальный ежемесячный оборот — 2 000 000 руб.",
                ],
                "parties": ["ООО «МедиаГрупп»", "MediaSolutions LLC"],
                "is_template": False,
                "payment_terms": None,
                "payment_amount": None,
                "payment_frequency": "monthly",
                "payment_direction": "expense",
            },
        },
        # 29. Договор SEO
        {
            "doc_text": """ДОГОВОР НА ОКАЗАНИЕ УСЛУГ SEO-ПРОДВИЖЕНИЯ САЙТА

г. Нижний Новгород                           15 ноября 2025 года

ООО «ВебПродвижение» (Исполнитель) и ИП Тихонов Вадим Александрович (Заказчик):

1. Исполнитель обеспечивает вывод сайта Заказчика в ТОП-10 Яндекс по 30 ключевым запросам.

2. KPI: рост органического трафика на 50% за 6 месяцев.

3. Стоимость: 45 000 (сорок пять тысяч) рублей в месяц.

4. Срок: 6 месяцев, 01.12.2025 – 31.05.2026.
""",
            "answer": {
                "document_type": "Договор на оказание услуг поискового продвижения",
                "counterparty": "ИП Тихонов Вадим Александрович",
                "subject": "Продвижение сайта в поисковых системах по ключевым запросам",
                "date_signed": "2025-11-15",
                "date_start": "2025-12-01",
                "date_end": "2026-05-31",
                "amount": "45 000 руб.",
                "special_conditions": [
                    "Выход в ТОП-10 Яндекс по 30 ключевым запросам",
                    "Рост органического трафика на 50% за 6 месяцев",
                ],
                "parties": ["ООО «ВебПродвижение»", "ИП Тихонов Вадим Александрович"],
                "is_template": False,
                "payment_terms": None,
                "payment_amount": None,
                "payment_frequency": "monthly",
                "payment_direction": "income",
            },
        },
        # 30. Договор на SaaS с Corp.
        {
            "doc_text": """СОГЛАШЕНИЕ О КОРПОРАТИВНОМ ПОДКЛЮЧЕНИИ К ПЛАТФОРМЕ

г. Москва                                    1 декабря 2025 года

ООО «ФинТехПлатформа» и FinCloud Corp. (США):

1. FinCloud Corp. предоставляет доступ к облачной финансовой платформе для 500 пользователей.

2. Ежегодная лицензия: 7 500 000 (семь миллионов пятьсот тысяч) рублей.

3. Гарантия доступности (SLA): 99,9%.

4. Срок: 01.01.2026 – 31.12.2026.
""",
            "answer": {
                "document_type": "Соглашение о корпоративном подключении к облачной платформе",
                "counterparty": "FinCloud Corp.",
                "subject": "Предоставление доступа к облачной финансовой платформе для 500 пользователей",
                "date_signed": "2025-12-01",
                "date_start": "2026-01-01",
                "date_end": "2026-12-31",
                "amount": "7 500 000 руб.",
                "special_conditions": [
                    "Лицензия для 500 пользователей",
                    "Гарантия доступности (SLA) — 99,9%",
                ],
                "parties": ["ООО «ФинТехПлатформа»", "FinCloud Corp."],
                "is_template": False,
                "payment_terms": None,
                "payment_amount": None,
                "payment_frequency": "yearly",
                "payment_direction": "expense",
            },
        },
        # 31-50: упрощённые варианты
    ]

    # Генерируем ещё 20 лаконичных вариаций
    extra = [
        ("Договор на оказание консультационных услуг",
         "ООО «ЛегалПартнёр»", "Consulting Services Ltd.", "г. Москва", "2025-01-20",
         "Предоставление юридических консультаций по вопросам корпоративного права",
         "monthly", "expense", "200 000 руб.", [], ["ООО «ЛегалПартнёр»", "Consulting Services Ltd."]),
        ("Договор аренды офиса",
         "ООО «Арендодатель»", "Office Solutions GmbH", "г. Санкт-Петербург", "2025-02-01",
         "Аренда офисного помещения площадью 120 кв.м",
         "monthly", "income", "180 000 руб.", [], ["ООО «Арендодатель»", "Office Solutions GmbH"]),
        ("Договор поставки",
         "ООО «ПоставщикПро»", "Supply Corp.", "г. Казань", "2025-03-10",
         "Поставка промышленных фильтров в количестве 500 штук",
         "once", "income", "1 200 000 руб.", [], ["ООО «ПоставщикПро»", "Supply Corp."]),
        ("Договор подряда",
         "ООО «СтройМастер»", "BuildPro Ltd.", "г. Екатеринбург", "2025-04-05",
         "Ремонт производственного цеха по адресу: г. Екатеринбург, ул. Промышленная, д. 5",
         "once", "income", "3 800 000 руб.", [], ["ООО «СтройМастер»", "BuildPro Ltd."]),
        ("Лицензионный договор",
         "ООО «ПравоБаза»", "LegalTech Inc.", "г. Новосибирск", "2025-05-15",
         "Предоставление неисключительной лицензии на программное обеспечение для юридических фирм",
         "yearly", "income", "960 000 руб.", ["Лицензия для 20 рабочих мест"], ["ООО «ПравоБаза»", "LegalTech Inc."]),
        ("Договор транспортной экспедиции",
         "ООО «ЛогистикПро»", "Transport GmbH", "г. Ростов-на-Дону", "2025-06-20",
         "Организация перевозки грузов автомобильным транспортом",
         "once", "income", "850 000 руб.", [], ["ООО «ЛогистикПро»", "Transport GmbH"]),
        ("Договор оказания услуг связи",
         "ПАО «ТелеКом»", "ООО «Заказчик Плюс»", "г. Москва", "2025-07-01",
         "Предоставление услуг мобильной связи и интернета для корпоративных клиентов",
         "monthly", "income", "75 000 руб.", [], ["ПАО «ТелеКом»", "ООО «Заказчик Плюс»"]),
        ("Договор купли-продажи недвижимости",
         "ООО «НедвижПроект»", "Real Estate Solutions LLC", "г. Сочи", "2025-08-10",
         "Продажа нежилого помещения площадью 450 кв.м",
         "once", "income", "45 000 000 руб.", ["Расчёт через аккредитив"], ["ООО «НедвижПроект»", "Real Estate Solutions LLC"]),
        ("Договор страхования",
         "ПАО «РосСтрах»", "ООО «ТехноГрупп»", "г. Москва", "2025-09-01",
         "Страхование имущества предприятия",
         "yearly", "income", "320 000 руб.", [], ["ПАО «РосСтрах»", "ООО «ТехноГрупп»"]),
        ("Договор факторинга",
         "АО «ФинансБанк»", "ООО «ТоварОптом»", "г. Москва", "2025-10-05",
         "Финансирование под уступку денежного требования на сумму 5 000 000 руб.",
         "monthly", "income", "5 000 000 руб.", ["Комиссия за факторинговое обслуживание — 1,5%"], ["АО «ФинансБанк»", "ООО «ТоварОптом»"]),
        ("Договор аутстаффинга",
         "ООО «КадрОутсорс»", "HRPro Solutions Ltd.", "г. Москва", "2025-11-10",
         "Предоставление персонала для выполнения производственных задач",
         "monthly", "income", "1 100 000 руб.", ["Количество предоставляемых сотрудников — 10 человек"], ["ООО «КадрОутсорс»", "HRPro Solutions Ltd."]),
        ("Агентский договор на продажу авиабилетов",
         "ООО «АвиаТрэвел»", "Airline Corp. Inc.", "г. Санкт-Петербург", "2025-12-01",
         "Реализация авиабилетов от имени авиаперевозчика",
         "monthly", "expense", None,
         ["Агентское вознаграждение — 8% от стоимости реализованных билетов"],
         ["ООО «АвиаТрэвел»", "Airline Corp. Inc."]),
        ("Договор займа",
         "ООО «КредитФонд»", "ИП Захаров Николай Петрович", "г. Воронеж", "2025-01-15",
         "Предоставление займа",
         "monthly", "income", "500 000 руб.",
         ["Процентная ставка — 14% годовых", "Срок возврата — 12 месяцев"],
         ["ООО «КредитФонд»", "ИП Захаров Николай Петрович"]),
        ("Соглашение о партнёрстве",
         "ООО «РусТех»", "TechVentures GmbH", "г. Москва", "2025-02-20",
         "Совместное развитие рынка программного обеспечения в России",
         None, None, None,
         ["Распределение выручки: 60% ООО «РусТех», 40% TechVentures GmbH"],
         ["ООО «РусТех»", "TechVentures GmbH"]),
        ("Договор на оказание охранных услуг",
         "ООО «СекьюрГард»", "ТЦ «МегаМолл»", "г. Краснодар", "2025-03-01",
         "Охрана торгового центра и прилегающей территории",
         "monthly", "income", "380 000 руб.",
         ["Количество охранников — 8 человек", "Режим охраны — круглосуточный"],
         ["ООО «СекьюрГард»", "ТЦ «МегаМолл»"]),
        ("Договор аренды транспортного средства",
         "ИП Медведев Сергей Юрьевич", "ООО «КурьерДоставка»", "г. Тюмень", "2025-04-10",
         "Аренда грузового автомобиля марки Газель NEXT грузоподъёмностью 1,5 тонны",
         "monthly", "income", "55 000 руб.", [],
         ["ИП Медведев Сергей Юрьевич", "ООО «КурьерДоставка»"]),
        ("Договор комиссии",
         "ООО «КомисСион»", "Global Trade Corp.", "г. Москва", "2025-05-05",
         "Реализация товаров комитента на условиях комиссии",
         "monthly", "income", None,
         ["Комиссионное вознаграждение — 15% от суммы реализованных товаров"],
         ["ООО «КомисСион»", "Global Trade Corp."]),
        ("Договор на уборку помещений",
         "ООО «ЧистоПро»", "БЦ «Олимп»", "г. Екатеринбург", "2025-06-01",
         "Ежедневная уборка офисных помещений общей площадью 3 200 кв.м",
         "monthly", "income", "120 000 руб.", [],
         ["ООО «ЧистоПро»", "БЦ «Олимп»"]),
        ("Договор поставки медицинского оборудования",
         "ООО «МедТехника»", "MedEquip GmbH", "г. Москва", "2025-07-15",
         "Поставка аппарата магнитно-резонансной томографии (МРТ) 3 Тесла",
         "once", "income", "62 000 000 руб.",
         ["Шефмонтаж и пусконаладочные работы включены в стоимость",
          "Гарантийный срок — 3 года"],
         ["ООО «МедТехника»", "MedEquip GmbH"]),
        ("Договор на проведение аудита",
         "ООО «АудитЭксперт»", "Audit Partners LLC", "г. Санкт-Петербург", "2025-08-20",
         "Проведение обязательного аудита бухгалтерской отчётности за 2024 год",
         "once", "income", "1 500 000 руб.", [],
         ["ООО «АудитЭксперт»", "Audit Partners LLC"]),
    ]

    for i, (dt, party1, party2, city, date, subj, pf, pd, amount, conditions, parties) in enumerate(extra):
        doc_text = f"""{dt.upper()}

{city}                                    {date}

{party1} и {party2}:

1. Предмет: {subj}.
2. Сумма: {amount if amount else 'определяется дополнительно'}.
{'3. ' + conditions[0] if conditions else ''}
""".strip()

        answer_obj = {
            "document_type": dt,
            "counterparty": party2,
            "subject": subj,
            "date_signed": date,
            "date_start": None,
            "date_end": None,
            "amount": amount,
            "special_conditions": conditions,
            "parties": parties,
            "is_template": False,
            "payment_terms": None,
            "payment_amount": None,
            "payment_frequency": pf,
            "payment_direction": pd,
        }

        tool_call = json.dumps(
            {"name": "extract_metadata", "arguments": answer_obj},
            ensure_ascii=False,
        )
        chosen_content = f"<tool_call>\n{tool_call}\n</tool_call>"

        user_content = (
            "Извлеки метаданные из текста юридического документа.\n\n"
            f"Текст документа:\n{doc_text}"
        )

        variations.append({
            "prompt": [
                {"role": "system", "content": NEW_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "chosen": [{"role": "assistant", "content": chosen_content}],
            "rejected": None,
            "_source": "sft_en_ru",
        })

    # Convert the first 5 items (with doc_text/answer structure) to examples
    result = []
    for item in variations[:5]:
        if "doc_text" in item:
            answer_obj = item["answer"]
            tool_call = json.dumps(
                {"name": "extract_metadata", "arguments": answer_obj},
                ensure_ascii=False,
            )
            chosen_content = f"<tool_call>\n{tool_call}\n</tool_call>"
            user_content = (
                "Извлеки метаданные из текста юридического документа.\n\n"
                f"Текст документа:\n{item['doc_text'].strip()}"
            )
            result.append({
                "prompt": [
                    {"role": "system", "content": NEW_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "chosen": [{"role": "assistant", "content": chosen_content}],
                "rejected": None,
                "_source": "sft_en_ru",
            })
        else:
            result.append(item)

    # Add the "extra" tuple-based ones
    result.extend(variations[5:])
    return result


# ── Статистика ─────────────────────────────────────────────────────────────────

def collect_stats(examples: list) -> dict:
    total = len(examples)
    sft_only = sum(1 for e in examples if e.get("rejected") is None)
    preference = total - sft_only
    cs = sum(1 for e in examples if e.get("_source") in ("stress_dpo", "dpo_cs"))
    en_ru = sum(1 for e in examples if e.get("_source") == "sft_en_ru")

    # payment_frequency distribution
    pf_counts: dict = {}
    for e in examples:
        chosen = e.get("chosen", [])
        if not chosen:
            continue
        content = chosen[0].get("content", "")
        m = re.search(r'"payment_frequency"\s*:\s*"?([^",\}\s]+)"?', content)
        if m:
            pf = m.group(1).strip('"').strip("'").strip()
            pf_counts[pf] = pf_counts.get(pf, 0) + 1
        else:
            pf_counts["null/absent"] = pf_counts.get("null/absent", 0) + 1

    return {
        "total": total,
        "sft_only": sft_only,
        "preference": preference,
        "code_switching": cs,
        "en_ru_augmentation": en_ru,
        "payment_frequency": dict(sorted(pf_counts.items(), key=lambda x: -x[1])),
    }


def split_train_val(examples: list, val_ratio: float = 0.1) -> tuple[list, list]:
    """Разделить на train/val, сохраняя пропорции источников."""
    import random
    random.seed(42)

    by_source: dict = {}
    for e in examples:
        src = e.get("_source", "unknown")
        by_source.setdefault(src, []).append(e)

    train, val = [], []
    for src, items in by_source.items():
        random.shuffle(items)
        n_val = max(1, int(len(items) * val_ratio))
        if len(items) <= 2:
            train.extend(items)
        else:
            val.extend(items[:n_val])
            train.extend(items[n_val:])

    random.shuffle(train)
    random.shuffle(val)
    return train, val


def write_jsonl(path: Path, examples: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for e in examples:
            # Убрать внутреннее поле _source из финального файла
            out = {k: v for k, v in e.items() if k != "_source"}
            f.write(json.dumps(out, ensure_ascii=False) + "\n")


# ── MAIN ───────────────────────────────────────────────────────────────────────

def main():
    print("Загружаем SFT train (v2_train.jsonl)...")
    sft_train = load_sft(TRAINING / "v2_train.jsonl")
    print(f"  → {len(sft_train)} SFT train примеров")

    print("Загружаем SFT val (v2_val.jsonl)...")
    sft_val = load_sft(TRAINING / "v2_val.jsonl")
    print(f"  → {len(sft_val)} SFT val примеров")

    print("Загружаем DPO train (v2_dpo_train.jsonl)...")
    dpo_train = load_dpo(TRAINING / "v2_dpo_train.jsonl")
    print(f"  → {len(dpo_train)} DPO train примеров")

    print("Загружаем DPO val (v2_dpo_val.jsonl)...")
    dpo_val = load_dpo(TRAINING / "v2_dpo_val.jsonl")
    print(f"  → {len(dpo_val)} DPO val примеров")

    print("Загружаем DPO code-switching (v2_dpo_codeswitching.jsonl) + фикс enum...")
    dpo_cs = load_dpo(TRAINING / "v2_dpo_codeswitching.jsonl", fix_enums=True)
    for e in dpo_cs:
        e["_source"] = "dpo_cs"
    print(f"  → {len(dpo_cs)} DPO code-switching примеров")

    print("Генерируем stress DPO пары из stress-report (60 документов)...")
    stress_dpo = generate_stress_dpo_pairs()
    print(f"  → {len(stress_dpo)} stress DPO примеров")

    print("Генерируем EN→RU SFT аугментации (25 базовых + 25 вариаций)...")
    en_ru_base = generate_en_ru_augmentations()
    en_ru_var = make_variations()
    en_ru_all = en_ru_base + en_ru_var
    print(f"  → {len(en_ru_all)} EN→RU SFT примеров")

    # Объединяем всё
    all_train_raw = sft_train + dpo_train + dpo_cs + stress_dpo + en_ru_all
    all_val_raw = sft_val + dpo_val

    print(f"\nВсего до split: train={len(all_train_raw)}, val={len(all_val_raw)}")

    # stress и en_ru тоже частично в val
    stress_train, stress_val = split_train_val(stress_dpo, val_ratio=0.1)
    en_ru_train, en_ru_val = split_train_val(en_ru_all, val_ratio=0.1)

    # Финальные множества
    train_set = sft_train + dpo_train + dpo_cs + stress_train + en_ru_train
    val_set = sft_val + dpo_val + stress_val + en_ru_val

    print(f"Финально: train={len(train_set)}, val={len(val_set)}")

    # Сохраняем
    out_train = TRAINING / "v3_orpo_train.jsonl"
    out_val = TRAINING / "v3_orpo_val.jsonl"
    write_jsonl(out_train, train_set)
    write_jsonl(out_val, val_set)
    print(f"\nСохранено: {out_train}")
    print(f"Сохранено: {out_val}")

    # Статистика
    print("\n" + "=" * 60)
    print("СТАТИСТИКА v3_orpo_train.jsonl")
    print("=" * 60)
    stats = collect_stats(train_set)
    for k, v in stats.items():
        if isinstance(v, dict):
            print(f"  {k}:")
            for kk, vv in v.items():
                print(f"    {kk}: {vv}")
        else:
            print(f"  {k}: {v}")

    print("\n" + "=" * 60)
    print("СТАТИСТИКА v3_orpo_val.jsonl")
    print("=" * 60)
    stats_val = collect_stats(val_set)
    for k, v in stats_val.items():
        if isinstance(v, dict):
            print(f"  {k}:")
            for kk, vv in v.items():
                print(f"    {kk}: {vv}")
        else:
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
