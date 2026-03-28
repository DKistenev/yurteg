"""Bulk actions toolbar for registry.

Shows when one or more documents are selected via checkboxes.
Supports: Delete.
"""
import logging
from typing import Callable

from nicegui import ui

from app.styles import BULK_TOOLBAR

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
            f'<span style="font-size:14px;font-weight:600;color:var(--yt-p-slate-700);">'
            f'Выбрано: <span style="color:var(--yt-color-accent);">{len(selected_ids)}</span></span>'
        )

        ui.element("div").classes("flex-1")

        ui.button(
            "Снять выбор", icon="deselect", on_click=on_clear,
        ).props('flat dense no-caps aria-label="Снять выбор"').classes(
            "text-xs text-slate-500 hover:text-slate-700"
        )

        ui.button(
            "Удалить", icon="delete", on_click=on_delete,
        ).props('flat dense no-caps aria-label="Удалить выбранные"').classes(
            "text-xs text-red-600 hover:text-red-700"
        )

    return toolbar


def show_bulk_status_dialog(selected_ids: list[int], on_confirm: Callable) -> None:
    """Show dialog to change status for selected documents."""
    from services.lifecycle_service import STATUS_LABELS

    with ui.dialog() as dialog, ui.card().classes("p-6 min-w-[360px]"):
        ui.label("Изменить статус").classes("text-base font-semibold text-slate-900 mb-2")
        ui.label(
            f"Для {len(selected_ids)} документов"
        ).classes("text-sm text-slate-500 mb-4")

        for key, (icon, label, color) in STATUS_LABELS.items():
            async def _apply(s=key):
                await on_confirm(selected_ids, s)
                dialog.close()

            ui.button(
                f"{icon} {label}", on_click=_apply
            ).props("flat no-caps").classes("w-full justify-start").style(f"color: {color}")

        ui.button("Отмена", on_click=dialog.close).props("flat no-caps").classes("text-slate-500 mt-2")
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

            ui.button("Удалить", on_click=_delete).props("unelevated no-caps").classes(
                "px-4 py-1.5 bg-red-600 text-white text-sm font-semibold rounded-lg"
                " hover:bg-red-700 transition-colors duration-150"
            )
    dialog.open()
