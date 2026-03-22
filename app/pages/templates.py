"""Страница «Шаблоны» — управление шаблонами-эталонами для ревью договоров.

Phase 11, Plan 03.
Per D-12: заголовок с кнопкой «+ Добавить шаблон».
Per D-13: карточки шаблонов в двухколоночной сетке с preview, типом, датой.
Per D-14: нативный file picker (OPEN_DIALOG) → диалог имени+типа → extract_text → add_template.
Per D-15: кнопки «Изменить» и «Удалить» на каждой карточке.
Per D-16: run.io_bound() для extract_text (blocking I/O).
"""
from pathlib import Path
from typing import Optional

from nicegui import app, run, ui

import modules.extractor as extractor
import services.review_service as review_service
from app.components.ui_helpers import confirm_dialog
from app.state import get_state
from app.styles import (
    TEXT_HEADING_2XL,
    TEXT_MUTED,
    TMPL_TYPE_COLORS,
    TMPL_TYPE_DEFAULT,
    BTN_ACCENT_FILLED,
    TMPL_EMPTY_ICON,
    TMPL_EMPTY_TITLE,
    TMPL_EMPTY_BODY,
)
from config import Config
from modules.models import FileInfo
from services.client_manager import ClientManager


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
            with ui.column().classes("w-full items-center justify-center py-10"):
                ui.icon(TMPL_EMPTY_ICON).props("size=64px").classes("text-slate-300")
                ui.label("Шаблоны не добавлены").classes(TMPL_EMPTY_TITLE)
                ui.label(
                    "Добавьте образец договора — система будет использовать его как эталон при проверке новых документов"
                ).classes(TMPL_EMPTY_BODY + " mb-6")
                if on_add:
                    ui.button(
                        "Добавить первый шаблон", on_click=on_add
                    ).classes(BTN_ACCENT_FILLED).props('no-caps aria-label="Добавить первый шаблон договора"')

            # ── Demo карточка — показывает как выглядит шаблон (PLSH-05) ─────
            with ui.column().classes("w-full mt-6 gap-2 items-center"):
                ui.label("Так выглядит шаблон:").classes(
                    "text-xs font-semibold text-slate-400 uppercase tracking-wide text-center"
                )
                colors = TMPL_TYPE_COLORS.get("Договор аренды", TMPL_TYPE_DEFAULT)
                # Greyed-out версия карточки — opacity + pointer-events-none
                with ui.element("div").style(
                    "opacity:0.45;pointer-events:none;max-width:420px;width:100%"
                ):
                    with ui.card().classes(
                        "overflow-hidden border border-slate-200 shadow-none rounded-xl w-full"
                    ).style("padding:0"):
                        with ui.row().classes("w-full gap-0"):
                            # 4px color bar
                            with ui.element("div").style(
                                f"width:4px;background:{colors['border']};"
                                f"border-radius:12px 0 0 12px;flex-shrink:0"
                            ):
                                pass
                            with ui.column().classes("p-5 gap-1 flex-1"):
                                with ui.row().classes("items-center gap-2 mb-1"):
                                    ui.html(f'<span style="font-size:1.1rem">{colors["icon"]}</span>')
                                    ui.label("Договор аренды офиса").classes(
                                        "font-semibold text-slate-900 text-sm"
                                    )
                                badge_html = (
                                    f'<span style="display:inline-flex;align-items:center;'
                                    f'padding:2px 8px;border-radius:9999px;font-size:0.7rem;'
                                    f'font-weight:600;background:{colors["badge_bg"]};'
                                    f'color:{colors["badge_text"]}">'
                                    f'{colors["icon"]} Договор аренды</span>'
                                )
                                ui.html(badge_html)
                                ui.label(
                                    "Настоящий договор аренды нежилого помещения заключён между "
                                    "арендодателем и арендатором на условиях, изложенных ниже..."
                                ).classes("text-xs text-slate-400 mt-2 line-clamp-2")
                                ui.label("12 января 2025").classes("text-xs text-slate-300 mt-1")
                ui.label("Пример — после добавления шаблона карточка будет настоящей").classes(
                    "text-xs text-slate-400 text-center"
                )
            return

        with ui.grid(columns=2).classes("w-full gap-4"):
            for tmpl in templates:
                # ANIM-02: wrapper div с .card-enter для stagger-эффекта (не на ui.card напрямую)
                with ui.element('div').classes("card-enter"):
                    _render_card(tmpl, container, on_add=on_add)


def _render_card(tmpl, cards_container: ui.column, on_add: callable = None) -> None:
    """Рендерит одну карточку шаблона с color-coded левой полосой и type badge."""
    colors = TMPL_TYPE_COLORS.get(tmpl.contract_type, TMPL_TYPE_DEFAULT)
    preview = (tmpl.content_text or "")[:200]

    badge_html = (
        f'<span style="display:inline-flex;align-items:center;padding:2px 8px;'
        f'border-radius:9999px;font-size:0.7rem;font-weight:600;'
        f'background:{colors["badge_bg"]};color:{colors["badge_text"]}">'
        f'{colors["icon"]} {tmpl.contract_type}</span>'
    )

    with ui.card().classes(
        "overflow-hidden cursor-default border border-slate-200 shadow-none rounded-xl"
    ).style("padding:0").props(f'role="article" aria-label="Шаблон: {tmpl.name}"'):
        with ui.row().classes("w-full gap-0").style("min-height:100%"):
            # 4px color-coded left bar
            with ui.element("div").style(
                f"width:4px;background:{colors['border']};border-radius:12px 0 0 12px;flex-shrink:0"
            ):
                pass
            # Card content
            with ui.column().classes("p-5 gap-1 flex-1"):
                # Header row: icon + name
                with ui.row().classes("items-center gap-2 mb-1"):
                    ui.html(f'<span style="font-size:1.1rem">{colors["icon"]}</span>')
                    ui.label(tmpl.name).classes("font-semibold text-slate-900 text-sm")
                # Type badge
                ui.html(badge_html)
                # Preview
                ui.label(preview).classes(
                    "text-xs text-slate-400 mt-2 line-clamp-3 overflow-hidden"
                )
                # Date
                ui.label(tmpl.created_at or "").classes("text-xs text-slate-300 mt-1")
                # Action buttons
                with ui.row().classes("mt-3 gap-1"):
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
                except Exception as e:
                    ui.notify("Не удалось сохранить изменения. Попробуйте ещё раз.", type="negative")
                    return
                dlg.close()
                _render_cards(cards_container, on_add=on_add)
            finally:
                save_btn.enable()

        with ui.row().classes("justify-end gap-2 w-full"):
            ui.button("Отмена", on_click=dlg.close).props("flat no-caps color=grey")
            save_btn = ui.button("Сохранить", on_click=_confirm).props("no-caps color=primary")

    dlg.open()


def _open_delete_dialog(tmpl, cards_container: ui.column, on_add: callable = None) -> None:
    """Диалог подтверждения удаления шаблона."""

    async def _do_delete():
        state = get_state()
        db = ClientManager().get_db(state.current_client)
        try:
            await run.io_bound(review_service.delete_template, db, tmpl.id)
        except Exception:
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
                except Exception as e:
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
                except Exception as e:
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
            ).props("no-caps color=primary")

    dlg.open()


def build() -> None:
    """Страница «Шаблоны» — управление шаблонами-эталонами."""
    with ui.column().classes("w-full max-w-5xl mx-auto p-8"):
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
            ).props("flat no-caps color=primary")

        # Контейнер для карточек
        cards_container = ui.column().classes("w-full")
        cards_ref.append(cards_container)

        # Первоначальный рендер карточек
        _render_cards(cards_container, on_add=_on_add)
