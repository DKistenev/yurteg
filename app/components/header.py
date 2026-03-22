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

        # Left: logo mark — indigo square «Ю» + wordmark «рТэг»
        with ui.row().classes("items-center gap-2 shrink-0"):
            ui.html(
                '<div class="w-7 h-7 rounded-lg flex items-center justify-center'
                ' text-white text-sm font-bold" style="background: #4f46e5;'
                ' line-height: 1; flex-shrink: 0;">Ю</div>'
            )
            ui.label("рТэг").classes("text-base font-semibold text-white tracking-tight")

        # Center: text-link nav tabs with active indicator
        with ui.row().classes("gap-6 flex-1 justify-center"):
            _nav_link("Реестр", "/")
            _nav_link("Шаблоны", "/templates")
            _nav_link("⚙", "/settings", aria_label="Настройки")

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
        ).props("no-caps")

        # Сохраняем ссылку на кнопку для start_pipeline (ui_refs['upload_btn'])
        _header_refs["upload_btn"] = upload_btn

        # Right: client dropdown (D-20)
        with ui.row().classes("shrink-0 items-center gap-1"):
            profile_btn = ui.button(
                f"📁 {state.current_client}",
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
      var isActive = (path === elPath) || (path === '/' && elPath === '/');
      el.style.color = isActive ? '#ffffff' : '';
      el.style.borderBottomColor = isActive ? '#4f46e5' : 'transparent';
      el.style.fontWeight = isActive ? '600' : '500';
    });
  }
  updateNav();
  window.addEventListener('popstate', updateNav);
  document.addEventListener('nicegui:navigate', updateNav);
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

    with ui.dialog() as dlg, ui.card():
        ui.label("Новое рабочее пространство").classes("text-lg font-semibold")
        name_input = ui.input("Название").props("outlined")

        with ui.row().classes("gap-2 justify-end w-full"):
            ui.button("Отмена", on_click=dlg.close).props("flat")

            async def _add() -> None:
                n = name_input.value.strip()
                if n:
                    await run.io_bound(cm.add_client, n)
                    _switch_client(state, n, btn, None)
                    dlg.close()

            ui.button("Добавить", on_click=_add).props("flat color=primary")

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
