"""Карточка документа — полная информация, статус, заметки, навигация.

Per D-01: Single column, sections top-to-bottom.
Per D-02: Header: ← Назад слева, contract_type по центру, ◀ ▶ справа.
Per D-03: Prev/next переключают doc_id в URL.
"""
import logging

from nicegui import run, ui

from app.state import get_state
from app.styles import (
    CARD_SECTION, TEXT_SUBHEAD, TEXT_LABEL_UPPER, HEX,
    BREADCRUMB_LINK, BREADCRUMB_SEP, BREADCRUMB_CURRENT,
    SECTION_DIVIDER_HEADER, AI_REVIEW_BLOCK, AI_REVIEW_BORDER_STYLE,
    META_KEY, META_VAL, VERSION_DOT, VERSION_LINE,
)
from modules.models import ContractMetadata
from services.client_manager import ClientManager
from services.lifecycle_service import (
    STATUS_LABELS,
    MANUAL_STATUSES,
    get_computed_status_sql,
    set_manual_status,
    clear_manual_status,
)
from services.review_service import match_template, review_against_template, list_templates
from services.version_service import get_version_group, diff_versions, generate_redline_docx

logger = logging.getLogger(__name__)
_client_manager = ClientManager()


def _render_metadata(contract: dict) -> None:
    """Отображает метаданные контракта в 3-column grid (per D-04, D-05)."""
    fields = [
        ("Тип документа", contract.get("contract_type") or "—"),
        ("Контрагент", contract.get("counterparty") or "—"),
        ("Предмет договора", contract.get("subject") or "—"),
        ("Дата начала", contract.get("date_start") or "—"),
        ("Дата окончания", contract.get("date_end") or "—"),
        ("Сумма", contract.get("amount") or "—"),
        ("Дата подписания", contract.get("date_signed") or "—"),
    ]

    with ui.grid(columns=3).classes("gap-x-6 gap-y-3 w-full"):
        for label, value in fields:
            with ui.column().classes("gap-0.5"):
                ui.label(label).classes(TEXT_LABEL_UPPER)
                ui.label(value).classes("text-sm text-slate-900")


def _render_special_conditions(contract: dict) -> None:
    """Отображает особые условия — bulleted list."""
    conditions = contract.get("special_conditions") or []
    if conditions:
        with ui.column().classes("gap-1 mt-2"):
            ui.label("Особые условия").classes(TEXT_LABEL_UPPER)
            with ui.column().classes("gap-0.5 pl-3"):
                for cond in conditions:
                    ui.label(f"• {cond}").classes("text-sm text-slate-700")


def _dict_to_metadata(d: dict) -> ContractMetadata:
    """Конвертирует dict контракта в ContractMetadata для diff_versions."""
    return ContractMetadata(
        contract_type=d.get('contract_type') or '',
        counterparty=d.get('counterparty') or '',
        subject=d.get('subject') or '',
        date_signed=d.get('date_signed') or '',
        date_start=d.get('date_start') or '',
        date_end=d.get('date_end') or '',
        amount=d.get('amount') or '',
        special_conditions=d.get('special_conditions') or [],
        parties=d.get('parties') or [],
        confidence=d.get('confidence') or 0.0,
    )


def _render_deviations(container, deviations: list[dict]) -> None:
    """Отображает список отступлений с цветовыми полосками (per D-13, Pitfall 4 inline style)."""
    TYPE_LABEL = {"added": "Добавлено", "removed": "Удалено", "changed": "Изменено"}
    container.clear()
    with container:
        if not deviations:
            ui.label("Отступлений не найдено").classes('text-green-600 text-sm')
            return
        for d in deviations:
            # Per Pitfall 4: inline style для hex-цвета, не динамический Tailwind класс
            ui.html(
                f'<div style="border-left: 3px solid {d["color"]}; padding: 8px 12px; '
                f'background: {d["color"]}22; border-radius: 6px; margin-bottom: 8px;">'
                f'<div style="font-size: 11px; color: #94a3b8; margin-bottom: 4px;">'
                f'{TYPE_LABEL.get(d["type"], d["type"])}</div>'
                + (f'<div style="font-size: 12px; color: #64748b; text-decoration: line-through;">'
                   f'{d.get("template_text") or ""}</div>' if d.get("template_text") else '')
                + (f'<div style="font-size: 14px; color: #0f172a;">'
                   f'{d.get("document_text") or ""}</div>' if d.get("document_text") else '')
                + '</div>'
            )


def _render_diff_table(container, diffs: list[dict]) -> None:
    """Показывает таблицу изменённых полей между двумя версиями (per D-17)."""
    changed = [d for d in diffs if d['changed']]
    if not changed:
        with container:
            ui.label('Изменений не найдено').classes('text-green-600 text-sm')
        return
    with container:
        columns = [
            {'name': 'field', 'label': 'Поле', 'field': 'field', 'align': 'left'},
            {'name': 'old', 'label': 'Было', 'field': 'old', 'align': 'left'},
            {'name': 'new', 'label': 'Стало', 'field': 'new', 'align': 'left'},
        ]
        table = ui.table(columns=columns, rows=changed).classes('w-full text-sm')
        table.add_slot('body-cell-old', '<q-td :props="props"><span class="text-red-600 line-through">{{ props.value }}</span></q-td>')
        table.add_slot('body-cell-new', '<q-td :props="props"><span class="text-green-700">{{ props.value }}</span></q-td>')


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
        with ui.column().classes("w-full px-6 py-6 gap-4"):
            ui.label("Документ не найден").classes("text-xl text-slate-500")
            ui.button("← Назад к реестру", on_click=lambda: ui.navigate.to("/")).props("flat no-caps").classes("text-slate-600")
        return

    # Загружаем computed_status отдельным SQL-запросом (per Pattern 3)
    status_row = await run.io_bound(
        lambda: db.conn.execute(
            f"SELECT {get_computed_status_sql(state.warning_days_threshold)} AS computed_status FROM contracts WHERE id = :contract_id",
            {"warning_days": state.warning_days_threshold, "contract_id": int(doc_id)}
        ).fetchone()
    )
    computed_status = dict(status_row)["computed_status"] if status_row else "unknown"

    # ── Main content column ──────────────────────────────────────────────────
    with ui.column().classes("w-full px-6 py-6 gap-0 max-w-5xl mx-auto"):

        # ── Breadcrumbs (CARD-01) ─────────────────────────────────────────────
        with ui.row().classes("items-center gap-0 mb-6"):
            ui.link(
                "Реестр", "/"
            ).classes(BREADCRUMB_LINK + " no-underline")
            ui.label("→").classes(BREADCRUMB_SEP)
            ui.label(
                contract.get("contract_type") or "Документ"
            ).classes(BREADCRUMB_CURRENT)

            # Prev/next buttons (per D-03, D-20) — right-aligned
            doc_ids = state.filtered_doc_ids
            current_idx = doc_ids.index(int(doc_id)) if int(doc_id) in doc_ids else -1
            prev_id = doc_ids[current_idx - 1] if current_idx > 0 else None
            next_id = doc_ids[current_idx + 1] if current_idx < len(doc_ids) - 1 else None

            with ui.row().classes("gap-1 ml-auto"):
                prev_btn = ui.button(
                    "◀",
                    on_click=lambda pid=prev_id: ui.navigate.to(f"/document/{pid}")
                ).props('flat dense aria-label="Предыдущий документ"').classes("text-slate-400")
                prev_btn.set_enabled(prev_id is not None)

                next_btn = ui.button(
                    "▶",
                    on_click=lambda nid=next_id: ui.navigate.to(f"/document/{nid}")
                ).props('flat dense aria-label="Следующий документ"').classes("text-slate-400")
                next_btn.set_enabled(next_id is not None)

        # ── Two-column layout ─────────────────────────────────────────────────
        with ui.row().classes("w-full gap-6 items-start"):

            # LEFT COLUMN: metadata + status + special conditions
            with ui.column().classes("flex-1 gap-0 min-w-0"):

                # ── Метаданные (CARD-02, CARD-03: compact key-value, no card wrapper) ──
                ui.label("Сведения о документе").classes(SECTION_DIVIDER_HEADER)
                _render_metadata(contract)

                ui.element("div").classes("mb-8")  # вертикальный отступ между секциями

                # ── Статус (CARD-02: section divider) ────────────────────────────────
                ui.label("Статус").classes(SECTION_DIVIDER_HEADER)

                icon, label_text, color = STATUS_LABELS.get(
                    computed_status, ("?", computed_status, "#9ca3af")
                )
                status_css_class = f"status-{computed_status}"
                with ui.row().classes("items-center gap-4 mb-2"):
                    ui.html(f'<span class="{status_css_class}">{icon} {label_text}</span>')
                    status_select_container = ui.row().classes("items-center gap-2")

                with status_select_container:
                    change_btn = ui.button(
                        "Изменить",
                        on_click=lambda: status_row_el.set_visibility(True)
                    ).props("flat dense no-caps").classes("text-indigo-600 text-xs")

                    async def _clear_status() -> None:
                        try:
                            await run.io_bound(clear_manual_status, db, int(doc_id))
                        except Exception:
                            ui.notify("Не удалось сбросить статус. Попробуйте ещё раз.", type="negative")
                            return
                        ui.navigate.to(f"/document/{doc_id}")

                    if contract.get("manual_status"):
                        ui.button(
                            "Сбросить",
                            on_click=_clear_status
                        ).props("flat dense no-caps").classes("text-slate-500 text-xs")

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
                            apply_btn.disable()
                            try:
                                try:
                                    await run.io_bound(set_manual_status, db, int(doc_id), val)
                                except Exception:
                                    ui.notify("Не удалось изменить статус. Попробуйте ещё раз.", type="negative")
                                    return
                                ui.navigate.to(f"/document/{doc_id}")
                            finally:
                                apply_btn.enable()

                    apply_btn = ui.button(
                        "Применить",
                        on_click=_apply_status
                    ).props("dense no-caps").classes("bg-indigo-600 text-white text-xs")

                    ui.button(
                        "Отмена",
                        on_click=lambda: status_row_el.set_visibility(False)
                    ).props("flat dense no-caps").classes("text-slate-500 text-xs")

                ui.element("div").classes("mb-8")

                # ── Особые условия ───────────────────────────────────────────────
                _render_special_conditions(contract)

            # RIGHT COLUMN: notes + AI review + versions
            with ui.column().classes("w-80 shrink-0 gap-4"):

                # ── Пометки юриста (CARD-02: section divider) ────────────────────────
                ui.label("Пометки юриста").classes(SECTION_DIVIDER_HEADER)

                async def _save_comment(e) -> None:
                    comment_text = e.sender.value or ""
                    file_hash = contract.get("file_hash", "")
                    if file_hash:
                        try:
                            await run.io_bound(
                                db.update_review,
                                file_hash,
                                contract.get("review_status", "not_reviewed"),
                                comment_text,
                            )
                        except Exception:
                            ui.notify("Не удалось сохранить заметку. Попробуйте ещё раз.", type="negative")

                comment_area = ui.textarea(
                    value=contract.get("lawyer_comment", "")
                ).props('outlined rows=4 placeholder="Добавьте заметку..."').classes("w-full")
                comment_area.on("blur", _save_comment)

                # ── AI-ревью (CARD-02, CARD-03: amber accent left-border) ────────────
                ui.label("Проверка по шаблону").classes(SECTION_DIVIDER_HEADER)

                # Amber/orange accent wrapper — визуально отличает AI-контент от фактических данных
                with ui.element("div").classes(AI_REVIEW_BLOCK).style(AI_REVIEW_BORDER_STYLE):
                    review_container = ui.column().classes("w-full gap-2 py-2")

                    async def _run_review() -> None:
                        review_btn.disable()
                        try:
                            review_container.clear()
                            with review_container:
                                ui.spinner("dots").classes("text-amber-500")

                            _db = _client_manager.get_db(state.current_client)
                            try:
                                template = await run.io_bound(
                                    match_template, _db, contract.get("subject", ""), contract.get("contract_type")
                                )
                            except Exception:
                                ui.notify("Не удалось подобрать шаблон автоматически.", type="negative")
                                return
                            if template is None:
                                try:
                                    templates = await run.io_bound(list_templates, _db)
                                except Exception:
                                    ui.notify("Не удалось загрузить список шаблонов.", type="negative")
                                    return
                                if not templates:
                                    review_container.clear()
                                    with review_container:
                                        ui.label("Нет подходящего шаблона").classes("text-sm text-slate-500")
                                        ui.button(
                                            "Добавить шаблон →",
                                            on_click=lambda: ui.navigate.to("/templates"),
                                        ).props("flat no-caps").classes("text-indigo-600 text-sm")
                                    return
                                review_container.clear()
                                with review_container:
                                    template_options = {t.id: f"{t.name} ({t.contract_type})" for t in templates}
                                    selected_template = ui.select(
                                        template_options,
                                        label="Выберите шаблон",
                                    ).classes("w-full max-w-sm")

                                    async def _review_with_selected() -> None:
                                        sel_id = selected_template.value
                                        if sel_id is None:
                                            return
                                        sel_tmpl = next((t for t in templates if t.id == sel_id), None)
                                        if sel_tmpl:
                                            await _do_review(sel_tmpl.content_text)

                                    ui.button("Проверить", on_click=_review_with_selected).props("flat no-caps").classes("text-amber-600")
                                return

                            await _do_review(template.content_text)
                        finally:
                            review_btn.enable()

                    async def _do_review(template_text: str) -> None:
                        review_container.clear()
                        with review_container:
                            ui.spinner("dots").classes("text-amber-500")
                        try:
                            deviations = await run.io_bound(
                                review_against_template, template_text, contract.get("subject", "")
                            )
                        except Exception:
                            review_container.clear()
                            with review_container:
                                ui.notify("Не удалось выполнить проверку. Попробуйте ещё раз.", type="negative")
                            return
                        _render_deviations(review_container, deviations)

                    review_btn = ui.button("Проверить по шаблону", on_click=_run_review).props("flat no-caps").classes("text-amber-600")

                # ── История версий (CARD-02, CARD-03: timeline-стиль) ────────────────
                ui.label("История версий").classes(SECTION_DIVIDER_HEADER)

                _db2 = _client_manager.get_db(state.current_client)
                versions = await run.io_bound(get_version_group, _db2, int(doc_id))

                if not versions:
                    ui.label("Версии не найдены").classes("text-slate-400 text-sm py-2")
                else:
                    versions_container = ui.column().classes("w-full gap-0")
                    with versions_container:
                        for i, v in enumerate(versions):
                            is_last = (i == len(versions) - 1)
                            with ui.row().classes("w-full gap-3 items-start"):

                                # Timeline: вертикальная линия + точка
                                with ui.column().classes("items-center gap-0 pt-1"):
                                    ui.element("div").classes(VERSION_DOT)
                                    if not is_last:
                                        ui.element("div").classes(VERSION_LINE).style("height:36px")

                                # Версия данные
                                with ui.column().classes("flex-1 pb-4 gap-1"):
                                    with ui.row().classes("items-center gap-3 w-full"):
                                        ui.label(f"v{v.version_number}").classes("text-sm font-semibold text-slate-900")
                                        if v.link_method:
                                            ui.label(v.link_method).classes("text-xs text-slate-400")
                                        if v.created_at:
                                            ui.label(v.created_at).classes("text-xs text-slate-400")

                                        if v.contract_id != int(doc_id):
                                            with ui.row().classes("gap-2 ml-auto"):
                                                async def _show_diff(other_id: int = v.contract_id) -> None:
                                                    try:
                                                        other = await run.io_bound(_db2.get_contract_by_id, other_id)
                                                    except Exception:
                                                        ui.notify("Не удалось загрузить версию документа.", type="negative")
                                                        return
                                                    if other is None:
                                                        return
                                                    meta_current = _dict_to_metadata(contract)
                                                    meta_other = _dict_to_metadata(other)
                                                    try:
                                                        diffs = await run.io_bound(diff_versions, meta_current, meta_other)
                                                    except Exception:
                                                        ui.notify("Не удалось сравнить версии.", type="negative")
                                                        return
                                                    diff_container = ui.column().classes("w-full mt-2")
                                                    _render_diff_table(diff_container, diffs)

                                                ui.button("Сравнить", on_click=_show_diff).props("flat dense no-caps").classes("text-xs text-indigo-600")
                                                ui.link(
                                                    "Скачать с правками",
                                                    f"/download/redline/{doc_id}/{v.contract_id}"
                                                ).classes("text-xs text-indigo-600 underline")
