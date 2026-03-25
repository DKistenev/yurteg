"""Bulk actions toolbar for registry.

Shows when one or more documents are selected via checkboxes.
Supports: Change Status, Delete.
"""
import logging
from typing import Callable

from nicegui import ui

from app.styles import BULK_TOOLBAR, BULK_BTN, BULK_BTN_DANGER, BULK_COUNT
from services.lifecycle_service import MANUAL_STATUSES, STATUS_LABELS

logger = logging.getLogger(__name__)


def render_bulk_toolbar(
    selected_ids: list[int],
    total_count: int,
    on_clear: Callable,
    on_status_change: Callable,
    on_delete: Callable,
) -> ui.row:
    """Render the bulk actions toolbar above the table."""
    toolbar = ui.row().classes(BULK_TOOLBAR + " yt-toolbar-enter")
    with toolbar:
        ui.label(f"Выбрано: {len(selected_ids)} из {total_count}").classes(BULK_COUNT)

        ui.button("Изменить статус", icon="edit", on_click=on_status_change).props(
            "flat dense no-caps size=sm"
        ).classes(BULK_BTN)

        ui.element("div").classes("flex-1")

        ui.button("Снять выбор", on_click=on_clear).props(
            "flat dense no-caps size=sm"
        ).classes("text-xs text-slate-400")

        ui.button("Удалить", icon="delete", on_click=on_delete).props(
            "flat dense no-caps size=sm"
        ).classes(BULK_BTN_DANGER)

    return toolbar


def show_bulk_status_dialog(selected_ids: list[int], on_apply: Callable) -> None:
    """Show dialog to change status for multiple documents."""
    with ui.dialog() as dialog, ui.card().classes("p-6 min-w-[360px]"):
        ui.label("Изменить статус").classes("text-base font-semibold text-slate-900 mb-3")
        ui.label(f"Для {len(selected_ids)} документов").classes("text-sm text-slate-500 mb-4")
        status_select = ui.select(
            options={k: v[1] for k, v in STATUS_LABELS.items() if k in MANUAL_STATUSES},
            label="Новый статус",
        ).classes("w-full mb-4")

        with ui.row().classes("justify-end gap-2"):
            ui.button("Отмена", on_click=dialog.close).props("flat no-caps").classes("text-slate-500")

            async def _apply():
                if status_select.value:
                    await on_apply(selected_ids, status_select.value)
                    dialog.close()

            ui.button("Применить", on_click=_apply).props("no-caps color=indigo")
    dialog.open()


def show_bulk_delete_dialog(selected_ids: list[int], on_confirm: Callable) -> None:
    """Show confirmation dialog for bulk deletion."""
    with ui.dialog() as dialog, ui.card().classes("p-6 min-w-[360px]"):
        ui.label("Удалить документы?").classes("text-base font-semibold text-slate-900 mb-2")
        ui.label(
            f"Будет удалено {len(selected_ids)} документов. Это действие нельзя отменить."
        ).classes("text-sm text-slate-500 mb-4")
        with ui.row().classes("justify-end gap-2"):
            ui.button("Отмена", on_click=dialog.close).props("flat no-caps").classes("text-slate-500")

            async def _delete():
                await on_confirm(selected_ids)
                dialog.close()

            ui.button("Удалить", on_click=_delete).props("no-caps color=red")
    dialog.open()
