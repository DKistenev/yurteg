"""Карточка документа — двухколоночный layout: metadata left (45%) + PDF preview right (55%).

Per D-01: Two-column, left panel scrollable, right panel dark with iframe.
Per D-02: Header: breadcrumbs + prev/next + action buttons in left panel top.
Per D-03: Prev/next navigate doc_id in URL.
Per D-04: Dark bg (#1e293b) for preview panel, filename in toolbar.
"""
import logging

from pathlib import Path as _Path

from nicegui import run, ui

from app.state import get_state
from config import load_settings, save_setting
from app.styles import (
    DOC_SECTION_TITLE, DOC_FIELD_LABEL, DOC_FIELD_VALUE,
    DOC_LEFT_PANEL, DOC_PREVIEW_BG,
    BREADCRUMB_LINK, BREADCRUMB_CURRENT,
    VERSION_DOT, VERSION_LINE,
    ACTION_BTN, ACTION_BTN_PRIMARY,
    APPLE_CARD_COMPACT,
    PANEL_TYPE_TAG,
)
from app.utils import format_date_ru
from modules.models import ContractMetadata
from services.client_manager import ClientManager
from services.lifecycle_service import (
    STATUS_LABELS,
    get_computed_status_sql,
)
from services.review_service import match_template, review_against_template, list_templates
from services.version_service import get_version_group, diff_versions

logger = logging.getLogger(__name__)
_client_manager = ClientManager()


def _dict_to_metadata(d: dict) -> ContractMetadata:
    """Convert dict to ContractMetadata for diff_versions."""
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
    """Render review deviations with colored bars."""
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
    """Render diff table between two versions."""
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


def _section_title(text: str) -> None:
    """Render a section title (10px, uppercase, tracking)."""
    ui.label(text).classes(DOC_SECTION_TITLE)


def _field_row(label: str, value: str) -> None:
    """Render a field label + value pair."""
    with ui.column().classes("gap-0.5"):
        ui.label(label).classes(DOC_FIELD_LABEL)
        ui.label(value).classes(DOC_FIELD_VALUE)


async def build(doc_id: str = "") -> None:
    """Render document card: two-column layout with metadata left and preview right."""
    state = get_state()

    if not doc_id:
        ui.navigate.to("/")
        return

    db = _client_manager.get_db(state.current_client)

    contract = await run.io_bound(db.get_contract_by_id, int(doc_id))

    if contract is None:
        with ui.column().classes("w-full px-6 py-6 gap-4"):
            ui.label("Документ не найден").classes("text-xl text-slate-500")
            ui.button("\u2190 Назад к реестру", on_click=lambda: ui.navigate.to("/")).props("flat no-caps").classes("text-slate-600")
        return

    # Load computed_status
    status_row = await run.io_bound(
        lambda: db.conn.execute(
            f"SELECT {get_computed_status_sql(state.warning_days_threshold)} AS computed_status FROM contracts WHERE id = :contract_id",
            {"warning_days": state.warning_days_threshold, "contract_id": int(doc_id)}
        ).fetchone()
    )
    computed_status = dict(status_row)["computed_status"] if status_row else "unknown"

    # ── Two-column layout: metadata left (45%) + preview right (55%) ────────────
    with ui.row(wrap=False).classes("w-full min-w-0").style(
        "height: calc(100vh - 56px);"
    ):

        # ══════════════════════════════════════════════════════════════════
        # LEFT PANEL — metadata (45%, scrollable)
        # ══════════════════════════════════════════════════════════════════
        with ui.column().classes(DOC_LEFT_PANEL + " min-w-0").style(
            "width: 45%; overflow-y: auto;"
        ):

            # ── Top bar: breadcrumbs + prev/next + action buttons ──────
            with ui.row(wrap=False).classes("items-center gap-0 mb-4 w-full"):
                ui.link("Реестр", "/").classes(BREADCRUMB_LINK + " no-underline")
                ui.icon("chevron_right").classes("text-slate-300").style("font-size:18px;")
                ui.label(
                    contract.get("contract_type") or "Документ"
                ).classes(BREADCRUMB_CURRENT + " truncate").style("max-width: 180px;")

                # Prev/next
                doc_ids = state.filtered_doc_ids
                current_idx = doc_ids.index(int(doc_id)) if int(doc_id) in doc_ids else -1
                prev_id = doc_ids[current_idx - 1] if current_idx > 0 else None
                next_id = doc_ids[current_idx + 1] if current_idx < len(doc_ids) - 1 else None

                with ui.row().classes("gap-1 ml-auto shrink-0"):
                    prev_btn = ui.button(
                        icon="chevron_left",
                        on_click=lambda pid=prev_id: ui.navigate.to(f"/document/{pid}")
                    ).props('flat dense round aria-label="Предыдущий документ"').classes("text-slate-400")
                    prev_btn.set_enabled(prev_id is not None)
                    next_btn = ui.button(
                        icon="chevron_right",
                        on_click=lambda nid=next_id: ui.navigate.to(f"/document/{nid}")
                    ).props('flat dense round aria-label="Следующий документ"').classes("text-slate-400")
                    next_btn.set_enabled(next_id is not None)

            # ── Action buttons row ─────────────────────────────────────
            with ui.row(wrap=True).classes("gap-2 mb-4"):
                async def _open_file() -> None:
                    import platform
                    import subprocess
                    path_str = contract.get("original_path", "")
                    if not path_str:
                        ui.notify("Путь к файлу не найден", type="negative")
                        return
                    p = _Path(path_str)
                    if not p.exists():
                        ui.notify("Файл не найден на диске", type="negative")
                        return
                    system = platform.system()
                    try:
                        if system == "Darwin":
                            subprocess.Popen(["open", str(p)])
                        elif system == "Windows":
                            import os
                            os.startfile(str(p))
                        else:
                            subprocess.Popen(["xdg-open", str(p)])
                    except Exception:
                        logger.exception("Не удалось открыть файл")
                        ui.notify("Не удалось открыть файл", type="negative")

                ui.button("Открыть файл", icon="open_in_new", on_click=_open_file).props(
                    "flat dense no-caps"
                ).classes(ACTION_BTN)

                async def _reprocess():
                    """Re-run pipeline for this single document."""
                    original_path = _Path(contract.get("original_path", ""))
                    if not original_path.exists():
                        ui.notify("Файл не найден — переобработка невозможна", type="negative")
                        return
                    import os
                    import tempfile
                    with tempfile.TemporaryDirectory() as tmpdir:
                        tmp_path = _Path(tmpdir)
                        link = tmp_path / original_path.name
                        try:
                            os.symlink(original_path, link)
                        except OSError:
                            import shutil
                            shutil.copy2(original_path, link)
                        from config import Config
                        from controller import Controller
                        cm = ClientManager()
                        db_path = cm.get_db_path(state.current_client)
                        ctrl = Controller(Config())
                        ui.notify("Переобработка запущена...", type="info")
                        stats = await run.io_bound(
                            ctrl.process_archive,
                            tmp_path,
                            "both",
                            True,
                            None,
                            None,
                            db_path.parent,
                        )
                        errors = stats.get("errors", 0)
                        if errors:
                            ui.notify(f"Переобработка завершена с ошибками: {errors}", type="warning")
                        else:
                            ui.notify("Документ переобработан", type="positive")
                        ui.navigate.to(f"/document/{doc_id}")

                ui.button("Переобработать", icon="refresh", on_click=_reprocess).props(
                    "flat dense no-caps"
                ).classes(ACTION_BTN)

            # ══════════════════════════════════════════════════════════════
            # Section 1: ДОКУМЕНТ
            # ══════════════════════════════════════════════════════════════
            with ui.element("div").classes(APPLE_CARD_COMPACT + " p-4 mb-4 w-full"):
                _section_title("ДОКУМЕНТ")

                # Type badge
                contract_type = contract.get("contract_type") or "\u2014"
                ui.html(
                    f'<span class="{PANEL_TYPE_TAG}">{contract_type}</span>'
                )

                # Counterparty (bold, larger)
                counterparty = contract.get("counterparty") or "\u2014"
                ui.label(counterparty).style("font-size:16px;font-weight:600;color:#0f172a;margin-top:8px;")

                # Subject
                subject = contract.get("subject") or "\u2014"
                ui.label(subject).classes("text-[13px] text-slate-600 mt-1")

            # ══════════════════════════════════════════════════════════════
            # Section 2: СРОКИ И ФИНАНСЫ
            # ══════════════════════════════════════════════════════════════
            with ui.element("div").classes(APPLE_CARD_COMPACT + " p-4 mb-4 w-full"):
                _section_title("СРОКИ И ФИНАНСЫ")
                with ui.grid(columns=2).classes("gap-x-6 gap-y-3 w-full mt-2"):
                    _field_row("Дата начала", format_date_ru(contract.get("date_start")))
                    _field_row("Дата окончания", format_date_ru(contract.get("date_end")))
                    _field_row("Дата подписания", format_date_ru(contract.get("date_signed")))
                    # Amount — larger
                    with ui.column().classes("gap-0.5"):
                        ui.label("Сумма").classes(DOC_FIELD_LABEL)
                        ui.label(contract.get("amount") or "\u2014").style(
                            "font-size:18px;font-weight:700;color:#0f172a;"
                        )

            # Confidence warning
            settings = load_settings()
            confidence_threshold = settings.get("confidence_low", 0.5)
            confidence = contract.get("confidence", 1.0)
            if confidence < confidence_threshold:
                with ui.element("div").classes("bg-amber-50 border border-amber-200 rounded-lg p-3 mb-3"):
                    ui.label(
                        "\u26a0 Низкая уверенность AI \u2014 проверьте данные"
                    ).classes("text-xs text-amber-600 font-medium")

            # ══════════════════════════════════════════════════════════════
            # Section 3: СТАТУС
            # ══════════════════════════════════════════════════════════════
            with ui.element("div").classes(APPLE_CARD_COMPACT + " p-4 mb-4 w-full"):
                _section_title("СТАТУС")

                icon, label_text, _color, _css = STATUS_LABELS.get(
                    computed_status, ("?", computed_status, "#9ca3af", "")
                )
                status_css_class = f"status-{computed_status}"
                ui.html(f'<span class="{status_css_class}">{icon} {label_text}</span>')

            # ══════════════════════════════════════════════════════════════
            # Section 4: ПРОВЕРКА ПО ШАБЛОНУ
            # ══════════════════════════════════════════════════════════════
            with ui.element("div").classes(APPLE_CARD_COMPACT + " p-4 mb-4 w-full"):
                _section_title("ПРОВЕРКА ПО ШАБЛОНУ")

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
                            logger.exception("Ошибка подбора шаблона")
                            ui.notify("Не удалось подобрать шаблон автоматически.", type="negative")
                            return
                        if template is None:
                            try:
                                templates = await run.io_bound(list_templates, _db)
                            except Exception:
                                logger.exception("Ошибка загрузки шаблонов")
                                ui.notify("Не удалось загрузить список шаблонов.", type="negative")
                                return
                            if not templates:
                                review_container.clear()
                                with review_container:
                                    ui.label("Нет подходящего шаблона").classes("text-sm text-slate-500")
                                    ui.button(
                                        "Добавить шаблон \u2192",
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
                        logger.exception("Ошибка проверки по шаблону")
                        review_container.clear()
                        with review_container:
                            ui.notify("Не удалось выполнить проверку.", type="negative")
                        return
                    _render_deviations(review_container, deviations)

                with ui.row().classes("gap-2"):
                    review_btn = ui.button("Найти шаблон", on_click=_run_review).props("flat no-caps").classes(ACTION_BTN_PRIMARY)
                    ui.button(
                        "Добавить \u2192",
                        on_click=lambda: ui.navigate.to("/templates"),
                    ).props("flat no-caps").classes(ACTION_BTN)

            # ══════════════════════════════════════════════════════════════
            # Section 5: ИСТОРИЯ ВЕРСИЙ
            # ══════════════════════════════════════════════════════════════
            _section_title("ИСТОРИЯ ВЕРСИЙ")

            _db2 = _client_manager.get_db(state.current_client)
            versions = await run.io_bound(get_version_group, _db2, int(doc_id))

            if not versions:
                with ui.row().classes("items-center gap-2 py-2"):
                    ui.icon("history").style("font-size:16px; color:#cbd5e1;")
                    ui.label("Версии появятся после повторной обработки").classes("text-slate-400 text-xs")
            else:
                with ui.column().classes("w-full gap-0"):
                    for i, v in enumerate(versions):
                        is_last = (i == len(versions) - 1)
                        with ui.row().classes("w-full gap-3 items-start"):
                            with ui.column().classes("items-center gap-0 pt-1"):
                                ui.element("div").classes(VERSION_DOT)
                                if not is_last:
                                    ui.element("div").classes(VERSION_LINE).style("height:36px")
                            with ui.column().classes("flex-1 pb-4 gap-1 min-w-0"):
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
                                                    logger.exception("Ошибка загрузки версии")
                                                    ui.notify("Не удалось загрузить версию.", type="negative")
                                                    return
                                                if other is None:
                                                    return
                                                meta_current = _dict_to_metadata(contract)
                                                meta_other = _dict_to_metadata(other)
                                                try:
                                                    diffs = await run.io_bound(diff_versions, meta_current, meta_other)
                                                except Exception:
                                                    logger.exception("Ошибка сравнения версий")
                                                    ui.notify("Не удалось сравнить версии.", type="negative")
                                                    return
                                                diff_container = ui.column().classes("w-full mt-2")
                                                _render_diff_table(diff_container, diffs)

                                            ui.button("Сравнить", on_click=_show_diff).props("flat dense no-caps").classes("text-xs text-indigo-600")
                                            ui.link(
                                                "Скачать с правками",
                                                f"/download/redline/{doc_id}/{v.contract_id}"
                                            ).classes("text-xs text-indigo-600 underline")

            # ══════════════════════════════════════════════════════════════
            # Section 6: ПОМЕТКИ ЮРИСТА
            # ══════════════════════════════════════════════════════════════
            _section_title("ПОМЕТКИ ЮРИСТА")

            # First-use tooltip
            if not settings.get("tip_document_seen"):
                tip_container = ui.row().classes(
                    "w-full bg-slate-50 border border-slate-200 rounded-lg p-3 items-center gap-3 mb-2"
                )
                with tip_container:
                    ui.icon("lightbulb").style("font-size:18px; color:#d97706;")
                    ui.label("Добавьте пометку или проверьте договор по шаблону").classes(
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
                        ui.notify("Сохранено", type="positive")
                    except Exception:
                        logger.exception("Ошибка сохранения заметки")
                        ui.notify("Не удалось сохранить заметку.", type="negative")

            comment_area = ui.textarea(
                value=contract.get("lawyer_comment", "")
            ).props('outlined rows=4 placeholder="Добавьте заметку..."').classes("w-full")
            comment_area.on("blur", _save_comment)

            # Special conditions (if any)
            conditions = contract.get("special_conditions") or []
            if conditions:
                ui.element("div").classes("border-b border-slate-200 w-full my-3")
                _section_title("ОСОБЫЕ УСЛОВИЯ")
                with ui.column().classes("gap-0.5 pl-3"):
                    for cond in conditions:
                        ui.label(f"\u2022 {cond}").classes("text-sm text-slate-700")

            # Save as template button at bottom
            async def _save_as_template() -> None:
                from services.review_service import mark_contract_as_template as _mark_tmpl
                save_tmpl_btn.disable()
                try:
                    _db = _client_manager.get_db(state.current_client)
                    template_id = await run.io_bound(
                        _mark_tmpl, _db, int(doc_id)
                    )
                    if template_id is None:
                        ui.notify("Не удалось сохранить шаблон", type="negative")
                    else:
                        ui.notify("Документ сохранён как шаблон", type="positive")
                except Exception:
                    logger.exception("Ошибка сохранения шаблона")
                    ui.notify("Ошибка при сохранении шаблона", type="negative")
                finally:
                    save_tmpl_btn.enable()

            ui.element("div").classes("mb-4")
            save_tmpl_btn = ui.button(
                "Сохранить как шаблон", icon="bookmark_add", on_click=_save_as_template
            ).props("flat dense no-caps").classes(ACTION_BTN + " w-full justify-center")

        # ══════════════════════════════════════════════════════════════════
        # RIGHT PANEL — PDF/DOCX preview (55%, dark background)
        # Per D-01, D-02, D-03, D-04
        # ══════════════════════════════════════════════════════════════════
        original_path = contract.get("original_path", "")
        filename = _Path(original_path).name if original_path else "Документ"
        is_pdf = original_path.lower().endswith(".pdf") if original_path else False

        with ui.column().classes("min-w-0").style(
            f"width: 55%; background: {DOC_PREVIEW_BG}; height: 100%;"
        ):
            # Toolbar with filename
            with ui.element("div").classes("doc-preview-toolbar"):
                ui.label(filename).classes("doc-preview-filename")
                if original_path:
                    ui.button(
                        icon="open_in_new", on_click=_open_file
                    ).props("flat dense round size=sm").style("color: #94a3b8;")

            if is_pdf:
                # PDF iframe — /download/{doc_id} route serves the file
                ui.html(
                    f'<iframe src="/download/{doc_id}" '
                    f'style="width:100%; height:100%; border:none; background:white;" '
                    f'title="PDF превью"></iframe>'
                ).style("flex: 1; display: flex;")
            else:
                # DOCX or unknown — placeholder
                with ui.column().classes("flex-1 items-center justify-center gap-4"):
                    ui.icon("description").style("font-size: 64px; color: #475569;")
                    ui.label("Превью недоступно для DOCX").style(
                        "font-size: 14px; color: #94a3b8; font-weight: 500;"
                    )
                    ui.button(
                        "Открыть файл", icon="open_in_new", on_click=_open_file
                    ).props("flat no-caps").style(
                        "color: #94a3b8; border: 1px solid #334155;"
                    )

