"""Persistent header component — dark chrome band visual anchor.

Per D-12: Минималистичный текстовый header без иконок у табов.
Per D-13: Слева — лого «ЮрТэг», центр — табы «Реестр · Шаблоны · ⚙», справа — клиент.
Per D-14: Header persistent — остаётся при навигации между sub_pages.
Per D-20: Профиль → dropdown с клиентами + «Добавить клиента».
Per D-21: При переключении — сброс фильтров, перезагрузка реестра.
Per D-22: ClientManager.list_clients() для списка клиентов.
Per D-01/D-02: Кнопка «+ Загрузить» рядом с табами, видна на любой странице.
Phase 14-02: Dark chrome header, лого-марка «Ю» indigo квадрат, filled indigo CTA, active tab indicator.
"""
from typing import Callable, Optional

from nicegui import run, ui

from app.components.process import pick_folder
from app.state import AppState
from config import save_setting
from services.client_manager import ClientManager

# Module-level singletons
_cm = ClientManager()
_header_refs: dict = {"upload_btn": None}

# Preset colors for workspace avatars
_WORKSPACE_COLORS = [
    "#4f46e5",  # indigo
    "#0891b2",  # cyan
    "#059669",  # emerald
    "#d97706",  # amber
    "#dc2626",  # red
    "#7c3aed",  # violet
    "#db2777",  # pink
    "#2563eb",  # blue
]


def _color_for_name(name: str) -> str:
    """Deterministic color based on workspace name hash."""
    return _WORKSPACE_COLORS[hash(name) % len(_WORKSPACE_COLORS)]


def render_header(state: AppState, on_upload: Optional[Callable] = None) -> None:
    """Render persistent top navigation header.

    Args:
        state: AppState — для флага processing.
        on_upload: async callback(source_dir: Path) — вызывается после выбора папки.
                   Если None — папка выбирается, но pipeline не запускается.
    """
    with ui.header().classes(
        "px-6 py-0 flex items-center gap-6 h-14"
    ).style("background: #0f172a; border-bottom: 1px solid #334155; box-shadow: 0 1px 3px rgb(0 0 0 / 0.2);"):

        # Left: logo mark — indigo rect «Юр» + wordmark «Тэг»
        with ui.row().classes("items-center gap-2 shrink-0 cursor-pointer").on("click", lambda: ui.navigate.to("/")):
            ui.html(
                '<div style="display:flex;align-items:center;justify-content:center;'
                'width:32px;height:28px;background:#4f46e5;border-radius:8px;'
                'color:white;font-size:0.8rem;font-weight:700;letter-spacing:-0.02em;'
                'flex-shrink:0;line-height:1;">Юр</div>'
            )
            ui.label("Тэг").classes("text-base font-semibold text-white tracking-tight")

        # Center: text-link nav tabs with active indicator
        with ui.row().classes("gap-6 flex-1 justify-center").props("data-tour=nav"):
            _nav_link("Реестр", "/")
            _nav_link("Шаблоны", "/templates")
            _nav_link("Настройки", "/settings")

        # Upload CTA — filled indigo (NOT flat, NOT Quasar color prop — avoids !important)
        async def _on_upload_click() -> None:
            if state.processing:
                return
            source_dir = await pick_folder()
            if source_dir and on_upload:
                await on_upload(source_dir)

        upload_btn = ui.button(
            "+ Загрузить документы",
            on_click=_on_upload_click,
        ).classes(
            "px-4 py-1.5 bg-indigo-600 text-white text-sm font-semibold rounded-lg"
            " hover:bg-indigo-700 transition-colors duration-150 shrink-0"
        ).props("no-caps").props("data-tour=upload")

        # Сохраняем ссылку на кнопку для start_pipeline (ui_refs['upload_btn'])
        _header_refs["upload_btn"] = upload_btn

        # «? Гид» — subtle restart button (ONBR-02)
        def _restart_tour() -> None:
            save_setting("tour_completed", False)
            save_setting("trust_prompt_dismissed", True)
            save_setting("first_processing_done", True)  # ensure tour triggers even without processing
            ui.navigate.to("/")

        ui.button(
            "? Гид",
            on_click=_restart_tour,
        ).props('flat no-caps id=tour-guide-btn aria-label="Запустить тур по приложению"').classes(
            "text-slate-400 hover:text-slate-200 text-xs px-3 py-1"
            " border border-slate-600 rounded-lg transition-colors duration-150"
        )

        # Right: client dropdown (D-20)
        with ui.row().classes("shrink-0 items-center gap-1").props("data-tour=workspace"):
            profile_btn = ui.button(
                f"{state.current_client}",
                on_click=lambda: client_menu.open(),
            ).props('flat no-caps aria-label="Рабочее пространство"').classes(
                "text-sm text-slate-400 hover:text-slate-200 transition-colors duration-150"
            )

            with ui.menu().classes("min-w-[220px]") as client_menu:
                for name in _cm.list_clients():
                    color = _color_for_name(name)
                    letter = name[0].upper() if name else "?"
                    with ui.menu_item(
                        on_click=lambda n=name: _switch_client(state, n, profile_btn, client_menu),
                    ):
                        with ui.row().classes("items-center gap-3 w-full"):
                            ui.html(
                                f'<div style="width:28px;height:28px;border-radius:50%;'
                                f'background:{color};color:white;display:flex;align-items:center;'
                                f'justify-content:center;font-size:0.75rem;font-weight:700;'
                                f'flex-shrink:0;">{letter}</div>'
                            )
                            ui.label(name).classes("text-sm text-slate-700")
                ui.separator()
                ui.menu_item(
                    "+ Новое пространство",
                    on_click=lambda: _show_add_dialog(state, _cm, profile_btn, client_menu),
                )



    # Active tab indicator JS — runs on page load and SPA navigation
    ui.add_body_html("""
<script>
(function() {
  function updateNav() {
    var path = window.location.pathname;
    document.querySelectorAll('a[data-path]').forEach(function(el) {
      var elPath = el.getAttribute('data-path');
      var isActive = (path === elPath);
      el.style.color = isActive ? '#ffffff' : '';
      el.style.borderBottomColor = isActive ? '#4f46e5' : 'transparent';
      el.style.fontWeight = isActive ? '600' : '500';
    });
  }
  updateNav();
  window.addEventListener('popstate', updateNav);
  window.addEventListener('hashchange', updateNav);
  document.addEventListener('nicegui:navigate', updateNav);
  // Intercept pushState/replaceState for SPA navigation
  var _push = history.pushState;
  history.pushState = function() {
    _push.apply(history, arguments);
    updateNav();
  };
  var _replace = history.replaceState;
  history.replaceState = function() {
    _replace.apply(history, arguments);
    updateNav();
  };
})();
</script>
""")


def _switch_client(state: AppState, name: str, btn, menu) -> None:
    """Переключает активного клиента и перезагружает реестр (D-21)."""
    state.current_client = name
    state.filter_search = ""  # сброс фильтров при переключении
    btn.text = f"📁 {name}"
    if menu:
        menu.close()
    ui.navigate.to("/")  # перезагрузить реестр с данными нового клиента


def _show_add_dialog(state: AppState, cm: ClientManager, btn, menu) -> None:
    """Диалог добавления нового клиента — кастомный overlay (обходит Quasar z-index баг)."""
    menu.close()

    picker_colors = ["#4f46e5", "#0891b2", "#059669", "#d97706", "#dc2626", "#7c3aed"]
    selected_color = {"value": picker_colors[0]}

    with ui.dialog().props('no-backdrop-dismiss position="standard"') \
            .on('show', js_handler='() => { document.querySelector(".q-header").style.zIndex = "-1" }') \
            .on('hide', js_handler='() => { document.querySelector(".q-header").style.zIndex = "" }') as dlg:
        with ui.card().classes(
            "p-0 overflow-hidden rounded-2xl shadow-2xl"
        ).style("width:480px; max-width:90vw;"):
            # Gradient header — w-full чтобы растянулся на всю карточку
            with ui.element("div").classes("w-full").style(
                "padding:16px 20px; background:linear-gradient(135deg,#4f46e5 0%,#7c3aed 100%);"
            ):
                ui.label("Новое пространство").style("color:white;font-size:1rem;font-weight:700;")
                ui.label("Отдельный реестр для клиента или проекта").style("color:#c7d2fe;font-size:0.75rem;margin-top:2px;")

            with ui.column().classes("px-6 py-5 gap-5 w-full"):
                name_input = ui.input(
                    placeholder="Например: ООО Ромашка"
                ).props(
                    'outlined dense label="Название пространства"'
                ).classes("w-full").style("font-size:0.875rem;")

                # Color picker
                with ui.column().classes("gap-2"):
                    ui.label("Цвет").classes("text-xs text-slate-500 font-medium")
                    with ui.row().classes("gap-2 items-center"):
                        color_circles = []
                        for c in picker_colors:
                            circle = ui.element("div").classes("cursor-pointer").style(
                                f"width:32px;height:32px;border-radius:50%;background:{c};"
                                f"border:3px solid white;"
                                f"box-shadow:{'0 0 0 2px ' + c if c == selected_color['value'] else 'none'};"
                                f"transition:box-shadow 0.15s;"
                            )
                            color_circles.append((circle, c))

                        def _select_color(color: str) -> None:
                            selected_color["value"] = color
                            for circ, col in color_circles:
                                shadow = f"0 0 0 2px {col}" if col == color else "none"
                                circ.style(
                                    f"width:32px;height:32px;border-radius:50%;background:{col};"
                                    f"border:3px solid white;box-shadow:{shadow};"
                                    f"transition:box-shadow 0.15s;cursor:pointer;"
                                )

                        for circ, col in color_circles:
                            circ.on("click", lambda c=col: _select_color(c))

                # "Зачем это нужно"
                ui.html(
                    '<div style="background:#f8fafc;border-radius:12px;padding:14px;border:1px solid #f1f5f9;">'
                    '<div style="font-size:10px;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:0.04em;margin-bottom:10px;">Зачем это нужно</div>'
                    '<div style="display:flex;align-items:center;gap:10px;background:white;border-radius:8px;padding:10px;border:1px solid #e2e8f0;margin-bottom:6px;">'
                    '<div style="width:28px;height:28px;border-radius:7px;background:#eef2ff;display:flex;align-items:center;justify-content:center;font-size:13px;flex-shrink:0;">&#x1f512;</div>'
                    '<div><div style="font-size:12px;font-weight:600;color:#1e293b;">Изоляция данных</div><div style="font-size:11px;color:#94a3b8;">Документы клиента не видны в другом пространстве</div></div></div>'
                    '<div style="display:flex;align-items:center;gap:10px;background:white;border-radius:8px;padding:10px;border:1px solid #e2e8f0;margin-bottom:6px;">'
                    '<div style="width:28px;height:28px;border-radius:7px;background:#f0fdf4;display:flex;align-items:center;justify-content:center;font-size:13px;flex-shrink:0;">&#x26a1;</div>'
                    '<div><div style="font-size:12px;font-weight:600;color:#1e293b;">Мгновенное переключение</div><div style="font-size:11px;color:#94a3b8;">Один клик — другой реестр, другие настройки</div></div></div>'
                    '<div style="display:flex;align-items:center;gap:10px;background:white;border-radius:8px;padding:10px;border:1px solid #e2e8f0;">'
                    '<div style="width:28px;height:28px;border-radius:7px;background:#fef3c7;display:flex;align-items:center;justify-content:center;font-size:13px;flex-shrink:0;">&#x1f4ca;</div>'
                    '<div><div style="font-size:12px;font-weight:600;color:#1e293b;">Свой реестр</div><div style="font-size:11px;color:#94a3b8;">Отдельная база с документами и шаблонами</div></div></div>'
                    '</div>'
                )

                # Buttons
                with ui.row().classes("gap-2 justify-end w-full pt-1"):
                    ui.button("Отмена", on_click=dlg.close).props("flat no-caps").classes(
                        "text-slate-500 text-sm px-4 py-1.5 rounded-lg"
                    )

                    async def _add() -> None:
                        n = name_input.value.strip()
                        if n:
                            await run.io_bound(cm.add_client, n)
                            _switch_client(state, n, btn, None)
                            dlg.close()

                    ui.button("Создать", on_click=_add).props("no-caps unelevated").classes(
                        "px-5 py-1.5 bg-indigo-600 text-white text-sm font-semibold rounded-lg"
                        " hover:bg-indigo-700 transition-colors duration-150"
                    )

    # Quasar dialog z-index (6000) > QHeader z-index (2000) — перекрывает header
    dlg.open()


def _nav_link(label: str, path: str, aria_label: str = "") -> None:
    """Render nav link with active indicator for dark header."""
    link = ui.link(label, path).classes(
        "text-sm font-medium no-underline pb-1 transition-colors duration-150"
        " text-slate-300 hover:text-white"
        " border-b-2 border-transparent"
    ).props(f'data-path="{path}"')
    if aria_label:
        link.props(f'aria-label="{aria_label}"')
