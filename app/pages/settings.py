"""Страница «Настройки» — macOS Preferences layout (левая навигация + правая панель).

Phase 11, Plan 02.
Три секции: AI-провайдер · Обработка · Telegram.
Всё сохраняется в ~/.yurteg/settings.json через load_settings / save_setting.
"""
from nicegui import run, ui

from app.styles import TEXT_HEADING, TEXT_LABEL_SECTION, TEXT_SECONDARY, SECTION_DIVIDER_HEADER
from config import load_settings, save_setting
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
        content.clear()
        with content:
            if section == "ИИ":
                _render_ai_section()
            elif section == "Обработка":
                _render_processing_section()
            elif section == "Уведомления":
                _render_telegram_section()

    # Привязываем клики
    for section in _NAV_ITEMS:
        nav_buttons[section].on_click(lambda s=section: _switch(s))

    # --- Секция AI ---

    def _render_ai_section() -> None:
        s = load_settings()
        current_provider = s.get("active_provider", "ollama")

        ui.label("ИИ-помощник").classes(TEXT_HEADING + " mb-1")
        ui.label(
            "Выберите провайдера для извлечения метаданных из документов. Локальная модель работает без интернета и бесплатна."
        ).classes(TEXT_SECONDARY + " mb-4")
        ui.element('div').classes("border-t border-slate-200 w-full mb-4")

        # API key row — показываем только для облачных провайдеров
        api_key_row = ui.row().classes("w-full items-center gap-3")

        def _toggle_api_key(provider: str) -> None:
            api_key_row.clear()
            if provider in _CLOUD_PROVIDERS:
                key_val = load_settings().get(f"api_key_{provider}", "")
                with api_key_row:
                    inp = (
                        ui.input(
                            label=f"Ключ доступа ({_PROVIDERS.get(provider, provider)})",
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

        ui.label("Защита данных").classes(TEXT_HEADING + " mb-1")
        ui.label(
            "Выберите, какие персональные данные скрывать перед отправкой на обработку ИИ."
        ).classes(TEXT_SECONDARY + " mb-4")
        ui.element('div').classes("border-t border-slate-200 w-full mb-4")

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

        ui.label("Предупреждения").classes(SECTION_DIVIDER_HEADER + " mt-4")
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

        ui.label("Уведомления в Telegram").classes(TEXT_HEADING + " mb-1")
        ui.label(
            "Подключите бота, чтобы получать напоминания об истекающих договорах прямо в мессенджер."
        ).classes(TEXT_SECONDARY + " mb-4")
        ui.element('div').classes("border-t border-slate-200 w-full mb-4")

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
                try:
                    ok = await run.io_bound(tg.check_connection)
                except Exception as e:
                    ui.notify("Не удалось проверить подключение. Убедитесь, что адрес сервера указан верно.", type="negative")
                    return
                if ok:
                    status_label.set_text("● Подключён")
                    status_label.classes(remove="text-red-500", add="text-green-600")
                else:
                    status_label.set_text("● Не подключён")
                    status_label.classes(remove="text-green-600", add="text-red-500")

            ui.button(
                "Проверить подключение", on_click=_check_telegram
            ).props("flat no-caps size=sm").classes("text-slate-600")

    # Инициализация — открываем ИИ секцию (после определения всех render-функций)
    _switch("ИИ")
