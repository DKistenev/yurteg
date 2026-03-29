"""Страница «Шаблоны» — управление шаблонами-эталонами для ревью договоров.

Phase 11, Plan 03.
Per D-12: заголовок с кнопкой «+ Добавить шаблон».
Per D-13: карточки шаблонов в двухколоночной сетке с preview, типом, датой.
Per D-14: нативный file picker (OPEN_DIALOG) → диалог имени+типа → extract_text → add_template.
Per D-15: кнопки «Изменить» и «Удалить» на каждой карточке.
Per D-16: run.io_bound() для extract_text (blocking I/O).
"""
import logging
from itertools import groupby
from pathlib import Path
from typing import Optional

from nicegui import app, run, ui

import modules.extractor as extractor
import services.review_service as review_service
from app.components.ui_helpers import confirm_dialog
from app.state import get_state
from app.styles import (
    TEXT_HEADING_2XL,
    TMPL_TYPE_COLORS,
    TMPL_TYPE_DEFAULT,
    BTN_ACCENT_FILLED,
    TMPL_EMPTY_TITLE,
    TMPL_EMPTY_BODY,
    APPLE_CARD,
)
from config import Config, load_settings, save_setting
from modules.models import FileInfo
from services.client_manager import ClientManager

logger = logging.getLogger(__name__)


async def _pick_file() -> Optional[Path]:
    """Открывает нативный OS file picker для PDF/DOCX.

    Pitfall 5: всегда проверять `if result` перед использованием.
    RBST-01: graceful fallback в web mode.
    """
    try:
        import webview  # noqa: PLC0415 — local import guard for web mode
        result = await app.native.main_window.create_file_dialog(
            dialog_type=webview.OPEN_DIALOG,
            file_types=("PDF файлы (*.pdf)", "Word документы (*.docx)"),
        )
        if not result:
            return None
        return Path(result[0])
    except (ImportError, AttributeError):
        # Web mode: pywebview недоступен или app.native не инициализирован
        ui.notify(
            "Выбор файла недоступен в веб-режиме.",
            type="warning",
            timeout=4000,
        )
        return None


def _render_cards(container: ui.column, on_add: callable = None) -> None:
    """Рендерит карточки шаблонов в двухколоночной сетке."""
    state = get_state()
    db = ClientManager().get_db(state.current_client)
    templates = review_service.list_templates(db)

    container.clear()
    with container:
        if not templates:
            # Rich empty state (TMPL-03)
            with ui.column().classes("w-full items-center py-6"):
                ui.label("Шаблоны не добавлены").classes(TMPL_EMPTY_TITLE)
                ui.label(
                    "Загрузите образец договора — система сравнит новые документы с эталоном и покажет отклонения"
                ).classes(TMPL_EMPTY_BODY + " mb-6")
                if on_add:
                    ui.button(
                        "Добавить первый шаблон", on_click=on_add
                    ).classes(BTN_ACCENT_FILLED).props('no-caps aria-label="Добавить первый шаблон договора"')

            # ── Demo карточка — показывает как выглядит шаблон (PLSH-05) ─────
            with ui.column().classes("w-full mt-8 gap-3 items-center"):
                ui.label("Так будет выглядеть шаблон").classes(
                    "text-xs font-semibold text-slate-400 uppercase tracking-wide text-center"
                )
                colors = TMPL_TYPE_COLORS.get("Договор аренды", TMPL_TYPE_DEFAULT)
                # Prominent demo card — large, slightly faded
                with ui.element("div").style(
                    "opacity:0.55;pointer-events:none;max-width:540px;width:100%"
                ):
                    with ui.card().classes(
                        "overflow-hidden border border-slate-200 rounded-xl w-full shadow-sm"
                    ).style("padding:0"):
                        with ui.row().classes("w-full gap-0"):
                            # 4px color bar
                            with ui.element("div").style(
                                f"width:4px;background:{colors['border']};"
                                f"border-radius:12px 0 0 12px;flex-shrink:0"
                            ):
                                pass
                            with ui.column().classes("p-5 gap-1.5 flex-1 min-w-0"):
                                with ui.row().classes("items-center gap-3 mb-1"):
                                    # Icon in colored rounded square
                                    ui.html(
                                        f'<div style="width:32px;height:32px;border-radius:8px;'
                                        f'background:{colors["badge_bg"]};display:flex;'
                                        f'align-items:center;justify-content:center;'
                                        f'flex-shrink:0;font-size:16px;line-height:1">{colors["icon"]}</div>'
                                    )
                                    with ui.column().classes("gap-0"):
                                        ui.label("Договор аренды офиса").classes(
                                            "font-semibold text-slate-900"
                                        ).style("font-size:13px")
                                        ui.label("Договор аренды \u00b7 использован 3 раза").classes(
                                            "text-slate-500"
                                        ).style("font-size:11px")
                                ui.label(
                                    "Настоящий договор аренды нежилого помещения заключён между "
                                    "арендодателем и арендатором на условиях, изложенных ниже. "
                                    "Стороны пришли к соглашению о нижеследующем..."
                                ).classes("text-slate-400 mt-2 line-clamp-2").style("font-size:11px")
                                ui.label("12 января 2025").classes("text-slate-300 mt-1").style("font-size:11px")
            return

        # Group templates by contract_type
        templates_sorted = sorted(templates, key=lambda t: t.contract_type or "Прочее")
        for doc_type, group in groupby(templates_sorted, key=lambda t: t.contract_type or "Прочее"):
            group_list = list(group)
            colors = TMPL_TYPE_COLORS.get(doc_type, TMPL_TYPE_DEFAULT)
            with ui.column().classes("w-full gap-4 yt-fade-stagger"):
                # Section header
                with ui.row().classes("items-center gap-2 mt-4 mb-1"):
                    ui.html(
                        f'<div style="width:20px;height:20px;border-radius:6px;'
                        f'background:{colors["badge_bg"]};display:flex;'
                        f'align-items:center;justify-content:center;'
                        f'flex-shrink:0;font-size:11px;line-height:1">{colors["icon"]}</div>'
                    )
                    ui.label(doc_type).classes(
                        "text-xs font-semibold text-slate-400 uppercase tracking-wide"
                    )
                with ui.grid(columns=2).classes("w-full gap-4"):
                    for tmpl in group_list:
                        # ANIM-02: wrapper div с .card-enter для stagger-эффекта
                        with ui.element('div').classes("card-enter yt-hover-card"):
                            _render_card(tmpl, container, on_add=on_add)


def _render_card(tmpl, cards_container: ui.column, on_add: callable = None) -> None:
    """Рендерит одну карточку шаблона в Apple-like стиле."""
    colors = TMPL_TYPE_COLORS.get(tmpl.contract_type, TMPL_TYPE_DEFAULT)
    preview = (tmpl.content_text or "")[:100]
    usage_count = getattr(tmpl, "usage_count", 0) or 0

    with ui.card().classes(
        APPLE_CARD + " overflow-hidden cursor-default yt-hover-card hover:shadow-md hover:-translate-y-0.5 transition-all duration-200"
    ).style("padding:0").props(f'role="article" aria-label="Шаблон: {tmpl.name}"'):
        with ui.row().classes("w-full gap-0").style("min-height:100%"):
            # 4px color-coded left bar
            with ui.element("div").style(
                f"width:4px;background:{colors['border']};border-radius:12px 0 0 12px;flex-shrink:0"
            ):
                pass
            # Card content
            with ui.column().classes("p-5 gap-1.5 flex-1 min-w-0"):
                # Header row: icon square + title/subtitle
                with ui.row().classes("items-center gap-3 mb-1"):
                    # Icon in colored rounded square (emoji, not material-icons)
                    ui.html(
                        f'<div style="width:32px;height:32px;border-radius:8px;'
                        f'background:{colors["badge_bg"]};display:flex;'
                        f'align-items:center;justify-content:center;'
                        f'flex-shrink:0;font-size:16px;line-height:1">{colors["icon"]}</div>'
                    )
                    with ui.column().classes("gap-0 min-w-0"):
                        ui.label(tmpl.name).classes(
                            "font-semibold text-slate-900 truncate"
                        ).style("font-size:13px")
                        usage_text = f"{tmpl.contract_type} \u00b7 {usage_count} использ." if usage_count else tmpl.contract_type
                        ui.label(usage_text).classes(
                            "text-slate-500"
                        ).style("font-size:11px")
                # Preview text (2 lines max)
                if preview:
                    ui.label(preview).classes(
                        "text-slate-400 line-clamp-2 overflow-hidden"
                    ).style("font-size:11px")
                # Date
                if tmpl.created_at:
                    ui.label(tmpl.created_at).classes("text-slate-300 mt-0.5").style("font-size:11px")
                # Action buttons (visible on hover via hover-parent-show)
                with ui.row().classes("mt-2 gap-1 hover-parent-show"):
                    ui.button(
                        "Изменить",
                        on_click=lambda t=tmpl: _open_edit_dialog(t, cards_container, on_add=on_add),
                    ).props("flat no-caps dense color=primary").classes("text-xs")
                    ui.button(
                        "Удалить",
                        on_click=lambda t=tmpl: _open_delete_dialog(t, cards_container, on_add=on_add),
                    ).props("flat no-caps dense color=negative").classes("text-xs")


def _open_edit_dialog(tmpl, cards_container: ui.column, on_add: callable = None) -> None:
    """Диалог редактирования имени и типа шаблона."""
    with ui.dialog() as dlg, ui.card().classes("p-6 min-w-[400px]"):
        ui.label("Изменить шаблон").classes("text-lg font-semibold text-slate-900 mb-4")

        name_input = ui.input(
            label="Название",
            value=tmpl.name,
        ).props("outlined dense").classes("w-full mb-3")

        type_select = ui.select(
            options=Config().document_types_hints,
            label="Тип документа",
            value=tmpl.contract_type,
        ).props("outlined dense use-input").classes("w-full mb-4")

        async def _confirm() -> None:
            new_name = name_input.value.strip()
            new_type = type_select.value or "Прочее"
            if not new_name:
                ui.notify("Введите название шаблона", type="warning")
                return
            save_btn.disable()
            try:
                state = get_state()
                db = ClientManager().get_db(state.current_client)
                try:
                    await run.io_bound(
                        review_service.update_template, db, tmpl.id, new_name, new_type
                    )
                except Exception:
                    logger.exception("Ошибка при работе с шаблонами: сохранение изменений")
                    ui.notify("Не удалось сохранить изменения. Попробуйте ещё раз.", type="negative")
                    return
                dlg.close()
                _render_cards(cards_container, on_add=on_add)
            finally:
                save_btn.enable()

        with ui.row().classes("justify-end gap-2 w-full"):
            ui.button("Отмена", on_click=dlg.close).props("flat no-caps color=grey")
            save_btn = ui.button("Сохранить", on_click=_confirm).props("unelevated no-caps").classes(
                "px-4 py-1.5 bg-indigo-600 text-white text-sm font-semibold rounded-lg"
                " hover:bg-indigo-700 transition-colors duration-150"
            )

    dlg.open()


def _open_delete_dialog(tmpl, cards_container: ui.column, on_add: callable = None) -> None:
    """Диалог подтверждения удаления шаблона."""

    async def _do_delete():
        state = get_state()
        db = ClientManager().get_db(state.current_client)
        try:
            await run.io_bound(review_service.delete_template, db, tmpl.id)
        except Exception:
            logger.exception("Ошибка при работе с шаблонами: удаление шаблона")
            ui.notify("Не удалось удалить шаблон. Попробуйте ещё раз.", type="negative")
            return
        _render_cards(cards_container, on_add=on_add)

    confirm_dialog(
        title="Удалить шаблон?",
        message=f"«{tmpl.name}»",
        on_confirm=_do_delete,
    )


async def _add_template_flow(cards_container: ui.column, on_add: callable = None) -> None:
    """Поток добавления шаблона: file picker → диалог имени+типа → extract → save.

    Per D-14, D-16:
    1. Нативный OPEN_DIALOG для выбора PDF/DOCX
    2. Диалог с именем (prefilled из имени файла) и типом документа
    3. run.io_bound(extract_text) — blocking I/O
    4. run.io_bound(add_template) — DB запись
    5. Обновление карточек
    """
    file_path = await _pick_file()
    if not file_path:
        return

    # Открываем диалог имени и типа
    with ui.dialog() as dlg, ui.card().classes("p-6 min-w-[400px]"):
        ui.label("Добавить шаблон").classes("text-lg font-semibold text-slate-900 mb-4")

        name_input = ui.input(
            label="Название",
            value=file_path.stem,
        ).props("outlined dense").classes("w-full mb-3")

        type_select = ui.select(
            options=Config().document_types_hints,
            label="Тип документа",
        ).props("outlined dense use-input").classes("w-full mb-4")

        status_label = ui.label("").classes("text-xs text-slate-400 mb-2")

        async def _confirm() -> None:
            new_name = name_input.value.strip()
            if not new_name:
                ui.notify("Введите название шаблона", type="warning")
                return

            add_btn.disable()
            try:
                # Показываем статус извлечения
                status_label.set_text("Читаю документ...")

                # Construct FileInfo — Pitfall 4: не передавать Path напрямую
                fi = FileInfo(
                    path=file_path,
                    filename=file_path.name,
                    extension=file_path.suffix.lower(),
                    size_bytes=file_path.stat().st_size,
                    file_hash="",
                )

                # Blocking I/O — run.io_bound
                try:
                    extracted = await run.io_bound(extractor.extract_text, fi)
                except Exception:
                    logger.exception("Ошибка при работе с шаблонами: чтение файла")
                    ui.notify("Не удалось прочитать файл. Проверьте формат документа.", type="negative")
                    return

                state = get_state()
                db = ClientManager().get_db(state.current_client)
                doc_type = type_select.value or "Прочее"

                try:
                    await run.io_bound(
                        review_service.add_template,
                        db,
                        doc_type,
                        new_name,
                        extracted.text,
                        str(file_path),
                    )
                except Exception:
                    logger.exception("Ошибка при работе с шаблонами: сохранение шаблона")
                    ui.notify("Не удалось сохранить шаблон. Попробуйте ещё раз.", type="negative")
                    return

                dlg.close()
                _render_cards(cards_container, on_add=on_add)
                ui.notify(f"Шаблон «{new_name}» добавлен", type="positive")
            finally:
                add_btn.enable()

        with ui.row().classes("justify-end gap-2 w-full"):
            ui.button("Отмена", on_click=dlg.close).props("flat no-caps color=grey")
            add_btn = ui.button(
                "Добавить", on_click=_confirm
            ).props("unelevated no-caps").classes(
                "px-4 py-1.5 bg-indigo-600 text-white text-sm font-semibold rounded-lg"
                " hover:bg-indigo-700 transition-colors duration-150"
            )

    dlg.open()


def build() -> None:
    """Страница «Шаблоны» — управление шаблонами-эталонами."""
    with ui.column().classes("w-full max-w-5xl mx-auto p-8"):

        # ── First-use tooltip ──────────────────────────────────────────────
        settings = load_settings()
        if not settings.get("tip_templates_seen"):
            tip_container = ui.row().classes(
                "w-full bg-slate-50 border border-slate-200 rounded-lg p-3 items-center gap-3 mb-4"
            )
            with tip_container:
                ui.icon("lightbulb").style("font-size:18px; color:#d97706;")
                ui.label(
                    "Загрузите образец договора — система будет сравнивать новые документы с эталоном"
                ).classes("text-sm text-slate-600 flex-1")

                def _dismiss_templates_tip():
                    save_setting("tip_templates_seen", True)
                    tip_container.set_visibility(False)

                ui.button(icon="close", on_click=_dismiss_templates_tip).props(
                    "flat round dense size=sm"
                ).classes("text-slate-400")

        # cards_ref используется через closure — заполняется после создания заголовка
        cards_ref: list[ui.column] = []

        # on_add: общий callback для кнопки в заголовке и CTA в empty state
        def _on_add() -> None:
            _add_template_flow(cards_ref[0], on_add=_on_add)

        # Заголовок
        with ui.row().classes("w-full items-start justify-between mb-6"):
            with ui.column().classes("gap-0"):
                ui.label("Шаблоны").classes(TEXT_HEADING_2XL)
                ui.label(
                    "Образцы документов для проверки договоров"
                ).classes("text-sm text-slate-400 mb-4")

            ui.button(
                "+ Добавить шаблон",
                on_click=_on_add,
            ).props("unelevated no-caps").classes(
                "px-6 py-2 bg-indigo-600 text-white font-semibold rounded-lg text-sm"
                " hover:bg-indigo-700 transition-colors duration-150"
            )

        # Контейнер для карточек
        cards_container = ui.column().classes("w-full")
        cards_ref.append(cards_container)

        # Первоначальный рендер карточек
        _render_cards(cards_container, on_add=_on_add)
