"""Страница «Настройки» — macOS Preferences layout (левая навигация + правая панель).

Phase 11, Plan 02.
Три секции: AI-провайдер · Обработка · Telegram.
Всё сохраняется в ~/.yurteg/settings.json через load_settings / save_setting.
"""
from pathlib import Path

from nicegui import run, ui

from app.styles import TEXT_HEADING, TEXT_LABEL_SECTION, TEXT_SECONDARY, SECTION_DIVIDER_HEADER
from config import Config, load_settings, save_setting
from modules.anonymizer import ENTITY_TYPES
from services.telegram_sync import TelegramSync

# Текстовые метки навигации
_NAV_ITEMS = ["ИИ", "Обработка", "Уведомления"]

# Провайдеры
_PROVIDERS = {
    "ollama": "Локальный (Qwen)",
    "zai": "ZAI GLM-4.7",
    "openrouter": "OpenRouter",
}

# Провайдеры, требующие API-ключ
_CLOUD_PROVIDERS = {"zai", "openrouter"}


# ── Вспомогательная функция для строки настроек ───────────────────────────────

def _settings_row(label: str, description: str = "", *, control_fn=None) -> None:
    """Render a single settings row: label+description left, control right."""
    with ui.row().classes("w-full items-center justify-between py-3 border-b border-slate-100"):
        with ui.column().classes("gap-0.5 flex-1 min-w-0"):
            ui.label(label).classes("text-sm text-slate-900")
            if description:
                ui.label(description).classes("text-xs text-slate-400")
        if control_fn:
            control_fn()


def build() -> None:
    """Рендерит страницу настроек с левой навигацией и правой панелью."""

    settings = load_settings()
    active_section: list[str] = ["ИИ"]  # mutable container для захвата в closures
    nav_buttons: dict[str, ui.button] = {}

    with ui.row().classes("w-full flex-1 gap-0"):
        # --- Левая навигация ---
        with ui.column().classes(
            "w-52 self-stretch border-r border-slate-200 bg-white p-4 gap-1"
        ):
            ui.label("Настройки").classes(
                SECTION_DIVIDER_HEADER + " px-1 mb-2"
            )
            for section in _NAV_ITEMS:
                btn = ui.button(section).props("flat no-caps").classes(
                    "w-full text-left justify-start text-slate-600 bg-transparent px-3 py-2 rounded-lg transition-colors duration-150"
                )
                nav_buttons[section] = btn

        # --- Правая панель ---
        content = ui.column().classes("flex-1 p-8 gap-6 max-w-2xl")

    # --- Переключение секций ---

    def _switch(section: str) -> None:
        active_section[0] = section
        for name, btn in nav_buttons.items():
            if name == section:
                btn.classes(
                    remove="text-slate-600 bg-transparent hover:bg-slate-100",
                    add="text-indigo-700 bg-indigo-50 rounded-lg font-medium",
                )
            else:
                btn.classes(
                    remove="text-indigo-700 bg-indigo-50 font-medium",
                    add="text-slate-600 hover:bg-slate-100 bg-transparent",
                )
        if section == "ИИ":
            _render_ai(content, settings)
        elif section == "Обработка":
            _render_processing(content, settings)
        elif section == "Уведомления":
            _render_notifications(content, settings)

    # Привязываем клики
    for section in _NAV_ITEMS:
        nav_buttons[section].on_click(lambda s=section: _switch(s))

    # --- Секция AI ---

    def _render_ai(content_el, s) -> None:
        content_el.clear()
        with content_el:
            ui.label("ИИ-помощник").classes(TEXT_HEADING)
            ui.label("Провайдер для извлечения метаданных из документов").classes(TEXT_SECONDARY + " mb-4")

            # Row 1: Provider dropdown
            def _provider_control():
                sel = ui.select(
                    options=_PROVIDERS,
                    value=s.get("active_provider", "ollama"),
                ).props("dense outlined").classes("w-48")
                sel.on_value_change(lambda e: save_setting("active_provider", e.value))

            _settings_row("Провайдер", "Локальная модель работает офлайн", control_fn=_provider_control)

            # Row 2: Model status
            def _model_status():
                cfg = Config()
                model_path = Path.home() / ".yurteg" / cfg.llama_model_filename
                exists = model_path.exists()
                size_mb = f"{model_path.stat().st_size / 1024 / 1024:.0f} MB" if exists else ""
                badge_cls = "bg-green-100 text-green-700" if exists else "bg-amber-100 text-amber-700"
                badge_text = "Готова" if exists else "Не скачана"
                with ui.row().classes("items-center gap-2"):
                    if exists:
                        ui.label(f"{cfg.llama_model_filename} \u00b7 {size_mb}").classes("text-xs text-slate-400")
                    ui.label(badge_text).classes(f"text-xs px-2 py-0.5 rounded-full {badge_cls}")

            _settings_row("Статус модели", "", control_fn=_model_status)

            # Row 3: Thinking mode toggle
            def _thinking_control():
                sw = ui.switch(value=s.get("ai_disable_thinking", True)).props("dense")
                sw.on_value_change(lambda e: save_setting("ai_disable_thinking", e.value))

            _settings_row("Thinking mode", "Отключить для 5-7x ускорения", control_fn=_thinking_control)

            # Row 4: Check connection
            def _check_control():
                result_label = ui.label("").classes("text-xs")

                async def _check():
                    import httpx as _httpx
                    try:
                        async with _httpx.AsyncClient(timeout=3) as client:
                            resp = await client.get("http://localhost:8080/health")
                        if resp.status_code == 200:
                            result_label.set_text("\u2713 Работает")
                            result_label.classes(remove="text-red-500", add="text-green-600")
                        else:
                            result_label.set_text("\u2717 Недоступен")
                            result_label.classes(remove="text-green-600", add="text-red-500")
                    except Exception:
                        result_label.set_text("\u2717 Недоступен")
                        result_label.classes(remove="text-green-600", add="text-red-500")

                with ui.row().classes("items-center gap-2"):
                    ui.button("Проверить", on_click=_check).props("flat dense no-caps").classes("text-indigo-600 text-sm")
                    result_label  # noqa: B018 — side-effect: attaches to current context

            _settings_row("Соединение", "", control_fn=_check_control)

    # --- Секция Обработка ---

    def _render_processing(content_el, s) -> None:
        content_el.clear()
        with content_el:
            ui.label("Обработка").classes(TEXT_HEADING)
            ui.label("Параметры извлечения метаданных").classes(TEXT_SECONDARY + " mb-4")

            # Row 1: Anonymization toggle
            def _anon_control():
                sw = ui.switch(value=s.get("anonymize_for_cloud", True)).props("dense")
                sw.on_value_change(lambda e: save_setting("anonymize_for_cloud", e.value))

            _settings_row(
                "Анонимизация для облака",
                "Маскировать ФИО и телефоны при отправке в облачные провайдеры",
                control_fn=_anon_control,
            )

            # Row 2: Confidence threshold
            def _confidence_control():
                raw = s.get("confidence_low", 0.5)
                inp = ui.number(
                    value=int(raw * 100),
                    min=0, max=100, step=5,
                ).props("dense outlined suffix='%'").classes("w-24")
                inp.on_value_change(lambda e: save_setting("confidence_low", (e.value or 50) / 100))

            _settings_row(
                "Порог уверенности",
                "Поля с уверенностью ниже порога будут подсвечены",
                control_fn=_confidence_control,
            )

            # Row 3: Max workers
            def _workers_control():
                inp = ui.number(
                    value=s.get("max_workers", 5),
                    min=1, max=10, step=1,
                ).props("dense outlined").classes("w-24")
                inp.on_value_change(lambda e: save_setting("max_workers", int(e.value or 5)))

            _settings_row(
                "Параллельные потоки",
                "Количество одновременных AI-запросов",
                control_fn=_workers_control,
            )

    # --- Секция Уведомления ---

    def _render_notifications(content_el, s) -> None:
        content_el.clear()
        with content_el:
            ui.label("Уведомления").classes(TEXT_HEADING)
            ui.label("Telegram-бот для напоминаний о сроках").classes(TEXT_SECONDARY + " mb-4")

            # Row 1: Telegram binding
            def _telegram_control():
                srv_url = s.get("telegram_server_url", "")
                chat_id = s.get("telegram_chat_id", 0)
                is_bound = bool(chat_id)

                if is_bound:
                    with ui.row().classes("items-center gap-2"):
                        ui.label("Привязан").classes(
                            "text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700"
                        )
                        ui.button("Отвязать", on_click=lambda: (
                            save_setting("telegram_chat_id", ""),
                            ui.navigate.to("/settings"),
                        )).props("flat dense no-caps").classes("text-red-500 text-xs")
                else:
                    with ui.column().classes("gap-2"):
                        ui.label("Не привязан").classes(
                            "text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700"
                        )
                        with ui.row().classes("items-center gap-2"):
                            code_input = ui.input(placeholder="Код из Telegram").props("dense outlined").classes("w-32")

                            async def _bind():
                                code = code_input.value
                                if code and len(code) == 6:
                                    try:
                                        sync = TelegramSync(server_url=srv_url, chat_id=0)
                                        result = await run.io_bound(sync.bind, code)
                                        if result:
                                            save_setting("telegram_chat_id", result)
                                            ui.notify("Telegram привязан!", type="positive")
                                            ui.navigate.to("/settings")
                                        else:
                                            ui.notify("Неверный код или бот недоступен", type="negative")
                                    except Exception:
                                        ui.notify("Неверный код или бот недоступен", type="negative")

                            ui.button("Привязать", on_click=_bind).props("dense no-caps").classes(
                                "bg-indigo-600 text-white text-xs"
                            )
                        ui.label("Отправьте /start боту @YurTagBot \u2014 он пришлёт код").classes(
                            "text-xs text-slate-400"
                        )

            _settings_row("Telegram", "", control_fn=_telegram_control)

            # Row 2: Warning threshold
            def _threshold_control():
                inp = ui.number(
                    value=s.get("warning_days_threshold", 30),
                    min=1, max=90, step=1,
                ).props("dense outlined suffix='\u0434\u043d\u0435\u0439'").classes("w-28")
                inp.on_value_change(lambda e: save_setting("warning_days_threshold", int(e.value or 30)))

            _settings_row(
                "Порог напоминания",
                "За сколько дней до истечения предупреждать",
                control_fn=_threshold_control,
            )

    # Инициализация — открываем ИИ секцию (после определения всех render-функций)
    _switch("ИИ")
