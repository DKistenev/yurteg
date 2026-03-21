"""Документы page — placeholder, реализация в Phase 8."""
from nicegui import ui
from app.state import get_state


def build() -> None:
    """Render Документы placeholder page."""
    state = get_state()  # noqa: F841 — будет использоваться в Phase 8
    with ui.column().classes('w-full p-8'):
        ui.label('Документы').classes('text-2xl font-semibold text-gray-900')
        ui.label('Реестр документов — Phase 8').classes('text-gray-400 text-sm')
