"""Шаблоны page — placeholder, реализация в Phase 11."""
from nicegui import ui
from app.state import get_state


def build() -> None:
    """Render Шаблоны placeholder page."""
    state = get_state()  # noqa: F841 — будет использоваться в Phase 11
    with ui.column().classes('w-full p-8'):
        ui.label('Шаблоны').classes('text-2xl font-semibold text-gray-900')
        ui.label('Шаблоны — Phase 11').classes('text-gray-400 text-sm')
