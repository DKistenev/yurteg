"""Splash screen — первый запуск ЮрТэг.

Показывается только при first_run_completed != true в ~/.yurteg/settings.json.
Содержит:
- Логотип и приветствие
- 3 capability bullets
- Прогресс-бар загрузки модели (thread-safe через call_soon_threadsafe)
- 2-шаговый wizard: Приветствие → Telegram

Per D-02, D-03, D-04, D-06, D-07, D-08, D-09: UI-SPEC Component 1.
"""
import asyncio
import logging

from nicegui import run, ui

from app.styles import TEXT_HEADING_XL, BTN_PRIMARY, BTN_FLAT
from config import Config, save_setting
from modules.postprocessor import get_grammar_path
from services.llama_server import LlamaServerManager

logger = logging.getLogger(__name__)

# Модель ~940 МБ
_MODEL_SIZE_MB = 940


def render_splash() -> None:
    """Рендерит full-page splash screen с wizard и прогрессом загрузки модели.

    Вызывается из root() при first_run_completed == False.
    Делает early return — header и sub_pages не рендерятся.
    """
    # Outer wrapper — full screen, white, centered
    with ui.column().classes("min-h-screen bg-white flex items-center justify-center"):
        # Inner content card
        with ui.column().classes("max-w-lg w-full mx-auto py-16 px-8 gap-6"):

            # Logo
            ui.label("ЮрТэг").classes("text-3xl font-semibold text-slate-900")

            # Welcome heading
            ui.label("Добро пожаловать!").classes(TEXT_HEADING_XL + " mt-2")

            # Capability bullets section
            with ui.column().classes("bg-slate-50 rounded-lg p-4 gap-2"):
                _bullets = [
                    "Загрузите папку с документами → получите готовый реестр",
                    "Файлы автоматически разложатся по папкам",
                    "Напомним, когда договор истекает",
                ]
                for text in _bullets:
                    with ui.row().classes("gap-2 items-start"):
                        ui.label("·").classes("text-slate-400 text-sm shrink-0")
                        ui.label(text).classes("text-sm text-slate-600 font-normal")

            # Progress bar section
            with ui.column().classes("gap-1 w-full"):
                progress_label = ui.label(
                    f"Загрузка ИИ-помощника (0/{_MODEL_SIZE_MB} МБ)"
                ).classes("text-sm text-slate-500 font-normal")
                progress_bar = (
                    ui.linear_progress(value=0)
                    .props("color=indigo track-color=grey-3")
                    .classes("w-full h-1.5 rounded-full")
                )

            # Wizard area (step 1 initially)
            wizard_area = ui.column().classes("w-full gap-4")

            def _finish() -> None:
                """Завершает onboarding: сохраняет флаг, переходит в реестр."""
                save_setting("first_run_completed", True)
                ui.navigate.to("/")

            def _save_and_finish(token_input: ui.input) -> None:
                """Сохраняет Telegram-токен если введён, завершает onboarding."""
                if token_input.value and token_input.value.strip():
                    save_setting("bot_token", token_input.value.strip())
                _finish()

            def _show_step_2() -> None:
                """Переходит на шаг 2 wizard: Telegram."""
                wizard_area.clear()
                with wizard_area:
                    # Heading
                    ui.label("Уведомления").classes(TEXT_HEADING_XL)
                    # Body
                    ui.label(
                        "Получайте уведомления об истекающих документах прямо в мессенджер."
                    ).classes("text-sm text-slate-500 font-normal")
                    # Token input
                    token_input = ui.input(
                        placeholder="110201543:AAHdqTcvCH1vGWJxfSeofSs0K"
                    ).props("outlined dense").classes("w-full")
                    # Navigation row
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.button("Пропустить").props("flat no-caps").classes(
                            BTN_FLAT
                        ).on_click(lambda: _finish())
                        save_btn = ui.button("Сохранить и начать").props("no-caps").classes(
                            BTN_PRIMARY
                        )

                        def _on_save_click(btn=save_btn, ti=token_input) -> None:
                            btn.disable()
                            try:
                                _save_and_finish(ti)
                            finally:
                                btn.enable()

                        save_btn.on_click(_on_save_click)

            # Render step 1 wizard content (navigation only — bullets above)
            with wizard_area:
                with ui.row().classes("w-full justify-between items-center"):
                    ui.button("Пропустить").props("flat no-caps").classes(
                        BTN_FLAT
                    ).on_click(lambda: _finish())
                    ui.button("Далее: Уведомления \u2192").props("no-caps").classes(
                        BTN_PRIMARY
                    ).on_click(_show_step_2)

            # Start model download asynchronously
            async def _run_model_download() -> None:
                """Скачивает модель и запускает llama-server в фоне.

                Per D-11: run.io_bound для blocking operations.
                Per D-09: loop.call_soon_threadsafe для thread-safe UI updates.
                Pitfall 1 guard: всегда ставим set_value(1.0) после ensure_model —
                  модель может быть уже скачана (early return без вызова on_progress).
                """
                loop = asyncio.get_running_loop()
                config = Config()
                manager = LlamaServerManager(port=config.llama_server_port)

                def on_progress(fraction: float, msg: str) -> None:
                    """Callback из thread pool — обновляет UI через event loop."""
                    downloaded_mb = int(fraction * _MODEL_SIZE_MB)
                    label_text = f"Загрузка ИИ-помощника ({downloaded_mb}/{_MODEL_SIZE_MB} МБ)"
                    loop.call_soon_threadsafe(progress_bar.set_value, fraction)
                    loop.call_soon_threadsafe(progress_label.set_text, label_text)

                try:
                    await run.io_bound(manager.ensure_model, on_progress)
                except Exception as exc:
                    logger.warning("ensure_model завершился с ошибкой: %s", exc)
                    ui.notify(
                        "Не удалось загрузить ИИ-помощника. Проверьте интернет-соединение "
                        "и попробуйте снова.",
                        type="negative",
                        timeout=10000,
                    )

                # Pitfall 1 guard: гарантируем 1.0 даже если ensure_model не вызвал on_progress
                loop.call_soon_threadsafe(progress_bar.set_value, 1.0)
                loop.call_soon_threadsafe(
                    progress_label.set_text,
                    f"ИИ-помощник готов ({_MODEL_SIZE_MB}/{_MODEL_SIZE_MB} МБ)",
                )

                try:
                    await run.io_bound(manager.ensure_server_binary)
                    await run.io_bound(manager.start, get_grammar_path())
                    logger.info("llama-server запущен через splash screen")
                except Exception as exc:
                    logger.warning("llama-server не запустился из splash: %s", exc)

            # Запускаем загрузку через таймер (once=True — один вызов)
            ui.timer(0, _run_model_download, once=True)
