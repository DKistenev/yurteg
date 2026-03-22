"""Страница «Документы» — реестр договоров на AG Grid.

Phase 08, Plans 02-03.
Phase 12, Plan 02 — empty state + guided tour onboarding.
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
from pathlib import Path

from nicegui import ui

from app.components.header import _header_refs
from app.components.process import start_pipeline
from app.components.registry_table import (
    load_table_data,
    load_version_children,
    render_registry_table,
    _client_manager,
    _collapse_version_children,
)
from app.state import get_state
from config import load_settings, save_setting
from services.lifecycle_service import MANUAL_STATUSES, STATUS_LABELS, set_manual_status

# Segment styling — literal classes per D-24
_SEG_ACTIVE = "px-4 py-1.5 text-sm font-medium rounded-md bg-gray-900 text-white"
_SEG_INACTIVE = "px-4 py-1.5 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-100"


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

    with container:
        with ui.column().classes("py-16 flex flex-col items-center gap-4"):
            # Folder SVG icon — outline, stroke gray-300
            ui.html(
                '<svg width="48" height="48" viewBox="0 0 24 24" fill="none"'
                ' stroke="#d1d5db" stroke-width="1.5">'
                '<path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>'
                "</svg>"
            )
            # Heading
            ui.label("Загрузите первые документы").classes(
                "text-xl font-semibold text-gray-900"
            )
            # Body description
            ui.label(
                "Выберите папку с PDF или DOCX — мы извлечём метаданные"
                " и разложим файлы автоматически."
            ).classes("text-sm text-gray-500 font-normal text-center max-w-xs")
            # CTA button
            ui.button("Выбрать папку", on_click=_on_pick_folder).props(
                "no-caps"
            ).classes("px-6 py-2 bg-gray-900 text-white font-semibold rounded-lg text-sm")
            # Hint bullets
            with ui.column().classes("mt-2 gap-1"):
                ui.label("· Извлечёт метаданные").classes(
                    "text-sm text-gray-400 font-normal"
                )
                ui.label("· Разложит по папкам").classes(
                    "text-sm text-gray-400 font-normal"
                )
                ui.label("· Проверит сроки").classes(
                    "text-sm text-gray-400 font-normal"
                )


def build() -> None:
    """Рендерит страницу реестра документов с поиском, сегментами и навигацией."""
    state = get_state()
    active_segment = {"value": "all"}
    grid_ref = {"grid": None}
    seg_buttons: dict = {}
    _timer: list = [None]

    with ui.column().classes("w-full"):
        # Search + Segments row — search-row class for guided tour targeting (D-14 onboarding)
        with ui.row().classes("w-full px-6 pt-4 pb-2 items-center gap-4 search-row"):
            search_input = (
                ui.input(placeholder="Поиск по реестру...")
                .props("outlined dense")
                .classes("flex-1 max-w-md")
            )

            with ui.row().classes("gap-1 bg-gray-100 p-1 rounded-lg"):
                for key, label in [
                    ("all", "Все"),
                    ("expiring", "Истекают ⚠"),
                    ("attention", "Требуют внимания"),
                ]:
                    btn = ui.button(
                        label,
                        on_click=lambda k=key: _switch_segment(k),
                    ).props("flat unelevated no-caps")
                    btn.classes(_SEG_ACTIVE if key == "all" else _SEG_INACTIVE)
                    seg_buttons[key] = btn

        # Progress section — hidden by default (D-12)
        progress_section = ui.column().classes("w-full px-6 py-3 gap-2")
        progress_section.set_visibility(False)

        with progress_section:
            with ui.row().classes("items-center gap-3 w-full"):
                progress_bar = ui.linear_progress(value=0).classes("flex-1")
                count_label = ui.label("0/0 файлов").classes("text-sm text-gray-500 shrink-0")
            file_label = ui.label("").classes("text-xs text-gray-400")
            error_col = ui.column().classes("gap-1")

        grid_container = ui.column().classes("w-full")

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

    def _apply_segment_classes(active_key: str) -> None:
        """Update button classes based on active segment."""
        for k, b in seg_buttons.items():
            b.classes(remove=_SEG_ACTIVE + " " + _SEG_INACTIVE)
            b.classes(_SEG_ACTIVE if k == active_key else _SEG_INACTIVE)

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

    # ── Action menu ─────────────────────────────────────────────────────────────

    async def _show_action_menu(data: dict) -> None:
        """Показывает контекстное меню с действиями для строки (D-13, D-14)."""
        contract_id = data.get("id")
        if not contract_id:
            return

        with ui.menu() as menu:
            # Открыть (D-13)
            ui.menu_item("Открыть", on_click=lambda: ui.navigate.to(f"/document/{contract_id}"))
            # Скачать оригинал (D-13) — placeholder, путь из БД в Phase 10
            ui.menu_item("Скачать оригинал", on_click=lambda: ui.notify("Функция доступна в следующей версии", type="info"))
            # Переобработать (D-13) — Phase 10
            ui.menu_item("Переобработать", on_click=lambda: ui.notify("Функция доступна в следующей версии", type="info"))
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
            ui.separator()
            # Удалить (D-13) — placeholder с подтверждением
            ui.menu_item(
                "Удалить",
                on_click=lambda: _confirm_delete(contract_id),
            ).classes("text-red-600")

        menu.open()

    async def _quick_status_change(contract_id: int, status: str) -> None:
        """Устанавливает ручной статус и перегружает таблицу (D-14)."""
        from nicegui import run
        db = _client_manager.get_db(state.current_client)
        await run.io_bound(set_manual_status, db, contract_id, status)
        if grid_ref["grid"]:
            await load_table_data(grid_ref["grid"], state, active_segment["value"])
        label_info = STATUS_LABELS.get(status, ("", status, ""))
        ui.notify(f"Статус изменён: {label_info[1]}", type="positive")

    async def _clear_status(contract_id: int) -> None:
        """Сбрасывает ручной статус."""
        from nicegui import run
        from services.lifecycle_service import clear_manual_status
        db = _client_manager.get_db(state.current_client)
        await run.io_bound(clear_manual_status, db, contract_id)
        if grid_ref["grid"]:
            await load_table_data(grid_ref["grid"], state, active_segment["value"])
        ui.notify("Статус сброшен", type="info")

    def _confirm_delete(contract_id: int) -> None:
        """Показывает диалог подтверждения удаления (placeholder)."""
        with ui.dialog() as dialog, ui.card():
            ui.label("Удалить документ?").classes("text-lg font-semibold")
            ui.label("Это действие необратимо. Файл в исходной папке останется.").classes("text-sm text-gray-500")
            with ui.row().classes("gap-2 mt-4"):
                ui.button("Отмена", on_click=dialog.close).props("flat")
                ui.button(
                    "Удалить",
                    on_click=lambda: (ui.notify("Функция удаления доступна в следующей версии", type="warning"), dialog.close()),
                ).props("color=red")
        dialog.open()

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
                _render_empty_state(grid_container, state)
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
