"""Tests: logging.warning вызывается при обрезке текста >30K символов в extract_metadata."""
import logging
from unittest.mock import MagicMock


def test_warning_on_long_text(caplog):
    """extract_metadata с текстом 31000 символов — warning с 'обрезан' и длиной."""
    from modules.ai_extractor import extract_metadata
    from config import Config
    cfg = Config()
    long_text = "А" * 31_000
    mock_provider = MagicMock()
    mock_provider.name = "test"
    mock_provider.complete.return_value = (
        '{"document_type":"Договор","counterparty":"ООО Тест","subject":"Тест",'
        '"confidence":0.9,"parties":[],"special_conditions":[]}'
    )
    with caplog.at_level(logging.WARNING, logger="modules.ai_extractor"):
        extract_metadata(long_text, cfg, provider=mock_provider)
    assert any("обрезан" in r.message for r in caplog.records), (
        f"Expected truncation warning, got: {[r.message for r in caplog.records]}"
    )


def test_no_warning_on_short_text(caplog):
    """extract_metadata с текстом 5000 символов — warning НЕ вызывается."""
    from modules.ai_extractor import extract_metadata
    from config import Config
    cfg = Config()
    short_text = "А" * 5_000
    mock_provider = MagicMock()
    mock_provider.name = "test"
    mock_provider.complete.return_value = (
        '{"document_type":"Договор","counterparty":"ООО Тест","subject":"Тест",'
        '"confidence":0.9,"parties":[],"special_conditions":[]}'
    )
    with caplog.at_level(logging.WARNING, logger="modules.ai_extractor"):
        extract_metadata(short_text, cfg, provider=mock_provider)
    assert not any("обрезан" in r.message for r in caplog.records)


def test_no_warning_on_exact_boundary(caplog):
    """extract_metadata с текстом ровно 30000 символов — warning НЕ вызывается."""
    from modules.ai_extractor import extract_metadata
    from config import Config
    cfg = Config()
    boundary_text = "А" * 30_000
    mock_provider = MagicMock()
    mock_provider.name = "test"
    mock_provider.complete.return_value = (
        '{"document_type":"Договор","counterparty":"ООО Тест","subject":"Тест",'
        '"confidence":0.9,"parties":[],"special_conditions":[]}'
    )
    with caplog.at_level(logging.WARNING, logger="modules.ai_extractor"):
        extract_metadata(boundary_text, cfg, provider=mock_provider)
    assert not any("обрезан" in r.message for r in caplog.records)
