"""Страница «Настройки» — macOS Preferences layout (левая навигация + правая панель).

Phase 11, Plan 02.
Три секции: AI-провайдер · Обработка · Telegram.
Всё сохраняется в ~/.yurteg/settings.json через load_settings / save_setting.
"""
import logging
from pathlib import Path

from nicegui import run, ui

from app.styles import (
    TEXT_HEADING, TEXT_SECONDARY,
    APPLE_CARD_COMPACT,
)
from config import load_runtime_config, load_settings, save_setting
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
    with ui.row().classes("w-full items-center justify-between py-4 border-b border-slate-100"):
        with ui.column().classes("gap-0.5 flex-1 min-w-0"):
            ui.label(label).classes("text-sm text-slate-900")
            if description:
                ui.label(description).classes("text-xs text-slate-400")
        if control_fn:
            control_fn()


def _render_summary_cards(settings: dict, switch_fn, card_refs: dict) -> None:
    """Рендерит компактные summary-карточки над sidebar layout."""
    # --- AI summary ---
    cfg = load_runtime_config()
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
            "icon": "smart_toy", "icon_bg": "var(--yt-color-accent-subtle)", "icon_color": "var(--yt-color-accent)",
            "title": "ИИ-помощник",
            "detail": ai_detail, "detail_color": ai_detail_color, "section": "ИИ",
        },
        {
            "icon": "tune", "icon_bg": "var(--yt-p-slate-100)", "icon_color": "var(--yt-color-text-secondary)",
            "title": "Обработка",
            "detail": anon_text, "detail_color": proc_detail_color, "section": "Обработка",
        },
        {
            "icon": "notifications_none", "icon_bg": "#fef3c7", "icon_color": "var(--yt-p-amber-600)",
            "title": "Уведомления",
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
                    # Icon in colored rounded square (Material Icon)
                    ui.html(
                        f'<div style="width:32px;height:32px;border-radius:8px;'
                        f'background:{card["icon_bg"]};display:flex;'
                        f'align-items:center;justify-content:center;'
                        f'flex-shrink:0"><span class="material-icons" style="'
                        f'font-size:18px;color:{card["icon_color"]}">'
                        f'{card["icon"]}</span></div>'
                    )
                    with ui.column().classes("gap-0"):
                        ui.label(card["title"]).classes(
                            "font-semibold text-slate-900"
                        ).style("font-size:13px")
                        ui.label(card["detail"]).classes(
                            card["detail_color"]
                        ).style("font-size:11px")


def _section_header(icon: str, title: str, description: str, *, section_id: str = "") -> None:
    """Render a section header with icon, title, and description."""
    row = ui.row().classes("items-center gap-3 mb-4")
    if section_id:
        row.props(f'id="settings-section-{section_id}"')
    with row:
        ui.icon(icon).style("font-size:22px; color:var(--yt-color-accent);")
        with ui.column().classes("gap-0"):
            ui.label(title).classes(TEXT_HEADING)
            ui.label(description).classes(TEXT_SECONDARY)


def build() -> None:
    """Рендерит страницу настроек — вертикальный скролл, все секции видны."""

    settings = load_settings()
    summary_card_refs: dict[str, ui.card] = {}

    # Summary cards at top
    summary_container = ui.column().classes("w-full")

    # All sections in vertical scroll
    with ui.column().classes("w-full max-w-3xl mx-auto px-6 py-4 gap-0"):

        # ═══════════════════════════════════════════════════════════════
        # Секция 1: ИИ-помощник
        # ═══════════════════════════════════════════════════════════════
        _section_header("smart_toy", "Модель ИИ", "Извлечение метаданных из документов", section_id="ai")

        with ui.column().classes("w-full gap-0 mt-2"):
            # Provider
            def _provider_control():
                sel = ui.select(
                    options=_PROVIDERS,
                    value=settings.get("active_provider", "ollama"),
                ).props("dense outlined").classes("w-48")
                sel.on_value_change(lambda e: save_setting("active_provider", e.value))

            _settings_row("Модель", "Локальная модель работает офлайн", control_fn=_provider_control)

            # Model status
            def _model_status():
                cfg = load_runtime_config()
                model_path = Path.home() / ".yurteg" / cfg.llama_model_filename
                exists = model_path.exists()
                size_mb = f"{model_path.stat().st_size / 1024 / 1024:.0f} MB" if exists else ""
                badge_cls = "bg-green-100 text-green-700" if exists else "bg-amber-100 text-amber-700"
                badge_text = "Готова" if exists else "Не скачана"
                with ui.row().classes("items-center gap-2"):
                    if exists:
                        ui.label(f"{cfg.llama_model_filename} \u00b7 {size_mb}").classes("text-xs text-slate-400")
                    ui.label(badge_text).classes(f"text-xs px-2 py-0.5 rounded-full {badge_cls}")

            _settings_row("Статус", "", control_fn=_model_status)

            # Check connection
            def _check_control():
                result_label = ui.label("").classes("text-xs")

                async def _check():
                    import httpx as _httpx
                    check_btn.props(add="loading")
                    result_label.set_text("")
                    try:
                        cfg = load_runtime_config()
                        provider = settings.get("active_provider", cfg.active_provider)
                        async with _httpx.AsyncClient(timeout=3) as client:
                            if provider == "ollama":
                                resp = await client.get(f"http://localhost:{cfg.llama_server_port}/health")
                            else:
                                result_label.set_text("Ключ и облачный провайдер настроены отдельно")
                                result_label.classes(remove="text-red-500", add="text-slate-500")
                                return
                        if resp.status_code == 200:
                            result_label.set_text("Работает")
                            result_label.classes(remove="text-red-500", add="text-green-600")
                        else:
                            result_label.set_text("Недоступна")
                            result_label.classes(remove="text-green-600", add="text-red-500")
                    except Exception:
                        logger.exception("Ошибка при проверке подключения провайдера")
                        result_label.set_text("Недоступна")
                        result_label.classes(remove="text-green-600", add="text-red-500")
                    finally:
                        check_btn.props(remove="loading")

                with ui.row().classes("items-center gap-2"):
                    check_btn = ui.button("Проверить", on_click=_check).props("flat dense no-caps").classes("text-indigo-600 text-sm")
                    result_label  # noqa: B018 — side-effect: attaches to current context

            _settings_row("Проверить работу", "", control_fn=_check_control)

        # Разделитель
        ui.element("div").classes("w-full border-t border-slate-200 my-6")

        # ═══════════════════════════════════════════════════════════════
        # Секция 2: Обработка
        # ═══════════════════════════════════════════════════════════════
        _section_header("tune", "Обработка", "Параметры извлечения метаданных", section_id="processing")

        with ui.column().classes("w-full gap-0 mt-2"):
            # Anonymization
            def _anon_control():
                sw = ui.switch(value=settings.get("anonymize_for_cloud", True)).props("dense")
                sw.on_value_change(lambda e: save_setting("anonymize_for_cloud", e.value))

            _settings_row(
                "Анонимизация",
                "Маскировать ФИО и телефоны при отправке в облако",
                control_fn=_anon_control,
            )

            # Confidence threshold
            def _confidence_control():
                raw = settings.get("confidence_low", 0.5)
                inp = ui.number(
                    value=int(raw * 100),
                    min=0, max=100, step=5,
                ).props("dense outlined suffix='%'").classes("w-24")
                inp.on_value_change(lambda e: save_setting("confidence_low", (e.value or 50) / 100))

            _settings_row(
                "Порог уверенности",
                "Документы ниже порога будут помечены для проверки",
                control_fn=_confidence_control,
            )

            # Max workers
            def _workers_control():
                inp = ui.number(
                    value=settings.get("max_workers", 5),
                    min=1, max=10, step=1,
                ).props("dense outlined").classes("w-24")
                inp.on_value_change(lambda e: save_setting("max_workers", int(e.value or 5)))

            _settings_row(
                "Параллельные потоки",
                "Сколько документов обрабатывать одновременно",
                control_fn=_workers_control,
            )

        # Разделитель
        ui.element("div").classes("w-full border-t border-slate-200 my-6")

        # ═══════════════════════════════════════════════════════════════
        # Секция 3: Уведомления
        # ═══════════════════════════════════════════════════════════════
        _section_header("notifications_none", "Уведомления", "Напоминания о сроках через Telegram", section_id="notifications")

        with ui.column().classes("w-full gap-0 mt-2"):
            # Warning threshold
            def _threshold_control():
                inp = ui.number(
                    value=settings.get("warning_days_threshold", 30),
                    min=1, max=90, step=1,
                ).props("dense outlined suffix='\u0434\u043d\u0435\u0439'").classes("w-28")
                inp.on_value_change(lambda e: save_setting("warning_days_threshold", int(e.value or 30)))

            _settings_row(
                "Порог напоминания",
                "За сколько дней до истечения предупреждать",
                control_fn=_threshold_control,
            )

            # Telegram status
            srv_url = settings.get("telegram_server_url", "")
            chat_id = settings.get("telegram_chat_id", 0)
            is_bound = bool(chat_id)

            def _telegram_status_control():
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
                    ui.label("Не привязан").classes(
                        "text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700"
                    )

            _settings_row(
                "Telegram",
                "Получайте уведомления о сроках в мессенджер",
                control_fn=_telegram_status_control,
            )

            # Telegram bind flow (only if not bound)
            if not is_bound:
                def _telegram_bind_control():
                    code_input = ui.input(placeholder="6-значный код").props("dense outlined").classes("w-32")

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

                    with ui.row().classes("items-center gap-2"):
                        code_input  # noqa: B018
                        ui.button("Привязать", on_click=_bind).props("flat dense no-caps").classes(
                            "text-sm font-semibold text-indigo-600 hover:text-indigo-800 transition-colors duration-150"
                        )

                _settings_row(
                    "Привязка бота",
                    "Отправьте /start боту @YurTagBot \u2014 он пришлёт код",
                    control_fn=_telegram_bind_control,
                )

    # Section name -> DOM id mapping
    _SECTION_IDS = {
        "ИИ": "settings-section-ai",
        "Обработка": "settings-section-processing",
        "Уведомления": "settings-section-notifications",
    }

    # Summary cards at top — click scrolls to corresponding section
    def _switch(section: str) -> None:
        dom_id = _SECTION_IDS.get(section)
        if dom_id:
            ui.run_javascript(
                f'document.getElementById("{dom_id}")?.scrollIntoView({{behavior:"smooth",block:"start"}})'
            )

    with summary_container:
        _render_summary_cards(settings, _switch, summary_card_refs)

    # Инициализация — открываем ИИ секцию (после определения всех render-функций)
    _switch("ИИ")
