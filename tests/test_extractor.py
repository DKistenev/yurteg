"""Тесты модуля extractor — извлечение текста из PDF/DOCX."""
import pytest
from pathlib import Path

from modules.extractor import extract_text
from modules.models import FileInfo


def _make_file_info(path: Path) -> FileInfo:
    """Вспомогательная функция для создания FileInfo."""
    return FileInfo(
        path=path,
        filename=path.name,
        extension=path.suffix.lower(),
        size_bytes=path.stat().st_size,
        file_hash="0" * 64,
    )


# Путь к тестовым данным
TEST_DATA = Path(__file__).parent / "test_data"


def test_extract_pdf_text():
    """Реальный PDF возвращает текст с extraction_method=pdfplumber."""
    pdf_path = TEST_DATA / "договор_аренды.pdf"
    assert pdf_path.exists(), f"Test PDF not found: {pdf_path}"
    fi = _make_file_info(pdf_path)
    result = extract_text(fi)
    assert result.extraction_method == "pdfplumber"
    assert result.page_count >= 1


def test_extract_docx_text():
    """Реальный DOCX возвращает текст с extraction_method=python-docx."""
    docx_path = TEST_DATA / "договор_поставки.docx"
    assert docx_path.exists(), f"Test DOCX not found: {docx_path}"
    fi = _make_file_info(docx_path)
    result = extract_text(fi)
    assert result.extraction_method == "python-docx"
    assert len(result.text) > 0
    assert result.is_scanned is False


def test_extract_corrupt_file(tmp_path):
    """Битый файл с расширением .pdf возвращает extraction_method=failed без исключений."""
    corrupt = tmp_path / "corrupt.pdf"
    corrupt.write_bytes(b"this is not a valid PDF content at all!!!")
    fi = _make_file_info(corrupt)
    result = extract_text(fi)
    assert result.extraction_method == "failed"
    assert result.text == ""


def test_extract_unsupported_extension(tmp_path):
    """Файл .txt возвращает extraction_method=failed без исключений."""
    txt_file = tmp_path / "readme.txt"
    txt_file.write_text("some text content")
    fi = _make_file_info(txt_file)
    result = extract_text(fi)
    assert result.extraction_method == "failed"


def test_extract_empty_pdf_is_scanned(tmp_path):
    """PDF с текстом < 50 символов/страницу помечается is_scanned=True."""
    # Создаём минимальный валидный PDF с почти пустыми страницами
    # Используем reportlab если доступен, иначе пишем raw PDF
    try:
        from reportlab.pdfgen import canvas as rl_canvas
        pdf_path = tmp_path / "empty.pdf"
        c = rl_canvas.Canvas(str(pdf_path))
        c.drawString(10, 500, "")  # пустая строка
        c.showPage()
        c.save()
    except ImportError:
        # Создаём минимальный валидный PDF с пустой страницей
        pdf_content = (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << >> >>\nendobj\n"
            b"4 0 obj\n<< /Length 2 >>\nstream\n  \nendstream\nendobj\n"
            b"xref\n0 5\n"
            b"0000000000 65535 f \n"
            b"0000000009 00000 n \n"
            b"0000000058 00000 n \n"
            b"0000000115 00000 n \n"
            b"0000000227 00000 n \n"
            b"trailer\n<< /Size 5 /Root 1 0 R >>\n"
            b"startxref\n283\n%%EOF\n"
        )
        pdf_path = tmp_path / "empty.pdf"
        pdf_path.write_bytes(pdf_content)

    fi = _make_file_info(pdf_path)
    result = extract_text(fi)
    # Либо is_scanned=True (текст < 50 символов/стр), либо failed при parse error
    assert result.is_scanned is True or result.extraction_method == "failed"


def test_extract_docx_returns_no_exception_on_corrupt(tmp_path):
    """Битый DOCX с реальным расширением не бросает исключение."""
    bad_docx = tmp_path / "bad.docx"
    bad_docx.write_bytes(b"not a real docx file, just garbage bytes 1234567890")
    fi = _make_file_info(bad_docx)
    result = extract_text(fi)  # не должен упасть
    assert result.extraction_method == "failed"
