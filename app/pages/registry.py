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
import json
from pathlib import Path

from nicegui import run, ui

from app.components.header import _header_refs
from app.components.process import start_pipeline
from app.components.ui_helpers import empty_state
from app.styles import SEG_ACTIVE, SEG_INACTIVE, TOGGLE_ACTIVE, TOGGLE_INACTIVE, STATS_BAR, STATS_ITEM, STAT_NUMBER, STAT_LABEL
from app.components.registry_table import (
    load_table_data,
    load_version_children,
    render_registry_table,
    _client_manager,
    _collapse_version_children,
    _fetch_counts,
)
from app.state import get_state
from config import load_settings, save_setting
from services.lifecycle_service import MANUAL_STATUSES, STATUS_LABELS, set_manual_status
from services.payment_service import get_calendar_events



def _render_empty_state(container, state) -> None:
    """Рендерит empty state при пустой БД без активных фильтров.

    Per UI-SPEC Component 3 — точный layout, CSS и копия.
    Отображается когда load_table_data вернул 0 строк И нет активных фильтров.
    """
    async def _on_pick_folder():
        from app.components.process import pick_folder
        source_dir = await pick_folder()
        if source_dir and hasattr(state, "_on_upload") and state._on_upload:
            await state._on_upload(source_dir)

    FOLDER_ICON = (
        '<svg width="48" height="48" viewBox="0 0 24 24" fill="none"'
        ' stroke="#cbd5e1" stroke-width="1.5">'
        '<path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>'
        '</svg>'
    )

    with container:
        empty_state(
            icon_svg=FOLDER_ICON,
            title="Загрузите первые документы",
            description="Выберите папку с PDF или DOCX — мы извлечём метаданные и разложим файлы автоматически.",
            button_label="Выбрать папку",
            on_click=_on_pick_folder,
            hints=["Извлечёт метаданные", "Разложит по папкам", "Проверит сроки"],
        )


def build() -> None:
    """Рендерит страницу реестра документов с поиском, сегментами и навигацией."""
    state = get_state()
    active_segment = {"value": "all"}
    grid_ref = {"grid": None}
    seg_buttons: dict = {}
    _timer: list = [None]

    with ui.column().classes("w-full"):
        # ── Stats bar (REGI-01) — светлый фон, не тёмная полоса ──────────────────
        stats_row = ui.row().classes(STATS_BAR)
        total_num = ui.label("—")
        expiring_num = ui.label("—")
        attention_num = ui.label("—")

        with stats_row:
            with ui.column().classes(STATS_ITEM):
                total_num.classes(STAT_NUMBER + " text-slate-900")
                ui.label("документов").classes(STAT_LABEL + " text-slate-500")
            ui.label("·").classes("text-slate-300 text-xl font-light")
            with ui.column().classes(STATS_ITEM):
                expiring_num.classes(STAT_NUMBER + " text-amber-600")
                ui.label("истекают").classes(STAT_LABEL + " text-slate-500")
            ui.label("·").classes("text-slate-300 text-xl font-light")
            with ui.column().classes(STATS_ITEM):
                attention_num.classes(STAT_NUMBER + " text-red-600")
                ui.label("требуют внимания").classes(STAT_LABEL + " text-slate-500")

        # ── Page heading + controls row ──────────────────────────────────────────
        with ui.row().classes("w-full px-6 pt-5 pb-2 items-center gap-4"):
            # REGI-05: Заголовок с визуальным весом
            ui.label("Реестр").classes("text-2xl font-semibold text-slate-900 mr-auto")

            # Calendar toggle — right-aligned (DSGN-04, D-15)
            with ui.row().classes("items-center gap-1.5"):
                list_btn = ui.button("≡").props("flat no-caps").classes(TOGGLE_ACTIVE)
                list_btn.props('title="Список" aria-label="Вид списком"')
                cal_btn = ui.button("⊞").props("flat no-caps").classes(TOGGLE_INACTIVE)
                cal_btn.props('title="Календарь" aria-label="Вид календарём"')

        # ── Search + Filter bar row (REGI-06) — search-row class for guided tour targeting (D-14 onboarding) ──
        with ui.row().classes("w-full px-6 pb-4 items-center gap-4 search-row"):
            search_input = (
                ui.input(placeholder="Поиск по реестру...")
                .props("outlined dense")
                .classes("flex-1 max-w-md")
            )

            # REGI-06: Filter bar с filled active state
            with ui.row().classes("gap-1.5 bg-slate-100 p-1 rounded-lg"):
                for key, label in [
                    ("all", "Все"),
                    ("expiring", "Истекают ⚠"),
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

        grid_container = ui.column().classes("w-full")

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

    async def _refresh_stats() -> None:
        """Обновляет counts в stats bar (REGI-01). Вызывается при init и после фильтрации."""
        counts = await run.io_bound(_fetch_counts, state.current_client, state.warning_days_threshold)
        total_num.set_text(str(counts["total"]))
        expiring_num.set_text(str(counts["expiring"]))
        attention_num.set_text(str(counts["attention"]))

    def _apply_segment_classes(active_key: str) -> None:
        """Update button classes based on active segment."""
        for k, b in seg_buttons.items():
            b.classes(remove=SEG_ACTIVE + " " + SEG_INACTIVE)
            b.classes(SEG_ACTIVE if k == active_key else SEG_INACTIVE)

    _fc_loaded = {"done": False}

    async def _ensure_fullcalendar() -> None:
        """Lazy-load FullCalendar CDN on first calendar toggle."""
        if _fc_loaded["done"]:
            return
        await ui.run_javascript("""
            if (!window.FullCalendar) {
                const link = document.createElement('link');
                link.rel = 'stylesheet';
                link.href = 'https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.css';
                document.head.appendChild(link);
                await new Promise((resolve, reject) => {
                    const script = document.createElement('script');
                    script.src = 'https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.js';
                    script.onload = resolve;
                    script.onerror = reject;
                    document.head.appendChild(script);
                });
            }
        """)
        _fc_loaded["done"] = True

    async def _show_calendar() -> None:
        """Fetch events and render FullCalendar via JS (D-10, D-11, D-12, D-16)."""
        await _ensure_fullcalendar()
        db = _client_manager.get_db(state.current_client)

        # Payment events — override color to slate-400 (Pitfall 5, D-12)
        try:
            payment_events = await run.io_bound(get_calendar_events, db)
        except Exception:
            payment_events = []
        for ev in payment_events:
            ev["color"] = "#94a3b8"  # slate-400 — all payments same color
            ev["id"] = f"payment-{ev.get('extendedProps', {}).get('contract_id', 0)}-{ev.get('start', '')}"
            # Normalise extendedProps to include type=payment
            if "extendedProps" not in ev:
                ev["extendedProps"] = {}
            ev["extendedProps"]["type"] = "payment"

        # Contract end-date events — indigo (D-12)
        # Optimized: fetch only needed columns instead of get_all_results (full table scan)
        try:
            rows = await run.io_bound(
                lambda: db.conn.execute(
                    "SELECT id, contract_type, counterparty, date_end "
                    "FROM contracts WHERE date_end IS NOT NULL AND status = 'done'"
                ).fetchall()
            )
        except Exception:
            rows = []
        end_events: list[dict] = []
        for r in rows:
            c = dict(r)
            end_events.append({
                "id": f"contract-{c['id']}",
                "title": f"{c.get('counterparty', '')} · {c.get('contract_type', '')}",
                "start": c["date_end"],
                "color": "#4f46e5",  # indigo-600
                "extendedProps": {
                    "type": "end_date",
                    "contract_id": c["id"],
                    "counterparty": c.get("counterparty", ""),
                    "doc_type": c.get("contract_type", ""),
                },
            })

        all_events = payment_events + end_events

        if not all_events:
            ui.notify(
                "Не удалось загрузить события календаря. Попробуйте переключить вид.",
                type="warning",
            )

        json_str = json.dumps(all_events, ensure_ascii=False, default=str)

        calendar_container.clear()
        with calendar_container:
            ui.html('<div id="yurteg-calendar"></div>').classes("w-full")

        # Per Pitfall 2: delay JS init to ensure DOM element exists
        ui.timer(0.1, lambda: ui.run_javascript(f"window.initCalendar({json_str})"), once=True)

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
                grid_container.set_visibility(False)
                calendar_container.set_visibility(True)
                await _show_calendar()
            else:
                list_btn.classes(remove=TOGGLE_ACTIVE + " " + TOGGLE_INACTIVE)
                list_btn.classes(TOGGLE_ACTIVE)
                cal_btn.classes(remove=TOGGLE_ACTIVE + " " + TOGGLE_INACTIVE)
                cal_btn.classes(TOGGLE_INACTIVE)
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
            # Pitfall 7: отключаем row animation перед фильтрацией, чтобы не replay
            await ui.run_javascript(
                "document.querySelectorAll('.ag-row').forEach(r => r.style.animation = 'none')"
            )
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

    # ── Action menu ─────────────────────────────────────────────────────────────

    async def _show_action_menu(data: dict) -> None:
        """Показывает контекстное меню с действиями для строки (D-13, D-14)."""
        contract_id = data.get("id")
        if not contract_id:
            return

        with ui.menu() as menu:
            # Открыть (D-13)
            ui.menu_item("Открыть", on_click=lambda: ui.navigate.to(f"/document/{contract_id}"))
            ui.separator()
            # Быстрая смена статуса (D-14)
            with ui.menu_item("Изменить статус"):
                with ui.menu():
                    for status in sorted(MANUAL_STATUSES):
                        label_info = STATUS_LABELS.get(status, ("", status, ""))
                        display = f"{label_info[0]} {label_info[1]}"
                        ui.menu_item(
                            display,
                            on_click=lambda s=status: _quick_status_change(contract_id, s),
                        )
                    ui.separator()
                    ui.menu_item(
                        "Сбросить ручной статус",
                        on_click=lambda: _clear_status(contract_id),
                    )

        menu.open()

    async def _quick_status_change(contract_id: int, status: str) -> None:
        """Устанавливает ручной статус и перегружает таблицу (D-14)."""
        from nicegui import run
        db = _client_manager.get_db(state.current_client)
        try:
            await run.io_bound(set_manual_status, db, contract_id, status)
        except Exception as e:
            ui.notify("Не удалось выполнить действие. Попробуйте ещё раз.", type="negative")
            return
        if grid_ref["grid"]:
            await load_table_data(grid_ref["grid"], state, active_segment["value"])
        label_info = STATUS_LABELS.get(status, ("", status, ""))
        ui.notify(f"Статус изменён: {label_info[1]}", type="positive")

    async def _clear_status(contract_id: int) -> None:
        """Сбрасывает ручной статус."""
        from nicegui import run
        from services.lifecycle_service import clear_manual_status
        db = _client_manager.get_db(state.current_client)
        try:
            await run.io_bound(clear_manual_status, db, contract_id)
        except Exception as e:
            ui.notify("Не удалось выполнить действие. Попробуйте ещё раз.", type="negative")
            return
        if grid_ref["grid"]:
            await load_table_data(grid_ref["grid"], state, active_segment["value"])
        ui.notify("Статус сброшен", type="info")

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

    # Row click → navigate to document (D-18), with action/expand dispatch (D-19)
    async def _on_cell_clicked(e) -> None:
        col_id = e.args.get("colId", "")
        data = e.args.get("data", {})

        if col_id == "actions":
            # D-19: action clicks don't navigate
            await _show_action_menu(data)
            return

        if col_id == "has_children" and data.get("has_children"):
            # D-16: expand/collapse version children
            await _toggle_expand(data["id"], data)
            return

        # Default: navigate (D-18) — skip child rows
        doc_id = data.get("id")
        if doc_id and not data.get("is_child"):
            ui.navigate.to(f"/document/{doc_id}")

    async def _on_upload(source_dir: Path) -> None:
        """Callback triggered by header upload button (D-06, D-07, D-08, D-11)."""
        # Re-grab upload_btn ref (may not be set at module init time)
        ui_refs["upload_btn"] = _header_refs.get("upload_btn")
        stats = await start_pipeline(source_dir, state, ui_refs)
        # After pipeline: refresh table (D-11)
        if grid_ref["grid"]:
            await load_table_data(grid_ref["grid"], state, active_segment["value"])

    # Store callback on state so main.py can delegate to it
    state._on_upload = _on_upload  # type: ignore[attr-defined]

    async def _init() -> None:
        await _refresh_stats()
        with grid_container:
            grid = await render_registry_table(state)
            grid_ref["grid"] = grid
            grid.on("cellClicked", _on_cell_clicked)
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
                # Tour: show after first processing, one time only (per D-14, D-18)
                settings = load_settings()
                if not settings.get("tour_completed"):
                    upload_btn = _header_refs.get("upload_btn")
                    if upload_btn:
                        upload_btn.props("id=upload-btn")
                    from app.components.onboarding.tour import render_tour

                    async def _on_tour_complete():
                        save_setting("tour_completed", True)

                    ui.timer(0.5, lambda: render_tour(_on_tour_complete), once=True)

    ui.timer(0, _init, once=True)
