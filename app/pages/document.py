"""Карточка документа — полная информация, статус, заметки, навигация.

Per D-01: Single column, sections top-to-bottom.
Per D-02: Header: ← Назад слева, contract_type по центру, ◀ ▶ справа.
Per D-03: Prev/next переключают doc_id в URL.
"""
import logging

from nicegui import run, ui

from app.state import get_state
from services.client_manager import ClientManager
from services.lifecycle_service import (
    STATUS_LABELS,
    MANUAL_STATUSES,
    get_computed_status_sql,
    set_manual_status,
    clear_manual_status,
)

logger = logging.getLogger(__name__)
_client_manager = ClientManager()


def _render_metadata(contract: dict) -> None:
    """Отображает метаданные контракта в 2-column grid (per D-04, D-05)."""
    fields = [
        ("Тип документа", contract.get("contract_type") or "—"),
        ("Контрагент", contract.get("counterparty") or "—"),
        ("Предмет договора", contract.get("subject") or "—"),
        ("Дата начала", contract.get("date_start") or "—"),
        ("Дата окончания", contract.get("date_end") or "—"),
        ("Сумма", contract.get("amount") or "—"),
        ("Дата подписания", contract.get("date_signed") or "—"),
    ]

    with ui.grid(columns=2).classes("gap-x-8 gap-y-3 w-full"):
        for label, value in fields:
            with ui.column().classes("gap-0.5"):
                ui.label(label).classes("text-xs font-medium text-gray-400 uppercase tracking-wide")
                ui.label(value).classes("text-sm text-gray-900")

    # Особые условия — bulleted list
    conditions = contract.get("special_conditions") or []
    if conditions:
        with ui.column().classes("gap-1 mt-2"):
            ui.label("Особые условия").classes("text-xs font-medium text-gray-400 uppercase tracking-wide")
            with ui.column().classes("gap-0.5 pl-3"):
                for cond in conditions:
                    ui.label(f"• {cond}").classes("text-sm text-gray-700")


async def build(doc_id: str = "") -> None:
    """Render карточки документа: заголовок, метаданные, статус, заметки.

    Per Pattern 1: все DB-вызовы через run.io_bound().
    Per D-01: Single column layout, top-to-bottom sections.
    """
    state = get_state()

    if not doc_id:
        ui.navigate.to("/")
        return

    db = _client_manager.get_db(state.current_client)

    # Загружаем контракт (per Pattern 1 — run.io_bound для блокирующих вызовов)
    contract = await run.io_bound(db.get_contract_by_id, int(doc_id))

    if contract is None:
        with ui.column().classes("w-full p-8 gap-4"):
            ui.label("Документ не найден").classes("text-xl text-gray-500")
            ui.button("← Назад к реестру", on_click=lambda: ui.navigate.to("/")).props("flat no-caps").classes("text-gray-600")
        return

    # Загружаем computed_status отдельным SQL-запросом (per Pattern 3)
    status_row = await run.io_bound(
        lambda: db.conn.execute(
            f"SELECT {get_computed_status_sql(state.warning_days_threshold)} AS computed_status FROM contracts WHERE id = :contract_id",
            {"warning_days": state.warning_days_threshold, "contract_id": int(doc_id)}
        ).fetchone()
    )
    computed_status = dict(status_row)["computed_status"] if status_row else "unknown"

    # ── Main content column (Notion-style clean layout) ──────────────────────────
    with ui.column().classes("max-w-4xl mx-auto px-6 py-6 gap-6 w-full"):

        # ── Header (per D-02) ──────────────────────────────────────────────────
        with ui.row().classes("w-full items-center justify-between border-b pb-4"):
            ui.button(
                "← Назад к реестру",
                on_click=lambda: ui.navigate.to("/")
            ).props("flat no-caps").classes("text-gray-600")

            ui.label(
                contract.get("contract_type") or "Документ"
            ).classes("text-xl font-semibold text-gray-900")

            # Prev/next buttons (per D-03, D-20)
            doc_ids = state.filtered_doc_ids
            current_idx = doc_ids.index(int(doc_id)) if int(doc_id) in doc_ids else -1
            prev_id = doc_ids[current_idx - 1] if current_idx > 0 else None
            next_id = doc_ids[current_idx + 1] if current_idx < len(doc_ids) - 1 else None

            with ui.row().classes("gap-1"):
                prev_btn = ui.button(
                    "◀",
                    on_click=lambda pid=prev_id: ui.navigate.to(f"/document/{pid}")
                ).props("flat dense").classes("text-gray-500")
                prev_btn.set_enabled(prev_id is not None)

                next_btn = ui.button(
                    "▶",
                    on_click=lambda nid=next_id: ui.navigate.to(f"/document/{nid}")
                ).props("flat dense").classes("text-gray-500")
                next_btn.set_enabled(next_id is not None)

        # ── Metadata grid (per D-04, D-05) ────────────────────────────────────
        with ui.card().classes("w-full shadow-none border rounded-lg p-5"):
            ui.label("Метаданные").classes("text-sm font-semibold text-gray-700 mb-3")
            _render_metadata(contract)

        # ── Status section (per D-06, D-07) ───────────────────────────────────
        with ui.card().classes("w-full shadow-none border rounded-lg p-5"):
            ui.label("Статус").classes("text-sm font-semibold text-gray-700 mb-3")

            # Отображаем бейдж статуса
            icon, label_text, color = STATUS_LABELS.get(
                computed_status, ("?", computed_status, "#9ca3af")
            )
            status_css_class = f"status-{computed_status}"
            with ui.row().classes("items-center gap-4"):
                ui.html(f'<span class="{status_css_class}">{icon} {label_text}</span>')

                # Кнопки управления статусом
                status_select_container = ui.row().classes("items-center gap-2")

            with status_select_container:
                change_btn = ui.button(
                    "Изменить",
                    on_click=lambda: status_row_el.set_visibility(True)
                ).props("flat dense no-caps").classes("text-blue-600 text-xs")

                async def _clear_status() -> None:
                    await run.io_bound(clear_manual_status, db, int(doc_id))
                    ui.navigate.to(f"/document/{doc_id}")

                if contract.get("manual_status"):
                    ui.button(
                        "Сбросить",
                        on_click=_clear_status
                    ).props("flat dense no-caps").classes("text-gray-500 text-xs")

            # Select dropdown для ручного статуса
            status_row_el = ui.row().classes("items-center gap-2 mt-2")
            status_row_el.set_visibility(False)

            manual_status_options = {
                "terminated": "Расторгнут",
                "extended": "Продлён",
                "negotiation": "На согласовании",
                "suspended": "Приостановлен",
            }

            with status_row_el:
                status_sel = ui.select(
                    options=manual_status_options,
                    value=contract.get("manual_status"),
                    label="Выберите статус",
                ).classes("w-48").props("dense outlined")

                async def _apply_status() -> None:
                    val = status_sel.value
                    if val and val in MANUAL_STATUSES:
                        await run.io_bound(set_manual_status, db, int(doc_id), val)
                        ui.navigate.to(f"/document/{doc_id}")

                ui.button(
                    "Применить",
                    on_click=_apply_status
                ).props("dense no-caps").classes("bg-blue-600 text-white text-xs")

                ui.button(
                    "Отмена",
                    on_click=lambda: status_row_el.set_visibility(False)
                ).props("flat dense no-caps").classes("text-gray-500 text-xs")

        # ── Lawyer notes (per D-08, D-09) ─────────────────────────────────────
        with ui.card().classes("w-full shadow-none border rounded-lg p-5"):
            ui.label("Пометки юриста").classes("text-sm font-semibold text-gray-700 mb-3")

            async def _save_comment(e) -> None:
                comment_text = e.sender.value or ""
                file_hash = contract.get("file_hash", "")
                if file_hash:
                    await run.io_bound(
                        db.update_review,
                        file_hash,
                        contract.get("review_status", "not_reviewed"),
                        comment_text,
                    )

            comment_area = ui.textarea(
                value=contract.get("lawyer_comment", "")
            ).props('outlined rows=4 placeholder="Добавьте заметку..."').classes("w-full")
            comment_area.on("blur", _save_comment)

        # ── AI Review section (Plan 02) ──
        # ── Version History section (Plan 02) ──
