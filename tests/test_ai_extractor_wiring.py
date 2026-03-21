"""Regression tests for ai_extractor wiring bugs (Phase 06, Plan 01).

Tests verify:
- provider.complete() is called when provider is passed (not _try_model)
- sanitize_metadata receives dict (not ContractMetadata dataclass)
- sanitize_metadata return value is used to rebuild ContractMetadata
- Legacy path (_try_model) is preserved when provider=None
- fallback_provider.complete() is called when primary provider raises
"""
import json
import sys
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from modules.models import ContractMetadata

# Valid JSON that a local model might return
_VALID_JSON = json.dumps({
    "document_type": "Договор аренды",
    "counterparty": "ООО Тест",
    "subject": "Аренда офиса",
    "date_signed": None,
    "date_start": None,
    "date_end": None,
    "amount": None,
    "special_conditions": [],
    "parties": [],
    "confidence": 0.9,
    "is_template": False,
    "payment_terms": None,
    "payment_amount": None,
    "payment_frequency": None,
    "payment_direction": None,
})


def _make_config() -> Config:
    """Return a Config with active_provider=ollama."""
    cfg = Config()
    cfg.active_provider = "ollama"
    return cfg


def _make_provider(name: str = "ollama", response: str = _VALID_JSON) -> MagicMock:
    """Return a mock LLMProvider."""
    p = MagicMock()
    p.name = name
    p.complete = MagicMock(return_value=response)
    return p


# ── Tests ──────────────────────────────────────────────────────────────────────


def test_provider_route_called():
    """When provider is passed, provider.complete() must be called (not _try_model)."""
    from modules.ai_extractor import extract_metadata

    provider = _make_provider()
    cfg = _make_config()

    # _try_model must NOT be called — patch it to raise so we'd notice
    with patch("modules.ai_extractor._try_model", side_effect=AssertionError("_try_model must not be called when provider is given")):
        result = extract_metadata("Текст договора", cfg, provider=provider)

    assert provider.complete.called, "provider.complete() должен быть вызван"
    assert isinstance(result, ContractMetadata)



def test_legacy_route_when_no_provider():
    """When provider=None, _try_model is used (backward compat)."""
    from modules.ai_extractor import extract_metadata

    cfg = _make_config()
    cfg.active_provider = "zai"  # not ollama, so sanitize not triggered
    expected = ContractMetadata(contract_type="Договор поставки", confidence=0.8)

    with patch("modules.ai_extractor._try_model", return_value=expected) as mock_try:
        result = extract_metadata("Текст договора", cfg, provider=None)

    assert mock_try.called, "_try_model должен быть вызван когда provider=None"
    assert result.contract_type == "Договор поставки"



def test_sanitize_receives_dict_not_dataclass():
    """sanitize_metadata must receive a dict, not a ContractMetadata instance."""
    from modules.ai_extractor import extract_metadata

    provider = _make_provider()
    cfg = _make_config()

    call_args_holder: list = []

    def capturing_sanitize(raw):
        call_args_holder.append(raw)
        # Return a valid dict so downstream _json_to_metadata works
        return {
            "contract_type": "Договор аренды",
            "confidence": 0.9,
            "parties": [],
            "special_conditions": [],
            "is_template": False,
        }

    with patch("modules.ai_extractor.sanitize_metadata", side_effect=capturing_sanitize):
        extract_metadata("Текст договора", cfg, provider=provider)

    assert call_args_holder, "sanitize_metadata должна быть вызвана"
    first_arg = call_args_holder[0]
    assert isinstance(first_arg, dict), (
        f"sanitize_metadata должна получить dict, получила {type(first_arg).__name__}"
    )
    assert not isinstance(first_arg, ContractMetadata), (
        "sanitize_metadata не должна получать ContractMetadata"
    )



def test_sanitize_return_value_used():
    """Return value of sanitize_metadata must be used to build the final ContractMetadata."""
    from modules.ai_extractor import extract_metadata

    provider = _make_provider()
    cfg = _make_config()

    # Sanitize changes contract_type to a sentinel value
    SENTINEL = "САНИТИЗИРОВАНО"

    def sentinel_sanitize(raw):
        result = dict(raw)
        result["contract_type"] = SENTINEL
        result.setdefault("parties", [])
        result.setdefault("special_conditions", [])
        result.setdefault("is_template", False)
        result.setdefault("confidence", 0.9)
        return result

    with patch("modules.ai_extractor.sanitize_metadata", side_effect=sentinel_sanitize):
        result = extract_metadata("Текст договора", cfg, provider=provider)

    assert result.contract_type == SENTINEL, (
        f"Возврат sanitize_metadata должен использоваться. "
        f"Ожидалось '{SENTINEL}', получено '{result.contract_type}'"
    )



def test_fallback_provider_used_on_failure():
    """When primary provider raises RuntimeError, fallback_provider.complete() is called."""
    from modules.ai_extractor import extract_metadata

    primary = _make_provider(name="ollama")
    primary.complete.side_effect = RuntimeError("primary failed")

    fallback = _make_provider(name="zai")
    cfg = _make_config()

    result = extract_metadata("Текст договора", cfg, provider=primary, fallback_provider=fallback)

    assert fallback.complete.called, "fallback_provider.complete() должен быть вызван при сбое основного"
    assert isinstance(result, ContractMetadata)
