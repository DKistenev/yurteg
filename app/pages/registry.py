"""Страница «Документы» — реестр договоров на AG Grid.

Phase 08, Plan 01.
Per D-03: сортировка по processed_at DESC (через COLUMN_DEFS hidden column).
Per D-10: floatingFilter в заголовках колонок.
"""
from nicegui import ui

from app.components.registry_table import load_table_data, render_registry_table
from app.state import get_state


def build() -> None:
    """Рендерит страницу реестра документов."""
    state = get_state()

    with ui.column().classes("w-full px-6 pt-4"):
        ui.label("Документы").classes("text-2xl font-semibold text-gray-900")

    grid_container = ui.column().classes("w-full")

    async def _init() -> None:
        with grid_container:
            grid = await render_registry_table(state)
            await load_table_data(grid, state)

    ui.timer(0, _init, once=True)
