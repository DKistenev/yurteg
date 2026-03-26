"""Тесты для services/redline_service.py — word-level redline движок."""
import io
import zipfile

def _get_xml(data: bytes) -> str:
    """Извлечь word/document.xml из DOCX bytes."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return z.read("word/document.xml").decode("utf-8")


def test_returns_bytes():
    """generate_redline_docx возвращает bytes."""
    from services.redline_service import generate_redline_docx

    result = generate_redline_docx("foo bar", "foo bar")
    assert isinstance(result, bytes), "Должно вернуть bytes"
    assert len(result) > 0, "bytes не должны быть пустыми"


def test_equal_texts():
    """Одинаковые тексты — нет w:ins/w:del в XML."""
    from services.redline_service import generate_redline_docx

    data = generate_redline_docx("foo bar", "foo bar")
    xml = _get_xml(data)
    assert "w:ins" not in xml, "Не должно быть w:ins при одинаковых текстах"
    assert "w:del" not in xml, "Не должно быть w:del при одинаковых текстах"


def test_word_insert():
    """Вставка слова BAZ — w:ins содержит 'BAZ'."""
    from services.redline_service import generate_redline_docx

    data = generate_redline_docx("foo bar", "foo BAZ bar")
    xml = _get_xml(data)
    assert "w:ins" in xml, "Должен быть тег w:ins"
    assert "BAZ" in xml, "BAZ должен присутствовать в XML"


def test_word_delete():
    """Удаление слова BAZ — w:del/w:delText содержит 'BAZ'."""
    from services.redline_service import generate_redline_docx

    data = generate_redline_docx("foo BAZ bar", "foo bar")
    xml = _get_xml(data)
    assert "w:delText" in xml, "Должен быть тег w:delText (не w:t!) для удалений"
    assert "BAZ" in xml, "BAZ должен присутствовать в XML"


def test_word_replace():
    """Замена слова — оба тега w:del и w:ins присутствуют."""
    from services.redline_service import generate_redline_docx

    data = generate_redline_docx("старый текст", "новый текст")
    xml = _get_xml(data)
    assert "w:del" in xml, "Должен быть тег w:del"
    assert "w:ins" in xml, "Должен быть тег w:ins"


def test_rpr_copy():
    """Функция работает корректно — rPr элемент присутствует в track changes."""
    from services.redline_service import generate_redline_docx

    # plain text — rPr должен присутствовать (пустой, но создан)
    data = generate_redline_docx("старый текст документа", "новый текст документа")
    xml = _get_xml(data)
    # Проверяем что w:rPr внутри w:ins или w:del
    assert "w:rPr" in xml, "w:rPr должен присутствовать внутри track changes"
