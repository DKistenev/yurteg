# Phase 7: App Scaffold + State Architecture - Research

**Researched:** 2026-03-22
**Domain:** NiceGUI app entrypoint, AppState dataclass, SPA navigation, llama-server lifecycle
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**App structure**
- D-01: Создать `app/` директорию с `main.py`, `state.py`, `pages/`, `components/`
- D-02: Каждая страница — модуль с функцией `build()` внутри `@ui.page` декоратора
- D-03: `ui.sub_pages` для SPA-навигации — URL обновляется, header остаётся

**State management**
- D-04: `AppState` dataclass в `app/state.py` — единственный источник правды для UI-состояния
- D-05: `app.storage.client['state']` для хранения AppState (per-connection, in-memory)
- D-06: Persistent settings (провайдер, Telegram) остаются в `~/.yurteg/settings.json` — без изменений

**Async patterns**
- D-07: Все DB-вызовы из UI обёрнуты в `await run.io_bound()` — шаблон зафиксирован до написания любых обработчиков
- D-08: `reload=False` в `ui.run()` — предотвращение двойной инициализации

**llama-server lifecycle**
- D-09: Module-level singleton, инициализация в `app.on_startup`
- D-10: Тройная защита при закрытии: `app.on_shutdown` + `app.on_disconnect` + `atexit.register`
- D-11: `ensure_model()` и `start()` через `run.io_bound()` — не блокируют event loop

**Header layout**
- D-12: Минималистичный текстовый header без иконок у табов
- D-13: Слева — текстовый лого «ЮрТэг», центр — табы «Документы · Шаблоны · ⚙», справа — иконка профиля клиента 👤▾
- D-14: Header persistent — остаётся при навигации между sub_pages

**Old Streamlit UI**
- D-15: Старый `main.py` архивируется в ветку `archive/streamlit-ui`, не удаляется и не переименовывается в main branch

**NiceGUI run config**
- D-16: `ui.run(native=True, dark=False, reload=False, host='127.0.0.1', title='ЮрТэг', window_size=(1400, 900), storage_secret='yurteg-desktop-secret')`

### Claude's Discretion
- Exact AppState fields (based on existing session_state keys analysis)
- File structure within `app/components/`
- Error handling strategy for llama-server startup failures
- NiceGUI version pinning

### Deferred Ideas (OUT OF SCOPE)
- Splash screen с onboarding wizard при первом запуске — Phase 12 (Onboarding)
- Настройка Telegram во время загрузки модели — Phase 12 (Onboarding)
- Светлая тема и типографика — Phase 13 (Design Polish)
- Empty state реестра — Phase 12 (Onboarding)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FUND-01 | Приложение запускается на NiceGUI с `app/` структурой и `@ui.page` архитектурой | Pattern 2 (ui.sub_pages), directory scaffold in Architecture section |
| FUND-02 | Состояние управляется через typed `AppState` dataclass (замена 45 `st.session_state` ключей) | Pattern 1 (AppState), full field mapping below |
| FUND-03 | Все DB-вызовы из UI обёрнуты в `run.io_bound()` (не блокируют event loop) | Anti-pattern from PITFALLS.md §Pitfall 2, Pattern 4 code example |
| FUND-04 | llama-server запускается через `app.on_startup`, останавливается через тройную защиту | Pattern 3 (LlamaServerManager singleton), PITFALLS.md §Pitfall 3 |
| FUND-05 | Приложение запускается с `reload=False` в production entrypoint | PITFALLS.md §Pitfall 4, STACK.md §Desktop Native Mode |
</phase_requirements>

---

## Summary

Phase 7 закладывает архитектурный фундамент всего NiceGUI-приложения. Три проблемы, которые она должна предотвратить, — global state leak, async blocking, double init — это дорогостоящие паттерны: если их не зафиксировать сейчас, они будут размазаны по всем последующим фазам и потребуют дорогого рефактора.

Вся необходимая техническая база хорошо изучена в предыдущем research-цикле (ARCHITECTURE.md, PITFALLS.md, STACK.md — все с HIGH confidence). Phase 7 — это не исследование новых технологий, а строгое воплощение уже принятых решений в конкретный скелет кода. Весь backend (controller, modules, services) остаётся нетронутым. Мигрирует только UI-слой.

Ключевой артефакт фазы: рабочее приложение с тремя пустыми вкладками в нативном окне, где уже работают `ui.sub_pages`, `AppState`, `run.io_bound` шаблон и тройная защита llama-server. Это то, на что будут нанизываться все следующие фазы.

**Primary recommendation:** Создать `app/` скелет с AppState и `ui.sub_pages` в одном wave, сразу прописать тройную защиту llama-server и `run.io_bound` шаблон — до написания единой строки UI-контента.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| nicegui | 3.9.0 | UI framework (FastAPI + Vue + Quasar + Tailwind) | Решение принято, locked в D-16 |
| nicegui[native] | 3.9.0 | pywebview desktop window | Locked в D-16: `native=True` |
| pywebview | >=5.0.1,<7 | macOS WKWebView / Windows EdgeChromium | Ставится автоматически через nicegui[native] |

### Поддерживающие (без изменений)

| Library | Purpose | Notes |
|---------|---------|-------|
| services/llama_server.py | LlamaServerManager — готов, только вызов меняется | `@st.cache_resource` → module-level singleton |
| config.py | Config dataclass, active_provider, llama_server_port | Используется без изменений |
| modules/postprocessor.py | `get_grammar_path()` для llama-server | Используется без изменений |
| services/client_manager.py | `ClientManager.list_clients()` для header profile selector | Используется без изменений |

### Installation

```bash
pip install "nicegui[native]==3.9.0"
# Удалить из requirements.txt: streamlit, streamlit-calendar
```

---

## Architecture Patterns

### Recommended Project Structure

```
yurteg/
├── app/
│   ├── __init__.py
│   ├── main.py              # ui.run() entry + on_startup hooks
│   ├── state.py             # AppState dataclass + get_state()
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── registry.py      # / (default) — пустой placeholder
│   │   ├── document.py      # /document/{doc_id} — пустой placeholder
│   │   ├── templates.py     # /templates — пустой placeholder
│   │   └── settings.py      # /settings — пустой placeholder
│   └── components/
│       ├── __init__.py
│       └── header.py        # persistent top navigation
│
├── main.py                  # АРХИВИРУЕТСЯ в ветку archive/streamlit-ui
├── controller.py            # без изменений
├── config.py                # без изменений
├── modules/                 # без изменений
├── providers/               # без изменений
├── services/                # без изменений
└── requirements.txt         # streamlit → nicegui[native]
```

### Pattern 1: AppState dataclass (FUND-02)

**Маппинг st.session_state → AppState поля:**

Анализ main.py выявил 14 уникальных session_state ключей. Вот их полный маппинг:

| session_state key | AppState field | Type | Default |
|-------------------|---------------|------|---------|
| `source_dir` | `source_dir` | `str` | `""` |
| `output_dir` | `output_dir` | `Optional[Path]` | `None` |
| `report_path` | `report_path` | `Optional[Path]` | `None` |
| `show_results` | `show_results` | `bool` | `False` |
| `force_reprocess` | `force_reprocess` | `bool` | `False` |
| `processing_time` | `processing_time` | `Optional[float]` | `None` |
| `upload_dir` | `upload_dir` | `Optional[Path]` | `None` |
| `warning_days_threshold` | `warning_days_threshold` | `int` | `30` |
| `telegram_chat_id` | `telegram_chat_id` | `int` | `0` |
| `telegram_server_url` | `telegram_server_url` | `str` | `""` |
| `tg_queue_fetched` | `tg_queue_fetched` | `bool` | `False` |
| `startup_toast_shown` | `startup_toast_shown` | `bool` | `False` |
| `deadlines_pushed` | `deadlines_pushed` | `bool` | `False` |
| `auto_bind_summary` | `auto_bind_summary` | `Optional[dict]` | `None` |

**Плюс поля навигации (новые, без аналога в st.session_state):**

| AppState field | Type | Default | Purpose |
|---------------|------|---------|---------|
| `current_client` | `str` | `"Основной реестр"` | Активный клиент |
| `selected_doc_id` | `Optional[int]` | `None` | Открытый документ |
| `filter_type` | `str` | `""` | Фильтр по типу |
| `filter_status` | `str` | `""` | Фильтр по статусу |
| `filter_search` | `str` | `""` | Текстовый поиск |
| `processing` | `bool` | `False` | Pipeline в процессе |

**Code example:**

```python
# app/state.py
# Source: .planning/research/ARCHITECTURE.md §Pattern 1
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

@dataclass
class AppState:
    # Processing
    source_dir: str = ""
    output_dir: Optional[Path] = None
    report_path: Optional[Path] = None
    show_results: bool = False
    force_reprocess: bool = False
    processing: bool = False
    processing_time: Optional[float] = None
    upload_dir: Optional[Path] = None
    # Settings (UI-side cache — persistent truth in settings.json)
    warning_days_threshold: int = 30
    telegram_chat_id: int = 0
    telegram_server_url: str = ""
    tg_queue_fetched: bool = False
    startup_toast_shown: bool = False
    deadlines_pushed: bool = False
    auto_bind_summary: Optional[dict] = None
    # Navigation
    current_client: str = "Основной реестр"
    selected_doc_id: Optional[int] = None
    # Filters
    filter_type: str = ""
    filter_status: str = ""
    filter_search: str = ""


def get_state() -> AppState:
    from nicegui import app
    if 'state' not in app.storage.client:
        app.storage.client['state'] = AppState()
    return app.storage.client['state']
```

**Критически важно:** `app.storage.client` — in-memory, per-connection, теряется при перезагрузке страницы (те же семантики, что у `st.session_state`). `warning_days_threshold`, `telegram_chat_id`, `telegram_server_url` и другие persistent-настройки — в AppState только как UI-кеш; canonical source — `~/.yurteg/settings.json` через `config.py`.

---

### Pattern 2: ui.sub_pages для SPA-навигации (FUND-01, D-03)

**Что:** `ui.sub_pages` внутри единственного `@ui.page('/')` — URL обновляется, header персистентен, только контент-область перерисовывается.

**Пример:**

```python
# app/main.py
# Source: .planning/research/ARCHITECTURE.md §Pattern 2
from nicegui import ui, app
from app.components.header import render_header
from app.pages import registry, document, templates, settings
from app.state import get_state

@ui.page('/')
def root():
    ui.dark_mode(value=False)
    state = get_state()
    render_header(state)
    ui.sub_pages({
        '/': registry.build,
        '/document/{doc_id}': document.build,
        '/templates': templates.build,
        '/settings': settings.build,
    })

ui.run(
    native=True,
    dark=False,
    reload=False,
    host='127.0.0.1',
    title='ЮрТэг',
    window_size=(1400, 900),
    storage_secret='yurteg-desktop-secret',
)
```

**Ограничение:** Вложенные `ui.sub_pages` (sub_pages внутри sub_pages) не поддерживаются. Маршрутизация должна быть плоской.

---

### Pattern 3: Singleton LlamaServerManager через app.on_startup (FUND-04, D-09/10/11)

**Что:** Module-level переменная, инициализируется ровно один раз в `app.on_startup`. `ensure_model()` и `start()` вызываются через `run.io_bound()`, чтобы не блокировать event loop.

```python
# app/main.py (фрагмент)
# Source: .planning/research/ARCHITECTURE.md §Pattern 3
from nicegui import app, run
from services.llama_server import LlamaServerManager
from modules.postprocessor import get_grammar_path
from config import Config
import atexit
import logging

logger = logging.getLogger(__name__)
_llama_manager: LlamaServerManager | None = None


async def _start_llama():
    global _llama_manager
    config = Config()
    if config.active_provider != "ollama":
        return
    manager = LlamaServerManager(port=config.llama_server_port)
    try:
        await run.io_bound(manager.ensure_model)
        await run.io_bound(manager.ensure_server_binary)
        await run.io_bound(manager.start, get_grammar_path())
        _llama_manager = manager
        logger.info("llama-server запущен")
    except Exception as e:
        logger.warning(f"llama-server не запустился: {e}. Fallback на облачный провайдер.")


def _stop_llama():
    global _llama_manager
    if _llama_manager and _llama_manager.is_running():
        _llama_manager.stop()
        logger.info("llama-server остановлен")


app.on_startup(_start_llama)
app.on_shutdown(_stop_llama)       # не всегда вызывается в native mode (баг NiceGUI #2107)
app.on_disconnect(_stop_llama)     # второй уровень защиты
atexit.register(_stop_llama)       # третий уровень — безопасный fallback


def get_llama_manager() -> LlamaServerManager | None:
    return _llama_manager
```

**Критически:** `app.on_shutdown` в `native=True` на macOS не вызывается надёжно (NiceGUI issue #2107). Тройная защита — не параноя, а обязательный паттерн.

---

### Pattern 4: run.io_bound шаблон (FUND-03, D-07)

**Шаблон для всех DB-вызовов из UI:**

```python
# Source: .planning/research/PITFALLS.md §Pitfall 2
from nicegui import run

async def on_some_button_click(state: AppState):
    # ПРАВИЛЬНО: оборачивать любой синхронный DB-вызов
    rows = await run.io_bound(db_service.get_all_documents, state.current_client)
    # обновить UI
    table.options['rowData'] = rows
    table.update()

# НЕ ПРАВИЛЬНО: прямой вызов блокирует event loop
# rows = db_service.get_all_documents(state.current_client)  # ЗАПРЕЩЕНО
```

**Правило:** Этот шаблон должен быть задокументирован как архитектурное ограничение ДО написания любых page-модулей. Retrofit потребует прохода по каждому async-обработчику в Phase 8-11.

---

### Pattern 5: Минималистичный header (D-12/13/14)

**Дизайн:** Linear/Notion стиль — чистый текстовый header, custom text links с подчёркиванием активного таба (не Quasar ui.tabs визуально).

```python
# app/components/header.py
from nicegui import ui
from app.state import AppState

def render_header(state: AppState):
    with ui.header().classes('bg-white border-b border-gray-200 px-6 py-0 flex items-center gap-8 h-12'):
        # Левый блок: лого
        ui.label('ЮрТэг').classes('text-base font-semibold text-gray-900 shrink-0')

        # Центр: кастомные text-link табы
        with ui.row().classes('gap-6 flex-1 justify-center'):
            _nav_link('Документы', '/')
            _nav_link('Шаблоны', '/templates')
            _nav_link('⚙', '/settings')

        # Правый блок: профиль клиента
        with ui.row().classes('shrink-0 items-center gap-1 cursor-pointer'):
            ui.label('👤▾').classes('text-gray-500 text-sm')


def _nav_link(label: str, path: str):
    ui.link(label, path).classes(
        'text-sm text-gray-600 hover:text-gray-900 no-underline'
        ' border-b-2 border-transparent hover:border-gray-900 pb-0.5'
    )
```

**Важно:** Активное подчёркивание (определение текущего маршрута) потребует чтения `ui.context.client.url` или передачи активного пути в render_header. Для Phase 7 достаточно статического header без активного состояния — это задача Phase 8 (Registry) при полной проводке навигации.

---

### Anti-Patterns to Avoid

- **Global scope UI elements:** Любой `ui.*` вне `@ui.page` функции — общий для всех соединений. Всегда оборачивать в декоратор.
- **Porting st.rerun():** Нет аналога. NiceGUI реактивный — обновлять элементы через `.set_text()`, `.update()`, reactive bindings.
- **Монолитный main.py:** Запрещено. Каждая страница — отдельный модуль с `build()` функцией. `main.py` — только entrypoint (~50 LOC).
- **app.storage.user вместо app.storage.client:** `app.storage.user` — персистентный on-disk JSON, требует request context. `app.storage.client` — in-memory, правильный аналог `st.session_state`.
- **reload=True:** Запускает llama-server дважды. `reload=False` — всегда и везде.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SPA navigation | Свою систему роутинга | `ui.sub_pages` | Встроено в NiceGUI, URL updates, header persistence |
| Per-connection state | Глобальный dict keyed by session | `app.storage.client` | NiceGUI решает per-connection изоляцию |
| Non-blocking I/O | `asyncio.to_thread`, `loop.run_in_executor` | `run.io_bound()` | NiceGUI-специфичная обёртка, правильно интегрируется с event loop |
| Desktop window | Electron, отдельный процесс | `ui.run(native=True)` + pywebview | Встроено, без Node.js |
| Process cleanup hooks | Кастомный signal handler | `atexit.register` + `app.on_shutdown` + `app.on_disconnect` | Тройная защита обязательна из-за NiceGUI bug #2107 |

---

## Common Pitfalls

### Pitfall 1: app.on_shutdown не вызывается при закрытии нативного окна
**What goes wrong:** llama-server процесс остаётся в памяти после закрытия окна (~1.5 ГБ RAM). При повторном запуске — "port already in use" на порту 8080.
**Why it happens:** NiceGUI bug #2107 — `native=True` использует pywebview; при закрытии окна shutdown lifecycle не срабатывает на macOS.
**How to avoid:** Тройная защита: `app.on_shutdown` + `app.on_disconnect` + `atexit.register`. Все три на одну и ту же функцию `_stop_llama`. Функция идемпотентна — вызов несколько раз безвреден.
**Warning signs:** `ps aux | grep llama` показывает процесс после закрытия приложения.

### Pitfall 2: Двойная инициализация при reload=True
**What goes wrong:** Два llama-server процесса на одном порту. Второй падает с "address already in use".
**Why it happens:** NiceGUI reload=True запускает subprocess с `__name__ == '__mp_main__'`, обходя `if __name__ == '__main__'` guard. Код уровня модуля выполняется дважды.
**How to avoid:** `reload=False` в `ui.run()`. Все side-effect инициализации — только в `app.on_startup`.
**Warning signs:** Activity Monitor показывает два llama-server сразу после запуска.

### Pitfall 3: Синхронный SQLite блокирует event loop
**What goes wrong:** UI зависает при любом DB-вызове. Spinner не анимируется (event loop заблокирован до его рендера).
**Why it happens:** NiceGUI работает на asyncio event loop. Любой blocking call >10ms останавливает все соединения одновременно. `sqlite3` — синхронный.
**How to avoid:** Каждый вызов `database.py` методов из UI обёрнут в `await run.io_bound(...)`. Шаблон зафиксировать в Phase 7, до Phase 8.
**Warning signs:** WebSocket timeout ошибки в DevTools консоли.

### Pitfall 4: app.storage.user вместо app.storage.client
**What goes wrong:** `RuntimeError: No storage available` в фоновых задачах. Данные неожиданно переживают перезапуск (on-disk JSON).
**Why it happens:** `app.storage.user` требует активного HTTP-сессионного контекста. Фоновые задачи (pipeline callbacks, Telegram handlers, `app.on_startup`) его не имеют.
**How to avoid:** `app.storage.client` для ephemeral UI state (AppState). `app.storage.user` — только для persistent user preferences. Для background tasks — module-level dict.

### Pitfall 5: native config внутри if __name__ == '__main__'
**What goes wrong:** `app.native.window_args` не применяется — subprocess игнорирует main guard.
**Why it happens:** native=True спавнит subprocess. Конфиг уровня модуля применяется, main guard — нет.
**How to avoid:** Все `app.native.*` настройки — на уровне модуля, до `ui.run()`.

---

## Code Examples

### Полный app/main.py (~50 LOC)

```python
# app/main.py
# Source: .planning/research/ARCHITECTURE.md §Pattern 2 + Pattern 3
import atexit
import logging
from nicegui import ui, app, run
from services.llama_server import LlamaServerManager
from modules.postprocessor import get_grammar_path
from config import Config
from app.components.header import render_header
from app.pages import registry, document, templates, settings
from app.state import get_state

logger = logging.getLogger(__name__)

# ── llama-server singleton ─────────────────────────────────────────
_llama_manager: LlamaServerManager | None = None


async def _start_llama():
    global _llama_manager
    config = Config()
    if config.active_provider != "ollama":
        return
    manager = LlamaServerManager(port=config.llama_server_port)
    try:
        await run.io_bound(manager.ensure_model)
        await run.io_bound(manager.ensure_server_binary)
        await run.io_bound(manager.start, get_grammar_path())
        _llama_manager = manager
    except Exception as e:
        logger.warning(f"llama-server не запустился: {e}")


def _stop_llama():
    global _llama_manager
    if _llama_manager and _llama_manager.is_running():
        _llama_manager.stop()


def get_llama_manager() -> LlamaServerManager | None:
    return _llama_manager


app.on_startup(_start_llama)
app.on_shutdown(_stop_llama)
app.on_disconnect(_stop_llama)
atexit.register(_stop_llama)

# ── UI root ────────────────────────────────────────────────────────
@ui.page('/')
def root():
    ui.dark_mode(value=False)
    state = get_state()
    render_header(state)
    ui.sub_pages({
        '/': registry.build,
        '/document/{doc_id}': document.build,
        '/templates': templates.build,
        '/settings': settings.build,
    })


# ── Entry point ────────────────────────────────────────────────────
ui.run(
    native=True,
    dark=False,
    reload=False,
    host='127.0.0.1',
    title='ЮрТэг',
    window_size=(1400, 900),
    storage_secret='yurteg-desktop-secret',
)
```

### Page placeholder (реестр)

```python
# app/pages/registry.py
from nicegui import ui
from app.state import AppState

def build(state: AppState | None = None):
    """Placeholder — реализация в Phase 8."""
    with ui.column().classes('w-full p-8'):
        ui.label('Документы').classes('text-2xl font-semibold text-gray-900')
        ui.label('Реестр документов — Phase 8').classes('text-gray-400 text-sm')
```

### run.io_bound шаблон для DB-вызовов

```python
# Source: .planning/research/PITFALLS.md §Pitfall 2
from nicegui import run

# В любом async обработчике:
async def load_registry(state: AppState):
    # ПРАВИЛЬНО
    rows = await run.io_bound(db_service.get_all_results, state.current_client)
    return rows

# ЗАПРЕЩЕНО (блокирует event loop):
# rows = db_service.get_all_results(state.current_client)
```

### Архивирование Streamlit main.py

```bash
# D-15: создать ветку archive/streamlit-ui с текущим main.py
git checkout -b archive/streamlit-ui
git push origin archive/streamlit-ui
git checkout dev/phase-2-lifecycle  # вернуться на рабочую ветку

# В рабочей ветке: main.py НЕ удаляется, НЕ переименовывается
# app/main.py — новый entrypoint
# Запуск теперь: python -m nicegui app/main.py или python app/main.py
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `@st.cache_resource` для llama-server | Module-level singleton + `app.on_startup` | Переживает навигацию, не стартует дважды |
| 45 разрозненных `st.session_state` ключей | Один typed `AppState` dataclass | Type safety, единая точка правды |
| Весь UI в 2247-строчном main.py | `app/pages/*` + `app/components/*` | Каждая фаза добавляет свой модуль |
| Streamlit script rerun при каждом действии | NiceGUI reactive — обновление только нужных элементов | Нет flickering, нет потери состояния |
| `reload=True` (Streamlit default) | `reload=False` всегда | Нет двойной инициализации |

---

## Open Questions

1. **app.on_disconnect надёжность в native=True mode на macOS**
   - Что знаем: `app.on_shutdown` ненадёжен (bug #2107). `atexit` — надёжен. `app.on_disconnect` — поведение в native mode не подтверждено.
   - Что неясно: Триггерит ли `on_disconnect` при закрытии нативного окна на macOS 25.x?
   - Рекомендация: Добавить ручной тест в Phase 7 verification: закрыть окно → `ps aux | grep llama` должен показать 0 процессов. Если нет — `atexit` подхватит.

2. **Запуск приложения: команда**
   - Что знаем: Streamlit запускался через `streamlit run main.py`. NiceGUI — `python app/main.py` или `python -m nicegui app/main.py`.
   - Рекомендация: `python app/main.py` (прямой запуск). Обновить README.

3. **sub_pages и передача state в build()**
   - Что знаем: `ui.sub_pages` вызывает `build` как callback. Сигнатура `build(state)` требует partial или closure.
   - Рекомендация: Использовать closure в root() или `functools.partial`: `'/': lambda: registry.build(get_state())`. Либо `build()` сама вызывает `get_state()` внутри — чище.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (pytest.ini существует) |
| Config file | `yurteg/pytest.ini` |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FUND-01 | app/ структура создана, main.py импортируется без ошибок | smoke | `python -c "import app.main"` — нет, но можно `pytest tests/test_app_scaffold.py::test_imports -x` | ❌ Wave 0 |
| FUND-02 | AppState инициализируется со всеми полями и дефолтами | unit | `pytest tests/test_app_scaffold.py::test_appstate_defaults -x` | ❌ Wave 0 |
| FUND-03 | DB-вызовы не делаются напрямую в async handlers (grep audit) | static | `grep -r "database\." app/ | grep -v "run.io_bound"` — ручной аудит | manual-only в Phase 7 |
| FUND-04 | LlamaServerManager инициализируется через on_startup, не на уровне модуля | unit | `pytest tests/test_app_scaffold.py::test_llama_singleton -x` | ❌ Wave 0 |
| FUND-05 | ui.run вызывается с reload=False | static/smoke | `grep -r "reload=False" app/main.py` — trivial | manual-only |

### Sampling Rate

- **Per task commit:** `pytest tests/test_app_scaffold.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green перед `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_app_scaffold.py` — covers FUND-01, FUND-02, FUND-04
- [ ] Тесты для AppState: проверка дефолтов, типов, get_state() без app context (unit mock)
- [ ] Smoke: импорт `app.state`, `app.components.header` без NiceGUI server

*(Существующие тесты в tests/ покрывают backend — они не трогаются)*

---

## Sources

### Primary (HIGH confidence)
- `.planning/research/ARCHITECTURE.md` — полная архитектура миграции, Pattern 1-5, code examples
- `.planning/research/PITFALLS.md` — 9 критических питфолов с prevention strategies
- `.planning/research/STACK.md` — NiceGUI v3.9.0 компоненты, APIs, v3 breaking changes
- NiceGUI official docs: https://nicegui.io/documentation/storage (storage scopes)
- NiceGUI official docs: https://nicegui.io/documentation/section_pages_routing (sub_pages, @ui.page)
- NiceGUI official docs: https://nicegui.io/documentation/section_configuration_deployment (native mode, reload=False)

### Secondary (MEDIUM confidence)
- NiceGUI issue #2107 — on_shutdown unreliable in native mode (подтверждает тройную защиту)
- NiceGUI issue #5684 — double init with reload=True
- Прямой анализ main.py — 14 session_state ключей выявлено grep-ом

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — версии верифицированы в STACK.md
- Architecture: HIGH — прямой анализ кодовой базы + официальная документация
- Pitfalls: HIGH — верифицированы через официальные GitHub issues NiceGUI
- AppState fields: HIGH — grep по main.py (прямой анализ кода)

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (NiceGUI 3.x — стабильная серия)
