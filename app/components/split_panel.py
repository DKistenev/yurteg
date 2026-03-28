"""Side preview panel for split-view registry — Linear-style.

Phase 24, Plan 01: REG-04 — Linear/Stripe-style panel with sections.
Shows document summary when a row is clicked.
Panel slides in from the right (yt-panel-enter animation).
"""
import logging
from typing import Callable, Optional

from nicegui import ui

from app.styles import (
    PANEL_TYPE_TAG,
    PANEL_SEC_TITLE,
    PANEL_FIELD_LABEL,
    PANEL_FIELD_VALUE,
)
from app.utils import format_date_ru

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


def _format_amount(amount) -> str:
    """Форматирует сумму в рублях."""
    if amount:
        try:
            formatted = (
                f"{int(float(str(amount).replace(' ', '').replace(',', '.'))):,}"
                .replace(",", "\u00a0")
                + "\u00a0\u20bd"
            )
            return formatted
        except (ValueError, TypeError):
            return str(amount)
    return "—"


def _field_linear(label: str, value: str) -> None:
    """Render a single field in Linear-style (no uppercase labels)."""
    with ui.column().classes("gap-0.5 mb-1.5"):
        ui.label(label).classes(PANEL_FIELD_LABEL)
        ui.label(value or "—").classes(PANEL_FIELD_VALUE)


def render_split_panel(
    container: ui.element,
    doc: Optional[dict],
    on_close: Callable,
    on_open_full: Callable,
) -> None:
    """Render or update the split panel content in Linear-style.

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
        # TOP: контрагент + тег-бейдж типа + кнопка ✕
        with ui.row().classes("px-5 py-4 border-b border-slate-100 justify-between items-start w-full"):
            with ui.column().classes("gap-1"):
                ui.label(doc.get("counterparty", "—")).style(
                    "font-size:15px; font-weight:600; color:#1e293b; line-height:1.3;"
                )
                contract_type = doc.get("contract_type", "")
                if contract_type:
                    ui.label(contract_type).classes(PANEL_TYPE_TAG)
            ui.button(icon="close", on_click=on_close).props("flat dense round").style(
                "color:#94a3b8; min-width:28px; min-height:28px;"
            )

        # Секция ДОКУМЕНТ
        with ui.column().classes("px-5 py-3 border-b border-slate-50 gap-1 w-full"):
            ui.label("Документ").classes(PANEL_SEC_TITLE)
            _field_linear("Предмет", doc.get("subject", "—"))
            # Статус badge
            status = doc.get("computed_status", "unknown")
            badge_cls, badge_label = _STATUS_STYLE.get(status, _STATUS_STYLE["unknown"])
            ui.label(badge_label).classes(
                f"mt-1 px-2.5 py-0.5 text-[11px] font-medium rounded-full {badge_cls}"
            )

        # Секция СРОКИ
        with ui.column().classes("px-5 py-3 border-b border-slate-50 w-full gap-0"):
            ui.label("Сроки").classes(PANEL_SEC_TITLE)
            with ui.row().classes("gap-4 w-full"):
                with ui.column().classes("gap-0.5 flex-1"):
                    ui.label("Начало").classes(PANEL_FIELD_LABEL)
                    ui.label(format_date_ru(doc.get("date_start"), short=True)).classes(PANEL_FIELD_VALUE)
                with ui.column().classes("gap-0.5 flex-1"):
                    ui.label("Окончание").classes(PANEL_FIELD_LABEL)
                    ui.label(format_date_ru(doc.get("date_end"), short=True)).classes(PANEL_FIELD_VALUE)

        # Секция ФИНАНСЫ
        with ui.column().classes("px-5 py-3 w-full gap-1"):
            ui.label("Финансы").classes(PANEL_SEC_TITLE)
            amount_str = _format_amount(doc.get("amount"))
            ui.label(amount_str).style(
                "font-size:20px; font-weight:700; color:#1e293b; letter-spacing:-0.02em;"
            )

        # Кнопка "Открыть карточку →"
        ui.button("Открыть карточку →", on_click=on_open_full).style(
            "margin:12px 16px 16px; padding:8px; border:1px solid #e2e8f0; border-radius:8px; "
            "background:white; color:#475569; font-size:12px; font-weight:500; "
            "width:calc(100% - 32px); text-align:center; font-family:inherit;"
        ).props("flat no-caps")
