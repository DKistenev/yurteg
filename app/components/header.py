"""Persistent header component — Linear/Notion minimal style.

Per D-12: Минималистичный текстовый header без иконок у табов.
Per D-13: Слева — лого «ЮрТэг», центр — табы «Документы · Шаблоны · ⚙», справа — профиль.
Per D-14: Header persistent — остаётся при навигации между sub_pages.
"""
from nicegui import ui
from app.state import AppState


def render_header(state: AppState) -> None:
    """Render persistent top navigation header."""
    with ui.header().classes(
        'bg-white border-b border-gray-200 px-6 py-0 flex items-center gap-8 h-12'
    ):
        # Left: text logo
        ui.label('ЮрТэг').classes('text-base font-semibold text-gray-900 shrink-0')

        # Center: text-link nav tabs
        with ui.row().classes('gap-6 flex-1 justify-center'):
            _nav_link('Документы', '/')
            _nav_link('Шаблоны', '/templates')
            _nav_link('⚙', '/settings')

        # Right: profile / client indicator
        with ui.row().classes('shrink-0 items-center gap-1 cursor-pointer'):
            ui.label('👤▾').classes('text-gray-500 text-sm')


def _nav_link(label: str, path: str) -> None:
    """Render a single text navigation link."""
    ui.link(label, path).classes(
        'text-sm text-gray-600 hover:text-gray-900 no-underline'
        ' border-b-2 border-transparent hover:border-gray-900 pb-0.5'
    )
