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
            save_setting("trust_prompt_dismissed", True)  # skip trust prompt, go directly to tour
            ui.navigate.to("/")  # перезагружает реестр, _init() проверит флаг и запустит тур

        ui.button(
            icon="help_outline",
            on_click=_restart_tour,
        ).props('flat round dense id=tour-guide-btn aria-label="Запустить тур по приложению"').classes(
            "text-slate-400 hover:text-slate-200 transition-colors duration-150"
        )

        # Right: client dropdown (D-20)
        with ui.row().classes("shrink-0 items-center gap-1").props("data-tour=workspace"):
            profile_btn = ui.button(
                f"{state.current_client}",
                on_click=lambda: client_menu.open(),
            ).props('flat no-caps aria-label="Рабочее пространство"').classes(
                "text-sm text-slate-400 hover:text-slate-200 transition-colors duration-150"
            )

            with ui.menu() as client_menu:
                for name in _cm.list_clients():
                    ui.menu_item(
                        name,
                        on_click=lambda n=name: _switch_client(state, n, profile_btn, client_menu),
                    )
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
    """Диалог добавления нового клиента."""
    menu.close()

    with ui.dialog() as dlg, ui.card().classes("p-0 min-w-[420px] max-w-[520px] overflow-hidden shadow-xl"):
        # Заголовок с indigo-полосой
        with ui.element("div").style(
            "background:#4f46e5;padding:20px 24px 16px;"
        ):
            with ui.element("p").style("color:white;font-size:1rem;font-weight:600;margin:0;"):
                ui.html("Новое рабочее пространство")
            with ui.element("p").style("color:#c7d2fe;font-size:0.8rem;margin:4px 0 0;"):
                ui.html("Создайте отдельный реестр для клиента или проекта")

        # Тело диалога
        with ui.column().classes("p-6 gap-4"):
            name_input = ui.input(
                placeholder="Например: ООО Ромашка"
            ).props('outlined dense label="Название пространства" aria-label="Название рабочего пространства"').classes("w-full").style("font-size:0.875rem;")

            with ui.row().classes("gap-2 justify-end w-full"):
                ui.button("Отмена", on_click=dlg.close).props("flat no-caps").classes(
                    "text-slate-500 text-sm"
                )

                async def _add() -> None:
                    n = name_input.value.strip()
                    if n:
                        await run.io_bound(cm.add_client, n)
                        _switch_client(state, n, btn, None)
                        dlg.close()

                ui.button("Создать", on_click=_add).props("no-caps").classes(
                    "px-4 py-1.5 bg-indigo-600 text-white text-sm font-semibold rounded-lg"
                    " hover:bg-indigo-700 transition-colors duration-150"
                )

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
