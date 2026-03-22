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

# ── Global design system CSS (Phase 13 — D-06, D-07, D-09, D-22) ─────────────
# Font FIRST — must load before any rendered element (Pitfall 4 from UI-SPEC).

_FONT_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap&subset=cyrillic" rel="stylesheet">
<style>
  * { font-family: 'IBM Plex Sans', sans-serif; }
</style>
"""

# FullCalendar v6.1.15 CDN (D-10) — loaded globally so registry calendar renders instantly
_FULLCALENDAR_CSS = """
<link href='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.css' rel='stylesheet' />
<script src='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.js'></script>
"""

# Staggered row + page fade animations (D-17, D-18, D-19, D-20, D-21)
_ANIMATION_CSS = """
<style>
@keyframes row-in {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
.ag-row {
  animation: row-in 200ms cubic-bezier(0.25, 1, 0.5, 1) both;
}
.ag-row:nth-child(1)  { animation-delay: 0ms; }
.ag-row:nth-child(2)  { animation-delay: 80ms; }
.ag-row:nth-child(3)  { animation-delay: 160ms; }
.ag-row:nth-child(4)  { animation-delay: 240ms; }
.ag-row:nth-child(5)  { animation-delay: 320ms; }
.ag-row:nth-child(6)  { animation-delay: 400ms; }
.ag-row:nth-child(7)  { animation-delay: 480ms; }
.ag-row:nth-child(8)  { animation-delay: 560ms; }
.ag-row:nth-child(n+9) { animation-delay: 640ms; }

@keyframes page-fade-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}
.nicegui-content {
  animation: page-fade-in 200ms ease-out both;
}

.ag-row { transition: background-color 150ms ease-out; }
</style>
"""

# FullCalendar init JS + tooltip (D-13, D-14, D-15, D-16)
# initCalendar() is global — called via ui.run_javascript from registry.py
_CALENDAR_JS = """
<div id="cal-tooltip" style="
    position: fixed; z-index: 1000; background: white;
    border: 1px solid #e2e8f0; border-radius: 8px;
    padding: 12px; max-width: 256px;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.07);
    display: none;
"></div>
<style>
.fc { font-family: 'IBM Plex Sans', sans-serif; font-size: 13px; }
.fc-toolbar-title { font-size: 16px; font-weight: 600; color: #0f172a; }
.fc-button { font-family: 'IBM Plex Sans', sans-serif; font-size: 13px; }
.fc-button-primary { background-color: #4f46e5 !important; border-color: #4f46e5 !important; }
.fc-button-primary:not(.fc-button-active):hover { background-color: #4338ca !important; }
.fc-daygrid-day-number { color: #475569; font-size: 12px; }
.fc-daygrid-day.fc-day-today { background-color: #eef2ff !important; }
.fc-event { border-radius: 3px; font-size: 11px; padding: 1px 4px; }
</style>
<script>
window.initCalendar = function(events) {
  var el = document.getElementById('yurteg-calendar');
  if (!el) return;
  if (window._cal) { window._cal.destroy(); }
  window._cal = new FullCalendar.Calendar(el, {
    initialView: 'dayGridMonth',
    locale: 'ru',
    headerToolbar: { left: 'prev,next today', center: 'title', right: '' },
    height: 'auto',
    events: events,
    eventClick: function(info) { showCalTooltip(info); },
    buttonText: { today: 'Сегодня' },
    dayMaxEvents: 3,
  });
  window._cal.render();
};

function showCalTooltip(info) {
  var ev = info.event;
  var props = ev.extendedProps || {};
  var tooltip = document.getElementById('cal-tooltip');
  if (!tooltip) return;
  var typeLabel = props.type === 'end_date' ? 'Дата окончания' : 'Платёж';
  var detail = props.type === 'payment'
    ? (props.amount ? props.amount.toLocaleString('ru') + ' ₽' : '')
    : (ev.startStr || '');
  tooltip.innerHTML =
    '<div style="font-size:11px;color:#94a3b8;">' + typeLabel + '</div>' +
    '<div style="font-size:14px;font-weight:600;color:#0f172a;margin-top:2px;">' + (props.counterparty || ev.title) + '</div>' +
    '<div style="font-size:13px;color:#475569;margin-top:2px;">' + detail + '</div>' +
    '<div style="font-size:13px;color:#4f46e5;font-weight:600;cursor:pointer;margin-top:8px;" onclick="window.location.href=\'/document/' + props.contract_id + '\'">Открыть →</div>';
  var rect = info.el.getBoundingClientRect();
  tooltip.style.display = 'block';
  tooltip.style.top = (rect.bottom + 8) + 'px';
  tooltip.style.left = Math.min(rect.left, window.innerWidth - 280) + 'px';
}

document.addEventListener('click', function(e) {
  var tooltip = document.getElementById('cal-tooltip');
  if (tooltip && !tooltip.contains(e.target) && !e.target.closest('.fc-event')) {
    tooltip.style.display = 'none';
  }
});
</script>
"""

# ── Status badge CSS (D-23, D-24, Pattern 4 from Phase 8 RESEARCH) ────────────
# Tailwind @layer components — literal class strings для JS cellRenderer.
# Определяются один раз при старте, безопасны для JIT-purge.
# Phase 13 migration: unknown/terminated → slate-100/slate-500 (per DSGN-01, D-04, D-25)

_STATUS_CSS = """
<style type="text/tailwindcss">
  @layer components {
    .status-active      { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-50 text-green-700; }
    .status-expiring    { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-50 text-yellow-700; }
    .status-expired     { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-50 text-red-700; }
    .status-unknown     { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-500; }
    .status-terminated  { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-500; }
    .status-extended    { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700; }
    .status-negotiation { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-50 text-purple-700; }
    .status-suspended   { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-orange-50 text-orange-700; }
  }
</style>
"""

# Hover-actions CSS (Phase 08, Plan 03 — D-12, REG-06)
# actions-cell скрыт по умолчанию, появляется при наведении на строку
# Phase 13 migration: gray hex → slate/indigo hex (per DSGN-01, UI-SPEC migration map)
_ACTIONS_CSS = """
<style>
  .actions-cell { opacity: 0; transition: opacity 150ms ease; display: flex; align-items: center; justify-content: center; }
  .ag-row:hover .actions-cell { opacity: 1; }
  .action-icon { cursor: pointer; font-size: 18px; color: #64748b; line-height: 1; }
  .action-icon:hover { color: #4f46e5; }
  .expand-icon { color: #94a3b8; font-size: 12px; user-select: none; }
  .expand-icon:hover { color: #475569; }
</style>
"""

# Inject in correct order: font FIRST (Pitfall 4), then CDN, animations, calendar JS, status, actions
ui.add_head_html(_FONT_CSS)
ui.add_head_html(_FULLCALENDAR_CSS)
ui.add_head_html(_ANIMATION_CSS)
ui.add_head_html(_CALENDAR_JS)
ui.add_head_html(_STATUS_CSS)
ui.add_head_html(_ACTIONS_CSS)

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
    state.warning_days_threshold = app_settings.get("warning_days", 30)

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
