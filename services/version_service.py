"""Сервис версионирования документов.

Использует sentence-transformers MiniLM-L12-v2 для семантического
сравнения текстов договоров. Вектора кэшируются в SQLite (embeddings table).

Не импортирует streamlit — вызывается из controller и main.py.
"""
import io
import json
import logging
import threading
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from modules.models import ContractMetadata

import numpy as np

from modules.database import Database
from modules.models import DocumentVersion
from services.redline_service import generate_redline_docx  # noqa: F401 — re-export

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
VERSION_LINK_THRESHOLD = 0.85    # sim >= 0.85 → версия того же договора
TEMPLATE_MATCH_THRESHOLD = 0.92  # sim >= 0.92 → тот же шаблон с другими реквизитами

_model = None
_model_lock = threading.Lock()


def get_embedding_model():
    """Загружает модель один раз (lazy singleton). Thread-safe."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer
                logger.info("Загрузка embedding-модели %s...", EMBEDDING_MODEL)
                _model = SentenceTransformer(EMBEDDING_MODEL)
                logger.info("Embedding-модель загружена")
    return _model


def compute_embedding(text: str) -> np.ndarray:
    """Вычисляет 384-мерный вектор для текста. Передаёт полный текст — модель усечёт до max_seq_length."""
    model = get_embedding_model()
    return model.encode(text, normalize_embeddings=True)


def _store_embedding(conn, contract_id: int, vector: np.ndarray) -> None:
    buf = io.BytesIO()
    np.save(buf, vector)
    conn.execute(
        "INSERT OR REPLACE INTO embeddings (contract_id, vector, model_version) VALUES (?,?,?)",
        (contract_id, buf.getvalue(), EMBEDDING_MODEL),
    )
    conn.commit()


def _load_embedding(conn, contract_id: int) -> Optional[np.ndarray]:
    row = conn.execute(
        "SELECT vector, model_version FROM embeddings WHERE contract_id=?",
        (contract_id,),
    ).fetchone()
    if row is None:
        return None
    # Если модель изменилась — вернуть None для пересчёта
    if row[1] != EMBEDDING_MODEL:
        return None
    return np.load(io.BytesIO(row[0]))


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def ensure_embedding(db: Database, contract_id: int, text: str) -> np.ndarray:
    """Возвращает кэшированный вектор или вычисляет и сохраняет новый. Thread-safe."""
    with db._lock:
        cached = _load_embedding(db.conn, contract_id)
        if cached is not None:
            return cached
        vector = compute_embedding(text)
        _store_embedding(db.conn, contract_id, vector)
    return vector


def find_version_match(
    db: Database,
    contract_id: int,
    text: str,
    contract_number: Optional[str] = None,
    parties: Optional[list[str]] = None,
    # Legacy params — kept for backward compatibility, not used in new algorithm
    contract_type: Optional[str] = None,
    counterparty: Optional[str] = None,
) -> Optional[int]:
    """Ищет существующий документ, который является предыдущей версией этого.

    Алгоритм (двухпутевой):
    Путь 1: Номер договора совпал → версия (100% точность)
    Путь 2: Стороны совпали + embedding >= 0.85 → версия (ловит смену номера)

    Пути работают независимо (ИЛИ). Это позволяет поймать версию
    даже если контрагент сменил номер договора при правке.

    Returns: contract_group_id существующей группы или None (новый документ)
    """
    new_vector = ensure_embedding(db, contract_id, text)
    parties_set = set(parties) if parties else set()

    # Загрузить всех кандидатов (с версиями) один раз
    with db._lock:
        candidates = db.conn.execute(
            """
            SELECT c.id, dv.contract_group_id, c.contract_number, c.parties
            FROM contracts c
            JOIN document_versions dv ON dv.contract_id = c.id
            WHERE c.id != ? AND c.status = 'done'
            """,
            (contract_id,),
        ).fetchall()

    if not candidates:
        return None

    best_sim = 0.0
    best_group_id = None
    number_match_group = None

    with db._lock:
        for row in candidates:
            cand_id, group_id, cand_number, cand_parties_json = row

            # Путь 1: номер совпал
            if contract_number and cand_number and contract_number == cand_number:
                logger.info(
                    "Версия по номеру: contract_id=%d → group_id=%d (номер=%s)",
                    contract_id, group_id, contract_number,
                )
                number_match_group = group_id

            # Путь 2: стороны совпали → проверить embedding
            if parties_set:
                try:
                    cand_parties = set(json.loads(cand_parties_json)) if cand_parties_json else set()
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning("Не удалось разобрать parties для id=%d: %s", cand_id, e)
                    cand_parties = set()

                if cand_parties and parties_set == cand_parties:
                    cand_vector = _load_embedding(db.conn, cand_id)
                    if cand_vector is not None:
                        sim = _cosine_sim(new_vector, cand_vector)
                        if sim > best_sim:
                            best_sim = sim
                            best_group_id = group_id

    # Путь 1 приоритетнее (точный)
    if number_match_group is not None:
        return number_match_group

    # Путь 2: стороны + embedding
    if best_sim >= VERSION_LINK_THRESHOLD:
        logger.info(
            "Версия по сторонам+embed: contract_id=%d → group_id=%d (sim=%.3f)",
            contract_id, best_group_id, best_sim,
        )
        return best_group_id

    return None


def link_versions(
    db: Database,
    contract_id: int,
    group_id: Optional[int],
    link_method: str = "auto_embedding",
) -> int:
    """Связывает документ с группой версий или создаёт новую группу.

    Returns: contract_group_id (существующий или новый)
    """
    with db._lock:
        if group_id is None:
            # Новый договор — group_id = contract_id (convention)
            effective_group_id = contract_id
        else:
            effective_group_id = group_id

        # Определить следующий version_number в группе
        row = db.conn.execute(
            "SELECT MAX(version_number) FROM document_versions WHERE contract_group_id=?",
            (effective_group_id,),
        ).fetchone()
        next_version = (row[0] or 0) + 1

        db.conn.execute(
            """INSERT INTO document_versions
               (contract_group_id, contract_id, version_number, link_method)
               VALUES (?, ?, ?, ?)""",
            (effective_group_id, contract_id, next_version, link_method),
        )
        db.conn.commit()

    logger.info(
        "Документ contract_id=%d добавлен в группу %d как v%d (%s)",
        contract_id, effective_group_id, next_version, link_method,
    )
    return effective_group_id


def diff_versions(
    meta_old: "ContractMetadata",
    meta_new: "ContractMetadata",
) -> list[dict]:
    """Сравнивает метаданные двух версий договора.

    Returns: список изменений, каждое:
        {"field": "Контрагент", "old": "...", "new": "...", "changed": True/False}
    """
    from dataclasses import asdict
    from modules.models import ContractMetadata  # noqa: F401 (type hint import)

    _DIFF_FIELDS = [
        ("contract_type",     "Тип договора"),
        ("counterparty",      "Контрагент"),
        ("subject",           "Предмет"),
        ("date_signed",       "Дата подписания"),
        ("date_start",        "Дата начала"),
        ("date_end",          "Дата окончания"),
        ("amount",            "Сумма"),
        ("payment_amount",    "Сумма платежа"),
        ("payment_frequency", "Периодичность"),
        ("payment_direction", "Направление платежа"),
    ]

    old_d = asdict(meta_old)
    new_d = asdict(meta_new)
    result = []
    for field_key, field_label in _DIFF_FIELDS:
        old_val = str(old_d.get(field_key) or "—")
        new_val = str(new_d.get(field_key) or "—")
        result.append({
            "field": field_label,
            "old": old_val,
            "new": new_val,
            "changed": old_val != new_val,
        })
    return result



def get_version_group(db: Database, contract_id: int) -> list[DocumentVersion]:
    """Возвращает все версии договора из той же группы, отсортированные по version_number."""
    with db._lock:
        # Найти group_id для этого contract_id
        row = db.conn.execute(
            "SELECT contract_group_id FROM document_versions WHERE contract_id=?",
            (contract_id,),
        ).fetchone()
        if row is None:
            return []
        group_id = row[0]

        rows = db.conn.execute(
            """SELECT id, contract_group_id, contract_id, version_number,
                      link_method, created_at, linked_at
               FROM document_versions
               WHERE contract_group_id=?
               ORDER BY version_number ASC""",
            (group_id,),
        ).fetchall()

    return [
        DocumentVersion(
            id=r[0], contract_group_id=r[1], contract_id=r[2],
            version_number=r[3], link_method=r[4],
            created_at=r[5], linked_at=r[6],
        )
        for r in rows
    ]
