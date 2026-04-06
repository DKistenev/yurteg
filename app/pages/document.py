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
from config import load_runtime_config, load_settings
from app.styles import (
    DOC_SECTION_TITLE, DOC_FIELD_LABEL, DOC_FIELD_VALUE,
    DOC_LEFT_PANEL, DOC_PREVIEW_BG,
    BREADCRUMB_LINK, BREADCRUMB_CURRENT,
    VERSION_DOT, VERSION_LINE,
    ACTION_BTN, ACTION_BTN_PRIMARY,
    APPLE_CARD_COMPACT,
    DOC_HERO, DOC_HERO_BG, DOC_HERO_TYPE_BADGE, DOC_HERO_AMOUNT, DOC_HERO_SUBTITLE,
)
from app.utils import format_date_ru
from modules.models import ContractMetadata
from services.client_manager import ClientManager
from services.review_service import match_template, review_against_template, list_templates
from services.version_service import get_version_group, diff_versions

logger = logging.getLogger(__name__)
_client_manager = ClientManager()

FREQUENCY_LABELS = {
    "monthly": "Ежемесячно",
    "quarterly": "Ежеквартально",
    "yearly": "Ежегодно",
    "once": "Разовый платёж",
}


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


def _section_title(text: str, icon: str = "") -> None:
    """Render a section title (10px, uppercase, tracking), optionally with icon."""
    if icon:
        with ui.row().classes("items-center gap-1.5 mb-2"):
            ui.icon(icon).style("font-size:14px; color:#94a3b8;")
            ui.label(text).classes(DOC_SECTION_TITLE).style("margin-bottom:0;")
    else:
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

    # Hide footer on document page — preview needs full height
    ui.run_javascript("document.querySelector('footer')?.style.setProperty('display','none')")

    # ── Two-column layout: metadata left (55%) + preview right (45%) ────────────
    with ui.row(wrap=False).classes("w-full min-w-0").style(
        "height: calc(100vh - 56px);"
    ):

        # ══════════════════════════════════════════════════════════════════
        # LEFT PANEL — metadata (55%, scrollable)
        # ══════════════════════════════════════════════════════════════════
        with ui.column().classes(DOC_LEFT_PANEL + " min-w-0").style(
            "width: 55%; overflow-y: auto;"
        ):

            # ── Top bar: breadcrumbs + prev/next ──────────────────────
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

            # ══════════════════════════════════════════════════════════════
            # Hero block: dark gradient with doc info + financial summary
            # ══════════════════════════════════════════════════════════════
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
                        getattr(os, "startfile")(str(p))
                    else:
                        subprocess.Popen(["xdg-open", str(p)])
                except Exception:
                    logger.exception("Не удалось открыть файл")
                    ui.notify("Не удалось открыть файл", type="negative")

            async def _reprocess() -> None:
                """Re-run pipeline for this single document."""
                real_path = _Path(contract.get("original_path", ""))
                if not real_path.exists():
                    ui.notify("Файл не найден — переобработка невозможна", type="negative")
                    return
                import os
                import tempfile
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp_path = _Path(tmpdir)
                    link = tmp_path / real_path.name
                    try:
                        os.symlink(real_path, link)
                    except OSError:
                        import shutil
                        shutil.copy2(real_path, link)
                    from controller import Controller
                    db_path = _client_manager.get_db_path(state.current_client)
                    ctrl = Controller(load_runtime_config())
                    ui.notify("Переобработка запущена...", type="info")
                    try:
                        stats = await run.io_bound(
                            ctrl.process_archive,
                            tmp_path,
                            "both",
                            True,
                            None,
                            None,
                            db_path.parent,
                            db_path,
                        )
                    finally:
                        ctrl.close()
                    # Restore original path (pipeline may have saved temp symlink path)
                    _db_fix = _client_manager.get_db(state.current_client)
                    file_hash = contract.get("file_hash", "")
                    if file_hash:
                        try:
                            _db_fix.conn.execute(
                                "UPDATE contracts SET original_path = ? WHERE file_hash = ?",
                                (str(real_path), file_hash),
                            )
                            _db_fix.conn.commit()
                        except Exception:
                            logger.exception("Не удалось восстановить original_path")
                    errors = stats.get("errors", 0)
                    try:
                        if errors:
                            ui.notify(f"Переобработка завершена с ошибками: {errors}", type="warning")
                        else:
                            ui.notify("Документ переобработан", type="positive")
                        ui.navigate.to(f"/document/{doc_id}")
                    except RuntimeError:
                        pass  # page already navigated away

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

            with ui.element("div").classes(DOC_HERO + " w-full").style(DOC_HERO_BG):
                # Top row: type badge + direction badge
                contract_type = contract.get("contract_type") or "\u2014"
                direction = contract.get("direction")
                with ui.row().classes("items-center justify-between w-full mb-3"):
                    ui.html(
                        f'<span class="{DOC_HERO_TYPE_BADGE}" '
                        f'style="background:rgba(255,255,255,0.15); color:rgba(255,255,255,0.9);">'
                        f'{contract_type}</span>'
                    )
                    if direction == "income":
                        ui.html(
                            f'<span class="{DOC_HERO_TYPE_BADGE}" '
                            f'style="background:rgba(74,222,128,0.2); color:#86efac;">'
                            f'\u2191 Доход</span>'
                        )
                    elif direction == "expense":
                        ui.html(
                            f'<span class="{DOC_HERO_TYPE_BADGE}" '
                            f'style="background:rgba(248,113,113,0.2); color:#fca5a5;">'
                            f'\u2193 Расход</span>'
                        )

                # Counterparty + subject
                counterparty = contract.get("counterparty") or "\u2014"
                subject = contract.get("subject") or "\u2014"
                ui.label(counterparty).style("font-size:15px; font-weight:600; color:#fff;")
                ui.label(subject).style("font-size:11px; color:rgba(255,255,255,0.5); margin-top:2px;")

                # Divider
                ui.element("div").style(
                    "border-top:1px solid rgba(255,255,255,0.1); margin:12px 0;"
                )

                # Amount
                amount = contract.get("amount") or "\u2014"
                ui.label(amount).classes(DOC_HERO_AMOUNT)

                # Payment subtitle (frequency + payment_amount)
                frequency = contract.get("frequency")
                payment_amount = contract.get("payment_amount")
                if frequency and payment_amount:
                    freq_label = FREQUENCY_LABELS.get(frequency, frequency)
                    ui.label(f"{freq_label} \u2022 {payment_amount} \u20bd").classes(DOC_HERO_SUBTITLE)

            # ── Action bar ────────────────────────────────────────────
            with ui.row(wrap=False).classes("gap-2 mb-4"):
                ui.button("Открыть файл", icon="open_in_new", on_click=_open_file).props(
                    "flat dense no-caps"
                ).classes(ACTION_BTN)
                ui.button("Переобработать", icon="refresh", on_click=_reprocess).props(
                    "flat dense no-caps"
                ).classes(ACTION_BTN)
                save_tmpl_btn = ui.button(
                    "Сохранить как шаблон", icon="bookmark_add", on_click=_save_as_template
                ).props("flat dense no-caps").classes(ACTION_BTN)

            # ══════════════════════════════════════════════════════════════
            # Сроки card
            # ══════════════════════════════════════════════════════════════
            with ui.element("div").classes(APPLE_CARD_COMPACT + " p-4 mb-4 w-full"):
                _section_title("СРОКИ", "calendar_today")
                with ui.grid(columns=3).classes("gap-x-6 gap-y-3 w-full mt-2"):
                    _field_row("Подписан", format_date_ru(contract.get("date_signed")))
                    _field_row("Начало", format_date_ru(contract.get("date_start")))
                    _field_row("Окончание", format_date_ru(contract.get("date_end")))

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
            # Проверка по шаблону card
            # ══════════════════════════════════════════════════════════════
            with ui.element("div").classes(APPLE_CARD_COMPACT + " p-4 mb-4 w-full"):
                _section_title("ПРОВЕРКА ПО ШАБЛОНУ", "fact_check")

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
                                match_template,
                                _db,
                                contract.get("full_text") or contract.get("subject", ""),
                                contract.get("contract_type"),
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
                            review_against_template,
                            template_text,
                            contract.get("full_text") or contract.get("subject", ""),
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
            # История версий card
            # ══════════════════════════════════════════════════════════════
            with ui.element("div").classes(APPLE_CARD_COMPACT + " p-4 mb-4 w-full"):
                _section_title("ИСТОРИЯ ВЕРСИЙ", "history")

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
                                                    f"/download/redline/{doc_id}/{v.contract_id}?client={state.current_client}"
                                                ).classes("text-xs text-indigo-600 underline")

            # ══════════════════════════════════════════════════════════════
            # Особые условия (только если есть)
            # ══════════════════════════════════════════════════════════════
            conditions = contract.get("special_conditions") or []
            if conditions:
                with ui.element("div").classes(APPLE_CARD_COMPACT + " p-4 mb-4 w-full"):
                    _section_title("ОСОБЫЕ УСЛОВИЯ", "warning_amber")
                    with ui.column().classes("gap-0.5 pl-3 mt-1"):
                        for cond in conditions:
                            ui.label(f"\u2022 {cond}").classes("text-sm text-slate-700")

        # ══════════════════════════════════════════════════════════════════
        # RIGHT PANEL — PDF/DOCX preview (45%, dark background)
        # Per D-01, D-02, D-03, D-04
        # ══════════════════════════════════════════════════════════════════
        original_path = contract.get("original_path", "")
        filename = _Path(original_path).name if original_path else "Документ"
        is_pdf = original_path.lower().endswith(".pdf") if original_path else False
        file_exists = _Path(original_path).exists() if original_path else False

        preview_bg = DOC_PREVIEW_BG if (is_pdf or not file_exists) else "#f1f5f9"
        with ui.column().classes("min-w-0").style(
            f"width: 45%; background: {preview_bg}; height: 100%;"
            " display: flex; flex-direction: column; overflow: hidden;"
        ):
            # Toolbar with filename
            with ui.element("div").classes("doc-preview-toolbar"):
                ui.label(filename).classes("doc-preview-filename")
                if original_path and file_exists:
                    ui.button(
                        icon="open_in_new", on_click=_open_file
                    ).props("flat dense round size=sm").style("color: #94a3b8;")

            if not file_exists:
                # File missing (demo data or deleted) — show placeholder
                with ui.column().style(
                    "flex: 1; display: flex; align-items: center;"
                    " justify-content: center; gap: 12px; padding: 24px;"
                ):
                    ui.icon("visibility_off").style("font-size: 56px; color: #475569;")
                    ui.label("Файл недоступен").style(
                        "font-size: 15px; color: #94a3b8; font-weight: 600; text-align: center;"
                    )
                    ui.label("Загрузите документ для предпросмотра").style(
                        "font-size: 13px; color: #64748b; text-align: center;"
                    )
            elif is_pdf:
                # PDF iframe — /download/{doc_id} route serves the file
                ui.html(
                    f'<iframe src="/download/{doc_id}?client={state.current_client}" '
                    f'style="width:100%; height:100%; border:none; background:white;" '
                    f'title="PDF превью"></iframe>'
                ).style("flex: 1; display: flex;")
            else:
                # DOCX preview via docx-preview.js (local vendor files)
                container_id = f"docx-preview-{doc_id}"
                ui.html(
                    f'<div id="{container_id}" style="width:100%;height:100%;overflow:auto;background:#f1f5f9;">'
                    '<div style="padding:40px;text-align:center;color:#94a3b8;">Загрузка превью...</div>'
                    '</div>'
                ).style("flex: 1; min-height: 0;")
                docx_url = f"/download/{doc_id}?client={state.current_client}"
                # Load scripts dynamically to guarantee order
                ui.run_javascript(f"""
(function() {{
    function loadScript(src, cb) {{
        var s = document.createElement('script');
        s.src = src;
        s.onload = cb;
        s.onerror = function() {{ console.error('Failed to load: ' + src); }};
        document.head.appendChild(s);
    }}
    function addStyle() {{
        var st = document.createElement('style');
        st.textContent = '#{container_id} .docx-preview-wrapper {{ background:#f1f5f9; padding:8px; zoom:0.75; }}'
            + ' #{container_id} .docx-preview-wrapper > section.docx-preview {{ margin:0 auto; box-shadow:0 2px 8px rgba(0,0,0,0.1); }}';
        document.head.appendChild(st);
    }}
    function doRender() {{
        var container = document.getElementById('{container_id}');
        if (!container) return;
        addStyle();
        fetch('{docx_url}')
            .then(function(r) {{ return r.blob(); }})
            .then(function(blob) {{
                return docx.renderAsync(blob, container, null, {{
                    className: 'docx-preview',
                    inWrapper: true,
                    ignoreWidth: false,
                    ignoreHeight: true,
                    renderHeaders: true,
                    renderFooters: true,
                }});
            }})
            .catch(function(err) {{
                container.innerHTML = '<div style="padding:40px;text-align:center;color:#94a3b8;">'
                    + '<span class="material-icons" style="font-size:48px;display:block;margin-bottom:12px;">description</span>'
                    + 'Не удалось загрузить превью: ' + err.message + '</div>';
            }});
    }}
    // Chain: jszip -> docx-preview -> render
    if (typeof JSZip !== 'undefined' && typeof docx !== 'undefined') {{
        doRender();
    }} else {{
        loadScript('/static/vendor/jszip.min.js', function() {{
            loadScript('/static/vendor/docx-preview.min.js', function() {{
                setTimeout(doRender, 100);
            }});
        }});
    }}
}})();
""")
