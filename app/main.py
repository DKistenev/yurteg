"""NiceGUI entrypoint — ЮрТэг desktop application.

Per D-08: reload=False предотвращает двойную инициализацию.
Per D-09: llama-server singleton через app.on_startup.
Per D-10: Тройная защита shutdown: on_shutdown + on_disconnect + atexit.
Per D-11: ensure_model() и start() через run.io_bound() — не блокируют event loop.
Per D-03: ui.sub_pages для SPA-навигации — URL обновляется, header персистентен.
Per D-16: ui.run с native=True, dark=False, reload=False, window_size=(1400, 900).
"""
# ruff: noqa: E402
# freeze_support() MUST be called before any heavy imports (PyInstaller requirement)
from multiprocessing import freeze_support
freeze_support()

import atexit
import logging

from nicegui import app, run, ui

from app.components.header import render_header
from app.pages import document, registry, settings, templates
from app.state import get_state
from config import APP_VERSION, load_runtime_config, load_settings, save_setting
from runtime_paths import get_resource_path
from services.client_manager import ClientManager
from services.llama_server import LlamaServerManager
from services.instance_lock import acquire_instance_lock
from services.log_setup import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# Pattern: await run.io_bound(sync_function, args) — use for ALL blocking calls from UI

# ── llama-server singleton ─────────────────────────────────────────────────────

_llama_manager: LlamaServerManager | None = None


async def _start_llama() -> None:
    """Start llama-server if active_provider is 'ollama'. Called via app.on_startup."""
    global _llama_manager
    config = load_runtime_config()
    if config.active_provider != "ollama":
        logger.info("Провайдер '%s' — llama-server не запускается.", config.active_provider)
        return
    manager = LlamaServerManager(port=config.llama_server_port)
    try:
        await run.io_bound(manager.ensure_model)
        await run.io_bound(manager.ensure_server_binary)
        await run.io_bound(manager.start)
        _llama_manager = manager
        logger.info("llama-server запущен")
    except Exception as e:
        logger.warning(f"llama-server не запустился: {e}")
        ui.notify("Локальная модель недоступна. Используется облачный провайдер.", type="warning")


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

# Quasar color bridge — синхронизировать --q-primary с --yt-color-accent
app.colors(
    primary='#4f46e5',    # --yt-p-indigo-600
    secondary='#64748b',  # --yt-p-slate-500
    accent='#4f46e5',
    positive='#059669',   # green-600
    negative='#dc2626',   # red-600
    warning='#d97706',    # amber-600
    info='#3b82f6',       # blue-500
    dark='#0f172a',       # --yt-p-slate-900
    dark_page='#0f172a',
)

# ── Global design system ──────────────────────────────────────────────────────
# CSS/JS extracted to app/static/ for maintainability. Load order matters: font first.

_STATIC = get_resource_path("app", "static")
app.add_static_files("/static", str(_STATIC))

# Font (must load before any rendered element) — served locally, no CDN
ui.add_head_html("""
<style>
@font-face {
  font-family: 'IBM Plex Sans';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url('/static/fonts/IBMPlexSans-Regular.woff2') format('woff2');
}
@font-face {
  font-family: 'IBM Plex Sans';
  font-style: normal;
  font-weight: 500;
  font-display: swap;
  src: url('/static/fonts/IBMPlexSans-Regular.woff2') format('woff2');
}
@font-face {
  font-family: 'IBM Plex Sans';
  font-style: normal;
  font-weight: 700;
  font-display: swap;
  src: url('/static/fonts/IBMPlexSans-Bold.woff2') format('woff2');
}
body { font-family: 'IBM Plex Sans', sans-serif; font-weight: 500; line-height: 1.5; letter-spacing: -0.01em; -webkit-font-smoothing: antialiased; color: var(--yt-color-text-primary); }
</style>
""", shared=True)

# tokens.css — ПЕРВЫМ (CSS custom properties должны быть до всех потребителей)
ui.add_head_html(f'<style>{(_STATIC / "tokens.css").read_text()}</style>', shared=True)

# FullCalendar CDN — lazy-loaded on first calendar toggle (see _load_fullcalendar_js)
# Moved from eager <script> to on-demand loading in registry.py _show_calendar()

# Design system CSS (animations, hover-actions, FullCalendar theme)
ui.add_head_html(f'<style>{(_STATIC / "design-system.css").read_text()}</style>', shared=True)

# Calendar tooltip container + calendar.js (lightweight, no FullCalendar dependency)
ui.add_head_html(f"""
<div id="cal-tooltip" style="position:fixed;z-index:1000;background:white;border:1px solid #e2e8f0;border-radius:8px;padding:12px;max-width:256px;box-shadow:0 4px 6px -1px rgba(0,0,0,0.07);display:none;"></div>
<script>{(_STATIC / "calendar.js").read_text()}</script>
""", shared=True)

# Status badge CSS — defined in design-system.css (pill style, semantic colors)
# No duplicate here — single source of truth in design-system.css

# Content area background — не белый (DSGN-05)
# min-h-screen + flex col on nicegui-content pushes footer to bottom
ui.add_head_html("""
<style>
  body { background: var(--yt-surface-bg) !important; }
  .nicegui-content {
    background: var(--yt-surface-bg);
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    align-items: stretch;  /* CRITICAL: без этого дети сжимаются к flex-start */
  }
  .nicegui-sub-pages {
    width: 100%;  /* sub_pages контейнер ДОЛЖЕН растягиваться */
    max-width: none;
  }
  .q-page {
    max-width: none;
    width: 100%;
  }
</style>
""", shared=True)

# ── Startup loading overlay (DUX-02) ─────────────────────────────────────────
# Shows branded splash during PyInstaller cold start (3-5 sec).
# Pure CSS — visible immediately, hidden by JS once NiceGUI mounts.
ui.add_head_html("""
<style>
  #loading-overlay {
    position: fixed;
    inset: 0;
    z-index: 99999;
    background: #0f172a;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1.5rem;
    transition: opacity 0.4s ease;
  }
  #loading-overlay.fade-out {
    opacity: 0;
    pointer-events: none;
  }
  #loading-overlay .logo-circle {
    width: 80px;
    height: 80px;
    border-radius: 20px;
    background: #4f46e5;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  #loading-overlay .logo-letter {
    font-family: 'IBM Plex Sans', system-ui, sans-serif;
    font-size: 40px;
    font-weight: 700;
    color: white;
    line-height: 1;
  }
  #loading-overlay .app-name {
    font-family: 'IBM Plex Sans', system-ui, sans-serif;
    font-size: 1.25rem;
    font-weight: 600;
    color: #e2e8f0;
    letter-spacing: 0.02em;
  }
  #loading-overlay .loader-dots {
    display: flex;
    gap: 6px;
  }
  #loading-overlay .loader-dots span {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #4f46e5;
    animation: dot-pulse 1.2s infinite ease-in-out;
  }
  #loading-overlay .loader-dots span:nth-child(2) { animation-delay: 0.2s; }
  #loading-overlay .loader-dots span:nth-child(3) { animation-delay: 0.4s; }
  @keyframes dot-pulse {
    0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
    40% { opacity: 1; transform: scale(1); }
  }
</style>
<div id="loading-overlay">
  <div class="logo-circle">
    <span class="logo-letter">\u042e</span>
  </div>
  <span class="app-name">\u042e\u0440\u0422\u044d\u0433</span>
  <div class="loader-dots">
    <span></span><span></span><span></span>
  </div>
</div>
<script>
  function _hideLoadingOverlay() {
    var el = document.getElementById('loading-overlay');
    if (el) {
      el.classList.add('fade-out');
      setTimeout(function() { el.remove(); }, 500);
    }
  }
  var _obs = new MutationObserver(function(mutations) {
    if (document.querySelector('.nicegui-content')) {
      _obs.disconnect();
      setTimeout(_hideLoadingOverlay, 300);
    }
  });
  _obs.observe(document.body, { childList: true, subtree: true });
  setTimeout(_hideLoadingOverlay, 8000);
</script>
""", shared=True)

# ── UI root ────────────────────────────────────────────────────────────────────


@ui.page("/")
def root() -> None:
    """Single root page — header is persistent, content area switches via sub_pages."""
    ui.dark_mode(value=False)

    # Splash gate: при первом запуске показываем onboarding, header не рендерится
    from config import load_settings
    app_settings = load_settings()
    if not app_settings.get("first_run_completed"):
        from app.components.onboarding.splash import render_splash
        render_splash()
        return  # early return — no header, no sub_pages

    state = get_state()
    # Bridge persisted warning_days → AppState (BUG-02 fix)
    state.warning_days_threshold = app_settings.get("warning_days_threshold", 30)

    async def _handle_upload(path):
        """Delegate upload to registry page's on_upload callback (stored on state)."""
        if hasattr(state, "_on_upload") and state._on_upload:
            await state._on_upload(path)

    render_header(state, on_upload=_handle_upload)
    with ui.column().classes("flex-1 w-full"):
        ui.sub_pages({
            "/": registry.build,
            "/document/{doc_id}": document.build,
            "/templates": templates.build,
            "/settings": settings.build,
        })
    # Footer — минимальный, только версия (per CONTEXT.md: «только версия, минимальный»)
    with ui.element('footer').classes(
        "w-full py-3 px-8 flex justify-center items-center border-t border-slate-200 bg-white shrink-0"
    ):
        ui.label(f"ЮрТэг v{APP_VERSION}").classes("text-xs text-slate-400")


# ── Redline download route (Phase 9, D-18) ────────────────────────────────────
# FastAPI route вместо ui.download — не блокирует event loop (Pitfall 1 from RESEARCH)
from fastapi.responses import Response as FastAPIResponse


@app.get('/download/redline/{contract_id}/{other_id}')
async def download_redline(contract_id: int, other_id: int, client: str = ClientManager.DEFAULT_CLIENT):
    """Скачивает redline .docx сравнивая два документа-версии."""
    from services.version_service import generate_redline_docx as _gen_redline
    from services.client_manager import ClientManager as _CM

    cm = _CM()
    db = cm.get_db(client)
    c1 = await run.io_bound(db.get_contract_by_id, contract_id)
    c2 = await run.io_bound(db.get_contract_by_id, other_id)
    if c1 is None or c2 is None:
        return FastAPIResponse(content="Документ не найден", status_code=404)
    text_old = c1.get('full_text') or c1.get('subject', '') or ''
    text_new = c2.get('full_text') or c2.get('subject', '') or ''
    title = f"Redline: {c1.get('contract_type', '')} vs {c2.get('contract_type', '')}"
    docx_bytes = await run.io_bound(_gen_redline, text_old, text_new, title)
    return FastAPIResponse(
        content=docx_bytes,
        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        headers={'Content-Disposition': f'attachment; filename="redline_{contract_id}_vs_{other_id}.docx"'},
    )


# ── Document download route (UIFIX-02) ────────────────────────────────────────
@app.get('/download/{doc_id}')
async def download_document(doc_id: int, client: str = ClientManager.DEFAULT_CLIENT):
    """Скачивает оригинальный файл документа."""
    from pathlib import Path as _Path
    from services.client_manager import ClientManager as _CM

    cm = _CM()
    db = cm.get_db(client)
    doc = await run.io_bound(db.get_contract_by_id, doc_id)
    if doc is None:
        return FastAPIResponse(content="Документ не найден", status_code=404)

    original_path = _Path(doc.get("original_path", ""))
    if not original_path.exists():
        return FastAPIResponse(
            content=f"Файл не найден: {original_path.name}", status_code=404
        )

    content_bytes = original_path.read_bytes()
    suffix = original_path.suffix.lower()
    media_type = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
    }.get(suffix, "application/octet-stream")

    return FastAPIResponse(
        content=content_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{original_path.name}"'},
    )


# ── Entry point ────────────────────────────────────────────────────────────────
# Note: ui.run() is at module level, NOT inside if __name__ == '__main__'.
# native=True subprocess bypasses main guard (Research Pitfall 5).


def _get_storage_secret() -> str:
    """Return persistent storage_secret, generating on first run."""
    import secrets as _secrets

    s = load_settings()
    secret = s.get("storage_secret")
    if not secret:
        secret = _secrets.token_hex(32)
        save_setting("storage_secret", secret)
    return secret


acquire_instance_lock()

ui.run(
    native=True,
    dark=False,
    reload=False,
    host="127.0.0.1",
    title="ЮрТэг",
    window_size=(1400, 900),
    storage_secret=_get_storage_secret(),
)
