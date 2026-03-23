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
from config import Config


async def pick_folder() -> Optional[Path]:
    """Открывает нативный OS folder picker.

    Per D-03/D-04: app.native.main_window.create_file_dialog с FOLDER_DIALOG.
    Pitfall 1: всегда проверять `if result` перед использованием.
    RBST-01: в web mode (без pywebview) — graceful fallback с уведомлением.

    Returns:
        Path к выбранной папке или None если юрист отменил диалог или web mode.
    """
    try:
        import webview  # noqa: PLC0415 — local import guard for web mode
        result = await app.native.main_window.create_file_dialog(
            dialog_type=webview.FOLDER_DIALOG,
        )
        if not result:
            return None
        return Path(result[0])
    except (ImportError, AttributeError):
        # Web mode: pywebview недоступен или app.native не инициализирован
        ui.notify(
            "Выбор папки недоступен в веб-режиме. Используйте кнопку «Загрузить тестовые данные».",
            type="warning",
            timeout=5000,
        )
        return None


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
    # Pitfall 5: использовать get_running_loop() внутри async-функции
    loop = asyncio.get_running_loop()
    config = Config()
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
        loop.call_soon_threadsafe(
            ui_refs['count'].set_text, f"{current}/{total} файлов"
        )

        # Формируем label: "Стадия... — filename" или просто "Стадия..."
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
