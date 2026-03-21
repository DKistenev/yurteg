# Architecture Research

**Domain:** Legal document processing pipeline — NiceGUI migration from Streamlit
**Researched:** 2026-03-21
**Confidence:** HIGH (codebase analyzed directly + verified from NiceGUI official docs)

---

## Context: What We Are Migrating

`main.py` is a 2247-line Streamlit monolith with 262 `st.*` calls. It is the ONLY file with Streamlit imports. All business logic lives in clean service/module layers with no Streamlit dependency. The migration scope is:

- **Delete:** `main.py` (Streamlit), `streamlit-calendar` dependency
- **Create:** NiceGUI UI layer (new `main.py` or `app/` directory)
- **Preserve unchanged:** `controller.py`, `modules/`, `services/`, `providers/`, `config.py`, SQLite DB

Key Streamlit APIs used and their NiceGUI equivalents:
| Streamlit | Count | NiceGUI equivalent |
|-----------|-------|--------------------|
| `st.session_state` | 45 | `app.storage.client` (in-memory per-connection) |
| `st.button` | 19 | `ui.button(on_click=...)` |
| `st.selectbox` | 12 | `ui.select(on_change=...)` |
| `st.rerun` | 11 | `ui.navigate.to('/')` or reactive binding — no equivalent needed |
| `st.columns` | 11 | `ui.row()` + CSS classes |
| `st.text_input` | 7 | `ui.input(on_change=...)` |
| `st.sidebar` | 5 | `ui.left_drawer()` |
| `st.expander` | 4 | `ui.expansion()` |
| `st.tabs` | 3 | `ui.tabs()` + `ui.tab_panels()` |
| `st.spinner` | 3 | `ui.spinner()` inside `async` handler |
| `st.metric` | 3 | `ui.label()` + typography classes |
| `st.checkbox` | 3 | `ui.checkbox(on_change=...)` |
| `st.cache_resource` | 1 | module-level singleton (see llama-server section) |
| `st.dataframe` | 1 | `ui.aggrid(...)` |

---

## System Overview (Target State After Migration)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         NiceGUI UI Layer                            │
│  app/                                                               │
│  ├── main.py          ui.run() entry, app.on_startup hooks          │
│  ├── state.py         AppState dataclass — single source of truth   │
│  ├── pages/                                                         │
│  │   ├── registry.py  Реестр (default view)                         │
│  │   ├── document.py  Full-page карточка документа                  │
│  │   ├── templates.py Шаблоны                                       │
│  │   └── settings.py  Настройки                                     │
│  └── components/                                                    │
│      ├── header.py    Верхняя навигация                             │
│      ├── table.py     ui.aggrid wrapper + row click handler         │
│      └── process.py  Кнопка запуска + прогресс-бар                 │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ Direct Python calls (same process)
┌──────────────────────────▼──────────────────────────────────────────┐
│                      Service Layer (unchanged)                      │
│  services/pipeline_service.py  — process_archive()                 │
│  services/lifecycle_service.py — статусы, MANUAL_STATUSES           │
│  services/version_service.py  — версионирование                    │
│  services/payment_service.py  — платёжный календарь                │
│  services/review_service.py   — ревью против шаблонов              │
│  services/client_manager.py   — мультиклиент                       │
│  services/telegram_sync.py    — Telegram очередь                   │
│  services/llama_server.py     — LlamaServerManager (singleton)     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
         ┌─────────────────┴─────────────────┐
         │                                   │
┌────────▼──────────┐             ┌──────────▼───────────┐
│  Processing Modules│             │   Data Layer          │
│  controller.py     │             │   SQLite (yurteg.db)  │
│  modules/*         │             │   File system         │
└───────────────────┘             └───────────────────────┘
```

---

## Component Responsibilities

| Component | Responsibility | Notes |
|-----------|---------------|-------|
| `app/main.py` | `ui.run()` entry, app.on_startup (llama-server, TG sync), layout root | Replaces old main.py |
| `app/state.py` | `AppState` dataclass: current_client, results, filters, selected_doc_id | Instantiated once per connection in `app.storage.client` |
| `app/pages/registry.py` | Таблица реестра, фильтры, поиск, открытие карточки | Core view |
| `app/pages/document.py` | Full-page карточка: метаданные, версии, ревью, пометки | Receives doc_id as URL param |
| `app/pages/templates.py` | Список шаблонов, добавление, удаление | Calls review_service |
| `app/pages/settings.py` | Провайдер, анонимизация, Telegram, предупреждения | Saves to settings.json |
| `app/components/header.py` | Топ-навигация: три таба + имя клиента | Shared across pages via sub_pages |
| `app/components/table.py` | `ui.aggrid` wrapper: колонки, фильтры, обработка rowClicked | Encapsulates AG Grid config |
| `app/components/process.py` | Выбор папки, кнопка запуска, прогресс-бар | Calls pipeline_service |

---

## Recommended Project Structure

```
yurteg/
├── app/
│   ├── __init__.py
│   ├── main.py              # ui.run() entry point, on_startup hooks
│   ├── state.py             # AppState dataclass definition
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── registry.py      # /  (default)
│   │   ├── document.py      # /document/{doc_id}
│   │   ├── templates.py     # /templates
│   │   └── settings.py      # /settings
│   └── components/
│       ├── __init__.py
│       ├── header.py        # shared top navigation
│       ├── table.py         # ag-grid registry wrapper
│       └── process.py       # folder picker + process button + progress
│
├── controller.py            # unchanged
├── config.py                # unchanged
├── modules/                 # unchanged
├── providers/               # unchanged
├── services/                # unchanged
├── tests/                   # unchanged
└── requirements.txt         # streamlit → nicegui
```

### Structure Rationale

- **`app/` subdirectory** — isolates new UI code from existing backend; a new developer sees immediately what is new and what is not touched.
- **`pages/` separation** — each page is a module with `def build(state: AppState)` function. Pages don't know about each other — they get state injected, not import each other.
- **`components/` extraction** — the header and table are reused across multiple pages; keeping them in separate modules prevents duplication.
- **`state.py` separate module** — imported by pages and components without circular imports. Single definition, easy to extend.

---

## Architectural Patterns

### Pattern 1: AppState via `app.storage.client`

**What:** Define a dataclass `AppState` holding all mutable UI state. On each page load, store/retrieve it from `app.storage.client['state']`. This replaces Streamlit's 45 `session_state` keys with one typed object.

**When to use:** Always — this is the NiceGUI equivalent of `st.session_state`. `app.storage.client` is in-memory, per-connection, disappears on page reload (same semantics as session_state). For state that must persist between sessions (e.g., active provider, warning_days), use the existing `~/.yurteg/settings.json` file (same as current).

**Trade-offs:** Slightly more boilerplate than bare dict, but type-checking catches bugs early.

**Example:**
```python
# app/state.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

@dataclass
class AppState:
    # Client/registry
    current_client: str = "Основной реестр"
    output_dir: Optional[Path] = None
    results: list = field(default_factory=list)
    # Filters
    filter_type: str = ""
    filter_status: str = ""
    filter_search: str = ""
    # UI navigation
    selected_doc_id: Optional[int] = None
    show_results: bool = False
    # Processing
    processing: bool = False
    source_dir: str = ""
    force_reprocess: bool = False

# app/main.py — getting/setting state
def get_state() -> AppState:
    if 'state' not in app.storage.client:
        app.storage.client['state'] = AppState()
    return app.storage.client['state']
```

---

### Pattern 2: `ui.sub_pages` for SPA Navigation

**What:** Use `ui.sub_pages({'/': registry, '/document/{doc_id}': document_page, '/templates': templates, '/settings': settings})` inside a shared root function that also renders the header. Navigation happens via `ui.navigate.to('/document/42')` — URL updates, header stays, only content area re-renders.

**When to use:** This is the right pattern for the "реестр = приложение" architecture. Full page reloads would lose state and feel sluggish. `ui.sub_pages` is the NiceGUI SPA primitive.

**Trade-offs:** `ui.sub_pages` is newer API (introduced ~2024). Nested sub_pages (sub_pages inside sub_pages) are not supported — keep routing flat.

**Example:**
```python
# app/main.py
from nicegui import ui, app
from app.components.header import render_header
from app.pages import registry, document, templates, settings

@ui.page('/')
def root():
    render_header()  # stays across all sub-page navigations
    ui.sub_pages({
        '/': registry.build,
        '/document/{doc_id}': document.build,
        '/templates': templates.build,
        '/settings': settings.build,
    })

ui.run(
    title='ЮрТэг',
    native=True,
    window_size=(1400, 900),
    storage_secret='yurteg-desktop-secret',
    dark=False,
    reload=False,
)
```

---

### Pattern 3: Singleton LlamaServerManager via `app.on_startup`

**What:** Replace `@st.cache_resource` with a module-level singleton initialized in `app.on_startup`. `app.on_startup` runs once when the NiceGUI server starts, before any client connects. Store the `LlamaServerManager` instance in a module-level variable, not in per-client storage.

**When to use:** For any resource that should survive between page navigations and be shared across all connections — exactly what `@st.cache_resource` was doing.

**Trade-offs:** `ensure_model()` may block for several minutes on first run (model download). This must run in a background thread/task to avoid blocking the event loop. Use `asyncio.get_event_loop().run_in_executor(None, manager.ensure_model)` or `app.on_startup` with `run.io_bound`.

**Example:**
```python
# app/main.py
from nicegui import app, run
from services.llama_server import LlamaServerManager
from modules.postprocessor import get_grammar_path
from config import Config

_llama_manager: LlamaServerManager | None = None

async def _start_llama():
    global _llama_manager
    config = Config()
    if config.active_provider != "ollama":
        return
    manager = LlamaServerManager(port=config.llama_server_port)
    try:
        # run blocking I/O (model download + server start) off the event loop
        await run.io_bound(manager.ensure_model)
        await run.io_bound(manager.start, get_grammar_path())
        _llama_manager = manager
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"llama-server failed to start: {e}")

async def _stop_llama():
    if _llama_manager:
        _llama_manager.stop()

app.on_startup(_start_llama)
app.on_shutdown(_stop_llama)

def get_llama_manager() -> LlamaServerManager | None:
    return _llama_manager
```

---

### Pattern 4: Blocking Pipeline in Background Thread

**What:** `pipeline_service.process_archive()` is CPU/IO-bound and runs synchronously (uses ThreadPoolExecutor internally). Call it via `await run.io_bound(...)` from an async NiceGUI event handler. Update UI progress via `ui.notify()` or a bound `ui.linear_progress` inside the `on_progress` callback — but callbacks must post updates to the event loop via `loop.call_soon_threadsafe`.

**When to use:** For any long-running blocking call from a NiceGUI button click handler.

**Trade-offs:** More explicit than Streamlit's `st.spinner` pattern but more flexible. The progress callback is called from the ThreadPoolExecutor thread, so must not touch NiceGUI UI objects directly.

**Example:**
```python
# app/components/process.py
import asyncio
from nicegui import ui, run

async def start_processing(state, config):
    loop = asyncio.get_event_loop()
    progress_bar = ui.linear_progress(value=0)
    label = ui.label("Начало обработки...")

    def on_progress(current: int, total: int, message: str):
        val = current / total if total > 0 else 0
        # Must schedule UI update on event loop thread
        loop.call_soon_threadsafe(progress_bar.set_value, val)
        loop.call_soon_threadsafe(label.set_text, message)

    def on_file_done(result):
        state.results.append(result)

    stats = await run.io_bound(
        pipeline_service.process_archive,
        Path(state.source_dir),
        config,
        on_progress=on_progress,
        on_file_done=on_file_done,
    )
    state.output_dir = stats['output_dir']
    state.show_results = True
    ui.navigate.to('/')  # refresh registry view
```

---

### Pattern 5: Clickable Registry Table via `ui.aggrid`

**What:** `ui.aggrid` wraps AG Grid (the same library Streamlit's `st.dataframe` uses under the hood). Configure `rowSelection: singleRow`, handle `rowClicked` event, navigate to `/document/{id}`. This replaces the current Streamlit dataframe with no native click support.

**When to use:** For any table that needs row-level interactivity — selection, click-to-open, inline status badges.

**Trade-offs:** AG Grid column definitions are verbose JSON. Encapsulate in `app/components/table.py` and pass data as rows list.

**Example:**
```python
# app/components/table.py
from nicegui import ui

def render_registry_table(rows: list[dict]):
    grid = ui.aggrid({
        'columnDefs': [
            {'headerName': 'Тип', 'field': 'doc_type', 'width': 180},
            {'headerName': 'Контрагент', 'field': 'counterparty', 'flex': 1},
            {'headerName': 'Статус', 'field': 'status_label', 'width': 130,
             'cellStyle': {'cursor': 'pointer'}},
            {'headerName': 'Действует до', 'field': 'date_end', 'width': 150},
            {'headerName': 'Сумма', 'field': 'amount', 'width': 120},
        ],
        'rowData': rows,
        'rowSelection': {'mode': 'singleRow'},
        'domLayout': 'autoHeight',
    }).classes('w-full')

    async def on_row_click(event):
        doc_id = event.args['data'].get('id')
        if doc_id:
            ui.navigate.to(f'/document/{doc_id}')

    grid.on('rowClicked', on_row_click)
    return grid
```

---

## Data Flow

### Page Navigation Flow

```
User clicks "Документы" tab in header
        |
        v
ui.navigate.to('/') — URL changes, sub_pages container re-renders
        |
        v
registry.build(state) called
        |
        v
loads db from state.output_dir
calls get_computed_status_sql() for each row
applies filter_type, filter_status, filter_search from state
        |
        v
render_registry_table(rows) — ui.aggrid renders
        |
User clicks row → on_row_click → ui.navigate.to('/document/42')
        |
        v
document.build(state, doc_id=42)
```

### Processing Flow (async)

```
User clicks "Запустить" button
        |
        v
async start_processing(state, config)
        |
        v
await run.io_bound(pipeline_service.process_archive, ...)
        |   [runs in thread pool, event loop free]
        |
        +---> on_progress(current, total, msg)
        |         loop.call_soon_threadsafe → update progress_bar
        |
        +---> on_file_done(result)
        |         state.results.append(result)
        |
        v
stats returned → state updated → ui.navigate.to('/')
```

### State Management

```
app.storage.client['state'] = AppState()  (per-connection, in-memory)
        |
        v
Pages read: state = get_state()
Pages write: state.filter_type = "Договор аренды"
        |
        v
Persistent settings (active_provider, warning_days, Telegram):
~/.yurteg/settings.json   (same as current, read by config.py)
```

---

## Build Order (Migration Phases)

**Phase 1 — Skeleton + Navigation (no services yet)**
- Create `app/` directory structure
- `app/main.py`: `ui.run()` with native mode + `ui.sub_pages`
- `app/state.py`: `AppState` dataclass + `get_state()`
- `app/components/header.py`: top navigation with three tabs (no functionality, navigates routes)
- `app/pages/registry.py`: empty layout placeholder
- `app/pages/document.py`: empty layout placeholder
- `app/pages/settings.py`: empty layout placeholder
- `app/pages/templates.py`: empty layout placeholder
- **Deliverable:** App launches, navigation works, empty views visible

**Phase 2 — Registry View (core product)**
- Wire `modules/database.py` + `lifecycle_service` to registry page
- `app/components/table.py`: ag-grid with columns, row click, status badges
- Filters: type, status, search
- Client selector (calls `client_manager.list_clients()`)
- **Deliverable:** Existing documents display in registry with filters

**Phase 3 — Document Card**
- `app/pages/document.py`: full-page layout
- Metadata display (all fields from ProcessingResult)
- Lawyer notes (read/write from DB)
- Version list + diff view (calls `version_service`)
- Review tab (calls `review_service`)
- Manual status override (calls `lifecycle_service.set_manual_status`)
- **Deliverable:** Clicking a row opens full document details

**Phase 4 — Processing (pipeline wiring)**
- `app/components/process.py`: folder picker + process button + progress bar
- Wire `app.on_startup` for `LlamaServerManager` singleton
- Wire `pipeline_service.process_archive` via `run.io_bound`
- Telegram queue fetch on startup (`telegram_sync`)
- **Deliverable:** Can process new documents from UI

**Phase 5 — Settings + Templates**
- `app/pages/settings.py`: provider selector, anonymization toggle, Telegram config, warning days
- `app/pages/templates.py`: list, add, delete templates (calls `review_service`)
- Persists to `~/.yurteg/settings.json`
- **Deliverable:** Full parity with current Streamlit settings

**Phase 6 — Polish (design milestone)**
- Apply typography, spacing, color system (Tailwind via NiceGUI classes)
- Empty state + onboarding for first launch
- Calendar view in registry (payment events from `payment_service`)
- Attention panel for expiring documents
- **Deliverable:** Production-ready UI

---

## Integration Points

### Services Wired Into NiceGUI Handlers

| Service | Where Called | NiceGUI Pattern |
|---------|-------------|-----------------|
| `pipeline_service.process_archive()` | `process.py` button click | `await run.io_bound(...)` |
| `lifecycle_service.get_computed_status_sql()` | `registry.py` data load | Direct call (fast SQL) |
| `lifecycle_service.set_manual_status()` | `document.py` status override | Direct call in `on_click` |
| `lifecycle_service.get_attention_required()` | `registry.py` header panel | Direct call |
| `version_service.get_version_group()` | `document.py` versions tab | Direct call |
| `version_service.diff_versions()` | `document.py` diff view | `await run.io_bound(...)` if slow |
| `payment_service.get_calendar_events()` | `registry.py` calendar view | Direct call |
| `review_service.review_against_template()` | `document.py` review tab | `await run.io_bound(...)` |
| `review_service.list_templates()` | `templates.py` | Direct call |
| `client_manager.list_clients()` | `header.py` client select | Direct call |
| `telegram_sync` | `main.py` on_startup | `await run.io_bound(...)` once |
| `LlamaServerManager` | `main.py` on_startup | Module-level singleton |

### New vs Modified Components

| Component | Status | Notes |
|-----------|--------|-------|
| `app/main.py` | NEW | Replaces old `main.py` |
| `app/state.py` | NEW | Replaces `st.session_state` |
| `app/pages/*.py` | NEW | All new |
| `app/components/*.py` | NEW | All new |
| `services/llama_server.py` | UNCHANGED | Singleton managed differently |
| `services/*.py` | UNCHANGED | All services unchanged |
| `modules/*.py` | UNCHANGED | All modules unchanged |
| `controller.py` | UNCHANGED | |
| `config.py` | UNCHANGED | |
| `providers/*.py` | UNCHANGED | |
| `requirements.txt` | MODIFIED | Remove streamlit/streamlit-calendar, add nicegui |

---

## Anti-Patterns

### Anti-Pattern 1: Porting `st.rerun()` Logic Directly

**What people do:** Find every `st.rerun()` call and try to find a NiceGUI equivalent. NiceGUI has no `rerun()`.

**Why it's wrong:** `st.rerun()` was a Streamlit workaround for the lack of reactive state. NiceGUI has actual reactivity — binding UI elements to state values means they update automatically when state changes, without a full re-render.

**Do this instead:** Use `ui.label().bind_text_from(state_obj, 'field')` for display values. For table re-renders, call `.update()` on the aggrid element or simply re-navigate to the page. Most `st.rerun()` calls can be eliminated entirely by restructuring as reactive bindings.

---

### Anti-Pattern 2: One Giant `main.py` Again

**What people do:** Translate the 2247-line Streamlit main.py into a 2247-line NiceGUI main.py.

**Why it's wrong:** NiceGUI pages are naturally modular — each `@ui.page` or sub-page function should live in its own module. A monolith loses this structure and makes the design milestone (Phase 6) much harder to execute.

**Do this instead:** Follow the `app/pages/` structure above. Each page module exports a single `build(state)` function. `main.py` only contains `ui.run()`, `app.on_startup` hooks, and the `ui.sub_pages` routing table.

---

### Anti-Pattern 3: Calling Blocking Services Directly in `on_click`

**What people do:** Call `pipeline_service.process_archive()` directly inside a button click handler (which is an async function in NiceGUI).

**Why it's wrong:** This blocks the asyncio event loop for the entire duration of processing (potentially minutes). The UI freezes — no progress updates, no other interactions.

**Do this instead:** Always use `await run.io_bound(blocking_function, *args)` for any call that involves disk I/O, network, or `ThreadPoolExecutor`. Progress callbacks must use `loop.call_soon_threadsafe()` to post UI updates back to the event loop.

---

### Anti-Pattern 4: Per-Client Storage for Singleton Resources

**What people do:** Store `LlamaServerManager` in `app.storage.client` (per connection) or `app.storage.user` (per session).

**Why it's wrong:** The llama-server is a subprocess — there should only ever be one instance. Storing it per-client would try to start multiple instances, conflict on the same port, or leak processes.

**Do this instead:** Module-level variable, initialized exactly once in `app.on_startup`. Expose via `get_llama_manager()` accessor. `app.on_shutdown` calls `manager.stop()`.

---

## NiceGUI Storage Reference

| Storage | Scope | Persistence | Use For |
|---------|-------|-------------|---------|
| `app.storage.client` | Per connection | Lost on reload | UI state (AppState) — replaces `st.session_state` |
| `app.storage.user` | Per browser session | Survives reloads | User preferences if multi-user ever needed |
| `app.storage.general` | All connections | Server memory | Global counters — not needed here |
| Module-level var | Application | Process lifetime | LlamaServerManager singleton |
| `~/.yurteg/settings.json` | Disk | Permanent | Provider, Telegram, warning_days |
| `~/.yurteg/yurteg.db` | Disk (SQLite) | Permanent | All contract data |

---

## Sources

- NiceGUI Storage documentation: [https://nicegui.io/documentation/storage](https://nicegui.io/documentation/storage) (HIGH confidence)
- NiceGUI ui.run() documentation: [https://nicegui.io/documentation/run](https://nicegui.io/documentation/run) (HIGH confidence)
- NiceGUI ui.sub_pages documentation: [https://nicegui.io/documentation/sub_pages](https://nicegui.io/documentation/sub_pages) (HIGH confidence)
- NiceGUI ui.aggrid documentation: [https://nicegui.io/documentation/aggrid](https://nicegui.io/documentation/aggrid) (HIGH confidence)
- NiceGUI Pages & Routing: [https://nicegui.io/documentation/section_pages_routing](https://nicegui.io/documentation/section_pages_routing) (HIGH confidence)
- NiceGUI Configuration & Deployment: [https://nicegui.io/documentation/section_configuration_deployment](https://nicegui.io/documentation/section_configuration_deployment) (HIGH confidence)
- NiceGUI background thread discussion: [https://github.com/zauberzeug/nicegui/discussions/836](https://github.com/zauberzeug/nicegui/discussions/836) (MEDIUM confidence)
- NiceGUI NiceGUI 3.0 episode (patterns): [https://talkpython.fm/episodes/show/525/nicegui-goes-3.0](https://talkpython.fm/episodes/show/525/nicegui-goes-3.0) (MEDIUM confidence)
- Current codebase: `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/main.py` (direct analysis, HIGH confidence)

---

*Architecture research for: ЮрТэг — Streamlit → NiceGUI migration*
*Researched: 2026-03-21*
