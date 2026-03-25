"""Тесты контроллера — оркестрация пайплайна с замоканными модулями."""
import pytest
from unittest.mock import patch, MagicMock

from config import Config
from modules.models import (
    FileInfo, ExtractedText, ContractMetadata,
)


# ── Фикстуры ──────────────────────────────────────────────────────────────────

@pytest.fixture
def cfg():
    return Config(active_provider="ollama")


@pytest.fixture
def sample_file_info(tmp_path):
    f = tmp_path / "sample.pdf"
    f.write_bytes(b"%PDF-1.4 test content")
    return FileInfo(
        path=f,
        filename="sample.pdf",
        extension=".pdf",
        size_bytes=f.stat().st_size,
        file_hash="abc123" + "0" * 58,
    )


@pytest.fixture
def sample_text():
    return ExtractedText(
        text="Договор оказания услуг между сторонами",
        page_count=1,
        is_scanned=False,
        extraction_method="pdfplumber",
    )


@pytest.fixture
def sample_metadata():
    return ContractMetadata(
        contract_type="Договор оказания услуг",
        counterparty="ООО Тест",
        date_signed="2024-01-01",
    )


# ── Controller.__init__ ────────────────────────────────────────────────────────

def test_controller_init(cfg):
    """Controller(config) создаёт экземпляр без ошибок."""
    with patch("controller.get_provider") as mock_prov, \
         patch("controller.get_fallback_provider") as mock_fall:
        mock_prov.return_value = MagicMock()
        mock_fall.return_value = MagicMock()
        from controller import Controller
        ctrl = Controller(cfg)
        assert ctrl.config is cfg
        assert ctrl._provider is not None


# ── process_archive — пустая директория ───────────────────────────────────────

def test_process_archive_empty_dir(cfg, tmp_path):
    """Пустая исходная директория возвращает total=0, report_path=None."""
    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "output"
    output.mkdir()

    with patch("controller.get_provider", return_value=MagicMock()), \
         patch("controller.get_fallback_provider", return_value=MagicMock()), \
         patch("controller.scan_directory", return_value=[]), \
         patch("controller.Database") as mock_db_cls:
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        from controller import Controller
        ctrl = Controller(cfg)
        result = ctrl.process_archive(source, output_dir_override=output)

    assert result["total"] == 0
    assert result["done"] == 0
    assert result["report_path"] is None


# ── process_archive — вызов пайплайна ─────────────────────────────────────────

def test_process_archive_calls_pipeline(
    cfg, tmp_path, sample_file_info, sample_text, sample_metadata
):
    """Пайплайн вызывает scan → extract → ai → organize → save."""
    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "output"
    output.mkdir()

    mock_db = MagicMock()
    mock_db.is_processed.return_value = False
    mock_db.get_all_results.return_value = []
    mock_db.get_contract_id_by_hash.return_value = None

    with patch("controller.get_provider", return_value=MagicMock()), \
         patch("controller.get_fallback_provider", return_value=MagicMock()), \
         patch("controller.scan_directory", return_value=[sample_file_info]), \
         patch("controller.extract_text", return_value=sample_text), \
         patch("controller.extract_metadata", return_value=sample_metadata), \
         patch("controller.organize_file", return_value=output / "done" / "sample.pdf"), \
         patch("controller.generate_report", return_value=None), \
         patch("controller.Database", return_value=mock_db):

        from controller import Controller
        ctrl = Controller(cfg)
        result = ctrl.process_archive(source, output_dir_override=output)

    assert result["total"] == 1
    assert result["errors"] == 0


# ── process_archive — обработка ошибок ────────────────────────────────────────

def test_process_archive_error_handling(
    cfg, tmp_path, sample_file_info, sample_metadata
):
    """Если extract_text бросает исключение, файл помечается как error и пайплайн продолжается."""
    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "output"
    output.mkdir()

    mock_db = MagicMock()
    mock_db.is_processed.return_value = False
    mock_db.get_all_results.return_value = []

    with patch("controller.get_provider", return_value=MagicMock()), \
         patch("controller.get_fallback_provider", return_value=MagicMock()), \
         patch("controller.scan_directory", return_value=[sample_file_info]), \
         patch("controller.extract_text", side_effect=RuntimeError("IO Error")), \
         patch("controller.generate_report", return_value=None), \
         patch("controller.Database", return_value=mock_db):

        from controller import Controller
        ctrl = Controller(cfg)
        result = ctrl.process_archive(source, output_dir_override=output)

    # Файл завершился ошибкой, но пайплайн не рухнул
    assert result["errors"] == 1
    assert result["total"] == 1


# ── process_archive — progress callback ───────────────────────────────────────

def test_process_archive_progress_callback(
    cfg, tmp_path, sample_file_info, sample_text, sample_metadata
):
    """on_progress вызывается с (current, total, message)."""
    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "output"
    output.mkdir()

    progress_calls = []

    def track_progress(current, total, message):
        progress_calls.append((current, total, message))

    mock_db = MagicMock()
    mock_db.is_processed.return_value = False
    mock_db.get_all_results.return_value = []
    mock_db.get_contract_id_by_hash.return_value = None

    with patch("controller.get_provider", return_value=MagicMock()), \
         patch("controller.get_fallback_provider", return_value=MagicMock()), \
         patch("controller.scan_directory", return_value=[sample_file_info]), \
         patch("controller.extract_text", return_value=sample_text), \
         patch("controller.extract_metadata", return_value=sample_metadata), \
         patch("controller.organize_file", return_value=output / "done" / "sample.pdf"), \
         patch("controller.generate_report", return_value=None), \
         patch("controller.Database", return_value=mock_db):

        from controller import Controller
        ctrl = Controller(cfg)
        ctrl.process_archive(source, output_dir_override=output, on_progress=track_progress)

    assert len(progress_calls) > 0
    # Каждый call должен быть (int, int, str)
    for current, total, message in progress_calls:
        assert isinstance(current, int)
        assert isinstance(total, int)
        assert isinstance(message, str)


# ── process_archive — force_reprocess ─────────────────────────────────────────

def test_process_archive_force_reprocess(
    cfg, tmp_path, sample_file_info, sample_text, sample_metadata
):
    """force_reprocess=True вызывает db.clear_all() и обрабатывает все файлы."""
    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "output"
    output.mkdir()

    mock_db = MagicMock()
    mock_db.is_processed.return_value = True  # файл уже обработан
    mock_db.get_all_results.return_value = []
    mock_db.get_contract_id_by_hash.return_value = None

    with patch("controller.get_provider", return_value=MagicMock()), \
         patch("controller.get_fallback_provider", return_value=MagicMock()), \
         patch("controller.scan_directory", return_value=[sample_file_info]), \
         patch("controller.extract_text", return_value=sample_text), \
         patch("controller.extract_metadata", return_value=sample_metadata), \
         patch("controller.organize_file", return_value=output / "done" / "sample.pdf"), \
         patch("controller.generate_report", return_value=None), \
         patch("controller.Database", return_value=mock_db):

        from controller import Controller
        ctrl = Controller(cfg)
        result = ctrl.process_archive(
            source, output_dir_override=output, force_reprocess=True
        )

    # clear_all должен был быть вызван при force_reprocess
    mock_db.clear_all.assert_called_once()
    # Файл обработан несмотря на is_processed=True
    assert result["total"] == 1
