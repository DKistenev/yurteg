"""Страница «Настройки» — macOS Preferences layout (левая навигация + правая панель).

Phase 11, Plan 02.
Три секции: AI-провайдер · Обработка · Telegram.
Всё сохраняется в ~/.yurteg/settings.json через load_settings / save_setting.
"""
import logging
from pathlib import Path

from nicegui import run, ui

from app.styles import (
    TEXT_HEADING, TEXT_SECONDARY, SECTION_DIVIDER_HEADER,
    APPLE_CARD_COMPACT,
)
from config import Config, load_settings, save_setting
from services.telegram_sync import TelegramSync

logger = logging.getLogger(__name__)

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


def _render_summary_cards(settings: dict, switch_fn, card_refs: dict) -> None:
    """Рендерит компактные summary-карточки над sidebar layout."""
    # --- AI summary ---
    cfg = Config()
    model_path = Path.home() / ".yurteg" / cfg.llama_model_filename
    model_exists = model_path.exists()
    model_size = f"{model_path.stat().st_size / 1024 / 1024:.0f}MB" if model_exists else ""
    model_status = "Готова" if model_exists else "Не скачана"
    provider = _PROVIDERS.get(settings.get("active_provider", "ollama"), "Локальный")
    provider_short = provider.split("(")[0].strip().split(" ")[0]
    ai_detail = f"{provider_short} \u00b7 {model_status}" + (f" \u00b7 {model_size}" if model_size else "")
    ai_detail_color = "text-slate-500" if model_exists else "text-amber-600"

    # --- Processing summary ---
    anon_on = settings.get("anonymize_for_cloud", True)
    anon_text = "Анонимизация: вкл" if anon_on else "Анонимизация: выкл"
    proc_detail_color = "text-slate-500"

    # --- Notifications summary ---
    chat_id = settings.get("telegram_chat_id", 0)
    tg_bound = bool(chat_id)
    tg_text = "Telegram: привязан" if tg_bound else "Telegram: не привязан"
    tg_detail_color = "text-slate-500" if tg_bound else "text-amber-600"

    cards_data = [
        {
            "icon": "\U0001f916", "icon_bg": "#eef2ff", "title": "ИИ-помощник",
            "detail": ai_detail, "detail_color": ai_detail_color, "section": "ИИ",
        },
        {
            "icon": "\u2699\ufe0f", "icon_bg": "#f1f5f9", "title": "Обработка",
            "detail": anon_text, "detail_color": proc_detail_color, "section": "Обработка",
        },
        {
            "icon": "\U0001f514", "icon_bg": "#fef3c7", "title": "Уведомления",
            "detail": tg_text, "detail_color": tg_detail_color, "section": "Уведомления",
        },
    ]

    _CARD_BASE = APPLE_CARD_COMPACT + " flex-1 cursor-pointer transition-colors duration-150"
    _CARD_ACTIVE_ADD = "border-indigo-200 bg-indigo-50/50"
    _CARD_ACTIVE_REMOVE = "border-slate-200 bg-white"

    with ui.row().classes("gap-3 px-6 py-4 w-full"):
        for card in cards_data:
            card_el = ui.card().classes(
                _CARD_BASE
            ).style("padding:14px").on(
                "click", lambda s=card["section"]: switch_fn(s)
            )
            card_refs[card["section"]] = card_el
            with card_el:
                with ui.row().classes("items-center gap-3"):
                    # Icon in colored rounded square
                    ui.html(
                        f'<div style="width:28px;height:28px;border-radius:8px;'
                        f'background:{card["icon_bg"]};display:flex;'
                        f'align-items:center;justify-content:center;'
                        f'font-size:0.875rem;flex-shrink:0">{card["icon"]}</div>'
                    )
                    with ui.column().classes("gap-0"):
                        ui.label(card["title"]).classes(
                            "font-semibold text-slate-900"
                        ).style("font-size:13px")
                        ui.label(card["detail"]).classes(
                            card["detail_color"]
                        ).style("font-size:11px")


def build() -> None:
    """Рендерит страницу настроек с левой навигацией и правой панелью."""

    settings = load_settings()
    active_section: list[str] = ["ИИ"]  # mutable container для захвата в closures
    nav_buttons: dict[str, ui.button] = {}
    summary_card_refs: dict[str, ui.card] = {}

    # Summary cards at top (rendered after switch_fn is defined)
    summary_container = ui.column().classes("w-full")

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
        # Update sidebar nav buttons
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
        # Update summary card active state
        for name, card_el in summary_card_refs.items():
            if name == section:
                card_el.classes(
                    remove="border-slate-200 bg-white",
                    add="border-indigo-200 bg-indigo-50/50",
                )
            else:
                card_el.classes(
                    remove="border-indigo-200 bg-indigo-50/50",
                    add="border-slate-200 bg-white",
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
            with ui.column().classes("w-full gap-6 yt-fade-stagger"):
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

                # Row 3: Check connection
                def _check_control():
                    result_label = ui.label("").classes("text-xs")

                    async def _check():
                        import httpx as _httpx
                        check_btn.props(add="loading")
                        result_label.set_text("")
                        try:
                            async with _httpx.AsyncClient(timeout=3) as client:
                                resp = await client.get("http://localhost:8080/health")
                            if resp.status_code == 200:
                                result_label.set_text("Подключено")
                                result_label.classes(remove="text-red-500", add="text-green-600")
                            else:
                                result_label.set_text("Ошибка")
                                result_label.classes(remove="text-green-600", add="text-red-500")
                        except Exception:
                            logger.exception("Ошибка при проверке подключения провайдера")
                            result_label.set_text("Ошибка")
                            result_label.classes(remove="text-green-600", add="text-red-500")
                        finally:
                            check_btn.props(remove="loading")

                    with ui.row().classes("items-center gap-2"):
                        check_btn = ui.button("Проверить", on_click=_check).props("flat dense no-caps").classes("text-indigo-600 text-sm")
                        result_label  # noqa: B018 — side-effect: attaches to current context

                _settings_row("Соединение", "", control_fn=_check_control)

    # --- Секция Обработка ---

    def _render_processing(content_el, s) -> None:
        content_el.clear()
        with content_el:
            with ui.column().classes("w-full gap-6 yt-fade-stagger"):
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
            with ui.column().classes("w-full gap-6 yt-fade-stagger"):
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
                                            logger.exception("Ошибка при привязке Telegram-бота")
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

    # Рендерим summary cards (теперь _switch определён)
    with summary_container:
        _render_summary_cards(settings, _switch, summary_card_refs)

    # Инициализация — открываем ИИ секцию (после определения всех render-функций)
    _switch("ИИ")
