"""Страница «Документы» — реестр договоров на AG Grid.

Phase 08, Plans 02-03.
Phase 12, Plan 02 — empty state + guided tour onboarding.
Phase 13, Plan 03 — calendar toggle: List/Calendar view switching (DSGN-04, D-15).
Per D-03: сортировка по processed_at DESC (через COLUMN_DEFS hidden column).
Per D-04: три сегмента — Все · Истекают ⚠ · Требуют внимания.
Per D-07: текстовый поиск с debounce 300ms через rapidfuzz.
Per D-12: hover-actions — ⋯ контекстное меню.
Per D-13: контекстное меню — Открыть, Скачать оригинал, Переобработать, Удалить.
Per D-14: быстрая смена статуса из MANUAL_STATUSES.
Per D-15, D-16, D-17: версии документов с expand/collapse ▶/▼.
Per D-18: клик по строке → navigate to /document/{doc_id}.
Per D-19: клики actions не триггерят навигацию.
Per D-12 (onboarding): empty state при пустой БД без активных фильтров.
Per D-14 (onboarding): guided tour после первой обработки, один раз.
"""
import logging
from pathlib import Path

from nicegui import run, ui

from app.components.header import _header_refs
from app.components.process import start_pipeline
from app.demo_data import insert_demo_contracts
from app.styles import SEG_ACTIVE, SEG_INACTIVE, TOGGLE_ACTIVE, TOGGLE_INACTIVE, BTN_ACCENT_FILLED
from app.components.registry_table import (
    load_table_data,
    load_version_children,
    render_registry_table,
    _client_manager,
    _collapse_version_children,
)
from app.components.split_panel import render_split_panel
from app.components.bulk_actions import (
    render_bulk_toolbar,
    show_bulk_delete_dialog,
)
from app.state import get_state
from config import load_settings, save_setting
from services.lifecycle_service import get_attention_required
from services.payment_service import get_calendar_events

logger = logging.getLogger(__name__)



def _render_empty_state(container, state) -> None:
    """Rich empty state — CTA + три карточки возможностей (REGI-04).

    Per Phase 16 decision: «Выбрать папку» + 3 пункта:
      извлечём метаданные / разложим по папкам / проверим сроки
    Функциональный callback _on_pick_folder сохранён без изменений.
    """
    async def _on_pick_folder():
        from app.components.process import pick_folder
        source_dir = await pick_folder()
        if source_dir and hasattr(state, "_on_upload") and state._on_upload:
            await state._on_upload(source_dir)

    CAPABILITIES = [
        {
            "icon": '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#4f46e5" stroke-width="1.5"><path d="M9 12h6M9 16h6M9 8h6M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>',
            "title": "Извлечём метаданные",
            "body": "Тип, контрагент, суммы, сроки — автоматически из PDF и DOCX",
        },
        {
            "icon": '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#4f46e5" stroke-width="1.5"><path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>',
            "title": "Разложим по папкам",
            "body": "Структура по типам документов и контрагентам создаётся автоматически",
        },
        {
            "icon": '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#4f46e5" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
            "title": "Проверим сроки",
            "body": "Уведомления об истечении договоров — никаких пропущенных дедлайнов",
        },
    ]

    with container:
        # Центральная колонка с max-w
        with ui.column().classes("w-full items-center py-16 gap-10"):

            # ── Hero-текст ────────────────────────────────────────────────────
            with ui.column().classes("items-center gap-3 text-center max-w-lg"):
                with ui.element("h2").style("font-size:1.5rem;font-weight:700;color:#0f172a;margin:0"):
                    ui.html("Загрузите первые документы")
                with ui.element("p").style("font-size:0.9rem;color:#64748b;margin:0;line-height:1.6"):
                    ui.html("Выберите папку с PDF или DOCX — мы извлечём метаданные и разложим файлы автоматически")

            # ── CTA кнопка (filled, per BTN_ACCENT_FILLED) ───────────────────
            ui.button(
                "Выбрать папку",
                on_click=_on_pick_folder,
            ).classes(BTN_ACCENT_FILLED + " text-base px-8 py-3").props('aria-label="Выбрать папку с документами"')

            # ── Demo data button — subtle, не конкурирует с основным CTA ─────
            async def _on_load_demo():
                db = _client_manager.get_db(state.current_client)
                count = await run.io_bound(insert_demo_contracts, db)
                if count > 0:
                    ui.notify(f"Загружено {count} тестовых документов", type="positive")
                else:
                    ui.notify("Тестовые данные уже загружены", type="info")
                ui.navigate.to("/")

            ui.button(
                "Загрузить тестовые данные",
                on_click=_on_load_demo,
            ).props('flat no-caps aria-label="Загрузить демо-документы для тестирования"').classes(
                "text-sm text-slate-500 hover:text-indigo-600 transition-colors duration-150"
            )

            async def _on_clear_demo():
                db = _client_manager.get_db(state.current_client)
                await run.io_bound(lambda: db.conn.execute("DELETE FROM contracts"))
                await run.io_bound(lambda: db.conn.commit())
                save_setting("first_run_completed", False)
                save_setting("tour_completed", False)
                save_setting("first_processing_done", False)
                save_setting("trust_prompt_dismissed", False)
                ui.notify("Данные очищены", type="info")
                ui.navigate.to("/")

            ui.button(
                "Очистить тестовые данные",
                on_click=_on_clear_demo,
            ).props('flat no-caps aria-label="Очистить все данные и сбросить онбординг"').classes(
                "text-xs text-slate-400 hover:text-red-500 transition-colors duration-150"
            )

            # ── Три карточки возможностей ─────────────────────────────────────
            with ui.row().classes("gap-4 w-full max-w-2xl justify-center flex-wrap"):
                for cap in CAPABILITIES:
                    with ui.column().classes(
                        "bg-white border border-slate-200 rounded-xl p-5 gap-3 items-start"
                        " flex-1 min-w-[180px] max-w-[220px]"
                    ):
                        ui.html(cap["icon"])
                        with ui.column().classes("gap-1"):
                            with ui.element("p").style("font-size:0.875rem;font-weight:600;color:#0f172a;margin:0"):
                                ui.html(cap["title"])
                            with ui.element("p").style("font-size:0.8rem;color:#64748b;margin:0;line-height:1.5"):
                                ui.html(cap["body"])


def _render_trust_banner(
    container,
    doc_count: int,
    first_doc_id: int | None,
) -> None:
    """Trust-building banner shown after first processing (Phase 16).

    Prompts user to verify AI results before launching the guided tour.
    Dismissing or clicking navigates away; tour triggers on next page load.
    """

    def _dismiss():
        save_setting("trust_prompt_dismissed", True)
        container.set_visibility(False)

    def _open_first():
        save_setting("trust_prompt_dismissed", True)
        if first_doc_id:
            ui.navigate.to(f"/document/{first_doc_id}")
        else:
            container.set_visibility(False)

    container.set_visibility(True)
    with container:
        with ui.row().classes(
            "w-full px-6 pt-3 pb-0"
        ):
            with ui.row().classes(
                "w-full bg-indigo-50 border border-indigo-200 rounded-lg p-4"
                " items-center gap-3"
            ):
                # Check icon
                ui.html(
                    '<svg width="20" height="20" viewBox="0 0 20 20" fill="none"'
                    ' xmlns="http://www.w3.org/2000/svg">'
                    '<path d="M10 18a8 8 0 100-16 8 8 0 000 16z" fill="#4f46e5" opacity="0.15"/>'
                    '<path d="M7 10l2 2 4-4" stroke="#4f46e5" stroke-width="1.5"'
                    ' stroke-linecap="round" stroke-linejoin="round"/></svg>'
                )
                # Message
                ui.label(
                    f"Обработано {doc_count} "
                    + _pluralize_docs(doc_count)
                    + ". Откройте один и проверьте — всё ли верно?"
                ).classes("text-sm text-indigo-700 flex-1")
                # CTA button
                ui.button(
                    "Открыть первый документ \u2192",
                    on_click=_open_first,
                ).props("flat no-caps").classes(
                    "text-sm font-semibold text-indigo-600 hover:text-indigo-800"
                    " transition-colors duration-150 px-3 py-1"
                )
                # Dismiss X
                ui.button(
                    icon="close",
                    on_click=_dismiss,
                ).props("flat round dense").classes(
                    "text-indigo-400 hover:text-indigo-600"
                )


def _pluralize_docs(n: int) -> str:
    """Russian pluralization for 'документ'."""
    if 11 <= n % 100 <= 19:
        return "документов"
    mod10 = n % 10
    if mod10 == 1:
        return "документ"
    if 2 <= mod10 <= 4:
        return "документа"
    return "документов"


def _inject_hover_preview(grid) -> None:
    """Inject Apple-style hover preview card for AG Grid rows.

    Shows a floating card with full document info after 500ms hover.
    Uses AG Grid API events wired via JavaScript.
    """
    grid_id = grid.id

    # The preview card container + styles + JS logic
    ui.add_body_html(f"""
    <div id="hover-preview-{grid_id}" style="
        position: fixed;
        display: none;
        opacity: 0;
        z-index: 100;
        max-width: 360px;
        background: #fff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.08);
        padding: 16px;
        pointer-events: auto;
        transform: translateY(0px);
        transition: opacity 0.2s ease, transform 0.2s ease;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    "></div>
    <script>
    (function() {{
        var hoverTimer = null;
        var isOverCard = false;
        var isOverRow = false;
        var currentRowId = null;
        var preview = document.getElementById('hover-preview-{grid_id}');
        if (!preview) return;

        var STATUS_MAP = {{
            'active':      ['\\u2714', 'Действует',       '#dcfce7', '#166534'],
            'expiring':    ['\\u26a0', 'Заканчивается',   '#fef9c3', '#854d0e'],
            'expired':     ['\\u2718', 'Закончился',      '#fee2e2', '#991b1b'],
            'unknown':     ['',  'Нет даты',              '#f1f5f9', '#475569'],
            'negotiation': ['',  'На согласовании',       '#faf5ff', '#6b21a8']
        }};

        function formatDate(d) {{
            if (!d) return '\\u2014';
            var parts = d.split('-');
            if (parts.length === 3) return parts[2] + '.' + parts[1] + '.' + parts[0];
            return d;
        }}

        function escapeHtml(s) {{
            if (!s) return '';
            var div = document.createElement('div');
            div.textContent = s;
            return div.innerHTML;
        }}

        function buildCard(data) {{
            var status = data.computed_status || 'unknown';
            var sm = STATUS_MAP[status] || STATUS_MAP['unknown'];
            var icon = sm[0], label = sm[1], bg = sm[2], color = sm[3];

            var counterparty = escapeHtml(data.counterparty || '\\u2014');
            var amount = escapeHtml(data.amount || '\\u2014');
            var dateStart = formatDate(data.date_start);
            var dateEnd = formatDate(data.date_end);
            var confidence = data.confidence
                ? Math.round(data.confidence * 100) + '%'
                : '\\u2014';
            var subject = escapeHtml(data.subject || '');
            var contractType = escapeHtml(data.contract_type || 'Документ');

            var html = ''
                + '<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">'
                + '  <div style="width:36px;height:36px;background:#eef2ff;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0">\\ud83d\\udcc4</div>'
                + '  <div style="flex:1;min-width:0">'
                + '    <div style="font-size:15px;font-weight:600;color:#0f172a;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + contractType + '</div>'
                + '  </div>'
                + '  <span style="display:inline-flex;align-items:center;gap:3px;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:500;background:' + bg + ';color:' + color + ';white-space:nowrap;flex-shrink:0">'
                + (icon ? '<span>' + icon + '</span>' : '') + label
                + '  </span>'
                + '</div>'
                + '<div style="display:flex;align-items:center;gap:6px;margin-bottom:12px;font-size:12px;color:#64748b">'
                + '  <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + counterparty + '</span>'
                + '  <span style="color:#cbd5e1">\\u00b7</span>'
                + '  <span style="white-space:nowrap;font-variant-numeric:tabular-nums">' + amount + '</span>'
                + '</div>'
                + '<div style="height:1px;background:#e2e8f0;margin-bottom:12px"></div>'
                + '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;text-align:center">'
                + '  <div>'
                + '    <div style="font-size:10px;color:#94a3b8;margin-bottom:2px">Начало</div>'
                + '    <div style="font-size:12px;color:#334155;font-weight:500">' + dateStart + '</div>'
                + '  </div>'
                + '  <div>'
                + '    <div style="font-size:10px;color:#94a3b8;margin-bottom:2px">Окончание</div>'
                + '    <div style="font-size:12px;color:#334155;font-weight:500">' + dateEnd + '</div>'
                + '  </div>'
                + '  <div>'
                + '    <div style="font-size:10px;color:#94a3b8;margin-bottom:2px">Уверенность</div>'
                + '    <div style="font-size:12px;color:#334155;font-weight:500">' + confidence + '</div>'
                + '  </div>'
                + '</div>';

            if (subject) {{
                html += '<div style="margin-top:10px;font-size:11px;color:#94a3b8;line-height:1.4;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">'
                    + subject + '</div>';
            }}

            return html;
        }}

        function showPreview(data, rowEl) {{
            preview.innerHTML = buildCard(data);
            var rect = rowEl.getBoundingClientRect();
            var cardW = 360;
            var cardH = preview.offsetHeight || 200;
            var left = rect.right + 12;
            var top = rect.top + window.scrollY;

            // If card would overflow right edge, position to the left of the row
            if (left + cardW > window.innerWidth - 16) {{
                left = rect.left - cardW - 12;
                if (left < 16) left = 16;
            }}
            // If card would overflow bottom, shift up
            var viewTop = rect.top;
            if (viewTop + cardH > window.innerHeight - 16) {{
                top = rect.bottom + window.scrollY - cardH;
            }}

            preview.style.left = left + 'px';
            preview.style.top = top + 'px';
            preview.style.display = 'block';

            // Force reflow for transition
            preview.offsetHeight;
            preview.style.opacity = '1';
            preview.style.transform = 'translateY(-4px)';
        }}

        function hidePreview() {{
            preview.style.opacity = '0';
            preview.style.transform = 'translateY(0px)';
            setTimeout(function() {{
                if (preview.style.opacity === '0') {{
                    preview.style.display = 'none';
                }}
            }}, 200);
        }}

        function scheduleHide() {{
            setTimeout(function() {{
                if (!isOverCard && !isOverRow) {{
                    hidePreview();
                    currentRowId = null;
                }}
            }}, 100);
        }}

        preview.addEventListener('mouseenter', function() {{
            isOverCard = true;
        }});
        preview.addEventListener('mouseleave', function() {{
            isOverCard = false;
            scheduleHide();
        }});

        // Wire AG Grid row hover via DOM event delegation on the grid element
        var gridEl = document.querySelector('[id="{grid_id}"] .ag-body-viewport')
                  || document.getElementById('c' + '{grid_id}')
                  || null;

        // Fallback: find the grid wrapper by NiceGUI component id pattern
        if (!gridEl) {{
            // NiceGUI renders ag-grid inside a div with id="cXXX" where XXX is grid.id
            var wrapper = document.querySelector('[id^="c"][id$="{grid_id}"]');
            if (wrapper) gridEl = wrapper.querySelector('.ag-body-viewport') || wrapper;
        }}
        // Another fallback — just find the ag-body-viewport in the page
        if (!gridEl) {{
            gridEl = document.querySelector('.ag-body-viewport');
        }}
        if (!gridEl) return;

        gridEl.addEventListener('mouseover', function(e) {{
            var rowEl = e.target.closest('.ag-row');
            if (!rowEl) return;
            var rowId = rowEl.getAttribute('row-id');
            if (!rowId || rowId === currentRowId) {{
                isOverRow = true;
                return;
            }}
            isOverRow = true;
            if (hoverTimer) clearTimeout(hoverTimer);

            hoverTimer = setTimeout(function() {{
                // Get row data from AG Grid API
                try {{
                    var gridApi = getElement({grid_id}).gridOptions.api
                               || getElement({grid_id}).gridOptions;
                    var rowNode = null;
                    if (gridApi && gridApi.getRowNode) {{
                        rowNode = gridApi.getRowNode(rowId);
                    }}
                    if (!rowNode && gridApi && gridApi.forEachNode) {{
                        gridApi.forEachNode(function(node) {{
                            if (String(node.id) === String(rowId)) rowNode = node;
                        }});
                    }}
                    if (rowNode && rowNode.data) {{
                        // Skip child rows (version sub-rows)
                        if (rowNode.data.is_child) return;
                        currentRowId = rowId;
                        showPreview(rowNode.data, rowEl);
                    }}
                }} catch(err) {{
                    // Silently fail — preview is non-critical
                }}
            }}, 500);
        }});

        gridEl.addEventListener('mouseout', function(e) {{
            var rowEl = e.target.closest('.ag-row');
            var relTarget = e.relatedTarget;
            // Check if we moved to another element inside the same row
            if (rowEl && relTarget && rowEl.contains(relTarget)) return;
            isOverRow = false;
            if (hoverTimer) {{
                clearTimeout(hoverTimer);
                hoverTimer = null;
            }}
            scheduleHide();
        }});

        // Hide on scroll inside grid
        gridEl.addEventListener('scroll', function() {{
            if (hoverTimer) {{ clearTimeout(hoverTimer); hoverTimer = null; }}
            isOverRow = false;
            isOverCard = false;
            hidePreview();
            currentRowId = null;
        }});
    }})();
    </script>
    """)


def build() -> None:
    """Рендерит страницу реестра документов с поиском, сегментами и навигацией."""
    state = get_state()
    active_segment = {"value": "all"}
    grid_ref = {"grid": None}
    seg_buttons: dict = {}
    _timer: list = [None]

    with ui.column().classes("w-full max-w-none"):
        # ── Trust-building banner placeholder (Phase 16) ──────────────────────────
        trust_banner_container = ui.column().classes("w-full")
        trust_banner_container.set_visibility(False)

        # ── Deadline widget placeholder (WIRE-03) ─────────────────────────────────
        deadline_container = ui.column().classes("w-full")
        deadline_container.set_visibility(False)

        # ── Page heading + controls row ──────────────────────────────────────────
        with ui.row().classes("w-full px-6 pt-5 pb-2 items-center gap-4"):
            # REGI-05: Заголовок с визуальным весом
            ui.label("Реестр").classes("text-2xl font-semibold text-slate-900 mr-auto")

            # Calendar toggle — right-aligned (DSGN-04, D-15)
            with ui.row().classes("items-center gap-1 bg-slate-100 p-1 rounded-lg").props("id=calendar-toggle data-tour=calendar"):
                list_btn = ui.button("Список", icon="view_list").props("flat no-caps").classes(TOGGLE_ACTIVE + " text-xs px-3 py-1")
                list_btn.props('aria-label="Вид списком"')
                cal_btn = ui.button("Календарь", icon="calendar_month").props("flat no-caps").classes(TOGGLE_INACTIVE + " text-xs px-3 py-1")
                cal_btn.props('aria-label="Вид календарём"')

        # ── Search + Filter bar row (REGI-06) — search-row class for guided tour targeting (D-14 onboarding) ──
        with ui.row().classes("w-full px-6 pb-4 items-center gap-4 search-row").props("data-tour=filters") as search_row:
            search_input = (
                ui.input(placeholder="Поиск по реестру...")
                .props("outlined dense clearable").props('prepend-inner-icon=search')
                .classes("flex-1 max-w-lg")
            )

            # REGI-06: Filter bar с filled active state
            with ui.row().classes("gap-1.5 bg-slate-100 p-1 rounded-lg"):
                for key, label in [
                    ("all", "Все"),
                    ("expiring", "Истекают"),
                    ("attention", "Требуют внимания"),
                ]:
                    btn = ui.button(
                        label,
                        on_click=lambda k=key: _switch_segment(k),
                    ).props("flat unelevated no-caps")
                    btn.classes(SEG_ACTIVE if key == "all" else SEG_INACTIVE)
                    seg_buttons[key] = btn

        # Progress section — hidden by default (D-12)
        progress_section = ui.column().classes("w-full px-6 py-4 gap-2")
        progress_section.set_visibility(False)

        with progress_section:
            with ui.row().classes("items-center gap-3 w-full"):
                progress_bar = ui.linear_progress(value=0).classes("flex-1")
                count_label = ui.label("0/0 файлов").classes("text-sm text-slate-500 shrink-0")
            file_label = ui.label("").classes("text-xs text-slate-400")
            error_col = ui.column().classes("gap-1")

        # Skeleton loader — показывается до инициализации AG Grid (ANIM-04)
        skeleton_container = ui.column().classes("w-full px-6 pt-2")
        with skeleton_container:
            for _ in range(5):
                ui.element('div').classes("yt-skeleton-pulse rounded").style("height: 44px; margin-bottom: 2px;")

        # ── Bulk actions toolbar (UI Overhaul) ─────────────────────────────────────
        bulk_container = ui.column().classes("w-full px-4")

        # ── Split-view: grid + side panel (UI Overhaul) ───────────────────────────
        with ui.row().classes("w-full flex-1").style("min-height: 0;"):
            grid_container = ui.column().classes("flex-1 max-w-none px-4 overflow-hidden")
            grid_container.set_visibility(False)

            # Split panel — hidden by default, slides in on row click
            panel_container = ui.column().classes(
                "border-l border-slate-200 bg-slate-50 overflow-y-auto yt-panel-enter"
            ).style("width: var(--yt-panel-width, 340px); flex-shrink: 0;")
            panel_container.set_visibility(False)

        # Calendar container — hidden by default, shown when calendar_visible=True (DSGN-04, D-15)
        calendar_container = ui.column().classes("w-full px-6 py-4")
        calendar_container.set_visibility(False)

    # Build ui_refs for start_pipeline (D-06, D-07, D-08)
    ui_refs: dict = {
        "section": progress_section,
        "bar": progress_bar,
        "count": count_label,
        "file_label": file_label,
        "error_col": error_col,
        "upload_btn": _header_refs.get("upload_btn"),
    }

    # ── Inner helpers ──────────────────────────────────────────────────────────

    async def _refresh_deadline_widget() -> None:
        """Загружает и отображает виджет документов, требующих внимания (WIRE-03)."""
        db = _client_manager.get_db(state.current_client)
        all_alerts = await run.io_bound(get_attention_required, db, state.warning_days_threshold)
        dismissed = set(load_settings().get("dismissed_alerts", []))
        alerts = [a for a in all_alerts if a.contract_id not in dismissed]
        deadline_container.clear()
        if not alerts:
            deadline_container.set_visibility(False)
            return
        deadline_container.set_visibility(True)

        # Split into expired vs expiring
        expired = [a for a in alerts if a.days_until_expiry < 0]
        expiring = [a for a in alerts if a.days_until_expiry >= 0]

        with deadline_container:
            with ui.element("div").style(
                "background:white;border:1px solid #e2e8f0;border-radius:12px;"
                "margin:0 24px 8px 24px;padding:14px 16px;"
                "box-shadow:0 1px 2px rgba(0,0,0,0.04);"
            ):
                _expanded: dict = {"v": False}
                expand_icon_ref: list = []

                # Header FIRST in DOM
                with ui.row().classes("items-center gap-2 cursor-pointer w-full") as _hdr_row:
                    ui.icon("schedule").style("font-size:18px;color:#d97706;")
                    ui.label(f"Требуют внимания: {len(alerts)}").style(
                        "font-size:13px;font-weight:600;color:#92400e;"
                    )
                    _icon = ui.icon("expand_more").style(
                        "color:#d97706;font-size:18px;margin-left:auto;"
                    )
                    expand_icon_ref.append(_icon)

                # Items AFTER header
                items_col = ui.column().classes("w-full gap-0 mt-2")
                items_col.set_visibility(False)

                def _toggle_deadline(
                    _exp: dict = _expanded,
                    _col: object = items_col,
                    _icons: list = expand_icon_ref,
                ) -> None:
                    _exp["v"] = not _exp["v"]
                    _col.set_visibility(_exp["v"])
                    if _icons:
                        _icons[0].set_name("expand_less" if _exp["v"] else "expand_more")

                _hdr_row.on("click", lambda: _toggle_deadline())

                async def _dismiss_alert(contract_id: int) -> None:
                    """Dismiss alert by saving to dismissed list in settings."""
                    dismissed = load_settings().get("dismissed_alerts", [])
                    if contract_id not in dismissed:
                        dismissed.append(contract_id)
                        save_setting("dismissed_alerts", dismissed)
                    await _refresh_deadline_widget()

                def _render_alert_row(alert, is_last: bool) -> None:
                    days = alert.days_until_expiry
                    if days < 0:
                        days_text = f"истёк {abs(days)} дн. назад"
                        badge_bg = "#fee2e2"
                        badge_color = "#b91c1c"
                    else:
                        days_text = f"через {days} дн."
                        badge_bg = "#fef3c7"
                        badge_color = "#a16207"

                    counterparty = alert.counterparty or "\u2014"
                    contract_type = alert.contract_type or "Документ"
                    border_bottom = "border-bottom:1px solid #f1f5f9;" if not is_last else ""

                    row_el = ui.element("div").style(
                        f"padding:8px 12px;{border_bottom}"
                        "display:flex;align-items:center;gap:8px;"
                    )
                    with row_el:
                        with ui.element("div").style(
                            "flex:1;overflow:hidden;cursor:pointer;"
                            "display:flex;align-items:center;gap:8px;"
                        ).on(
                            "click",
                            lambda cid=alert.contract_id: ui.navigate.to(f"/document/{cid}"),
                        ):
                            ui.label(f"{contract_type} \u00b7 {counterparty}").style(
                                "font-size:12px;color:#334155;flex:1;"
                                "overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
                            )
                            ui.html(
                                f'<span style="font-size:11px;font-weight:600;color:{badge_color};'
                                f'background:{badge_bg};padding:2px 8px;border-radius:99px;'
                                f'white-space:nowrap;">{days_text}</span>'
                            )
                        ui.button(
                            icon="close",
                            on_click=lambda _e, cid=alert.contract_id: _dismiss_alert(cid),
                        ).props("flat round dense size=xs").style(
                            "color:#94a3b8;min-width:24px;min-height:24px;"
                        ).tooltip("Скрыть")

                with items_col:
                    # Expired section (only if has items)
                    if expired:
                        ui.label("Просрочены").style(
                            "font-size:10px;font-weight:600;color:#b91c1c;"
                            "text-transform:uppercase;letter-spacing:0.05em;"
                            "padding:6px 12px 2px;"
                        )
                        for i, alert in enumerate(expired):
                            _render_alert_row(alert, is_last=(i == len(expired) - 1 and not expiring))

                    # Expiring section (only if has items)
                    if expiring:
                        if expired:
                            ui.element("div").style("height:8px;")
                        ui.label("Скоро истекают").style(
                            "font-size:10px;font-weight:600;color:#a16207;"
                            "text-transform:uppercase;letter-spacing:0.05em;"
                            "padding:6px 12px 2px;"
                        )
                        for i, alert in enumerate(expiring):
                            _render_alert_row(alert, is_last=(i == len(expiring) - 1))

    def _apply_segment_classes(active_key: str) -> None:
        """Update button classes based on active segment."""
        for k, b in seg_buttons.items():
            b.classes(remove=SEG_ACTIVE + " " + SEG_INACTIVE)
            b.classes(SEG_ACTIVE if k == active_key else SEG_INACTIVE)

    def _sum_row(dot_color: str, label: str, count: str) -> None:
        """Render a summary row with colored dot, label, and count."""
        with ui.row().classes("cal-sum-row"):
            ui.element("div").classes("cal-sum-dot").style(f"background:{dot_color};")
            ui.label(label).classes("cal-sum-label")
            ui.label(count).classes("cal-sum-count")

    def _render_mini_calendar(today_date, events: list) -> None:
        """Render mini calendar with month navigation and colored dots (REG-05, REG-03)."""
        import calendar as cal_module
        from datetime import date as date_cls

        # Build date -> event_types map
        date_events: dict = {}
        for ev in events:
            try:
                d = date_cls.fromisoformat(str(ev["date"])[:10])
                date_events.setdefault(d, []).append(ev["type"])
            except Exception:
                continue

        month_names_ru = [
            "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
        ]

        cal_state = {"year": today_date.year, "month": today_date.month}
        cal_container = ui.element("div").classes("mini-cal")

        def _draw_calendar() -> None:
            """Draw calendar grid for current cal_state month."""
            cal_container.clear()
            year = cal_state["year"]
            month = cal_state["month"]

            with cal_container:
                with ui.element("div").classes("mini-cal-header"):
                    ui.label(f"{month_names_ru[month]} {year}").classes("mini-cal-month")
                    with ui.element("div").classes("mini-cal-nav"):
                        prev_btn = ui.element("button").classes("mini-cal-btn")
                        with prev_btn:
                            ui.html("\u2039")
                        prev_btn.on("click", lambda: _nav_month(-1))

                        next_btn = ui.element("button").classes("mini-cal-btn")
                        with next_btn:
                            ui.html("\u203a")
                        next_btn.on("click", lambda: _nav_month(1))

                with ui.element("div").classes("mini-cal-grid"):
                    # Day headers (Monday first)
                    for day_name in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]:
                        with ui.element("div").classes("mini-cal-day-header"):
                            ui.html(day_name)

                    # Calendar days
                    cal = cal_module.Calendar(firstweekday=0)
                    for d in cal.itermonthdates(year, month):
                        is_other = d.month != month
                        is_today = d == today_date
                        cls = "mini-cal-day"
                        if is_other:
                            cls += " mini-cal-day-other"
                        if is_today:
                            cls += " mini-cal-day-today"

                        with ui.element("div").classes(cls):
                            ui.html(str(d.day))
                            types_on_day = date_events.get(d, [])
                            dot_types = list(set(types_on_day))
                            for i, t in enumerate(dot_types[:2]):  # Max 2 dots per day
                                dot_cls = {
                                    "end": "mini-cal-dot-end",
                                    "pay": "mini-cal-dot-pay",
                                    "expiring": "mini-cal-dot-expiring",
                                }.get(t, "")
                                offset = 40 + i * 20
                                ui.element("div").classes(f"mini-cal-dot {dot_cls}").style(
                                    f"left:{offset}%; transform:translateX(-50%);"
                                )

                # "Сегодня" reset link (only show when not on current month)
                if year != today_date.year or month != today_date.month:
                    today_link = ui.label("Сегодня \u21a9").style(
                        "font-size:12px;color:#4f46e5;cursor:pointer;"
                        "margin-top:6px;text-align:center;width:100%;"
                    )
                    today_link.on("click", lambda: _nav_today())

        def _nav_month(delta: int) -> None:
            """Navigate month by delta (-1 or +1), wrapping year."""
            m = cal_state["month"] + delta
            if m < 1:
                cal_state["year"] -= 1
                cal_state["month"] = 12
            elif m > 12:
                cal_state["year"] += 1
                cal_state["month"] = 1
            else:
                cal_state["month"] = m
            _draw_calendar()

        def _nav_today() -> None:
            """Reset to today's month."""
            cal_state["year"] = today_date.year
            cal_state["month"] = today_date.month
            _draw_calendar()

        _draw_calendar()

    async def _show_calendar() -> None:
        """Render timeline view with event cards and mini-calendar (REG-05)."""
        from datetime import date, timedelta

        db = _client_manager.get_db(state.current_client)
        today = date.today()

        def _parse_date_safe(d):
            try:
                return date.fromisoformat(str(d)[:10])
            except Exception:
                return None

        # 1. Fetch payment events
        try:
            payment_events = await run.io_bound(get_calendar_events, db)
        except Exception:
            logger.exception("Ошибка загрузки событий (платежи)")
            payment_events = []

        # 2. Fetch contract end-date events
        try:
            end_rows = await run.io_bound(
                lambda: db.conn.execute(
                    "SELECT id, contract_type, counterparty, subject, date_end, amount "
                    "FROM contracts WHERE date_end IS NOT NULL AND status = 'done'"
                ).fetchall()
            )
        except Exception:
            logger.exception("Ошибка загрузки событий (договоры)")
            end_rows = []

        # 3. Fetch expiring contracts (within warning_days threshold)
        try:
            expiring_rows = await run.io_bound(
                lambda: db.conn.execute(
                    "SELECT id FROM contracts WHERE date_end IS NOT NULL AND status = 'done' "
                    "AND date_end > date('now') AND date_end <= date('now', '+' || :wd || ' days')",
                    {"wd": state.warning_days_threshold},
                ).fetchall()
            )
        except Exception:
            logger.exception("Ошибка загрузки скоро истекающих")
            expiring_rows = []

        # 4. Build unified events list
        expiring_ids = {dict(r)["id"] for r in expiring_rows} if expiring_rows else set()
        events: list[dict] = []

        for r in end_rows:
            c = dict(r)
            evt_type = "expiring" if c["id"] in expiring_ids else "end"
            events.append({
                "type": evt_type,
                "date": c["date_end"],
                "contract_id": c["id"],
                "contract_type": c.get("contract_type", ""),
                "counterparty": c.get("counterparty", ""),
                "subject": c.get("subject", ""),
                "amount": c.get("amount"),
            })

        for ev in payment_events:
            title = ev.get("title", "")
            counterparty = title.split(" · ")[0] if " · " in title else title
            events.append({
                "type": "pay",
                "date": ev.get("start", ""),
                "contract_id": ev.get("extendedProps", {}).get("contract_id"),
                "contract_type": "",
                "counterparty": counterparty,
                "subject": title,
                "amount": ev.get("extendedProps", {}).get("amount"),
            })

        # Sort by date
        events.sort(key=lambda e: str(e.get("date", "9999")))

        # 5. Group events: today / this week / this month / later
        week_end = today + timedelta(days=7)
        month_end = today.replace(day=28) + timedelta(days=4)
        month_end = month_end.replace(day=1)  # first day of next month

        groups: dict[str, list] = {"past": [], "today": [], "week": [], "month": [], "later": []}
        for ev in events:
            d = _parse_date_safe(ev["date"])
            if d is None:
                continue
            if d < today:
                groups["past"].append(ev)
            elif d == today:
                groups["today"].append(ev)
            elif d <= week_end:
                groups["week"].append(ev)
            elif d < month_end:
                groups["month"].append(ev)
            else:
                groups["later"].append(ev)

        # 6. Stats for summary panel (current month)
        end_count = sum(
            1 for e in events
            if e["type"] == "end"
            and _parse_date_safe(e["date"])
            and _parse_date_safe(e["date"]).month == today.month
        )
        pay_count = sum(
            1 for e in events
            if e["type"] == "pay"
            and _parse_date_safe(e["date"])
            and _parse_date_safe(e["date"]).month == today.month
        )
        exp_count = sum(1 for e in events if e["type"] == "expiring")
        pay_total = sum(
            float(str(e.get("amount", 0) or 0).replace(" ", "").replace(",", "."))
            for e in events
            if e["type"] == "pay"
            and _parse_date_safe(e["date"])
            and _parse_date_safe(e["date"]).month == today.month
        )

        # 7. Render UI
        calendar_container.clear()
        with calendar_container:
            with ui.row(wrap=False).classes("w-full gap-6"):

                # LEFT: Timeline feed (fills remaining space)
                with ui.column().classes("min-w-0 flex-1"):
                    ui.label("Ближайшие события").style(
                        "font-size:15px; font-weight:600; color:#1e293b; margin-bottom:14px;"
                    )

                    def _render_event_card(ev: dict, future: bool = False) -> None:
                        type_map = {
                            "end": ("Окончание договора", "timeline-card-end", "timeline-type-end"),
                            "pay": ("Платёж", "timeline-card-pay", "timeline-type-pay"),
                            "expiring": (
                                f"Скоро истекает ({state.warning_days_threshold} дн.)",
                                "timeline-card-expiring",
                                "timeline-type-expiring",
                            ),
                        }
                        type_label, card_cls, type_cls = type_map.get(ev["type"], ("Событие", "", ""))
                        extra_cls = " timeline-future" if future else ""

                        cid = ev.get("contract_id")
                        card = ui.element("div").classes(f"timeline-card {card_cls}{extra_cls}")
                        with card:
                            with ui.column().classes("gap-0"):
                                ui.label(type_label).classes(f"timeline-type {type_cls}")
                                ui.label(ev.get("counterparty", "")).classes("timeline-name")
                                ui.label(ev.get("subject", "")).classes("timeline-meta")
                            with ui.column().classes("items-end gap-0 shrink-0"):
                                d = _parse_date_safe(ev["date"])
                                if d and d != today:
                                    _month_short_ru = [
                                        "", "янв", "фев", "мар", "апр", "мая", "июн",
                                        "июл", "авг", "сен", "окт", "ноя", "дек",
                                    ]
                                    ui.label(f"{d.day} {_month_short_ru[d.month]}").classes("timeline-date")
                                if ev.get("amount"):
                                    try:
                                        amt = (
                                            f"{int(float(str(ev['amount']).replace(' ', '').replace(',', '.'))):,}"
                                            .replace(",", " ") + " ₽"
                                        )
                                    except (ValueError, TypeError):
                                        amt = str(ev["amount"])
                                    ui.label(amt).classes("timeline-amount")
                        if cid:
                            card.on("click", lambda c=cid: ui.navigate.to(f"/document/{c}"))

                    # Past events — collapsible "Просрочены" (REG-02)
                    if groups["past"]:
                        _past_expanded: dict = {"v": False}
                        _past_icon_ref: list = []
                        past_hdr = ui.row().classes("items-center gap-2 cursor-pointer w-full")
                        with past_hdr:
                            ui.icon("warning").style("font-size:16px;color:#dc2626;")
                            ui.label(f"Просрочены \u2014 {len(groups['past'])}").classes(
                                "timeline-group-title"
                            ).style("color:#dc2626;margin:0;")
                            _pi = ui.icon("expand_more").style(
                                "color:#dc2626;font-size:18px;margin-left:auto;"
                            )
                            _past_icon_ref.append(_pi)
                        past_items = ui.column().classes("w-full gap-0")
                        past_items.set_visibility(False)
                        with past_items:
                            for ev in groups["past"]:
                                _render_event_card(ev)

                        def _toggle_past(
                            _exp: dict = _past_expanded,
                            _col: object = past_items,
                            _icons: list = _past_icon_ref,
                        ) -> None:
                            _exp["v"] = not _exp["v"]
                            _col.set_visibility(_exp["v"])
                            if _icons:
                                _icons[0].set_name("expand_less" if _exp["v"] else "expand_more")

                        past_hdr.on("click", lambda: _toggle_past())

                    # Today group
                    _month_full_ru = [
                        "", "января", "февраля", "марта", "апреля", "мая", "июня",
                        "июля", "августа", "сентября", "октября", "ноября", "декабря",
                    ]

                    if groups["today"]:
                        ui.label(f"Сегодня · {today.day} {_month_full_ru[today.month]}").classes(
                            "timeline-group-title timeline-group-today"
                        ).style("margin-top:4px;")
                        for ev in groups["today"]:
                            _render_event_card(ev)

                    # This week group
                    if groups["week"]:
                        ui.label("На этой неделе").classes("timeline-group-title timeline-group-week")
                        for ev in groups["week"]:
                            _render_event_card(ev)

                    # This month group
                    if groups["month"]:
                        month_names = [
                            "", "января", "февраля", "марта", "апреля", "мая", "июня",
                            "июля", "августа", "сентября", "октября", "ноября", "декабря",
                        ]
                        ui.label(f"В {month_names[today.month]}").classes(
                            "timeline-group-title timeline-group-month"
                        )
                        for ev in groups["month"]:
                            _render_event_card(ev)

                    # Later group (next month+, max 5)
                    if groups["later"]:
                        ui.label("Позже").classes("timeline-group-title timeline-group-month")
                        for ev in groups["later"][:5]:
                            _render_event_card(ev, future=True)

                    if not any(groups.values()):
                        ui.label("Нет предстоящих событий").classes(
                            "text-sm text-slate-400 py-8 text-center"
                        )

                # RIGHT: Mini-calendar + summary (fixed 280px)
                with ui.column().classes("shrink-0").style("width: 280px;"):
                    _render_mini_calendar(today, events)

                    with ui.element("div").classes("cal-summary"):
                        ui.label("Итого в этом месяце").classes("cal-sum-title")
                        _sum_row("#dc2626", "Истекает", str(end_count))
                        _sum_row("#2563eb", "Платежей", str(pay_count))
                        _sum_row("#d97706", "Скоро истекает", str(exp_count))
                        with ui.element("div").style(
                            "border-top:1px solid #f1f5f9; margin-top:8px; padding-top:8px;"
                        ):
                            with ui.row().classes("cal-sum-row"):
                                ui.label("Сумма платежей").classes("cal-sum-label")
                                try:
                                    pay_fmt = f"{int(pay_total):,}".replace(",", " ") + " ₽"
                                except Exception:
                                    pay_fmt = "—"
                                ui.label(pay_fmt).classes("cal-sum-count").style("font-size:14px;")

    async def _switch_view(view: str) -> None:
        """Переключает вид между списком и календарём (DSGN-04, D-15)."""
        list_btn.disable()
        cal_btn.disable()
        try:
            state.calendar_visible = (view == "calendar")
            if state.calendar_visible:
                list_btn.classes(remove=TOGGLE_ACTIVE + " " + TOGGLE_INACTIVE)
                list_btn.classes(TOGGLE_INACTIVE)
                cal_btn.classes(remove=TOGGLE_ACTIVE + " " + TOGGLE_INACTIVE)
                cal_btn.classes(TOGGLE_ACTIVE)
                search_row.set_visibility(False)
                grid_container.set_visibility(False)
                calendar_container.set_visibility(True)
                await _show_calendar()
            else:
                list_btn.classes(remove=TOGGLE_ACTIVE + " " + TOGGLE_INACTIVE)
                list_btn.classes(TOGGLE_ACTIVE)
                cal_btn.classes(remove=TOGGLE_ACTIVE + " " + TOGGLE_INACTIVE)
                cal_btn.classes(TOGGLE_INACTIVE)
                search_row.set_visibility(True)
                grid_container.set_visibility(True)
                calendar_container.set_visibility(False)
        finally:
            list_btn.enable()
            cal_btn.enable()

    list_btn.on_click(lambda: _switch_view("list"))
    cal_btn.on_click(lambda: _switch_view("calendar"))

    async def _switch_segment(key: str) -> None:
        active_segment["value"] = key
        _apply_segment_classes(key)
        if grid_ref["grid"]:
            await load_table_data(grid_ref["grid"], state, key)

    # Debounced search — per Pitfall 6 from RESEARCH, 300ms debounce
    def _on_search(e) -> None:
        state.filter_search = e.value if hasattr(e, "value") else str(e.args)
        if _timer[0]:
            _timer[0].cancel()
        _timer[0] = ui.timer(0.3, lambda: _do_search(), once=True)

    async def _do_search() -> None:
        if grid_ref["grid"]:
            await load_table_data(grid_ref["grid"], state, active_segment["value"])

    search_input.on("update:model-value", _on_search)

    # ── Action menu (persistent, repositioned on each click) ────────────────────

    # Anchor element for menu positioning — moved via JS to the clicked cell
    menu_anchor = ui.element("div").style(
        "position:fixed;width:1px;height:1px;pointer-events:none;z-index:-1;"
    )
    menu_anchor.props(f'id="action-menu-anchor-{id(menu_anchor)}"')
    _anchor_id = f"action-menu-anchor-{id(menu_anchor)}"

    with menu_anchor:
        action_menu = ui.menu().props("auto-close")
    menu_container = {"ref": action_menu}

    async def _show_action_menu(data: dict) -> None:
        """Показывает контекстное меню с действиями для строки (D-13, D-14)."""
        contract_id = data.get("id")
        if not contract_id:
            return

        # Position the anchor at the actions cell of the clicked row via JS
        await ui.run_javascript(f"""
            (function() {{
                var anchor = document.getElementById('{_anchor_id}');
                var focused = document.querySelector('.ag-row[row-id="' + {contract_id} + '"] .actions-cell');
                if (!focused) {{
                    // Fallback: find any visible actions-cell that was recently hovered
                    var cells = document.querySelectorAll('.ag-row:hover .actions-cell');
                    focused = cells.length ? cells[0] : null;
                }}
                if (focused && anchor) {{
                    var rect = focused.getBoundingClientRect();
                    anchor.style.left = rect.right + 'px';
                    anchor.style.top = (rect.top + rect.height / 2) + 'px';
                }}
            }})();
        """)

        # Rebuild menu content
        menu = menu_container["ref"]
        menu.clear()
        with menu:
            # Открыть (D-13)
            ui.menu_item("Открыть", on_click=lambda: ui.navigate.to(f"/document/{contract_id}"))

        menu.open()


    # ── Version expand/collapse ──────────────────────────────────────────────────

    async def _toggle_expand(contract_id: int, data: dict) -> None:
        """Раскрывает или сворачивает дочерние версии (D-16, D-17)."""
        grid = grid_ref["grid"]
        if not grid:
            return
        db = _client_manager.get_db(state.current_client)
        if data.get("is_expanded"):
            _collapse_version_children(grid, contract_id)
        else:
            await load_version_children(grid, db, contract_id)

    # ── Cell click handler ────────────────────────────────────────────────────────

    # ── Split panel helpers (UI Overhaul) ─────────────────────────────────────
    def _close_panel():
        state.split_panel_doc_id = None
        panel_container.set_visibility(False)

    # ── Bulk actions helpers (UI Overhaul) ─────────────────────────────────────
    def _refresh_bulk_toolbar():
        bulk_container.clear()
        if state.bulk_mode and state.selected_doc_ids:
            total = len(grid_ref["grid"].options.get("rowData", [])) if grid_ref["grid"] else 0
            with bulk_container:
                render_bulk_toolbar(
                    selected_ids=state.selected_doc_ids,
                    total_count=total,
                    on_clear=_clear_bulk_selection,
                    on_status_change=lambda: None,
                    on_delete=lambda: show_bulk_delete_dialog(state.selected_doc_ids, _delete_bulk),
                )

    def _clear_bulk_selection():
        state.selected_doc_ids = []
        state.bulk_mode = False
        bulk_container.clear()
        if grid_ref["grid"]:
            grid_ref["grid"].run_grid_method("deselectAll")

    async def _delete_bulk(doc_ids):
        db = _client_manager.get_db(state.current_client)
        for doc_id in doc_ids:
            await run.io_bound(lambda did=doc_id: db.conn.execute("DELETE FROM contracts WHERE id = ?", (did,)))
        await run.io_bound(lambda: db.conn.commit())
        _clear_bulk_selection()
        if grid_ref["grid"]:
            await load_table_data(grid_ref["grid"], state, active_segment["value"])
        await _refresh_deadline_widget()
        ui.notify(f"Удалено {len(doc_ids)} документов", type="positive")

    async def _on_selection_changed(e) -> None:
        """Handle AG Grid selection change — toggle bulk toolbar."""
        grid = grid_ref["grid"]
        if not grid:
            return
        selected = await grid.get_selected_rows()
        state.selected_doc_ids = [r["id"] for r in selected if "id" in r]
        state.bulk_mode = len(state.selected_doc_ids) > 0
        _refresh_bulk_toolbar()

    # Row click → show split panel (UI Overhaul — was navigate), with action/expand dispatch
    async def _on_cell_clicked(e) -> None:
        col_id = e.args.get("colId", "")
        data = e.args.get("data", {})

        # Skip checkbox column clicks
        if col_id == "selected":
            return

        if col_id == "actions_html":
            # D-19: action clicks don't navigate
            await _show_action_menu(data)
            return

        if col_id == "expand_html" and data.get("has_children"):
            # D-16: expand/collapse version children
            await _toggle_expand(data["id"], data)
            return

        # Default: show in split panel (UI Overhaul) — skip child rows
        doc_id = data.get("id")
        if doc_id and not data.get("is_child"):
            state.split_panel_doc_id = doc_id
            # Fetch full doc from DB for panel display
            db = _client_manager.get_db(state.current_client)
            doc = await run.io_bound(db.get_contract_by_id, doc_id)
            if doc:
                doc = dict(doc) if not isinstance(doc, dict) else doc
                doc["computed_status"] = data.get("computed_status", "unknown")
                render_split_panel(
                    panel_container, doc,
                    on_close=_close_panel,
                    on_open_full=lambda did=doc_id: ui.navigate.to(f"/document/{did}"),
                )

    async def _on_upload(source_dir: Path) -> None:
        """Callback triggered by header upload button (D-06, D-07, D-08, D-11)."""
        # Re-grab upload_btn ref (may not be set at module init time)
        ui_refs["upload_btn"] = _header_refs.get("upload_btn")
        try:
            await start_pipeline(source_dir, state, ui_refs)
        except Exception:
            logger.exception("Pipeline failed for %s", source_dir)
            ui.notify(
                "Ошибка при обработке документов. Попробуйте снова или проверьте настройки.",
                type="negative",
                timeout=8000,
            )
            # Restore UI state so the app doesn't hang
            state.processing = False
            upload_btn = ui_refs.get("upload_btn")
            if upload_btn:
                upload_btn.set_enabled(True)
            return
        # Mark first processing done for trust-building prompt (Phase 16)
        settings = load_settings()
        if not settings.get("first_processing_done"):
            save_setting("first_processing_done", True)
        # After pipeline: refresh table (D-11)
        if grid_ref["grid"]:
            await load_table_data(grid_ref["grid"], state, active_segment["value"])
        await _refresh_deadline_widget()

    # Store callback on state so main.py can delegate to it
    state._on_upload = _on_upload  # type: ignore[attr-defined]

    async def _init() -> None:
        await _refresh_deadline_widget()
        skeleton_container.set_visibility(False)
        grid_container.set_visibility(True)
        with grid_container:
            grid = await render_registry_table(state)
            grid_ref["grid"] = grid
            grid.on("cellClicked", _on_cell_clicked)
            grid.on("selectionChanged", _on_selection_changed)
            _inject_hover_preview(grid)
            await load_table_data(grid, state, "all")
            rows = grid.options.get("rowData", [])
            # Empty state: only when 0 rows AND no active filters (per D-12, Pitfall 4)
            if (
                not rows
                and not state.filter_search
                and active_segment["value"] == "all"
            ):
                grid.set_visibility(False)
                # Hide toggle buttons — calendar makes no sense with no data
                list_btn.set_visibility(False)
                cal_btn.set_visibility(False)
                _render_empty_state(grid_container, state)
            elif not rows:
                # Filtered search returned 0 results — show helpful message inside grid area
                with grid_container:
                    no_results = ui.column().classes("py-8 flex flex-col items-center gap-2")
                    with no_results:
                        ui.label("Ничего не найдено").classes("text-sm font-semibold text-slate-500")
                        ui.label("Попробуйте другой запрос или сбросьте фильтры").classes("text-xs text-slate-400")

                        async def _reset_filters():
                            state.filter_search = ""
                            active_segment["value"] = "all"
                            await load_table_data(grid, state, "all")
                            no_results.delete()

                        ui.button("Сбросить фильтры", on_click=_reset_filters).props(
                            "flat no-caps"
                        ).classes("text-xs text-indigo-600")
            elif rows:
                # Trust-building prompt + guided tour (Phase 16, D-14, D-18)
                settings = load_settings()
                if not settings.get("tour_completed"):
                    first_done = settings.get("first_processing_done", False)
                    trust_dismissed = settings.get("trust_prompt_dismissed", False)

                    if first_done and not trust_dismissed:
                        # Show trust-building banner before tour
                        doc_count = len(rows)
                        first_doc_id = rows[0].get("id") if rows else None
                        _render_trust_banner(
                            trust_banner_container, doc_count, first_doc_id,
                        )
                    elif first_done and trust_dismissed:
                        # Trust prompt already seen — now show the guided tour
                        upload_btn = _header_refs.get("upload_btn")
                        if upload_btn:
                            upload_btn.props("id=upload-btn")
                        from app.components.onboarding.tour import render_tour

                        async def _on_tour_complete():
                            save_setting("tour_completed", True)

                        ui.timer(0.5, lambda: render_tour(_on_tour_complete), once=True)

    ui.timer(0, _init, once=True)
