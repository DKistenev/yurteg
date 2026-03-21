"""Карточка документа page — placeholder, реализация в Phase 9."""
from nicegui import ui
from app.state import get_state


def build(doc_id: str = "") -> None:
    """Render карточка документа placeholder page."""
    state = get_state()  # noqa: F841 — будет использоваться в Phase 9
    with ui.column().classes('w-full p-8'):
        ui.label('Карточка документа — Phase 9').classes('text-2xl font-semibold text-gray-900')
        ui.label(f'doc_id: {doc_id}').classes('text-gray-400 text-sm')
