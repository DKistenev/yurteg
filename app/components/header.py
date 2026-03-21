"""Persistent header component — Linear/Notion minimal style.

Per D-12: Минималистичный текстовый header без иконок у табов.
Per D-13: Слева — лого «ЮрТэг», центр — табы «Документы · Шаблоны · ⚙», справа — клиент.
Per D-14: Header persistent — остаётся при навигации между sub_pages.
Per D-20: Профиль → dropdown с клиентами + «Добавить клиента».
Per D-21: При переключении — сброс фильтров, перезагрузка реестра.
Per D-22: ClientManager.list_clients() для списка клиентов.
Per D-01/D-02: Кнопка «+ Загрузить» рядом с табами, видна на любой странице.
"""
from typing import Callable, Optional

from nicegui import run, ui

from app.components.process import pick_folder
from app.state import AppState
from services.client_manager import ClientManager

# Module-level ref to upload button — позволяет start_pipeline получить ссылку на кнопку
_header_refs: dict = {"upload_btn": None}


def render_header(state: AppState, on_upload: Optional[Callable] = None) -> None:
    """Render persistent top navigation header.

    Args:
        state: AppState — для флага processing.
        on_upload: async callback(source_dir: Path) — вызывается после выбора папки.
                   Если None — папка выбирается, но pipeline не запускается.
    """
    with ui.header().classes(
        "bg-white border-b border-gray-200 px-6 py-0 flex items-center gap-8 h-12"
    ):
        # Left: text logo
        ui.label("ЮрТэг").classes("text-base font-semibold text-gray-900 shrink-0")

        # Center: text-link nav tabs
        with ui.row().classes("gap-6 flex-1 justify-center"):
            _nav_link("Документы", "/")
            _nav_link("Шаблоны", "/templates")
            _nav_link("⚙", "/settings")

        # Upload button — per D-01, D-02 (рядом с табами, перед профилем)
        async def _on_upload_click() -> None:
            if state.processing:
                return
            source_dir = await pick_folder()
            if source_dir and on_upload:
                await on_upload(source_dir)

        upload_btn = ui.button(
            "+ Загрузить",
            on_click=_on_upload_click,
        ).props("flat no-caps").classes("text-sm text-gray-700 shrink-0")

        # Сохраняем ссылку на кнопку для start_pipeline (ui_refs['upload_btn'])
        _header_refs["upload_btn"] = upload_btn

        # Right: client dropdown (D-20)
        cm = ClientManager()

        with ui.row().classes("shrink-0 items-center gap-1"):
            profile_btn = ui.button(
                f"👤 {state.current_client}",
                on_click=lambda: client_menu.open(),
            ).props("flat no-caps").classes("text-sm text-gray-600")

            with ui.menu() as client_menu:
                for name in cm.list_clients():
                    ui.menu_item(
                        name,
                        on_click=lambda n=name: _switch_client(state, n, profile_btn, client_menu),
                    )
                ui.separator()
                ui.menu_item(
                    "+ Добавить клиента",
                    on_click=lambda: _show_add_dialog(state, cm, profile_btn, client_menu),
                )


def _switch_client(state: AppState, name: str, btn, menu) -> None:
    """Переключает активного клиента и перезагружает реестр (D-21)."""
    state.current_client = name
    state.filter_search = ""  # сброс фильтров при переключении
    btn.text = f"👤 {name}"
    if menu:
        menu.close()
    ui.navigate.to("/")  # перезагрузить реестр с данными нового клиента


def _show_add_dialog(state: AppState, cm: ClientManager, btn, menu) -> None:
    """Диалог добавления нового клиента."""
    menu.close()

    with ui.dialog() as dlg, ui.card():
        ui.label("Новый клиент").classes("text-lg font-medium")
        name_input = ui.input("Название клиента").props("outlined")

        with ui.row().classes("gap-2 justify-end w-full"):
            ui.button("Отмена", on_click=dlg.close).props("flat")

            async def _add() -> None:
                n = name_input.value.strip()
                if n:
                    await run.io_bound(cm.add_client, n)
                    _switch_client(state, n, btn, None)
                    dlg.close()

            ui.button("Добавить", on_click=_add).props("flat color=primary")

    dlg.open()


def _nav_link(label: str, path: str) -> None:
    """Render a single text navigation link."""
    ui.link(label, path).classes(
        "text-sm text-gray-600 hover:text-gray-900 no-underline"
        " border-b-2 border-transparent hover:border-gray-900 pb-0.5"
    )
