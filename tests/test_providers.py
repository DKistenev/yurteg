"""Тесты пакета providers/ — фабрика, ZAI, Ollama."""
import os
from unittest.mock import MagicMock, patch

import pytest

from config import Config


def _make_config(**kwargs) -> Config:
    """Конфиг с переопределёнными полями для тестов."""
    defaults = dict(active_provider="zai", fallback_provider="ollama")
    defaults.update(kwargs)
    return Config(**defaults)


def test_factory_zai():
    """get_provider('zai') возвращает ZAIProvider."""
    from providers import get_provider
    from providers.zai import ZAIProvider
    cfg = _make_config(active_provider="zai")
    provider = get_provider(cfg)
    assert isinstance(provider, ZAIProvider)


def test_factory_unknown_raises():
    """get_provider с неизвестным провайдером поднимает ValueError."""
    from providers import get_provider
    cfg = _make_config(active_provider="unknown_provider_xyz")
    with pytest.raises(ValueError, match="unknown_provider_xyz"):
        get_provider(cfg)


def test_zai_thinking_disabled():
    """ZAIProvider.complete() передаёт extra_body thinking:disabled когда ai_disable_thinking=True."""
    from providers.zai import ZAIProvider
    cfg = _make_config(ai_disable_thinking=True)
    provider = ZAIProvider(cfg)

    # Мокаем chat.completions.create
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"ok": true}'
    provider._client = MagicMock()
    provider._client.chat.completions.create.return_value = mock_response

    messages = [{"role": "user", "content": "test"}]
    provider.complete(messages)

    call_kwargs = provider._client.chat.completions.create.call_args[1]
    assert "extra_body" in call_kwargs, "extra_body отсутствует в вызове ZAI"
    assert call_kwargs["extra_body"] == {"thinking": {"type": "disabled"}}


def test_ollama_instantiates():
    """OllamaProvider instantiates without error."""
    from providers.ollama import OllamaProvider
    cfg = _make_config()
    provider = OllamaProvider(cfg)
    assert provider is not None
    assert hasattr(provider, "complete")
