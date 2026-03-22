"""Страница «Настройки» — macOS Preferences layout (левая навигация + правая панель).

Phase 11, Plan 02.
Три секции: AI-провайдер · Обработка · Telegram.
Всё сохраняется в ~/.yurteg/settings.json через load_settings / save_setting.
"""
from nicegui import run, ui

from config import load_settings, save_setting
from modules.anonymizer import ENTITY_TYPES
from services.telegram_sync import TelegramSync

# Текстовые метки навигации
_NAV_ITEMS = ["AI", "Обработка", "Telegram"]

# Провайдеры
_PROVIDERS = {
    "ollama": "Локальный (Qwen)",
    "zai": "ZAI GLM-4.7",
    "openrouter": "OpenRouter",
}

# Провайдеры, требующие API-ключ
_CLOUD_PROVIDERS = {"zai", "openrouter"}


def build() -> None:
    """Рендерит страницу настроек с левой навигацией и правой панелью."""

    settings = load_settings()
    active_section: list[str] = ["AI"]  # mutable container для захвата в closures
    nav_buttons: dict[str, ui.button] = {}

    with ui.row().classes("w-full min-h-screen gap-0"):
        # --- Левая навигация ---
        with ui.column().classes(
            "w-48 min-h-screen border-r border-slate-200 bg-slate-50 p-3 gap-1"
        ):
            ui.label("Настройки").classes(
                "text-xs font-semibold text-slate-400 uppercase tracking-wide px-3 py-2"
            )
            for section in _NAV_ITEMS:
                btn = ui.button(section).props("flat no-caps").classes(
                    "w-full text-left justify-start text-slate-600 bg-transparent px-3 py-2 rounded-lg transition-colors duration-150 hover:bg-slate-50"
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
                    remove="text-slate-600 bg-transparent",
                    add="text-slate-900 bg-white shadow-sm rounded-lg",
                )
            else:
                btn.classes(
                    remove="text-slate-900 bg-white shadow-sm rounded-lg",
                    add="text-slate-600 bg-transparent",
                )
        content.clear()
        with content:
            if section == "AI":
                _render_ai_section()
            elif section == "Обработка":
                _render_processing_section()
            elif section == "Telegram":
                _render_telegram_section()

    # Привязываем клики
    for section in _NAV_ITEMS:
        nav_buttons[section].on_click(lambda s=section: _switch(s))

    # Инициализация — открываем AI секцию
    _switch("AI")

    # --- Секция AI ---

    def _render_ai_section() -> None:
        s = load_settings()
        current_provider = s.get("active_provider", "ollama")

        ui.label("AI-провайдер").classes("text-lg font-medium text-slate-900")
        ui.label(
            "Выберите модель для извлечения метаданных из документов."
        ).classes("text-sm text-slate-500")

        # API key row — показываем только для облачных провайдеров
        api_key_row = ui.row().classes("w-full items-center gap-3")

        def _toggle_api_key(provider: str) -> None:
            api_key_row.clear()
            if provider in _CLOUD_PROVIDERS:
                key_val = load_settings().get(f"api_key_{provider}", "")
                with api_key_row:
                    inp = (
                        ui.input(
                            label=f"API-ключ ({_PROVIDERS.get(provider, provider)})",
                            value=key_val,
                            password=True,
                            password_toggle_button=True,
                        )
                        .classes("w-full")
                    )
                    inp.on(
                        "blur",
                        lambda e, p=provider: save_setting(f"api_key_{p}", e.sender.value),
                    )

        def _on_provider_change(e) -> None:
            save_setting("active_provider", e.value)
            _toggle_api_key(e.value)

        ui.radio(
            options=_PROVIDERS,
            value=current_provider,
            on_change=_on_provider_change,
        ).classes("mt-2")

        # Инициализируем видимость API-ключа
        _toggle_api_key(current_provider)

    # --- Секция Обработка ---

    def _render_processing_section() -> None:
        s = load_settings()
        all_keys = set(ENTITY_TYPES.keys())
        saved_types = s.get("anonymize_types")
        current_types: set[str] = set(saved_types) if saved_types is not None else all_keys

        ui.label("Анонимизация").classes("text-lg font-medium text-slate-900")
        ui.label(
            "Какие типы персональных данных маскировать при отправке в облачный AI:"
        ).classes("text-sm text-slate-500 mb-2")

        def _on_checkbox_change(key: str, checked: bool) -> None:
            if checked:
                current_types.add(key)
            else:
                current_types.discard(key)
            save_setting("anonymize_types", list(current_types))

        for key, label in ENTITY_TYPES.items():
            ui.checkbox(
                text=label,
                value=(key in current_types),
                on_change=lambda e, k=key: _on_checkbox_change(k, e.value),
            ).classes("text-sm text-slate-700")

        ui.separator().classes("my-4")

        ui.label("Предупреждения").classes("text-base font-medium text-slate-900 mt-4")
        warning_days = s.get("warning_days", 30)
        inp = ui.number(
            label="За сколько дней предупреждать об истечении",
            value=warning_days,
            min=1,
            max=365,
        ).classes("w-64")
        inp.on(
            "blur",
            lambda e: save_setting("warning_days", int(e.sender.value or 30)),
        )

    # --- Секция Telegram ---

    def _render_telegram_section() -> None:
        s = load_settings()

        ui.label("Telegram-бот").classes("text-lg font-medium text-slate-900")
        ui.label(
            "Подключите бота для получения уведомлений о дедлайнах и отправки документов через Telegram."
        ).classes("text-sm text-slate-500")

        url_inp = (
            ui.input(
                label="URL сервера бота",
                value=s.get("telegram_server_url", ""),
                placeholder="https://yurteg-bot.railway.app",
            )
            .classes("w-full")
        )
        url_inp.on(
            "blur",
            lambda e: save_setting("telegram_server_url", e.sender.value.strip()),
        )

        token_inp = (
            ui.input(
                label="Токен бота",
                value=s.get("telegram_bot_token", ""),
                password=True,
                password_toggle_button=True,
            )
            .classes("w-full")
        )
        token_inp.on(
            "blur",
            lambda e: save_setting("telegram_bot_token", e.sender.value.strip()),
        )

        with ui.row().classes("items-center gap-3 mt-2"):
            status_label = ui.label("● Не подключён").classes("text-sm text-red-500")

            async def _check_telegram() -> None:
                srv_url = load_settings().get("telegram_server_url", "").strip()
                tg = TelegramSync(server_url=srv_url, chat_id=0)
                ok = await run.io_bound(tg.check_connection)
                if ok:
                    status_label.set_text("● Подключён")
                    status_label.classes(remove="text-red-500", add="text-green-600")
                else:
                    status_label.set_text("● Не подключён")
                    status_label.classes(remove="text-green-600", add="text-red-500")

            ui.button(
                "Проверить подключение", on_click=_check_telegram
            ).props("flat no-caps size=sm").classes("text-slate-600")
