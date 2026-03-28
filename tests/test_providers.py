"""Тесты пакета providers/ — фабрика, ZAI, OpenRouter, Ollama (FUND-03)."""
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


def test_factory_openrouter(monkeypatch):
    """get_provider('openrouter') возвращает OpenRouterProvider."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    from providers import get_provider
    from providers.openrouter import OpenRouterProvider
    cfg = _make_config(active_provider="openrouter")
    provider = get_provider(cfg)
    assert isinstance(provider, OpenRouterProvider)


def test_factory_unknown_falls_back_to_ollama():
    """get_provider с неизвестным провайдером → Config.__post_init__ исправляет на ollama."""
    from providers import get_provider
    from providers.ollama import OllamaProvider
    cfg = _make_config(active_provider="unknown_provider_xyz")
    # __post_init__ gracefully corrects to "ollama"
    assert cfg.active_provider == "ollama"
    provider = get_provider(cfg)
    assert isinstance(provider, OllamaProvider)


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


def test_ollama_instantiates():
    """OllamaProvider instantiates without error (fully implemented since Phase 4)."""
    from providers.ollama import OllamaProvider
    cfg = _make_config()
    provider = OllamaProvider(cfg)
    assert provider is not None
    assert hasattr(provider, "complete")
