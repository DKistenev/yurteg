"""Demo данные для empty state реестра.

Вставляет 10 pre-computed контрактов напрямую в SQLite без pipeline.
Используется из registry.py при нажатии «Загрузить тестовые данные».
"""
import hashlib
from datetime import date, timedelta

# ── 10 demo контрактов — разные типы, суммы, статусы ──────────────────────────
# date.today() вычисляется при импорте модуля (один раз при старте сервера),
# что достаточно для демо-целей.

_today = date.today()

DEMO_CONTRACTS = [
    {
        "filename": "Договор_поставки_ИнноТех.pdf",
        "contract_type": "Договор поставки",
        "counterparty": "ООО «ИнноТех»",
        "subject": "Поставка оборудования для офиса",
        "date_start": "2025-01-15",
        "date_end": str(_today + timedelta(days=12)),  # истекает скоро → expiring
        "amount": "1 200 000 ₽",
        "status": "done",
        "confidence": 0.95,
        "validation_score": 0.92,
        "processed_at": "2025-01-16 10:23:00",
        "original_path": "/demo/Договор_поставки_ИнноТех.pdf",
    },
    {
        "filename": "Договор_аренды_Альфа.pdf",
        "contract_type": "Договор аренды",
        "counterparty": "ЗАО «Альфа»",
        "subject": "Аренда нежилого помещения 120 кв.м.",
        "date_start": "2024-06-01",
        "date_end": str(_today + timedelta(days=180)),  # действует
        "amount": "85 000 ₽/мес",
        "status": "done",
        "confidence": 0.97,
        "validation_score": 0.95,
        "processed_at": "2024-06-02 09:15:00",
        "original_path": "/demo/Договор_аренды_Альфа.pdf",
    },
    {
        "filename": "Договор_оказания_услуг_Смирнова.pdf",
        "contract_type": "Договор оказания услуг",
        "counterparty": "ИП Смирнова А.В.",
        "subject": "Оказание юридических услуг",
        "date_start": "2025-03-01",
        "date_end": str(_today + timedelta(days=25)),  # истекает скоро → expiring
        "amount": "320 000 ₽",
        "status": "done",
        "confidence": 0.88,
        "validation_score": 0.85,
        "processed_at": "2025-03-02 14:40:00",
        "original_path": "/demo/Договор_оказания_услуг_Смирнова.pdf",
    },
    {
        "filename": "Трудовой_договор_Петров.pdf",
        "contract_type": "Трудовой договор",
        "counterparty": "Петров И.С.",
        "subject": "Выполнение обязанностей инженера-программиста",
        "date_start": "2024-09-01",
        "date_end": str(_today + timedelta(days=365)),  # бессрочный / долгий
        "amount": "95 000 ₽/мес",
        "status": "done",
        "confidence": 0.99,
        "validation_score": 0.98,
        "processed_at": "2024-09-03 11:00:00",
        "original_path": "/demo/Трудовой_договор_Петров.pdf",
    },
    {
        "filename": "Договор_подряда_СтройГрупп.pdf",
        "contract_type": "Договор подряда",
        "counterparty": "ООО «СтройГрупп»",
        "subject": "Капитальный ремонт офисного помещения",
        "date_start": "2024-11-01",
        "date_end": "2025-11-30",  # истёк
        "amount": "5 000 000 ₽",
        "status": "done",
        "confidence": 0.91,
        "validation_score": 0.88,
        "processed_at": "2024-11-05 16:30:00",
        "original_path": "/demo/Договор_подряда_СтройГрупп.pdf",
    },
    {
        "filename": "NDA_ТехПартнёр.pdf",
        "contract_type": "Лицензионное соглашение",
        "counterparty": "ООО «ТехПартнёр»",
        "subject": "Неразглашение конфиденциальной информации",
        "date_start": "2025-02-01",
        "date_end": str(_today + timedelta(days=400)),  # долгосрочный
        "amount": "—",
        "status": "done",
        "confidence": 0.82,
        "validation_score": 0.75,
        "processed_at": "2025-02-03 13:20:00",
        "original_path": "/demo/NDA_ТехПартнёр.pdf",
    },
    {
        "filename": "Договор_займа_Новиков.pdf",
        "contract_type": "Договор займа",
        "counterparty": "Новиков А.В.",
        "subject": "Кредитная линия на пополнение оборотных средств",
        "date_start": "2024-08-15",
        "date_end": "2025-08-14",  # истёк
        "amount": "500 000 ₽",
        "status": "done",
        "confidence": 0.78,
        "validation_score": 0.65,  # низкий score → попадёт в «требуют внимания»
        "processed_at": "2024-08-16 10:05:00",
        "original_path": "/demo/Договор_займа_Новиков.pdf",
    },
    {
        "filename": "Договор_поставки_ЛогистикПро.pdf",
        "contract_type": "Договор поставки",
        "counterparty": "ИП Логистик Про",
        "subject": "Поставка комплектующих для серверного оборудования",
        "date_start": "2025-09-01",
        "date_end": str(_today + timedelta(days=550)),
        "amount": "750 000 ₽",
        "status": "done",
        "confidence": 0.94,
        "validation_score": 0.90,
        "processed_at": "2025-09-02 09:00:00",
        "original_path": "/demo/Договор_поставки_ЛогистикПро.pdf",
    },
    {
        "filename": "Договор_аренды_КвадратМ.pdf",
        "contract_type": "Договор аренды",
        "counterparty": "ООО «КвадратМ»",
        "subject": "Аренда складского помещения 250 кв.м.",
        "date_start": "2024-04-01",
        "date_end": str(_today - timedelta(days=5)),  # только что истёк
        "amount": "150 000 ₽/мес",
        "status": "done",
        "confidence": 0.96,
        "validation_score": 0.93,
        "processed_at": "2024-04-03 15:10:00",
        "original_path": "/demo/Договор_аренды_КвадратМ.pdf",
    },
    {
        "filename": "Договор_оказания_услуг_МедиаГруп.pdf",
        "contract_type": "Договор оказания услуг",
        "counterparty": "ООО «МедиаГруп»",
        "subject": "Разработка программного обеспечения",
        "date_start": "2025-01-01",
        "date_end": str(_today + timedelta(days=290)),
        "amount": "240 000 ₽",
        "status": "done",
        "confidence": 0.87,
        "validation_score": 0.84,
        "processed_at": "2025-01-02 11:45:00",
        "original_path": "/demo/Договор_оказания_услуг_МедиаГруп.pdf",
    },
]


def insert_demo_contracts(db) -> int:
    """Вставляет demo контракты напрямую в SQLite.

    Args:
        db: Database объект с db.conn (sqlite3.Connection)

    Returns:
        Количество вставленных записей (0 если уже загружены).
    """
    conn = db.conn
    inserted = 0
    for c in DEMO_CONTRACTS:
        file_hash = hashlib.md5(c["filename"].encode("utf-8")).hexdigest()
        # Не дублировать если demo данные уже есть
        existing = conn.execute(
            "SELECT id FROM contracts WHERE file_hash = ?", (file_hash,)
        ).fetchone()
        if existing:
            continue
        conn.execute(
            """
            INSERT INTO contracts (
                filename, original_path, file_hash, status,
                contract_type, counterparty, subject, date_start, date_end,
                amount, confidence, validation_score,
                processed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                c["filename"],
                c["original_path"],
                file_hash,
                c["status"],
                c["contract_type"],
                c["counterparty"],
                c.get("subject", ""),
                c["date_start"],
                c["date_end"],
                c["amount"],
                c["confidence"],
                c["validation_score"],
                c["processed_at"],
            ),
        )
        inserted += 1
    conn.commit()
    return inserted
