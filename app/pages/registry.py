"""Страница «Документы» — реестр договоров на AG Grid.

Phase 08, Plan 02.
Per D-03: сортировка по processed_at DESC (через COLUMN_DEFS hidden column).
Per D-04: три сегмента — Все · Истекают ⚠ · Требуют внимания.
Per D-07: текстовый поиск с debounce 300ms через rapidfuzz.
Per D-18: клик по строке → navigate to /document/{doc_id}.
"""
from nicegui import ui

from app.components.registry_table import load_table_data, render_registry_table
from app.state import get_state

# Segment styling — literal classes per D-24
_SEG_ACTIVE = "px-4 py-1.5 text-sm font-medium rounded-md bg-gray-900 text-white"
_SEG_INACTIVE = "px-4 py-1.5 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-100"


def build() -> None:
    """Рендерит страницу реестра документов с поиском, сегментами и навигацией."""
    state = get_state()
    active_segment = {"value": "all"}
    grid_ref = {"grid": None}
    seg_buttons: dict = {}
    _timer: list = [None]

    with ui.column().classes("w-full"):
        # Search + Segments row
        with ui.row().classes("w-full px-6 pt-4 pb-2 items-center gap-4"):
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

        grid_container = ui.column().classes("w-full")

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

    # Row click → navigate to document (D-18)
    async def _on_cell_clicked(e) -> None:
        col_id = e.args.get("colId", "")
        if col_id == "actions":
            return  # D-19: don't navigate on action clicks
        data = e.args.get("data", {})
        doc_id = data.get("id")
        if doc_id:
            ui.navigate.to(f"/document/{doc_id}")

    async def _init() -> None:
        with grid_container:
            grid = await render_registry_table(state)
            grid_ref["grid"] = grid
            grid.on("cellClicked", _on_cell_clicked)
            await load_table_data(grid, state, "all")

    ui.timer(0, _init, once=True)
