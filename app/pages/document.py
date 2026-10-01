"""Карточка документа — полная информация, статус, заметки, навигация.

Per D-01: Hero dominant + 2-column layout.
Per D-02: Header: ← Назад слева, contract_type по центру, ◀ ▶ справа.
Per D-03: Prev/next переключают doc_id в URL.
"""
import logging
import os
import platform
import subprocess

from nicegui import run, ui

from app.state import get_state
from config import load_settings, save_setting
from app.styles import (
    BREADCRUMB_LINK, BREADCRUMB_SEP, BREADCRUMB_CURRENT,
    SECTION_DIVIDER_HEADER,
    VERSION_DOT, VERSION_LINE,
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

# ── Status badge colors ──────────────────────────────────────────────────────
STATUS_BG = {
    "active": "bg-green-100 text-green-700",
    "expiring": "bg-amber-100 text-amber-700",
    "expired": "bg-red-100 text-red-700",
    "terminated": "bg-slate-200 text-slate-600",
    "extended": "bg-blue-100 text-blue-700",
    "negotiation": "bg-purple-100 text-purple-700",
    "suspended": "bg-orange-100 text-orange-700",
    "unknown": "bg-slate-100 text-slate-500",
}


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


def _open_file_in_os(file_path: str) -> None:
    """Открывает файл стандартным приложением ОС."""
    try:
        if not file_path or not os.path.exists(file_path):
            ui.notify("Файл не найден на диске", type="warning")
            return
        if platform.system() == "Darwin":
            subprocess.Popen(["open", file_path])
        elif platform.system() == "Windows":
            os.startfile(file_path)
        else:
            subprocess.Popen(["xdg-open", file_path])
    except Exception as e:
        logger.error("Не удалось открыть файл: %s", e)
        ui.notify("Не удалось открыть файл", type="negative")


def _format_file_size(path: str) -> str:
    """Возвращает размер файла в человекочитаемом формате."""
    try:
        if not path or not os.path.exists(path):
            return "—"
        size = os.path.getsize(path)
        if size < 1024:
            return f"{size} Б"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} КБ"
        else:
            return f"{size / (1024 * 1024):.1f} МБ"
    except Exception:
        return "—"


async def build(doc_id: str = "") -> None:
    """Render карточки документа: hero + 2-column layout.

    Per Pattern 1: все DB-вызовы через run.io_bound().
    """
    state = get_state()

    if not doc_id:
        ui.navigate.to("/")
        return

    db = _client_manager.get_db(state.current_client)

    contract = await run.io_bound(db.get_contract_by_id, int(doc_id))

    if contract is None:
        with ui.column().classes("w-full px-6 py-6 gap-4"):
            ui.label("Документ не найден").classes("text-xl text-slate-500")
            ui.button("← Назад к реестру", on_click=lambda: ui.navigate.to("/")).props("flat no-caps").classes("text-slate-600")
        return

    # Загружаем computed_status
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
            ui.link("Реестр", "/").classes(BREADCRUMB_LINK + " no-underline")
            ui.label("→").classes(BREADCRUMB_SEP)
            ui.label(contract.get("contract_type") or "Документ").classes(BREADCRUMB_CURRENT)

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

        # ══════════════════════════════════════════════════════════════════════
        # ── HERO CARD (dominant, full-width) ─────────────────────────────────
        # ══════════════════════════════════════════════════════════════════════
        with ui.element("div").classes(
            "w-full bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm mb-6"
        ):
            with ui.row().classes("w-full items-stretch min-h-[200px]"):

                # ── Left: file preview thumbnail ─────────────────────────────
                original_path = contract.get("original_path") or ""
                filename = contract.get("filename") or "document"
                file_size = _format_file_size(original_path)

                with ui.column().classes(
                    "w-48 shrink-0 items-center justify-center gap-2 p-6"
                ).style(
                    "background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);"
                ):
                    ui.label("📄").classes("text-4xl")
                    ui.label(filename).classes(
                        "text-xs text-slate-500 text-center break-all max-w-full leading-tight"
                    )
                    if file_size != "—":
                        ui.label(file_size).classes("text-xs text-slate-400")

                # ── Right: main info ─────────────────────────────────────────
                with ui.column().classes("flex-1 p-6 gap-3 min-w-0"):

                    # Title + counterparty
                    contract_type = contract.get("contract_type") or "Документ"
                    counterparty = contract.get("counterparty") or ""
                    ui.label(contract_type).classes("text-2xl font-bold text-slate-900 leading-tight")
                    if counterparty:
                        ui.label(counterparty).classes("text-base text-slate-500 -mt-1")

                    # Status badge (prominent pill)
                    icon, label_text, color = STATUS_LABELS.get(
                        computed_status, ("?", computed_status, "#9ca3af")
                    )
                    badge_classes = STATUS_BG.get(computed_status, STATUS_BG["unknown"])
                    with ui.element("div").classes(
                        f"inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold w-fit {badge_classes}"
                    ):
                        ui.label(f"{icon} {label_text}")

                    # 4-column meta grid
                    meta_fields = [
                        ("Дата начала", contract.get("date_start") or "—"),
                        ("Дата окончания", contract.get("date_end") or "—"),
                        ("Сумма", contract.get("amount") or "—"),
                        ("Подписан", contract.get("date_signed") or "—"),
                    ]
                    with ui.row().classes("gap-6 mt-1"):
                        for label, value in meta_fields:
                            with ui.column().classes("gap-0"):
                                ui.label(label).classes("text-xs text-slate-400 uppercase tracking-wide")
                                ui.label(value).classes("text-sm text-slate-900 font-medium")

                    # Subject below divider
                    subject = contract.get("subject") or ""
                    if subject:
                        ui.element("div").classes("border-t border-slate-100 mt-2 pt-2")
                        ui.label(subject).classes("text-sm text-slate-600 leading-relaxed")

                    # Confidence warning (if low)
                    settings = load_settings()
                    confidence_threshold = settings.get("confidence_low", 0.5)
                    confidence = contract.get("confidence", 1.0)
                    if confidence < confidence_threshold:
                        with ui.row().classes("items-center gap-1.5 mt-1"):
                            ui.html(
                                '<span style="display:inline-block;width:8px;height:8px;'
                                'border-radius:50%;background:#d97706"></span>'
                            )
                            ui.label(
                                f"Низкая уверенность AI: {round(confidence * 100)}%"
                            ).classes("text-xs font-medium text-amber-600")

                    # Two action buttons
                    with ui.row().classes("gap-3 mt-2"):
                        ui.button(
                            "📝 Открыть в Word",
                            on_click=lambda p=original_path: _open_file_in_os(p),
                        ).props("no-caps unelevated").classes(
                            "bg-indigo-600 text-white text-sm font-semibold px-4 py-1.5 rounded-lg"
                        )

                        async def _reprocess() -> None:
                            ui.notify("Переобработка запущена...", type="info")
                            # Re-process is a placeholder — triggers page reload
                            ui.navigate.to(f"/document/{doc_id}")

                        ui.button(
                            "🔄 Переобработать",
                            on_click=_reprocess,
                        ).props("flat no-caps").classes(
                            "text-slate-600 text-sm font-medium border border-slate-200 rounded-lg px-4 py-1.5"
                        )

        # ══════════════════════════════════════════════════════════════════════
        # ── Two-column layout below hero ─────────────────────────────────────
        # ══════════════════════════════════════════════════════════════════════
        with ui.row().classes("w-full gap-6 items-start"):

            # ── LEFT COLUMN ──────────────────────────────────────────────────
            with ui.column().classes("flex-1 gap-0 min-w-0"):

                # ── Compact status bar ───────────────────────────────────────
                with ui.element("div").classes(
                    "w-full bg-white border border-slate-200 rounded-xl px-4 py-3 mb-4"
                ):
                    with ui.row().classes("items-center w-full"):
                        icon, label_text, color = STATUS_LABELS.get(
                            computed_status, ("?", computed_status, "#9ca3af")
                        )
                        badge_classes = STATUS_BG.get(computed_status, STATUS_BG["unknown"])
                        with ui.element("div").classes(
                            f"inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold {badge_classes}"
                        ):
                            ui.label(f"{icon} {label_text}")

                        status_select_container = ui.row().classes("items-center gap-2 ml-auto")

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

                    status_row_el = ui.row().classes("items-center gap-2 mt-2 px-1")
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

                # ── Special conditions (Apple-like mini-cards) ───────────────
                conditions = contract.get("special_conditions") or []
                if conditions:
                    ui.label("Особые условия").classes(SECTION_DIVIDER_HEADER)
                    with ui.column().classes("gap-2 mb-6"):
                        for cond in conditions:
                            with ui.element("div").classes(
                                "bg-white border border-slate-200 rounded-lg px-4 py-3 text-sm text-slate-700"
                            ):
                                ui.label(cond)

                # ── History versions (MOVED UP from right column) ────────────
                ui.label("История версий").classes(SECTION_DIVIDER_HEADER)

                _db2 = _client_manager.get_db(state.current_client)
                versions = await run.io_bound(get_version_group, _db2, int(doc_id))

                if not versions:
                    # ── Task 5: Rich empty state ─────────────────────────────
                    with ui.element("div").classes(
                        "w-full border-2 border-dashed border-slate-200 rounded-xl p-8 flex flex-col items-center gap-3 mb-6"
                    ):
                        ui.label("📄").classes("text-4xl")
                        ui.label("Это первая версия документа").classes(
                            "text-base font-semibold text-slate-700"
                        )
                        ui.label(
                            "Загрузите обновлённый файл или найдите похожие документы в реестре"
                        ).classes("text-sm text-slate-400 text-center max-w-xs")

                        with ui.row().classes("gap-3 mt-2"):
                            async def _upload_new_version() -> None:
                                ui.notify("Выберите файл для загрузки", type="info")
                                # Placeholder: in future, open file picker via NiceGUI upload
                                # For now just notify
                            ui.button(
                                "+ Загрузить новую версию",
                                on_click=_upload_new_version,
                            ).props("unelevated no-caps").classes(
                                "bg-indigo-600 text-white text-sm font-semibold px-4 py-1.5 rounded-lg"
                            )
                            ui.button(
                                "🔍 Найти похожие в реестре",
                                on_click=lambda: ui.notify("Функция в разработке"),
                            ).props("flat no-caps").classes(
                                "text-slate-600 text-sm font-medium border border-slate-200 rounded-lg px-4 py-1.5"
                            )
                else:
                    versions_container = ui.column().classes("w-full gap-0 mb-6")
                    with versions_container:
                        for i, v in enumerate(versions):
                            is_last = (i == len(versions) - 1)
                            with ui.row().classes("w-full gap-3 items-start"):

                                with ui.column().classes("items-center gap-0 pt-1"):
                                    ui.element("div").classes(VERSION_DOT)
                                    if not is_last:
                                        ui.element("div").classes(VERSION_LINE).style("height:36px")

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

                # ── Пометки юриста (MOVED TO BOTTOM — least important) ───────
                ui.label("Пометки юриста").classes(SECTION_DIVIDER_HEADER)

                # First-use tooltip
                settings_notes = load_settings()
                if not settings_notes.get("tip_document_seen"):
                    tip_container = ui.row().classes(
                        "w-full bg-slate-50 border border-slate-200 rounded-lg p-3 items-center gap-3 mb-3"
                    )
                    with tip_container:
                        ui.label("💡 Добавьте пометку или проверьте договор по шаблону").classes(
                            "text-sm text-slate-600 flex-1"
                        )

                        def _dismiss_document_tip():
                            save_setting("tip_document_seen", True)
                            tip_container.set_visibility(False)

                        ui.button(icon="close", on_click=_dismiss_document_tip).props(
                            "flat round dense size=sm"
                        ).classes("text-slate-400")

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

            # ── RIGHT COLUMN (w-340px) ───────────────────────────────────────
            with ui.column().classes("shrink-0 gap-4").style("width: 340px;"):

                # ══════════════════════════════════════════════════════════════
                # ── Task 4: AI review — clean white card (no yellow) ─────────
                # ══════════════════════════════════════════════════════════════
                with ui.element("div").classes(
                    "bg-white border border-slate-200 rounded-xl p-5 w-full"
                ):
                    # Icon header
                    with ui.row().classes("items-center gap-3 mb-3"):
                        with ui.element("div").classes(
                            "w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center text-base shrink-0"
                        ):
                            ui.label("🔍")
                        ui.label("Проверка по шаблону").classes(
                            "text-sm font-semibold text-slate-900"
                        )

                    # Confidence indicator
                    _confidence = contract.get("confidence")
                    if _confidence is not None:
                        _pct = round(_confidence * 100)
                        if _confidence >= 0.8:
                            _conf_color = "text-green-600"
                            _dot_color = "#16a34a"
                        elif _confidence >= 0.5:
                            _conf_color = "text-amber-600"
                            _dot_color = "#d97706"
                        else:
                            _conf_color = "text-red-600"
                            _dot_color = "#dc2626"
                        with ui.row().classes("items-center gap-1.5 mb-3"):
                            ui.html(
                                f'<span style="display:inline-block;width:8px;height:8px;'
                                f'border-radius:50%;background:{_dot_color}"></span>'
                            )
                            ui.label(f"Уверенность AI: {_pct}%").classes(
                                f"text-xs font-medium {_conf_color}"
                            )

                    review_container = ui.column().classes("w-full gap-2 py-2")

                    async def _run_review() -> None:
                        review_auto_btn.disable()
                        try:
                            review_container.clear()
                            with review_container:
                                ui.spinner("dots").classes("text-indigo-500")

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

                                    ui.button("Проверить", on_click=_review_with_selected).props("flat no-caps").classes("text-indigo-600")
                                return

                            await _do_review(template.content_text)
                        finally:
                            review_auto_btn.enable()

                    async def _do_review(template_text: str) -> None:
                        review_container.clear()
                        with review_container:
                            ui.spinner("dots").classes("text-indigo-500")
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

                    async def _manual_template_select() -> None:
                        """Показывает список шаблонов для ручного выбора."""
                        review_container.clear()
                        _db = _client_manager.get_db(state.current_client)
                        try:
                            templates = await run.io_bound(list_templates, _db)
                        except Exception:
                            ui.notify("Не удалось загрузить список шаблонов.", type="negative")
                            return
                        if not templates:
                            with review_container:
                                ui.label("Нет шаблонов").classes("text-sm text-slate-500")
                                ui.button(
                                    "Добавить шаблон →",
                                    on_click=lambda: ui.navigate.to("/templates"),
                                ).props("flat no-caps").classes("text-indigo-600 text-sm")
                            return
                        with review_container:
                            template_options = {t.id: f"{t.name} ({t.contract_type})" for t in templates}
                            selected_template = ui.select(
                                template_options,
                                label="Выберите шаблон",
                            ).classes("w-full")

                            async def _review_with_selected() -> None:
                                sel_id = selected_template.value
                                if sel_id is None:
                                    return
                                sel_tmpl = next((t for t in templates if t.id == sel_id), None)
                                if sel_tmpl:
                                    await _do_review(sel_tmpl.content_text)

                            ui.button("Проверить", on_click=_review_with_selected).props(
                                "unelevated no-caps"
                            ).classes("bg-indigo-600 text-white text-sm rounded-lg")

                    # Two buttons: manual select + auto-match
                    with ui.row().classes("gap-2 w-full mt-1"):
                        ui.button(
                            "Указать шаблон",
                            on_click=_manual_template_select,
                        ).props("flat no-caps").classes(
                            "text-slate-600 text-sm font-medium border border-slate-200 rounded-lg px-3 py-1"
                        )
                        review_auto_btn = ui.button(
                            "Проверить автоматически",
                            on_click=_run_review,
                        ).props("unelevated no-caps").classes(
                            "bg-indigo-600 text-white text-sm font-semibold px-3 py-1 rounded-lg"
                        )
