"""Пакет providers/ — фабрика LLM-провайдеров.

Использование:
    from providers import get_provider, get_fallback_provider
    provider = get_provider(config)          # активный провайдер
    fallback = get_fallback_provider(config) # запасной или None
"""
from config import Config
from providers.base import LLMProvider
from providers.zai import ZAIProvider
from providers.openrouter import OpenRouterProvider
from providers.ollama import OllamaProvider


def get_provider(config: Config) -> LLMProvider:
    """Создаёт провайдер по config.active_provider.

    Args:
        config: конфиг приложения

    Returns:
        Экземпляр LLMProvider для активного провайдера.

    Raises:
        ValueError: если active_provider неизвестен.
    """
    match config.active_provider:
        case "zai":
            return ZAIProvider(config)
        case "openrouter":
            return OpenRouterProvider(config)
        case "ollama":
            return OllamaProvider(config)
        case _:
            raise ValueError(
                f"Неизвестный active_provider: {config.active_provider!r}. "
                f"Допустимые значения: 'zai', 'openrouter', 'ollama'."
            )


def get_fallback_provider(config: Config) -> LLMProvider | None:
    """Создаёт запасной провайдер по config.fallback_provider.

    Returns:
        Экземпляр LLMProvider или None если fallback не задан или API-ключ отсутствует.
    """
    if not config.fallback_provider:
        return None
    try:
        match config.fallback_provider:
            case "openrouter":
                return OpenRouterProvider(config)
            case "ollama":
                return OllamaProvider(config)
            case "zai":
                return ZAIProvider(config)
            case _:
                return None
    except ValueError:
        # API-ключ не задан — fallback недоступен, не крашим приложение
        import logging
        logging.getLogger(__name__).warning(
            "Fallback провайдер %r недоступен (API-ключ не задан)", config.fallback_provider
        )
        return None
