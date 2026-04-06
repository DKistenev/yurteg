"""Pipeline trigger component — folder picker + async pipeline runner.

Per D-03: Нативный OS folder picker через app.native.main_window.create_file_dialog.
Per D-16: Pipeline запускается через run.io_bound (не блокирует event loop).
Per D-09: on_progress callback через loop.call_soon_threadsafe (thread-safe).
Per D-10: Toast-уведомление после завершения.
Per D-12: Прогресс-секция скрывается после завершения.
Per D-13/D-14: Ошибки рендерятся в expandable log.
"""
import asyncio
import time
from pathlib import Path
from typing import Optional

from nicegui import app, run, ui

import services.pipeline_service as pipeline_service
from app.state import AppState
from config import load_runtime_config
from services.client_manager import ClientManager


async def pick_folder() -> Optional[Path]:
    """Открывает нативный диалог выбора папки или файлов.

    Shows a choice menu first: folder or files.
    - Folder: native FOLDER_DIALOG via pywebview
    - Files: native OPEN_DIALOG for PDF/DOCX, copies to temp dir

    Returns:
        Path к папке с документами или None.
    """
    import logging as _log
    import shutil
    import tempfile
    _logger = _log.getLogger("pick_folder")

    # Show choice menu
    mode_future: asyncio.Future = asyncio.get_event_loop().create_future()

    with ui.dialog() as mode_dlg, \
         ui.card().classes("p-0 overflow-hidden rounded-xl shadow-xl").style("width: 360px;"):
        with ui.element("div").classes("px-6 pt-5 pb-2"):
            ui.html('<span style="font-size:1.1rem;font-weight:600;color:#1e293b;">Загрузить документы</span>')
            ui.html('<span style="font-size:0.8rem;color:#94a3b8;margin-top:4px;">Выберите способ загрузки</span>')

        with ui.column().classes("px-6 py-4 gap-2 w-full"):
            ui.button(
                "Выбрать папку", icon="folder_open",
                on_click=lambda: _pick("folder"),
            ).props("no-caps outline").classes(
                "w-full text-left text-sm"
            ).style("justify-content: flex-start;")
            ui.button(
                "Выбрать файлы (PDF, DOCX)", icon="description",
                on_click=lambda: _pick("files"),
            ).props("no-caps outline").classes(
                "w-full text-left text-sm"
            ).style("justify-content: flex-start;")

        with ui.row().classes("px-6 pb-4"):
            ui.button("Отмена", on_click=lambda: _pick(None)).props("flat no-caps").classes("text-slate-400 text-sm")

    def _pick(mode):
        if not mode_future.done():
            mode_future.set_result(mode)
        mode_dlg.close()

    mode_dlg.open()
    mode = await mode_future

    if not mode:
        return None

    try:
        import webview  # noqa: PLC0415
    except ImportError:
        ui.notify("Нативные диалоги недоступны в веб-режиме.", type="warning")
        return None

    if mode == "folder":
        dialog_type = webview.FileDialog.FOLDER if hasattr(webview, 'FileDialog') else webview.FOLDER_DIALOG
    else:
        dialog_type = webview.FileDialog.OPEN if hasattr(webview, 'FileDialog') else webview.OPEN_DIALOG

    try:
        _logger.info(">>> Opening native dialog (mode=%s, type=%s)...", mode, dialog_type)
        kwargs = {
            "dialog_type": dialog_type,
            "directory": str(Path.home()),
        }
        if mode == "files":
            kwargs["allow_multiple"] = True
            kwargs["file_types"] = ("Документы (*.pdf;*.docx;*.doc)",)

        result = await asyncio.wait_for(
            app.native.main_window.create_file_dialog(**kwargs),
            timeout=120,
        )
        _logger.info(">>> Dialog result: %s", result)
    except asyncio.TimeoutError:
        _logger.warning("Dialog timed out")
        return None
    except Exception as exc:
        _logger.warning("Dialog error: %s", exc)
        return None

    if not result:
        return None

    if mode == "folder":
        return Path(result[0])

    # Files mode: copy selected files to a temp directory for the pipeline
    tmp_dir = Path(tempfile.mkdtemp(prefix="yurteg_upload_"))
    for file_path in result:
        src = Path(file_path)
        if src.suffix.lower() in (".pdf", ".docx", ".doc") and src.is_file():
            shutil.copy2(src, tmp_dir / src.name)
            _logger.info("Copied %s → %s", src.name, tmp_dir)
    if not any(tmp_dir.iterdir()):
        shutil.rmtree(tmp_dir, ignore_errors=True)
        ui.notify("Не найдено PDF или DOCX файлов.", type="warning")
        return None
    return tmp_dir


async def start_pipeline(
    source_dir: Path,
    state: AppState,
    ui_refs: dict,
) -> dict:
    """Запускает pipeline обработки документов асинхронно.

    Per D-16: run.io_bound для запуска blocking pipeline в thread pool.
    Per D-09: on_progress через loop.call_soon_threadsafe (thread-safe).
    Per D-10: Toast-уведомление по завершении.
    Per D-12: Прогресс-секция скрывается после завершения.

    Args:
        source_dir: путь к папке с документами.
        state: AppState — для флага processing.
        ui_refs: dict с ключами:
            'section'     — ui.column (прогресс-секция)
            'bar'         — ui.linear_progress
            'count'       — ui.label (счётчик файлов)
            'file_label'  — ui.label (имя текущего файла)
            'error_col'   — ui.column (лог ошибок)
            'upload_btn'  — ui.button (кнопка загрузки)

    Returns:
        stats dict от pipeline_service.process_archive
        (total, done, errors, skipped, output_dir, report_path)
    """
    # Pre-flight: check if AI provider is reachable (ERRES-02)
    config = load_runtime_config()
    if config.active_provider == "ollama":
        try:
            import httpx as _httpx
            async with _httpx.AsyncClient(timeout=3) as _client:
                _resp = await _client.get(f"http://localhost:{config.llama_server_port}/health")
                if _resp.status_code != 200:
                    raise ConnectionError("llama-server unhealthy")
        except Exception:
            ui.notify(
                "AI-модель недоступна. Переключитесь на облачный провайдер в Настройках → Модель ИИ.",
                type="warning",
                timeout=10000,
            )

    # Pitfall 5: использовать get_running_loop() внутри async-функции
    loop = asyncio.get_running_loop()
    error_entries: list[tuple[str, str]] = []

    # --- Старт: показать секцию, задизейблить кнопку ---
    state.processing = True
    ui_refs['upload_btn'].set_enabled(False)
    ui_refs['section'].set_visibility(True)
    ui_refs['bar'].set_value(0)
    ui_refs['count'].set_text("Подготовка...")
    ui_refs['file_label'].set_text("")

    # Debounce: не обновлять UI чаще 500ms (Claude's Discretion, CONTEXT.md)
    last_update: list[float] = [0.0]
    # Текущая стадия pipeline — отображается в file_label
    current_stage: list[str] = [""]

    # Маппинг подстрок из controller.py → человекочитаемые стадии
    _STAGE_MARKERS = [
        ("Сканирование", "Читаем документы..."),
        ("Найдено", "Читаем документы..."),
        ("Пропущено", "Читаем документы..."),
        ("Режим переобработки", "Читаем документы..."),
        ("AI-анализ", "Извлекаем метаданные..."),
        ("Обработка:", "Извлекаем метаданные..."),
        ("Перекрёстная валидация", "Раскладываем по папкам..."),
        ("Генерация Excel", "Раскладываем по папкам..."),
        ("Готово!", "Готово!"),
    ]

    def _resolve_stage(msg: str) -> str:
        """Определяет стадию pipeline по тексту сообщения из controller."""
        for marker, stage in _STAGE_MARKERS:
            if marker in msg:
                return stage
        return current_stage[0]  # сохраняем предыдущую стадию

    def on_progress(current: int, total: int, message: str) -> None:
        """Callback из thread pool — обновляет прогресс-бар через call_soon_threadsafe.

        Pitfall 2: on_progress вызывается из ThreadPoolExecutor,
        нельзя трогать UI-объекты напрямую.
        """
        now = time.monotonic()
        # Всегда обновляем стадию, даже если debounce ещё не прошёл
        stage = _resolve_stage(message)
        if stage:
            current_stage[0] = stage

        if now - last_update[0] < 0.5:
            return
        last_update[0] = now

        val = current / total if total > 0 else 0
        loop.call_soon_threadsafe(ui_refs['bar'].set_value, val)
        if total > 0:
            loop.call_soon_threadsafe(
                ui_refs['count'].set_text, f"{current}/{total} файлов"
            )

        # Формируем label: "Стадия... — filename" или просто "Стадия..."
        # Скрываем системные пути (temp dirs, output dirs)
        if "/" in message and ("папка" in message.lower() or "/var/" in message or "/tmp/" in message):
            return  # не показывать raw пути пользователю

        # Извлекаем имя файла из сообщений вида "Обработка: filename.pdf"
        filename = ""
        if "Обработка:" in message:
            filename = message.split("Обработка:", 1)[1].strip()

        if current_stage[0] and filename:
            display = f"{current_stage[0]} \u2014 {filename}"
        elif current_stage[0]:
            display = current_stage[0]
        else:
            display = message

        loop.call_soon_threadsafe(ui_refs['file_label'].set_text, display)

    def on_file_done(result) -> None:
        """Callback после обработки каждого файла — собирает ошибки.

        Таблица реестра обновляется только один раз после завершения
        (Anti-pattern: flood WebSocket при обновлении на каждый файл).
        """
        if result.status == "error":
            error_entries.append(
                (result.file_info.filename, result.error_message)
            )

    # --- Запуск pipeline в thread pool ---
    stats = await run.io_bound(
        pipeline_service.process_archive,
        source_dir,
        config,
        on_progress=on_progress,
        on_file_done=on_file_done,
        db_path_override=ClientManager().get_db_path(state.current_client),
    )

    # --- Завершение: toast + лог ошибок ---
    done = stats.get("done", 0)
    errors = stats.get("errors", 0)
    msg = f"Обработано {done} документов"
    if errors:
        msg += f" ({errors} ошибок)"
    ui.notify(msg, type="positive" if not errors else "warning")

    # Рендер лога ошибок (D-13, D-14)
    _render_error_log(ui_refs['error_col'], error_entries)

    # Скрыть прогресс-секцию (D-12, specifics):
    # сразу если нет ошибок, через 10с если есть
    def _hide_section() -> None:
        ui_refs['section'].set_visibility(False)

    if not error_entries:
        _hide_section()
    else:
        ui.timer(10, _hide_section, once=True)

    # Восстановить состояние кнопки
    state.processing = False
    ui_refs['upload_btn'].set_enabled(True)

    return stats


def _render_error_log(
    error_col,
    error_entries: list[tuple[str, str]],
) -> None:
    """Рендерит список ошибок в expandable items под прогресс-баром.

    Per D-13: Ошибочные файлы отмечены ✗ красным.
    Per D-14: Клик по ошибке показывает причину (expansion).
    """
    error_col.clear()
    with error_col:
        for filename, message in error_entries:
            with ui.expansion(f"✗ {filename}").classes("text-red-600 text-sm"):
                ui.label(message).classes("text-xs text-slate-500 pl-4")
