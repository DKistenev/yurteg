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

# ── Status badge CSS (D-23, D-24, Pattern 4 from Phase 8 RESEARCH) ────────────
# Tailwind @layer components — literal class strings для JS cellRenderer.
# Определяются один раз при старте, безопасны для JIT-purge.

_STATUS_CSS = """
<style type="text/tailwindcss">
  @layer components {
    .status-active      { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-50 text-green-700; }
    .status-expiring    { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-50 text-yellow-700; }
    .status-expired     { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-50 text-red-700; }
    .status-unknown     { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500; }
    .status-terminated  { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500; }
    .status-extended    { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700; }
    .status-negotiation { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-50 text-purple-700; }
    .status-suspended   { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-orange-50 text-orange-700; }
  }
</style>
"""

# Hover-actions CSS (Phase 08, Plan 03 — D-12, REG-06)
# actions-cell скрыт по умолчанию, появляется при наведении на строку
_ACTIONS_CSS = """
<style>
  .actions-cell { opacity: 0; transition: opacity 150ms ease; display: flex; align-items: center; justify-content: center; }
  .ag-row:hover .actions-cell { opacity: 1; }
  .action-icon { cursor: pointer; font-size: 18px; color: #6b7280; line-height: 1; }
  .action-icon:hover { color: #111827; }
  .expand-icon { color: #9ca3af; font-size: 12px; user-select: none; }
  .expand-icon:hover { color: #374151; }
</style>
"""

ui.add_head_html(_STATUS_CSS)
ui.add_head_html(_ACTIONS_CSS)

# ── UI root ────────────────────────────────────────────────────────────────────


@ui.page("/")
def root() -> None:
    """Single root page — header is persistent, content area switches via sub_pages."""
    ui.dark_mode(value=False)

    # Splash gate: при первом запуске показываем onboarding, header не рендерится
    from config import load_settings
    settings = load_settings()
    if not settings.get("first_run_completed"):
        from app.components.onboarding.splash import render_splash
        render_splash()
        return  # early return — no header, no sub_pages

    state = get_state()

    async def _handle_upload(path):
        """Delegate upload to registry page's on_upload callback (stored on state)."""
        if hasattr(state, "_on_upload") and state._on_upload:
            await state._on_upload(path)

    render_header(state, on_upload=_handle_upload)
    ui.sub_pages({
        "/": registry.build,
        "/document/{doc_id}": document.build,
        "/templates": templates.build,
        "/settings": settings.build,
    })


# ── Redline download route (Phase 9, D-18) ────────────────────────────────────
# FastAPI route вместо ui.download — не блокирует event loop (Pitfall 1 from RESEARCH)
from fastapi.responses import Response as FastAPIResponse


@app.get('/download/redline/{contract_id}/{other_id}')
async def download_redline(contract_id: int, other_id: int):
    """Скачивает redline .docx сравнивая два документа-версии."""
    from services.version_service import generate_redline_docx as _gen_redline
    from services.client_manager import ClientManager as _CM

    cm = _CM()
    db = cm.get_db("Основной реестр")
    c1 = await run.io_bound(db.get_contract_by_id, contract_id)
    c2 = await run.io_bound(db.get_contract_by_id, other_id)
    if c1 is None or c2 is None:
        return FastAPIResponse(content="Документ не найден", status_code=404)
    text_old = c1.get('subject', '') or ''
    text_new = c2.get('subject', '') or ''
    title = f"Redline: {c1.get('contract_type', '')} vs {c2.get('contract_type', '')}"
    docx_bytes = await run.io_bound(_gen_redline, text_old, text_new, title)
    return FastAPIResponse(
        content=docx_bytes,
        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        headers={'Content-Disposition': f'attachment; filename="redline_{contract_id}_vs_{other_id}.docx"'},
    )


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
