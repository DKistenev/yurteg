"""Side preview panel for split-view registry.

Shows document summary when a row is clicked.
Panel slides in from the right (yt-panel-enter animation).
Close button or clicking another row updates content.
"""
import logging
from typing import Callable, Optional

from nicegui import ui

from app.styles import (
    PANEL_CONTAINER, PANEL_HEADER, PANEL_FIELD, PANEL_FIELD_LABEL, PANEL_FIELD_VALUE,
)

logger = logging.getLogger(__name__)

_STATUS_STYLE = {
    "active": ("bg-green-100 text-green-700", "Действует"),
    "expiring": ("bg-amber-100 text-amber-700", "Истекает"),
    "expired": ("bg-red-100 text-red-700", "Истёк"),
    "terminated": ("bg-slate-200 text-slate-600", "Расторгнут"),
    "extended": ("bg-blue-100 text-blue-700", "Продлён"),
    "negotiation": ("bg-purple-100 text-purple-700", "Переговоры"),
    "suspended": ("bg-orange-100 text-orange-700", "Приостановлен"),
    "unknown": ("bg-slate-100 text-slate-500", "Неизвестно"),
}


def render_split_panel(
    container: ui.element,
    doc: Optional[dict],
    on_close: Callable,
    on_open_full: Callable,
) -> None:
    """Render or update the split panel content.

    Args:
        container: The panel container element (already in DOM).
        doc: Document dict from DB, or None to hide.
        on_close: Callback to close the panel.
        on_open_full: Callback to navigate to full document page.
    """
    container.clear()
    if doc is None:
        container.set_visibility(False)
        return

    container.set_visibility(True)
    with container:
        # Header
        with ui.row().classes(PANEL_HEADER):
            ui.label(doc.get("contract_type", "Документ")).classes(
                "text-sm font-semibold text-slate-900 truncate"
            ).style("max-width: 220px;")
            ui.button(icon="close", on_click=on_close).props(
                "flat round dense size=sm"
            ).classes("text-slate-400")

        # Status badge
        status = doc.get("computed_status", "unknown")
        badge_cls, badge_label = _STATUS_STYLE.get(status, _STATUS_STYLE["unknown"])
        with ui.row().classes("px-4 pt-3 pb-1"):
            ui.label(badge_label).classes(
                f"px-2.5 py-0.5 text-xs font-medium rounded-full {badge_cls}"
            )

        # Fields
        _field("Контрагент", doc.get("counterparty", "—"))
        _field("Предмет", doc.get("subject", "—"))
        _field("Дата начала", doc.get("date_start", "—"))
        _field("Дата окончания", doc.get("date_end", "—"))
        _amount_field(doc.get("amount"))
        _confidence_field(doc.get("confidence"))

        # Actions
        with ui.row().classes("px-4 pt-4 pb-3 gap-2 w-full"):
            ui.button(
                "Открыть полностью",
                on_click=on_open_full,
            ).classes(
                "flex-1 text-xs font-semibold"
            ).props("outline rounded color=indigo")


def _field(label: str, value: str) -> None:
    """Render a single field row."""
    with ui.column().classes(PANEL_FIELD + " gap-0.5"):
        ui.label(label).classes(PANEL_FIELD_LABEL)
        ui.label(value or "—").classes(PANEL_FIELD_VALUE)


def _amount_field(amount) -> None:
    """Render amount with ruble formatting."""
    if amount:
        try:
            formatted = f"{int(float(str(amount).replace(' ', '').replace(',', '.'))):,}".replace(",", " ") + " \u20bd"
        except (ValueError, TypeError):
            formatted = str(amount)
    else:
        formatted = "—"
    _field("Сумма", formatted)


def _confidence_field(confidence) -> None:
    """Render AI confidence bar."""
    conf = float(confidence or 0) * 100 if confidence and float(confidence or 0) <= 1 else float(confidence or 0)
    with ui.column().classes(PANEL_FIELD + " gap-1"):
        ui.label("Уверенность AI").classes(PANEL_FIELD_LABEL)
        with ui.row().classes("items-center gap-2 w-full"):
            with ui.element("div").classes("h-1.5 flex-1 rounded-full bg-slate-200 overflow-hidden"):
                color = "bg-green-500" if conf >= 80 else "bg-amber-500" if conf >= 50 else "bg-red-500"
                ui.element("div").classes(f"h-full rounded-full {color}").style(
                    f"width: {conf}%; transition: width 0.5s;"
                )
            ui.label(f"{conf:.0f}%").classes("text-xs font-medium text-slate-500 w-8 text-right")
