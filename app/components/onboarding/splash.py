"""Splash screen — первый запуск ЮрТэг.

Показывается только при first_run_completed != true в ~/.yurteg/settings.json.
Содержит:
- Full-screen тёмный hero (slate-900) с IBM Plex Sans крупной типографикой
- 3 capability bullets
- Прогресс-бар загрузки модели (thread-safe через call_soon_threadsafe)
- 2-шаговый wizard: Приветствие → Telegram

Per D-02, D-03, D-04, D-06, D-07, D-08, D-09: UI-SPEC Component 1.
v0.7: hero-zone structural wrapper, TEXT_HERO, stagger .hero-enter
"""
import asyncio
import logging

from nicegui import run, ui

from app.styles import TEXT_HERO, TEXT_HERO_SUB, TEXT_EYEBROW, BTN_ACCENT_FILLED
from config import load_runtime_config, save_setting
from services.llama_server import LlamaServerManager

logger = logging.getLogger(__name__)

# Модель ~940 МБ
_MODEL_SIZE_MB = 940


def render_splash() -> None:
    """Рендерит full-page splash screen с wizard и прогрессом загрузки модели.

    Вызывается из root() при first_run_completed == False.
    Делает early return — header и sub_pages не рендерятся.
    """
    # Outer wrapper — full screen, dark hero-zone
    with ui.element('div').classes('hero-zone').style(
        'min-height: 100vh; background: var(--yt-color-hero-bg); '
        'display: flex; align-items: center; justify-content: center;'
    ):
        # Inner content column
        with ui.column().classes('max-w-xl w-full mx-auto px-8 gap-8'):

            # Eyebrow — hero-enter 1
            with ui.element('p').classes('hero-enter ' + TEXT_EYEBROW).style('margin: 0'):
                ui.html('ЮрТэг')

            # Headline — hero-enter 2
            with ui.element('h1').classes('hero-enter ' + TEXT_HERO).style(
                'font-size: var(--yt-text-hero); margin: 0'
            ):
                ui.html('Ваш архив договоров — под контролем')

            # Subtext — hero-enter 3
            with ui.element('p').classes('hero-enter ' + TEXT_HERO_SUB).style('margin: 0'):
                ui.html('Загрузите папку → готовый реестр за 20 минут')

            # Feature carousel — hero-enter 4 (auto-advances every 5s)
            _slides = [
                {
                    'icon': '\U0001F4C1',
                    'title': 'Загрузите папку — получите реестр',
                    'desc': 'Выберите папку с PDF и DOCX — через 20 минут '
                            'у вас готовый реестр с метаданными',
                },
                {
                    'icon': '\u2728',
                    'title': 'AI извлекает метаданные автоматически',
                    'desc': 'Тип договора, контрагент, даты, суммы — без ручного ввода',
                },
                {
                    'icon': '\u23F0',
                    'title': 'Следите за сроками договоров',
                    'desc': 'Уведомления об истекающих договорах — '
                            'никаких пропущенных дедлайнов',
                },
                {
                    'icon': '\u2713',
                    'title': 'Проверяйте договоры по шаблону',
                    'desc': 'Загрузите эталон — система покажет все отступления',
                },
                {
                    'icon': '\U0001F4AC',
                    'title': 'Telegram напомнит о дедлайнах',
                    'desc': 'Бот @YurTagBot присылает ежедневную сводку '
                            'прямо в мессенджер',
                },
            ]
            _carousel_idx = {'current': 0}

            carousel_container = ui.column().classes(
                'hero-enter w-full items-center gap-3'
            ).style('min-height: 120px; transition: opacity 0.3s')

            def _render_slide(idx: int) -> None:
                """Render a single carousel slide inside the container."""
                slide = _slides[idx]
                carousel_container.clear()
                with carousel_container:
                    ui.label(slide['icon']).classes('text-4xl').style(
                        'line-height: 1; user-select: none'
                    )
                    ui.label(slide['title']).classes(
                        'text-lg font-semibold text-white text-center'
                    )
                    ui.label(slide['desc']).classes(
                        'text-sm text-slate-300 text-center'
                    ).style('max-width: 360px')
                    # Dot indicators
                    with ui.row().classes('gap-2 justify-center'):
                        for i in range(len(_slides)):
                            dot_color = 'bg-indigo-400' if i == idx else 'bg-slate-600'
                            ui.element('span').classes(
                                f'inline-block w-2 h-2 rounded-full {dot_color}'
                            )

            def _next_slide() -> None:
                """Advance carousel to the next slide."""
                _carousel_idx['current'] = (
                    (_carousel_idx['current'] + 1) % len(_slides)
                )
                _render_slide(_carousel_idx['current'])

            # Initial slide
            _render_slide(0)
            # Auto-advance every 5 seconds
            ui.timer(5.0, _next_slide)

            # Progress section — hero-enter 5
            with ui.column().classes('gap-2 w-full hero-enter'):
                progress_label = ui.label(
                    f'Загрузка ИИ-помощника (0/{_MODEL_SIZE_MB} МБ)'
                ).classes('text-slate-400 text-sm font-normal')
                progress_bar = (
                    ui.linear_progress(value=0)
                    .props('color=indigo track-color=grey-8')
                    .classes('w-full h-1.5 rounded-full')
                )

            # Wizard area (step 1 initially)
            wizard_area = ui.column().classes('w-full gap-4')

            def _finish() -> None:
                """Завершает onboarding: сохраняет флаг, переходит в реестр."""
                save_setting('first_run_completed', True)
                ui.navigate.to('/')

            def _save_and_finish() -> None:
                """Завершает onboarding без сохранения неиспользуемых токенов."""
                _finish()

            def _show_step_2() -> None:
                """Переходит на шаг 2 wizard: Telegram."""
                wizard_area.clear()
                with wizard_area:
                    with ui.element('h2').classes('text-xl font-semibold text-white').style(
                        'margin: 0'
                    ):
                        ui.html('Уведомления')
                    with ui.element('p').classes('text-slate-300 text-sm font-normal').style(
                        'margin: 0'
                    ):
                        ui.html(
                            'Получайте уведомления об истекающих документах прямо в мессенджер.'
                        )
                    ui.label(
                        'Уведомления через Telegram появятся позже. Сейчас можно просто завершить запуск.'
                    ).classes('text-slate-300 text-sm')
                    with ui.row().classes('w-full justify-between items-center'):
                        ui.button('Пропустить').props('flat no-caps').classes(
                            'text-slate-400 text-sm hover:text-slate-200'
                        ).on_click(lambda: _finish())
                        save_btn = ui.button('Сохранить и начать').props('no-caps').classes(
                            BTN_ACCENT_FILLED
                        )

                        def _on_save_click(btn=save_btn) -> None:
                            btn.disable()
                            try:
                                _save_and_finish()
                            finally:
                                btn.enable()

                        save_btn.on_click(_on_save_click)

            # Render step 1 wizard content
            with wizard_area:
                with ui.row().classes('w-full justify-between items-center'):
                    ui.button('Пропустить').props('flat no-caps').classes(
                        'text-slate-400 text-sm hover:text-slate-200'
                    ).on_click(lambda: _finish())
                    ui.button('Далее: Уведомления \u2192').props('no-caps').classes(
                        BTN_ACCENT_FILLED
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
                config = load_runtime_config()
                manager = LlamaServerManager(port=config.llama_server_port)

                def on_progress(fraction: float, msg: str) -> None:
                    """Callback из thread pool — обновляет UI через event loop."""
                    downloaded_mb = int(fraction * _MODEL_SIZE_MB)
                    label_text = f'Загрузка ИИ-помощника ({downloaded_mb}/{_MODEL_SIZE_MB} МБ)'
                    loop.call_soon_threadsafe(progress_bar.set_value, fraction)
                    loop.call_soon_threadsafe(progress_label.set_text, label_text)

                # --- Pre-download safety checks (DUX-03, DUX-04) ---
                runtime_ready = await run.io_bound(manager.has_local_runtime_assets)
                if not runtime_ready:
                    has_internet = await run.io_bound(check_internet)
                    if not has_internet:
                        loop.call_soon_threadsafe(
                            progress_label.set_text,
                            'Нет подключения к интернету',
                        )
                        loop.call_soon_threadsafe(progress_bar.set_value, 0)
                        ui.notify(
                            'Подключитесь к интернету для первой настройки — '
                            'нужно скачать ИИ-модель (~1.5 ГБ)',
                            type='warning',
                            timeout=0,
                        )
                        return

                    disk_ok, free_gb = await run.io_bound(check_disk_space, YURTEG_DIR)
                    if not disk_ok:
                        loop.call_soon_threadsafe(
                            progress_label.set_text,
                            f'Недостаточно места на диске ({free_gb:.1f} ГБ свободно)',
                        )
                        loop.call_soon_threadsafe(progress_bar.set_value, 0)
                        ui.notify(
                            f'Для работы нужно ~{REQUIRED_SPACE_GB} ГБ свободного места. '
                            f'Сейчас доступно {free_gb:.1f} ГБ. Освободите место и перезапустите.',
                            type='warning',
                            timeout=0,
                        )
                        return
                try:
                    await run.io_bound(manager.ensure_model, on_progress)
                    await run.io_bound(manager.ensure_server_binary)
                    await run.io_bound(manager.start)
                    logger.info('llama-server запущен через splash screen')
                except Exception as exc:
                    logger.warning('llama-server не запустился из splash: %s', exc)
                    ui.notify(
                        'Не удалось подготовить ИИ-помощника. Проверьте модель или интернет-соединение.',
                        type='negative',
                        timeout=10000,
                    )
                    loop.call_soon_threadsafe(
                        progress_label.set_text,
                        'ИИ-помощник недоступен — продолжить можно, но локальная модель не готова',
                    )
                    return

                loop.call_soon_threadsafe(progress_bar.set_value, 1.0)
                loop.call_soon_threadsafe(
                    progress_label.set_text,
                    f'ИИ-помощник готов ({_MODEL_SIZE_MB}/{_MODEL_SIZE_MB} МБ)',
                )

            # Запускаем загрузку через таймер (once=True — один вызов)
            ui.timer(0, _run_model_download, once=True)
