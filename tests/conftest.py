"""Конфигурация pytest — добавляет корень проекта в sys.path."""
import os
import sys
from pathlib import Path

import pytest

# Добавляем yurteg/ в sys.path чтобы import config, modules.* работали
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True, scope="session")
def _clear_proxy_env():
    """Remove proxy env vars that break httpx in tests.

    System env var ALL_PROXY=socks5h://localhost:49644 is picked up by httpx
    when creating OpenAI clients. httpx doesn't support socks5h:// scheme.
    """
    proxy_vars = [
        "ALL_PROXY", "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY",
        "all_proxy", "https_proxy", "http_proxy", "no_proxy",
    ]
    saved = {k: os.environ.pop(k) for k in proxy_vars if k in os.environ}
    yield
    os.environ.update(saved)


@pytest.fixture(autouse=True)
def _close_cached_client_dbs():
    """Isolate tests from shared ClientManager DB cache."""
    yield
    try:
        from services.client_manager import ClientManager

        ClientManager.close_all()
    except Exception:
        pass
