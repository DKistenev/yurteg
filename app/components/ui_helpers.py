"""Reusable UI helpers — диалоги, кнопки действий, empty states.

Извлечены из повторяющихся паттернов в pages/ и components/.
"""
from typing import Callable, Optional

from nicegui import ui

from app.styles import CARD_DIALOG, CARD_DIALOG_SM


def action_buttons(
    primary_label: str,
    on_primary: Callable,
    on_cancel: Callable,
    cancel_label: str = "Отмена",
    primary_props: str = "no-caps color=primary",
    cancel_props: str = "flat no-caps color=grey",
) -> ui.button:
    """Рендерит стандартную пару кнопок Cancel / Save.

    Returns:
        primary button element (для disable/enable).
    """
    with ui.row().classes("justify-end gap-2 w-full"):
        ui.button(cancel_label, on_click=on_cancel).props(cancel_props)
        btn = ui.button(primary_label, on_click=on_primary).props(primary_props)
    return btn


def confirm_dialog(
    title: str,
    message: str,
    on_confirm: Callable,
    confirm_label: str = "Удалить",
    confirm_props: str = "flat no-caps color=negative",
) -> None:
    """Открывает диалог подтверждения (удаление, сброс и т.п.).

    Args:
        title: заголовок диалога.
        message: текст подтверждения (например, имя удаляемого объекта).
        on_confirm: async callback при подтверждении.
        confirm_label: текст кнопки подтверждения.
        confirm_props: Quasar props для кнопки подтверждения.
    """
    with ui.dialog() as dlg, ui.card().classes(CARD_DIALOG_SM):
        ui.label(title).classes("text-lg font-semibold text-slate-900 mb-2")
        ui.label(message).classes("text-slate-600 text-sm mb-4")

        async def _on_confirm() -> None:
            await on_confirm()
            dlg.close()

        action_buttons(
            confirm_label,
            on_primary=_on_confirm,
            on_cancel=dlg.close,
            primary_props=confirm_props,
        )
    dlg.open()


def form_dialog(
    title: str,
    content_builder: Callable,
    on_confirm: Callable,
    confirm_label: str = "Сохранить",
) -> None:
    """Открывает диалог с формой (добавление, редактирование).

    Args:
        title: заголовок диалога.
        content_builder: функция, рендерящая содержимое формы. Получает dlg.
        on_confirm: async callback при подтверждении.
        confirm_label: текст кнопки подтверждения.
    """
    with ui.dialog() as dlg, ui.card().classes(CARD_DIALOG):
        ui.label(title).classes("text-lg font-semibold text-slate-900 mb-4")
        content_builder(dlg)

        async def _wrapped():
            btn.disable()
            try:
                await on_confirm()
                dlg.close()
            except Exception:
                ui.notify("Не удалось сохранить. Попробуйте ещё раз.", type="negative")
            finally:
                btn.enable()

        btn = action_buttons(confirm_label, on_primary=_wrapped, on_cancel=dlg.close)
    dlg.open()


def empty_state(
    icon_svg: str,
    title: str,
    description: str,
    button_label: Optional[str] = None,
    on_click: Optional[Callable] = None,
    hints: Optional[list[str]] = None,
) -> None:
    """Рендерит centered empty state с иконкой, текстом и опциональной CTA.

    Args:
        icon_svg: HTML строка с SVG иконкой.
        title: заголовок.
        description: описание.
        button_label: текст кнопки CTA (опционально).
        on_click: callback для CTA кнопки.
        hints: список подсказок-буллетов под кнопкой.
    """
    with ui.column().classes("py-16 flex flex-col items-center gap-4"):
        ui.html(icon_svg)
        ui.label(title).classes("text-xl font-semibold text-slate-900")
        ui.label(description).classes(
            "text-sm text-slate-500 font-normal text-center max-w-xs"
        )
        if button_label and on_click:
            ui.button(button_label, on_click=on_click).props("no-caps").classes(
                "px-6 py-2 bg-indigo-600 text-white font-semibold rounded-lg text-sm"
            )
        if hints:
            with ui.column().classes("mt-2 gap-1"):
                for hint in hints:
                    ui.label(f"· {hint}").classes("text-sm text-slate-400 font-normal")


def section_card(title: str) -> ui.card:
    """Создаёт секционную карточку с заголовком (для страницы документа).

    Returns:
        card element — используй `with card:` для добавления содержимого.
    """
    card = ui.card().classes("w-full shadow-none border rounded-lg p-5")
    with card:
        ui.label(title).classes("text-sm font-semibold text-slate-700 mb-3")
    return card
