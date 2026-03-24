"""Тесты модуля scanner — сканирование директории и хеширование файлов."""
import pytest
from pathlib import Path

from config import Config
from modules.scanner import compute_file_hash, scan_directory


@pytest.fixture
def cfg():
    """Конфиг по умолчанию."""
    return Config()


# ── compute_file_hash ──────────────────────────────────────────────────────────

def test_compute_file_hash_deterministic(tmp_path):
    """Один и тот же файл даёт один и тот же хеш при двух вызовах."""
    f = tmp_path / "test.bin"
    f.write_bytes(b"hello world")
    h1 = compute_file_hash(f)
    h2 = compute_file_hash(f)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_compute_file_hash_different(tmp_path):
    """Разные файлы дают разные хеши."""
    f1 = tmp_path / "a.bin"
    f2 = tmp_path / "b.bin"
    f1.write_bytes(b"aaa")
    f2.write_bytes(b"bbb")
    assert compute_file_hash(f1) != compute_file_hash(f2)


# ── scan_directory ─────────────────────────────────────────────────────────────

def test_scan_empty_directory(tmp_path, cfg):
    """Пустая директория возвращает пустой список."""
    result = scan_directory(tmp_path, cfg)
    assert result == []


def test_scan_finds_pdf_and_docx(tmp_path, cfg):
    """Директория с .pdf и .docx возвращает два FileInfo."""
    (tmp_path / "doc.pdf").write_bytes(b"%PDF-1.4 dummy")
    (tmp_path / "doc.docx").write_bytes(b"PK dummy")
    result = scan_directory(tmp_path, cfg)
    assert len(result) == 2
    exts = {fi.extension for fi in result}
    assert ".pdf" in exts
    assert ".docx" in exts


def test_scan_ignores_unsupported(tmp_path, cfg):
    """Файлы .txt и .jpg игнорируются."""
    (tmp_path / "file.txt").write_text("hello")
    (tmp_path / "image.jpg").write_bytes(b"\xff\xd8\xff dummy")
    result = scan_directory(tmp_path, cfg)
    assert result == []


def test_scan_nested_directories(tmp_path, cfg):
    """Файлы во вложенных папках находятся через rglob."""
    sub = tmp_path / "sub" / "nested"
    sub.mkdir(parents=True)
    (sub / "contract.pdf").write_bytes(b"%PDF-1.4 dummy")
    result = scan_directory(tmp_path, cfg)
    assert len(result) == 1
    assert result[0].filename == "contract.pdf"


def test_scan_skips_large_files(tmp_path):
    """Файл, превышающий max_file_size_mb, пропускается."""
    cfg = Config()
    # 1 байт + tiny limit = гарантированный пропуск
    cfg = Config(max_file_size_mb=0)
    f = tmp_path / "big.pdf"
    f.write_bytes(b"%PDF-1.4 " + b"x" * 1024)  # 1 KB > 0 MB
    result = scan_directory(tmp_path, cfg)
    assert result == []


def test_scan_nonexistent_directory(cfg):
    """Несуществующая директория вызывает FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        scan_directory(Path("/nonexistent/path/xyz"), cfg)


def test_scan_file_info_fields(tmp_path, cfg):
    """FileInfo содержит корректные поля path, filename, extension, size_bytes, file_hash."""
    content = b"%PDF-1.4 dummy content"
    f = tmp_path / "sample.pdf"
    f.write_bytes(content)
    result = scan_directory(tmp_path, cfg)
    assert len(result) == 1
    fi = result[0]
    assert fi.filename == "sample.pdf"
    assert fi.extension == ".pdf"
    assert fi.size_bytes == len(content)
    assert len(fi.file_hash) == 64


def test_scan_sorted_by_filename(tmp_path, cfg):
    """Результат отсортирован по имени файла."""
    for name in ("z.pdf", "a.pdf", "m.docx"):
        (tmp_path / name).write_bytes(b"dummy")
    result = scan_directory(tmp_path, cfg)
    filenames = [fi.filename for fi in result]
    assert filenames == sorted(filenames)
