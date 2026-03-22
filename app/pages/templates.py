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

import webview
from nicegui import app, run, ui

import modules.extractor as extractor
import services.review_service as review_service
from app.state import get_state
from config import Config
from modules.models import FileInfo
from services.client_manager import ClientManager


async def _pick_file() -> Optional[Path]:
    """Открывает нативный OS file picker для PDF/DOCX.

    Pitfall 5: всегда проверять `if result` перед использованием.
    """
    result = await app.native.main_window.create_file_dialog(
        dialog_type=webview.OPEN_DIALOG,
        file_types=("PDF файлы (*.pdf)", "Word документы (*.docx)"),
    )
    if not result:
        return None
    return Path(result[0])


def _render_cards(container: ui.column) -> None:
    """Рендерит карточки шаблонов в двухколоночной сетке."""
    state = get_state()
    db = ClientManager().get_db(state.current_client)
    templates = review_service.list_templates(db)

    container.clear()
    with container:
        if not templates:
            # Empty state
            with ui.column().classes("w-full items-center justify-center py-16"):
                ui.label("Нет шаблонов").classes("text-slate-400 text-lg")
                ui.label(
                    "Добавьте первый шаблон-эталон для ревью договоров"
                ).classes("text-slate-300 text-sm mt-1")
            return

        with ui.grid(columns=2).classes("w-full gap-4"):
            for tmpl in templates:
                _render_card(tmpl, container)


def _render_card(tmpl, cards_container: ui.column) -> None:
    """Рендерит одну карточку шаблона."""
    with ui.card().classes(
        "p-4 cursor-default hover:shadow-md transition-shadow transition-colors duration-150 hover:bg-slate-100"
    ):
        # Имя
        ui.label(tmpl.name).classes("font-semibold text-slate-900 text-sm")
        # Тип документа
        ui.label(tmpl.contract_type).classes("text-xs text-slate-500 mt-0.5")
        # Preview первых ~200 символов
        preview = (tmpl.content_text or "")[:200]
        ui.label(preview).classes(
            "text-xs text-slate-400 mt-2 line-clamp-3 overflow-hidden"
        )
        # Дата создания
        ui.label(tmpl.created_at or "").classes("text-xs text-slate-300 mt-2")
        # Кнопки действий
        with ui.row().classes("mt-3 gap-1"):
            ui.button(
                "Изменить",
                on_click=lambda t=tmpl: _open_edit_dialog(t, cards_container),
            ).props("flat no-caps dense color=primary").classes("text-xs")
            ui.button(
                "Удалить",
                on_click=lambda t=tmpl: _open_delete_dialog(t, cards_container),
            ).props("flat no-caps dense color=negative").classes("text-xs")


def _open_edit_dialog(tmpl, cards_container: ui.column) -> None:
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
                    ui.notify(f"Ошибка: {e}", type="negative")
                    return
                dlg.close()
                _render_cards(cards_container)
            finally:
                save_btn.enable()

        with ui.row().classes("justify-end gap-2 w-full"):
            ui.button("Отмена", on_click=dlg.close).props("flat no-caps color=grey")
            save_btn = ui.button("Сохранить", on_click=_confirm).props("no-caps color=primary")

    dlg.open()


def _open_delete_dialog(tmpl, cards_container: ui.column) -> None:
    """Диалог подтверждения удаления шаблона."""
    with ui.dialog() as dlg, ui.card().classes("p-6 min-w-[360px]"):
        ui.label("Удалить шаблон?").classes("text-lg font-semibold text-slate-900 mb-2")
        ui.label(f"«{tmpl.name}»").classes("text-slate-600 text-sm mb-4")

        async def _confirm_delete() -> None:
            state = get_state()
            db = ClientManager().get_db(state.current_client)
            try:
                await run.io_bound(review_service.delete_template, db, tmpl.id)
            except Exception as e:
                ui.notify(f"Ошибка: {e}", type="negative")
                return
            dlg.close()
            _render_cards(cards_container)

        with ui.row().classes("justify-end gap-2 w-full"):
            ui.button("Отмена", on_click=dlg.close).props("flat no-caps color=grey")
            ui.button(
                "Удалить", on_click=_confirm_delete
            ).props("flat no-caps color=negative")

    dlg.open()


async def _add_template_flow(cards_container: ui.column) -> None:
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
                    ui.notify(f"Ошибка чтения файла: {e}", type="negative")
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
                    ui.notify(f"Ошибка сохранения: {e}", type="negative")
                    return

                dlg.close()
                _render_cards(cards_container)
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
    with ui.column().classes("w-full p-8"):
        # Заголовок
        with ui.row().classes("w-full items-start justify-between mb-6"):
            with ui.column().classes("gap-0"):
                ui.label("Шаблоны").classes("text-2xl font-semibold text-slate-900")
                ui.label(
                    "Эталонные документы для ревью договоров"
                ).classes("text-sm text-slate-400 mb-4")

            cards_ref: list[ui.column] = []

            ui.button(
                "+ Добавить шаблон",
                on_click=lambda: _add_template_flow(cards_ref[0]),
            ).props("flat no-caps color=primary")

        # Контейнер для карточек
        cards_container = ui.column().classes("w-full")
        cards_ref.append(cards_container)

        # Первоначальный рендер карточек
        _render_cards(cards_container)
