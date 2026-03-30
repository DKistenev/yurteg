"""Сервис ревью договора против шаблона-эталона.

Библиотека шаблонов хранится в SQLite (templates table, migration v6).
Сопоставление: авто по типу договора через косинусное сходство эмбеддингов.
Отступления: difflib sentence-level diff с цветовой разметкой.

Не зависит от UI-слоя.
"""
import difflib
import logging
import re
from typing import Optional

from modules.database import Database
from modules.models import Template
from services.redline_service import generate_redline_docx
from services.version_service import (
    TEMPLATE_MATCH_THRESHOLD,
    _cosine_sim,
    compute_embedding,
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
    if not content_text or not content_text.strip():
        raise ValueError("Нельзя сохранить пустой шаблон")
    with db.lock:
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

    Извлекает contract_type, filename, subject, full_text из contracts.
    Сохраняет embedding в template_embeddings для кэша.
    Returns: template id или None если contract не найден.
    """
    with db.lock:
        row = db.conn.execute(
            "SELECT contract_type, filename, subject, original_path, full_text FROM contracts WHERE id=?",
            (contract_id,),
        ).fetchone()
    if row is None:
        logger.warning("contract_id=%d не найден", contract_id)
        return None

    contract_type, filename, subject, original_path, full_text = row
    name = template_name or f"Эталон: {filename}"
    content = full_text or subject or filename  # per VEC-02: полный текст приоритетнее

    template_id = add_template(db, contract_type or "Прочее", name, content, original_path)

    if template_id and content:
        import io as _io

        import numpy as _np

        from services.version_service import EMBEDDING_MODEL

        vector = compute_embedding(content)
        buf = _io.BytesIO()
        _np.save(buf, vector)
        file_hash = ""  # нет file_hash у шаблона из реестра — пустая строка как sentinel
        with db.lock:
            db.conn.execute(
                """INSERT OR REPLACE INTO template_embeddings
                   (template_id, file_hash, vector, model_version)
                   VALUES (?, ?, ?, ?)""",
                (template_id, file_hash, buf.getvalue(), EMBEDDING_MODEL),
            )
            db.conn.commit()
        logger.info("Embedding сохранён в template_embeddings для template_id=%d", template_id)

    return template_id


def list_templates(db: Database, contract_type: Optional[str] = None) -> list[Template]:
    """Возвращает активные шаблоны, опционально фильтрует по типу договора."""
    sql = "SELECT id, contract_type, name, original_path, content_text, created_at, is_active FROM templates WHERE is_active=1"
    params: list = []
    if contract_type:
        sql += " AND contract_type=?"
        params.append(contract_type)
    sql += " ORDER BY contract_type, name"

    with db.lock:
        rows = db.conn.execute(sql, params).fetchall()
    return [
        Template(
            id=r[0], contract_type=r[1], name=r[2],
            original_path=r[3], content_text=r[4],
            created_at=r[5], is_active=bool(r[6]),
        )
        for r in rows
    ]


def delete_template(db: Database, template_id: int) -> bool:
    """Мягкое удаление шаблона (is_active=0). Возвращает True если шаблон найден."""
    with db.lock:
        cursor = db.conn.execute(
            "UPDATE templates SET is_active=0 WHERE id=? AND is_active=1",
            (template_id,),
        )
        db.conn.commit()
        deleted = cursor.rowcount > 0
    if deleted:
        logger.info("Шаблон id=%d деактивирован", template_id)
    return deleted


def update_template(db: Database, template_id: int, name: str, contract_type: str) -> bool:
    """Обновляет name и contract_type шаблона. Возвращает True если шаблон найден."""
    with db.lock:
        cursor = db.conn.execute(
            "UPDATE templates SET name=?, contract_type=? WHERE id=? AND is_active=1",
            (name, contract_type, template_id),
        )
        db.conn.commit()
        updated = cursor.rowcount > 0
    if updated:
        logger.info("Шаблон id=%d обновлён: name='%s', type='%s'", template_id, name, contract_type)
    return updated


def match_template(
    db: Database,
    document_text: str,
    contract_type: Optional[str],
) -> Optional[Template]:
    """Автоматически подбирает наиболее похожий шаблон.

    Алгоритм:
    1. Если есть шаблон с точным соответствием contract_type — предпочесть их
    2. Загрузить кэшированные embeddings из template_embeddings (не пересчитывать)
    3. Сравнить косинусное сходство эмбеддингов
    4. Вернуть шаблон с sim >= TEMPLATE_MATCH_THRESHOLD или None

    Returns: Template или None (предложить ручной выбор в UI)
    """
    import io as _io

    import numpy as _np

    from services.version_service import EMBEDDING_MODEL

    templates = list_templates(db, contract_type)  # сначала по типу
    if not templates:
        templates = list_templates(db)  # затем все
    if not templates:
        return None

    doc_vector = compute_embedding(document_text)

    # Загрузить кэшированные embeddings для всех шаблонов
    cached_vectors: dict[int, _np.ndarray] = {}
    with db.lock:
        rows = db.conn.execute(
            "SELECT template_id, vector, model_version FROM template_embeddings"
        ).fetchall()
    for cache_row in rows:
        if cache_row[2] == EMBEDDING_MODEL:  # пропустить если модель изменилась
            cached_vectors[cache_row[0]] = _np.load(_io.BytesIO(cache_row[1]))

    best_sim = 0.0
    best_template = None

    for tmpl in templates:
        if not tmpl.content_text:
            continue
        if tmpl.id in cached_vectors:
            tmpl_vector = cached_vectors[tmpl.id]
        else:
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
    if not text:
        return []
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


def get_redline_for_template(
    db: Database,
    contract_id: int,
    template_id: int,
) -> Optional[bytes]:
    """Генерирует редлайн документа против шаблона-эталона.

    Извлекает тексты из БД (templates.content_text, contracts.full_text).
    Возвращает bytes .docx с word-level track changes или None если данные не найдены.
    """
    with db.lock:
        tmpl_row = db.conn.execute(
            "SELECT content_text, name FROM templates WHERE id=? AND is_active=1",
            (template_id,),
        ).fetchone()
        contract_row = db.conn.execute(
            "SELECT full_text, filename FROM contracts WHERE id=?",
            (contract_id,),
        ).fetchone()

    if tmpl_row is None or contract_row is None:
        logger.warning(
            "get_redline_for_template: не найден template_id=%d или contract_id=%d",
            template_id, contract_id,
        )
        return None

    template_text, template_name = tmpl_row
    contract_text, contract_filename = contract_row

    if not template_text or not contract_text:
        logger.warning(
            "get_redline_for_template: пустой текст (template=%s, contract=%s)",
            bool(template_text), bool(contract_text),
        )
        return None

    title = f"Редлайн: {contract_filename} vs {template_name}"
    return generate_redline_docx(template_text, contract_text, title)
