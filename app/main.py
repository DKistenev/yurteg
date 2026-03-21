"""NiceGUI entrypoint — ЮрТэг desktop application.

Per D-08: reload=False предотвращает двойную инициализацию.
Per D-09: llama-server singleton через app.on_startup.
Per D-10: Тройная защита shutdown: on_shutdown + on_disconnect + atexit.
Per D-11: ensure_model() и start() через run.io_bound() — не блокируют event loop.
Per D-03: ui.sub_pages для SPA-навигации — URL обновляется, header персистентен.
Per D-16: ui.run с native=True, dark=False, reload=False, window_size=(1400, 900).
"""
import atexit
import logging

from nicegui import app, run, ui

from app.components.header import render_header
from app.pages import document, registry, settings, templates
from app.state import get_state
from config import Config
from modules.postprocessor import get_grammar_path
from services.llama_server import LlamaServerManager

logger = logging.getLogger(__name__)

# Pattern: await run.io_bound(sync_function, args) — use for ALL blocking calls from UI

# ── llama-server singleton ─────────────────────────────────────────────────────

_llama_manager: LlamaServerManager | None = None


async def _start_llama() -> None:
    """Start llama-server if active_provider is 'ollama'. Called via app.on_startup."""
    global _llama_manager
    config = Config()
    if config.active_provider != "ollama":
        logger.info("Провайдер '%s' — llama-server не запускается.", config.active_provider)
        return
    manager = LlamaServerManager(port=config.llama_server_port)
    try:
        await run.io_bound(manager.ensure_model)
        await run.io_bound(manager.ensure_server_binary)
        await run.io_bound(manager.start, get_grammar_path())
        _llama_manager = manager
        logger.info("llama-server запущен")
    except Exception as e:
        logger.warning(f"llama-server не запустился: {e}")


def _stop_llama() -> None:
    """Stop llama-server if running. Idempotent — safe to call multiple times."""
    global _llama_manager
    if _llama_manager and _llama_manager.is_running():
        _llama_manager.stop()
        logger.info("llama-server остановлен")


def get_llama_manager() -> LlamaServerManager | None:
    """Return the module-level LlamaServerManager singleton (may be None)."""
    return _llama_manager


# Тройная защита shutdown (D-10, FUND-04):
# on_shutdown ненадёжен в native=True на macOS (NiceGUI bug #2107)
app.on_startup(_start_llama)
app.on_shutdown(_stop_llama)
app.on_disconnect(_stop_llama)
atexit.register(_stop_llama)

# ── UI root ────────────────────────────────────────────────────────────────────


@ui.page("/")
def root() -> None:
    """Single root page — header is persistent, content area switches via sub_pages."""
    ui.dark_mode(value=False)
    state = get_state()
    render_header(state)
    ui.sub_pages({
        "/": registry.build,
        "/document/{doc_id}": document.build,
        "/templates": templates.build,
        "/settings": settings.build,
    })


# ── Entry point ────────────────────────────────────────────────────────────────
# Note: ui.run() is at module level, NOT inside if __name__ == '__main__'.
# native=True subprocess bypasses main guard (Research Pitfall 5).

ui.run(
    native=True,
    dark=False,
    reload=False,
    host="127.0.0.1",
    title="ЮрТэг",
    window_size=(1400, 900),
    storage_secret='yurteg-desktop-secret',
)
