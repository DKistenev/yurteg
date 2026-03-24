"""Тесты версионирования документов (Phase 2).

LIFE-03: Два варианта одного договора связываются; несвязанные — нет
LIFE-04: Redline .docx открывается без ошибок, содержит w:ins/w:del

Wave 0: тест-скелеты созданы до реализации (RED стадия).
Assertions дополняются после 02-03 (version_service) и 02-04 (diff/redline).
"""
import pytest


@pytest.fixture
def temp_db(tmp_path):
    """Создаёт временную БД с миграциями для тестов."""
    try:
        from modules.database import Database
        db = Database(tmp_path / "test.db")
        yield db
        db.close()
    except ImportError:
        pytest.skip("modules.database недоступен — запустите после 02-01")


def test_auto_version_linking(temp_db):
    """LIFE-03: Два договора связываются как версии через link_versions; несвязанный — нет."""
    from services.version_service import link_versions, get_version_group

    db = temp_db
    conn = db.conn

    # Добавить два договора одного контрагента и типа
    conn.execute(
        "INSERT INTO contracts (filename, original_path, status, counterparty, contract_type) "
        "VALUES ('nda_v1.pdf', '/tmp/n1.pdf', 'done', 'Альфа', 'NDA')"
    )
    conn.execute(
        "INSERT INTO contracts (filename, original_path, status, counterparty, contract_type) "
        "VALUES ('nda_v2.pdf', '/tmp/n2.pdf', 'done', 'Альфа', 'NDA')"
    )
    # Добавить несвязанный договор
    conn.execute(
        "INSERT INTO contracts (filename, original_path, status, counterparty, contract_type) "
        "VALUES ('other.pdf', '/tmp/o.pdf', 'done', 'Бета', 'Поставка')"
    )
    conn.commit()

    cid1 = conn.execute("SELECT id FROM contracts WHERE filename='nda_v1.pdf'").fetchone()[0]
    cid2 = conn.execute("SELECT id FROM contracts WHERE filename='nda_v2.pdf'").fetchone()[0]

    # Связываем: cid1 — первая версия (group_id=None → group_id=cid1)
    group_id = link_versions(db, cid1, group_id=None)
    # cid2 — вторая версия в той же группе
    link_versions(db, cid2, group_id=group_id)

    versions = get_version_group(db, cid1)
    linked_ids = {v.contract_id for v in versions}
    assert cid1 in linked_ids, "cid1 должен быть в своей группе версий"
    assert cid2 in linked_ids, "cid2 должен быть связан с той же группой"

    cid_other = conn.execute("SELECT id FROM contracts WHERE filename='other.pdf'").fetchone()[0]
    versions_other = get_version_group(db, cid_other)
    assert len(versions_other) == 0, "Несвязанный договор не должен попасть ни в какую группу"


def test_redline_generation():
    """LIFE-04: generate_redline_docx возвращает валидный .docx с w:del/w:ins."""
    from services.version_service import generate_redline_docx
    import zipfile
    import io

    old_text = "Договор действует один год. Сумма составляет 100 000 рублей."
    new_text = "Договор действует два года. Сумма составляет 150 000 рублей."

    docx_bytes = generate_redline_docx(old_text, new_text, title="Тест редлайна")

    assert isinstance(docx_bytes, bytes), "Должны вернуться bytes"
    assert docx_bytes[:2] == b"PK", "Файл должен быть валидным ZIP/docx"
    assert len(docx_bytes) > 1000, f"Слишком маленький файл: {len(docx_bytes)} байт"

    # Проверить наличие w:del или w:ins в document.xml
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
        doc_xml = zf.read("word/document.xml").decode("utf-8")
    assert "w:del" in doc_xml or "w:ins" in doc_xml, \
        "document.xml должен содержать track changes (w:del или w:ins)"
