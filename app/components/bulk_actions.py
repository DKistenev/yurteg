"""Bulk actions toolbar for registry.

Shows when one or more documents are selected via checkboxes.
Supports: Change Status, Delete.
"""
import logging
from typing import Callable

from nicegui import ui

from app.styles import BULK_TOOLBAR
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
        ui.html(
            f'<span style="font-size:14px;font-weight:600;color:#334155;">'
            f'Выбрано: <span style="color:#4f46e5;">{len(selected_ids)}</span></span>'
        )

        # Plain HTML buttons — bypass Quasar styling completely
        ui.html(
            '<button class="yt-bulk-btn" style="color:#4f46e5;" '
            'onclick="this.dispatchEvent(new Event(\'yt-status\', {bubbles:true}))">'
            '<span class="material-icons" style="font-size:15px;vertical-align:middle;margin-right:4px;">edit</span>'
            "Изменить статус</button>"
        ).on("yt-status", on_status_change)

        ui.element("div").classes("flex-1")

        ui.html(
            '<button class="yt-bulk-btn-text" style="color:#64748b;" '
            'onclick="this.dispatchEvent(new Event(\'yt-clear\', {bubbles:true}))">'
            '<span class="material-icons" style="font-size:15px;vertical-align:middle;margin-right:4px;">deselect</span>'
            "Снять выбор</button>"
        ).on("yt-clear", on_clear)

        ui.html(
            '<button class="yt-bulk-btn yt-bulk-btn-danger" style="color:#dc2626;" '
            'onclick="this.dispatchEvent(new Event(\'yt-del\', {bubbles:true}))">'
            '<span class="material-icons" style="font-size:15px;vertical-align:middle;margin-right:4px;">delete</span>'
            "Удалить</button>"
        ).on("yt-del", on_delete)

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
