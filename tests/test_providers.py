"""Тесты пакета providers/ — фабрика, ZAI, OpenRouter, Ollama (FUND-03)."""
import os
from unittest.mock import MagicMock, patch

import pytest

from config import Config


def _make_config(**kwargs) -> Config:
    """Конфиг с переопределёнными полями для тестов."""
    defaults = dict(active_provider="zai", fallback_provider="openrouter")
    defaults.update(kwargs)
    return Config(**defaults)


def test_factory_zai():
    """get_provider('zai') возвращает ZAIProvider."""
    from providers import get_provider
    from providers.zai import ZAIProvider
    cfg = _make_config(active_provider="zai")
    provider = get_provider(cfg)
    assert isinstance(provider, ZAIProvider)


def test_factory_openrouter():
    """get_provider('openrouter') возвращает OpenRouterProvider."""
    from providers import get_provider
    from providers.openrouter import OpenRouterProvider
    cfg = _make_config(active_provider="openrouter")
    provider = get_provider(cfg)
    assert isinstance(provider, OpenRouterProvider)


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


def test_openrouter_system_merge():
    """_merge_system_into_user вклеивает system-контент в первое user-сообщение."""
    from providers.openrouter import _merge_system_into_user
    messages = [
        {"role": "system", "content": "Ты юрист"},
        {"role": "user", "content": "Проанализируй договор"},
    ]
    merged = _merge_system_into_user(messages)
    assert len(merged) == 1
    assert merged[0]["role"] == "user"
    assert "Ты юрист" in merged[0]["content"]
    assert "Проанализируй договор" in merged[0]["content"]


def test_ollama_stub():
    """OllamaProvider.complete() поднимает NotImplementedError (stub для Вехи 3)."""
    from providers.ollama import OllamaProvider
    cfg = _make_config()
    provider = OllamaProvider(cfg)
    with pytest.raises(NotImplementedError):
        provider.complete([{"role": "user", "content": "test"}])
