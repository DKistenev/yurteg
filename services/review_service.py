"""Сервис ревью договора против шаблона-эталона.

Библиотека шаблонов хранится в SQLite (templates table, migration v6).
Сопоставление: авто по типу договора через косинусное сходство эмбеддингов.
Отступления: difflib sentence-level diff с цветовой разметкой.

Не импортирует streamlit.
"""
import difflib
import logging
import re
from typing import Optional

import numpy as np

from modules.database import Database
from modules.models import Template
from services.version_service import (
    compute_embedding,
    generate_redline_docx,
    TEMPLATE_MATCH_THRESHOLD,
    _cosine_sim,
)

logger = logging.getLogger(__name__)


def add_template(
    db: Database,
    contract_type: str,
    name: str,
    content_text: str,
    original_path: Optional[str] = None,
) -> int:
    """Добавляет шаблон-эталон в библиотеку. Возвращает id нового шаблона."""
    with db._lock:
        cursor = db.conn.execute(
            """INSERT INTO templates (contract_type, name, original_path, content_text)
               VALUES (?, ?, ?, ?)""",
            (contract_type, name, original_path, content_text),
        )
        db.conn.commit()
        template_id = cursor.lastrowid
    logger.info("Шаблон '%s' (%s) добавлен, id=%d", name, contract_type, template_id)
    return template_id


def mark_contract_as_template(
    db: Database,
    contract_id: int,
    template_name: Optional[str] = None,
) -> Optional[int]:
    """Отмечает документ из реестра как шаблон-эталон.

    Извлекает contract_type, filename, subject из contracts.
    Returns: template id или None если contract не найден.
    """
    with db._lock:
        row = db.conn.execute(
            "SELECT contract_type, filename, subject, original_path FROM contracts WHERE id=?",
            (contract_id,),
        ).fetchone()
    if row is None:
        logger.warning("contract_id=%d не найден", contract_id)
        return None

    contract_type, filename, subject, original_path = row
    name = template_name or f"Эталон: {filename}"
    content = subject or filename  # используем subject как контент если нет полного текста

    return add_template(db, contract_type or "Прочее", name, content, original_path)


def list_templates(db: Database, contract_type: Optional[str] = None) -> list[Template]:
    """Возвращает активные шаблоны, опционально фильтрует по типу договора."""
    sql = "SELECT id, contract_type, name, original_path, content_text, created_at, is_active FROM templates WHERE is_active=1"
    params: list = []
    if contract_type:
        sql += " AND contract_type=?"
        params.append(contract_type)
    sql += " ORDER BY contract_type, name"

    with db._lock:
        rows = db.conn.execute(sql, params).fetchall()
    return [
        Template(
            id=r[0], contract_type=r[1], name=r[2],
            original_path=r[3], content_text=r[4],
            created_at=r[5], is_active=bool(r[6]),
        )
        for r in rows
    ]


def match_template(
    db: Database,
    document_text: str,
    contract_type: Optional[str],
) -> Optional[Template]:
    """Автоматически подбирает наиболее похожий шаблон.

    Алгоритм:
    1. Если есть шаблон с точным соответствием contract_type — предпочесть их
    2. Сравнить косинусное сходство эмбеддингов
    3. Вернуть шаблон с sim >= TEMPLATE_MATCH_THRESHOLD или None

    Returns: Template или None (предложить ручной выбор в UI)
    """
    templates = list_templates(db, contract_type)  # сначала по типу
    if not templates:
        templates = list_templates(db)  # затем все
    if not templates:
        return None

    doc_vector = compute_embedding(document_text)

    best_sim = 0.0
    best_template = None

    for tmpl in templates:
        if not tmpl.content_text:
            continue
        tmpl_vector = compute_embedding(tmpl.content_text)
        sim = _cosine_sim(doc_vector, tmpl_vector)
        if sim > best_sim:
            best_sim = sim
            best_template = tmpl

    if best_sim >= TEMPLATE_MATCH_THRESHOLD:
        logger.info(
            "Подобран шаблон '%s' (sim=%.3f)", best_template.name, best_sim
        )
        return best_template

    logger.info(
        "Шаблон не подобран автоматически (best_sim=%.3f < threshold=%.2f)",
        best_sim, TEMPLATE_MATCH_THRESHOLD,
    )
    return None


def _split_sentences(text: str) -> list[str]:
    """Разбивает текст на предложения."""
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]


# Цвета для разметки отступлений в HTML
_DIFF_COLORS = {
    "added":   "#bbf7d0",  # зелёный фон — добавлено в договоре
    "removed": "#fecaca",  # красный фон — есть в шаблоне, нет в договоре
    "changed": "#fef3c7",  # жёлтый фон — изменено (пара delete+insert)
}


def review_against_template(
    template_text: str,
    document_text: str,
) -> list[dict]:
    """Сравнивает документ с шаблоном. Возвращает список отступлений.

    Каждое отступление:
        {"type": "added"|"removed"|"changed",
         "template_text": str|None,
         "document_text": str|None,
         "color": hex_color}

    "added" — есть в документе, нет в шаблоне
    "removed" — есть в шаблоне, нет в документе
    "changed" — заменено (одновременно delete+insert)
    """
    template_sents = _split_sentences(template_text)
    document_sents = _split_sentences(document_text)

    matcher = difflib.SequenceMatcher(None, template_sents, document_sents)
    result = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        elif tag == "replace":
            result.append({
                "type": "changed",
                "template_text": " ".join(template_sents[i1:i2]),
                "document_text": " ".join(document_sents[j1:j2]),
                "color": _DIFF_COLORS["changed"],
            })
        elif tag == "delete":
            result.append({
                "type": "removed",
                "template_text": " ".join(template_sents[i1:i2]),
                "document_text": None,
                "color": _DIFF_COLORS["removed"],
            })
        elif tag == "insert":
            result.append({
                "type": "added",
                "template_text": None,
                "document_text": " ".join(document_sents[j1:j2]),
                "color": _DIFF_COLORS["added"],
            })

    return result
