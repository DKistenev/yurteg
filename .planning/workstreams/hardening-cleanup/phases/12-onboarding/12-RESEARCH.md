# Phase 12: Onboarding — Research

**Researched:** 2026-03-22
**Domain:** NiceGUI first-run experience — splash screen, empty state, guided tour
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Splash screen**
- D-01: Тон — дружелюбное приветствие (не холодный инструмент, не flashy стартап)
- D-02: Композиция: логотип ЮрТэг наверху → «Добро пожаловать!» → 3 пункта возможностей → прогресс-бар загрузки модели → wizard под прогрессом
- D-03: 3 пункта описания: «Загрузите папку → получите реестр», «Автосортировка по папкам», «Контроль сроков и предупреждения»
- D-04: Прогресс-бар модели: «Загрузка модели (580/940 МБ)» с процентом
- D-05: Splash показывается ТОЛЬКО при первом запуске (флаг в `~/.yurteg/settings.json`)

**Setup wizard**
- D-06: 2 шага — Шаг 1: Приветствие + 3 пункта (совмещён с D-03); Шаг 2: Telegram
- D-07: Каждый шаг имеет кнопку «Пропустить» и «Далее»/«Готово»
- D-08: Wizard показывается ПОД прогресс-баром — юрист настраивает пока модель качается
- D-09: После загрузки модели + wizard → splash закрывается → открывается реестр

**Empty state реестра**
- D-10: Центрированный CTA + подсказки
- D-11: Иконка папки → «Загрузите первые документы» → кнопка «Выбрать папку» → 3 подсказки
- D-12: Таблица реестра скрыта при пустой базе — вместо неё empty state
- D-13: После загрузки первых документов — empty state исчезает навсегда

**Guided tour**
- D-14: Запускается ПОСЛЕ первой обработки (когда данные есть в реестре)
- D-15: 3 шага: Реестр → Фильтры → Загрузка
- D-16: Подсветка — затемнение фона + выделение целевого элемента (spotlight pattern)
- D-17: Каждый шаг — «Далее» и «Пропустить тур»
- D-18: Tour показывается один раз (флаг `tour_completed`)

**Флаги**
- D-19: В `~/.yurteg/settings.json` два флага: `first_run_completed` и `tour_completed`

### Claude's Discretion
- Exact CSS для spotlight overlay (z-index, opacity, transition)
- Tooltip positioning для шагов тура
- Анимация перехода между шагами wizard
- Размер и отступы splash screen

### Deferred Ideas (OUT OF SCOPE)
- Видео-tutorial или help section — v2+
- Contextual tooltips при первом использовании каждой функции — v2+
- Кнопка «Повторить тур» в настройках
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ONBR-01 | Splash screen при первом запуске с прогрессом загрузки модели и setup wizard (Telegram) | `_start_llama()` в `main.py` уже async; `LlamaServerManager.ensure_model()` принимает `on_progress` callback; `save_setting()` готов |
| ONBR-02 | Empty state реестра при пустой базе — центрированный CTA «Загрузить первые документы» | `load_table_data()` в `registry_table.py` возвращает список строк; `pick_folder()` из `process.py` переиспользуется |
| ONBR-03 | Флаг «первый запуск» — splash и wizard показываются только один раз | `load_settings()` / `save_setting()` в `config.py` — merge-семантика, готовы к добавлению двух новых ключей |
| ONBR-04 | Краткое описание возможностей на splash screen (3 пункта) | Совмещён с wizard Шаг 1 (D-06); тексты зафиксированы в UI-SPEC Copywriting Contract |
| ONBR-05 | Guided tour после первой обработки — 3 шага с spotlight (реестр → фильтры → загрузка) | Целевые элементы существуют: AG Grid, search row, upload_btn в `_header_refs`; overlay через `ui.html` + JS |
</phase_requirements>

---

## Summary

Фаза 12 добавляет три независимых onboarding-элемента поверх существующего NiceGUI-приложения без изменения бизнес-логики. Вся необходимая инфраструктура уже построена: `load_settings`/`save_setting` для флагов, `pick_folder()` для CTA, `_start_llama()` для интеграции с прогрессом, `_header_refs` для целевых элементов тура.

Ключевой технический вызов — прогресс-бар splash screen. `LlamaServerManager.ensure_model()` уже принимает `on_progress: Callable[[float, str], None]`, но `_start_llama()` в `main.py` вызывает его через `run.io_bound()` без передачи этого колбэка. Нужно пробросить колбэк через `loop.call_soon_threadsafe()` — паттерн идентичен тому, что уже реализован в `process.py` для pipeline-прогресса.

Guided tour реализуется через `ui.html` с fixed-position overlay и JS-позиционированием tooltip через `getBoundingClientRect()`. Это более надёжно, чем попытка использовать нативное позиционирование NiceGUI для фиксированных overlay-элементов.

**Primary recommendation:** Разбить фазу на 3 плана: (1) splash + wizard, (2) empty state, (3) guided tour. Планы 2 и 3 независимы от плана 1, но план 3 логически следует после плана 2.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| NiceGUI | уже установлен | Рендеринг всех UI-элементов | Единственный UI-фреймворк проекта |
| config.load_settings / save_setting | project | Персистентность флагов first_run / tour | Уже реализован в Phase 11, merge-семантика |
| LlamaServerManager.ensure_model | project | Источник прогресса загрузки | Уже принимает on_progress callback |
| process.pick_folder | project | Кнопка «Выбрать папку» в empty state | Уже реализован нативный OS picker |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio.get_running_loop | stdlib | thread-safe UI обновления из on_progress | Везде где колбэк вызывается из ThreadPoolExecutor |
| ui.html | NiceGUI | Overlay и JS-позиционирование тура | Фиксированные fullscreen overlay-элементы |
| ui.linear_progress | NiceGUI | Прогресс-бар загрузки модели | Splash screen |
| ui.input | NiceGUI | Поле ввода Telegram-токена | Wizard Step 2 |

**Installation:** Новые зависимости не требуются. Всё в уже установленном стеке.

---

## Architecture Patterns

### Recommended File Structure
```
app/
└── components/
    └── onboarding/
        ├── __init__.py
        ├── splash.py        # Splash screen + wizard (ONBR-01, ONBR-04)
        └── tour.py          # Guided tour overlay (ONBR-05)
```

Изменения в существующих файлах:
- `app/main.py` — добавить splash gate в `root()` перед `render_header` + `ui.sub_pages`
- `app/pages/registry.py` — empty state + tour trigger в `_init()`

### Pattern 1: Splash Gate в root()

`root()` — единственная `@ui.page('/')` функция. Splash должен рендериться ВМЕСТО обычного контента, а не поверх него.

```python
# app/main.py — в функции root()
@ui.page("/")
def root() -> None:
    ui.dark_mode(value=False)
    from config import load_settings
    settings = load_settings()

    if not settings.get("first_run_completed"):
        # Рендерим только splash — без header и sub_pages
        from app.components.onboarding.splash import render_splash
        render_splash()
        return  # ← критично: ранний return блокирует рендер основного UI

    # Обычный путь — header + sub_pages
    state = get_state()
    async def _handle_upload(path): ...
    render_header(state, on_upload=_handle_upload)
    ui.sub_pages({...})
```

**Почему ранний return:** NiceGUI рендерит всё, что вызывается внутри `@ui.page` функции. Без return header и sub_pages отрисуются поверх splash.

### Pattern 2: Progress Wiring для Splash

`_start_llama()` в `main.py` вызывает `ensure_model()` через `run.io_bound()` без колбэка. Нужно пробросить `on_progress`:

```python
# app/components/onboarding/splash.py
import asyncio
from nicegui import run, ui
from services.llama_server import LlamaServerManager
from config import Config

async def _run_model_download(progress_bar, progress_label) -> None:
    """Запускает загрузку модели с обновлением UI через call_soon_threadsafe."""
    loop = asyncio.get_running_loop()
    config = Config()

    def on_progress(fraction: float, msg: str) -> None:
        # Вызывается из ThreadPoolExecutor — нельзя трогать UI напрямую
        loop.call_soon_threadsafe(progress_bar.set_value, fraction)
        mb_done = int(fraction * 940)
        loop.call_soon_threadsafe(
            progress_label.set_text,
            f"Загрузка модели ({mb_done}/940 МБ)"
        )

    manager = LlamaServerManager(port=config.llama_server_port)
    await run.io_bound(manager.ensure_model, on_progress)
    await run.io_bound(manager.ensure_server_binary)
    await run.io_bound(manager.start, get_grammar_path())
```

**Важно:** Если модель уже скачана (`model_path.exists()` == True), `ensure_model()` возвращает немедленно без вызова `on_progress`. Splash должен показывать прогресс-бар заполненным сразу (`progress_bar.set_value(1.0)`) в этом случае.

### Pattern 3: Wizard Step Transition

Per UI-SPEC: `content.clear()` + re-render — instant, без анимации. Это осознанное решение из FEATURES.md anti-patterns.

```python
# app/components/onboarding/splash.py
def render_splash() -> None:
    step = {"current": 1}
    is_model_ready = {"value": False}

    with ui.column().classes("min-h-screen bg-white flex items-center justify-center"):
        with ui.column().classes("max-w-lg w-full mx-auto py-16 px-8 gap-6"):
            # Logo + heading (постоянная часть)
            ui.label("ЮрТэг").classes("text-3xl font-semibold text-gray-900")
            ui.label("Добро пожаловать!").classes("text-xl font-semibold text-gray-900 mt-8")

            # Capability bullets (постоянная часть)
            with ui.column().classes("bg-gray-50 rounded-lg p-4 gap-2"):
                for bullet in ["Загрузите папку → получите реестр",
                               "Автосортировка по папкам",
                               "Контроль сроков и предупреждения"]:
                    with ui.row().classes("gap-2 items-start"):
                        ui.label("·").classes("text-gray-400 text-sm shrink-0")
                        ui.label(bullet).classes("text-sm text-gray-600 font-normal")

            # Progress bar (постоянная часть)
            progress_label = ui.label("Загрузка модели (0/940 МБ)").classes("text-sm text-gray-500 font-normal")
            progress_bar = (
                ui.linear_progress(value=0)
                .props("color=grey-9 track-color=grey-3")
                .classes("w-full h-1.5 rounded-full")
            )

            # Wizard content area — меняется между шагами
            wizard_area = ui.column().classes("w-full mt-8 gap-4")

            def _render_step_1():
                wizard_area.clear()
                with wizard_area:
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.button("Пропустить", on_click=_finish).props("flat no-caps").classes(
                            "text-sm text-gray-400 hover:text-gray-600"
                        )
                        ui.button("Далее: Telegram →", on_click=_go_step2).props("no-caps").classes(
                            "px-6 py-2 bg-gray-900 text-white text-sm font-semibold rounded-lg"
                        )

            def _render_step_2():
                wizard_area.clear()
                with wizard_area:
                    ui.label("Подключите Telegram-бот").classes("text-xl font-semibold text-gray-900")
                    ui.label("Получайте уведомления об истекающих документах прямо в мессенджер.").classes(
                        "text-sm text-gray-500 font-normal"
                    )
                    token_input = ui.input(
                        placeholder="110201543:AAHdqTcvCH1vGWJxfSeofSs0K"
                    ).props("outlined dense").classes("w-full")
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.button("Пропустить", on_click=_finish).props("flat no-caps").classes(
                            "text-sm text-gray-400 hover:text-gray-600"
                        )
                        ui.button("Сохранить и начать", on_click=lambda: _save_and_finish(token_input)).props("no-caps").classes(
                            "px-6 py-2 bg-gray-900 text-white text-sm font-semibold rounded-lg"
                        )

            _render_step_1()
    ...
```

### Pattern 4: Empty State в registry.py

Добавляется в `_init()` после `load_table_data()`:

```python
async def _init() -> None:
    rows = await run.io_bound(load_table_data_raw, state)  # только строки, без рендера
    with grid_container:
        if not rows and not _any_filter_active(state):
            _render_empty_state(grid_container, state)
        else:
            grid = await render_registry_table(state)
            grid_ref["grid"] = grid
            grid.on("cellClicked", _on_cell_clicked)
            await load_table_data(grid, state, "all")
            # Tour trigger
            settings = load_settings()
            if rows and not settings.get("tour_completed"):
                await _start_tour()
```

**Риск:** `load_table_data()` в `registry_table.py` сейчас рендерит данные в переданный grid напрямую. Нужно либо проверять наличие строк до создания grid, либо вызывать `load_table_data_raw()` (отдельная функция без side effects). Проще всего: создать grid, загрузить данные, проверить `grid.rows` — если 0, убрать grid и показать empty state.

### Pattern 5: Guided Tour через ui.html + JS

NiceGUI не имеет нативного spotlight компонента. Overlay реализуется через `ui.html`:

```python
# app/components/onboarding/tour.py
from nicegui import ui

TOUR_STEPS = [
    {
        "target_selector": ".ag-root-wrapper",
        "title": "Реестр документов",
        "body": "Это ваш реестр. Кликните на строку для просмотра подробностей.",
        "position": "center-top",
    },
    {
        "target_selector": ".search-row",  # добавить class на search row
        "title": "Фильтры и поиск",
        "body": "Используйте сегменты и поиск. Истекающие документы выделены предупреждением.",
        "position": "below-left",
    },
    {
        "target_selector": "#upload-btn",  # добавить id на upload_btn
        "title": "Загрузка документов",
        "body": "Нажмите здесь для обработки новых документов.",
        "position": "below-right",
    },
]

def render_tour() -> None:
    """Рендерит guided tour overlay. Управляется через JS."""
    tour_html = """
    <div id="tour-overlay" style="
        position: fixed; inset: 0;
        background: rgba(0,0,0,0.5);
        z-index: 40;
        display: none;
    "></div>
    <div id="tour-tooltip" style="
        position: fixed;
        z-index: 50;
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 16px;
        max-width: 256px;
        display: none;
    "></div>
    """
    ui.html(tour_html)
    # JS-логика тура инжектируется отдельно через ui.add_head_html или inline
```

**Spotlight эффект:** Целевой элемент поднимается через `z-index: 50` + `box-shadow: 0 0 0 9999px rgba(0,0,0,0.5)` — это стандартная техника "cutout spotlight" без canvas.

**Позиционирование tooltip:** `getBoundingClientRect()` на целевом элементе + вычисление `top/left` с учётом viewport edges.

### Anti-Patterns to Avoid

- **Splash поверх основного UI (без early return):** Без `return` в `root()` NiceGUI отрисует и splash, и header, и sub_pages одновременно.
- **Прямые UI-вызовы из on_progress callback:** `on_progress` вызывается из ThreadPoolExecutor. Вызов `progress_bar.set_value()` напрямую вызовет RuntimeError. Только через `loop.call_soon_threadsafe()`.
- **Анимированные переходы между wizard-шагами:** NiceGUI не поддерживает CSS transitions на `content.clear()` → instant re-render. Анимация вызовет визуальный артефакт (мерцание).
- **ui.dialog для splash:** Модальный dialog не покрывает нативный заголовок окна и имеет backdrop по умолчанию. Splash лучше рендерить как полностраничный компонент внутри `root()`.
- **Проверка флагов один раз при импорте:** Флаги должны читаться при каждом вызове `root()`, иначе повторный запуск приложения покажет splash даже когда `first_run_completed: true`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Прогресс загрузки модели | Свою систему прогресса | `LlamaServerManager.ensure_model(on_progress=...)` | Колбэк уже реализован, тип `Callable[[float, str], None]` |
| Выбор папки в empty state | Свой file picker | `process.pick_folder()` | Уже реализован нативный OS picker, идентичная логика |
| Персистентность флагов | Свой JSON-файл | `config.load_settings()` / `config.save_setting()` | Уже merge-семантика, создаёт директорию если нет |
| Thread-safe UI updates | asyncio.Queue или Event | `loop.call_soon_threadsafe()` | Паттерн уже использован в `process.py` строки 95-99 |
| CSS-in-JS для overlay | Python-based позиционирование | `ui.html` + inline JS | NiceGUI не имеет fixed-position positioning API |

---

## Common Pitfalls

### Pitfall 1: `ensure_model()` не вызывает on_progress при уже скачанной модели

**What goes wrong:** `ensure_model()` возвращает немедленно если `model_path.exists()`. Прогресс-бар остаётся на 0%, хотя модель готова.

**Why it happens:** Early return без вызова `on_progress`. Строка 104 в `llama_server.py`: `return model_path`.

**How to avoid:** После вызова `ensure_model()` через `run.io_bound()` — принудительно выставить `progress_bar.set_value(1.0)` независимо от результата колбэка.

**Warning signs:** Splash никогда не закрывается при повторном запуске с уже скачанной моделью.

### Pitfall 2: Tour target elements не найдены в DOM

**What goes wrong:** JS `document.querySelector('.ag-root-wrapper')` возвращает `null` при первом запуске тура — AG Grid ещё не fully rendered.

**Why it happens:** `ui.timer(0, _init, once=True)` в `registry.py` запускает инициализацию asynchronously. Если tour стартует сразу после pipeline completion — grid может не успеть перерисоваться.

**How to avoid:** Запускать tour через `ui.timer(0.5, lambda: render_tour(), once=True)` — небольшая задержка после pipeline completion. Или добавить JS fallback: если `querySelector` вернул null — retry через 100ms.

**Warning signs:** Tooltip рендерится в позиции (0, 0) или overlay показывается без подсветки.

### Pitfall 3: `first_run_completed` проверяется в неправильном контексте

**What goes wrong:** Флаг читается один раз при импорте модуля — `settings = load_settings()` на уровне модуля. При первом запуске splash показывается. При повторном запуске приложения — импортированное значение кешировано, splash снова показывается.

**Why it happens:** NiceGUI с `reload=False` не перезагружает модули между сессиями.

**How to avoid:** Читать `load_settings()` ВНУТРИ функции `root()` при каждом запросе. Никакого module-level кеша.

### Pitfall 4: Empty state показывается при активных фильтрах

**What goes wrong:** Юрист вводит несуществующий поисковый запрос → 0 результатов → empty state с CTA «Выбрать папку» появляется, хотя документы в базе есть.

**Why it happens:** Условие проверяет только `len(rows) == 0` без проверки активности фильтров.

**How to avoid:** Empty state показывается ТОЛЬКО если `len(rows) == 0 AND state.filter_search == "" AND active_segment == "all"`. Per UI-SPEC: "Shown when `load_table_data()` returns 0 rows, no active filters".

### Pitfall 5: Splash не закрывается если модель уже скачана и wizard пропущен

**What goes wrong:** Логика: "ждём загрузку модели AND wizard completed". Если модель скачана мгновенно (ensure_model() early return) — событие "model ready" не приходит или теряется, splash висит.

**Why it happens:** Race condition между async model download completion и wizard navigation.

**How to avoid:** Использовать два независимых флага: `{"model_ready": False, "wizard_done": False}`. После каждого изменения проверять оба — если оба True, закрывать splash.

---

## Code Examples

### Thread-safe progress update (из process.py — переиспользовать паттерн)

```python
# Source: app/components/process.py, lines 83-99
loop = asyncio.get_running_loop()
last_update: list[float] = [0.0]

def on_progress(current: int, total: int, message: str) -> None:
    now = time.monotonic()
    if now - last_update[0] < 0.5:  # debounce 500ms
        return
    last_update[0] = now

    val = current / total if total > 0 else 0
    loop.call_soon_threadsafe(progress_bar.set_value, val)
    loop.call_soon_threadsafe(progress_label.set_text, message)
```

### save_setting (из config.py)

```python
# Source: config.py, lines 170-175
def save_setting(key: str, value) -> None:
    """Сохраняет один ключ в ~/.yurteg/settings.json (merge, не перезапись)."""
    s = load_settings()
    s[key] = value
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
```

Применение для флагов:
```python
save_setting("first_run_completed", True)
save_setting("tour_completed", True)
```

### Spotlight CSS техника (по UI-SPEC)

```html
<!-- Overlay div — покрывает весь экран, z-40 -->
<div style="position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 40;"></div>

<!-- Целевой элемент поднимается через JS -->
<script>
function highlightElement(selector) {
    const el = document.querySelector(selector);
    if (!el) return;
    el.style.position = 'relative';
    el.style.zIndex = '50';
    el.style.boxShadow = '0 0 0 9999px rgba(0,0,0,0.5)';
}
</script>
```

### pick_folder reuse в empty state

```python
# Source: app/components/process.py, lines 23-37
async def pick_folder() -> Optional[Path]:
    result = await app.native.main_window.create_file_dialog(
        dialog_type=webview.FOLDER_DIALOG,
    )
    if not result:
        return None
    return Path(result[0])

# Использование в empty state CTA:
async def _on_pick_folder():
    source_dir = await pick_folder()
    if source_dir:
        await state._on_upload(source_dir)  # тот же колбэк что в header
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (уже настроен в проекте) |
| Config file | нет отдельного pytest.ini — `pyproject.toml` или стандартный |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ONBR-01 | Splash рендерится когда `first_run_completed` отсутствует | unit | `pytest tests/test_onboarding.py::test_splash_shown_on_first_run -x` | ❌ Wave 0 |
| ONBR-01 | Splash НЕ рендерится когда `first_run_completed: true` | unit | `pytest tests/test_onboarding.py::test_splash_skipped_after_completion -x` | ❌ Wave 0 |
| ONBR-02 | Empty state показывается при 0 строках и нет фильтров | unit | `pytest tests/test_onboarding.py::test_empty_state_shown_when_no_rows -x` | ❌ Wave 0 |
| ONBR-02 | Empty state НЕ показывается при активном фильтре и 0 результатов | unit | `pytest tests/test_onboarding.py::test_empty_state_hidden_with_active_filter -x` | ❌ Wave 0 |
| ONBR-03 | `save_setting('first_run_completed', True)` записывает корректный JSON | unit | `pytest tests/test_onboarding.py::test_first_run_flag_persistence -x` | ❌ Wave 0 |
| ONBR-03 | `save_setting('tour_completed', True)` не перезаписывает другие ключи | unit | `pytest tests/test_onboarding.py::test_save_setting_merge_semantics -x` | ❌ Wave 0 |
| ONBR-04 | Splash содержит три capability bullets с правильным текстом | unit | `pytest tests/test_onboarding.py::test_splash_capability_bullets -x` | ❌ Wave 0 |
| ONBR-05 | Tour trigger: `tour_completed` отсутствует + rows > 0 → тур запускается | unit | `pytest tests/test_onboarding.py::test_tour_triggered_after_first_processing -x` | ❌ Wave 0 |
| ONBR-05 | Tour НЕ запускается если `tour_completed: true` | unit | `pytest tests/test_onboarding.py::test_tour_not_shown_after_completion -x` | ❌ Wave 0 |

**Примечание:** Полноценный e2e-тест NiceGUI-рендеринга (реальный браузер + pywebview) выходит за рамки unit-тестирования. Тесты проверяют логику флагов и условий показа/скрытия через mock-функции, а не реальный UI.

### Sampling Rate
- **Per task commit:** `pytest tests/test_onboarding.py -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green перед `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_onboarding.py` — все 9 тестов выше (логика флагов, условия показа)
- [ ] Mock для `load_settings` / `save_setting` в тестовом контексте (через `tmp_path` fixture)

---

## Integration Points (детали для планировщика)

### main.py changes

Единственное место: добавить splash gate в `root()` до `render_header` + `ui.sub_pages`.

```
CURRENT: root() → render_header() → ui.sub_pages()
TARGET:  root() → check first_run → [splash OR (render_header + sub_pages)]
```

Проблема: `_start_llama()` запускается в `app.on_startup` **до** того как `root()` вызывается. Т.е. к моменту рендера splash модель может уже качаться в фоне. Splash должен либо:
- (a) Запускать свой download task и отображать прогресс (но дублирует `_start_llama()`)
- (b) Интегрироваться с `_start_llama()` — передать прогресс-колбэк до старта

**Рекомендация (b):** Модифицировать `_start_llama()` чтобы принимать опциональный `on_progress` параметр. Splash при рендере регистрирует колбэк через module-level переменную в `main.py`, а `_start_llama()` вызывает его если он установлен.

```python
# main.py
_splash_progress_callback: list = [None]  # [0] = callable or None

async def _start_llama() -> None:
    ...
    on_prog = _splash_progress_callback[0]
    await run.io_bound(manager.ensure_model, on_prog)
    ...
```

### registry.py changes

В `_init()` после инициализации grid: проверить данные, показать empty state или table, запустить tour если нужно.

```
CURRENT: _init() → render_registry_table() → load_table_data() → done
TARGET:  _init() → load_table_data() → [empty_state OR table] → [tour trigger?]
```

### Файл app/components/onboarding/__init__.py

Пустой, нужен для Python package.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| st.session_state для first_run | load_settings() / save_setting() в JSON | Phase 11 (v0.6) | Готово, ничего менять не нужно |
| Streamlit spinner при загрузке | Явное управление linear_progress + call_soon_threadsafe | Phase 10 (v0.6) | Паттерн задокументирован в process.py |
| Huggingface_hub без прогресса | on_progress callback в ensure_model() | Phase 4 (v0.5) | Колбэк уже принимается, нужно только пробросить |

---

## Open Questions

1. **Синхронизация splash и _start_llama()**
   - Что знаем: `_start_llama()` вызывается в `app.on_startup`, до первого запроса к `root()`
   - Что неясно: Есть ли гарантия что `on_startup` завершится ДО первого рендера `root()`? Нет — `on_startup` async, `root()` может вызваться сразу после запуска сервера
   - Рекомендация: Передавать прогресс через module-level callback-регистрацию (см. Integration Points выше). Если `_start_llama()` уже запустился до регистрации колбэка — splash показывает модель как готовую (100%).

2. **CSS-классы для tour target elements**
   - Что знаем: AG Grid рендерит `.ag-root-wrapper`, upload_btn уже в `_header_refs`
   - Что неясно: Нужно ли добавлять CSS-классы/id на search row и upload button специально для тура
   - Рекомендация: Добавить `id="upload-btn"` на upload_btn в `header.py` и CSS-класс `search-row` на соответствующий `ui.row` в `registry.py` — минимальный invasive change.

---

## Sources

### Primary (HIGH confidence)
- `app/main.py` — текущий код `_start_llama()`, паттерн `app.on_startup`
- `services/llama_server.py` — сигнатура `ensure_model(on_progress: Optional[Callable[[float, str], None]] = None)`
- `app/components/process.py` — паттерн `loop.call_soon_threadsafe()` для прогресса
- `config.py` — `load_settings()` / `save_setting()` с merge-семантикой
- `app/pages/registry.py` — текущий `_init()` и структура build()
- `.planning/phases/12-onboarding/12-CONTEXT.md` — 19 locked decisions
- `.planning/phases/12-onboarding/12-UI-SPEC.md` — точные классы, тексты, взаимодействия
- `.planning/research/PITFALLS.md` — Pitfall 2 (run.io_bound), Pitfall 3 (llama lifecycle)

### Secondary (MEDIUM confidence)
- `.planning/research/FEATURES.md` — anti-pattern: animated transitions в NiceGUI

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — весь стек уже в проекте, новых зависимостей нет
- Architecture patterns: HIGH — паттерны взяты из существующего кода проекта
- Pitfalls: HIGH — Pitfall 2 и 3 задокументированы в PITFALLS.md, остальные из анализа кода
- Integration points: HIGH — все integration points верифицированы чтением исходного кода

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (стабильный стек, нет fast-moving dependencies)
