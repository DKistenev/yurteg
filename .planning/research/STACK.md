# Stack Research

**Domain:** Python desktop app UI layer — migration from Streamlit to NiceGUI
**Researched:** 2026-03-21
**Confidence:** HIGH (NiceGUI v3 verified via official docs + pyproject.toml; all APIs cross-checked against nicegui.io)

---

## Context

This is a targeted UI-layer replacement for ЮрТэг v0.6. The existing Python backend (controller, modules, services, SQLite, openai SDK, llama-server) is **not changing**. Only the UI shell changes: Streamlit out, NiceGUI in.

The goal: registry-centric single-workspace app, clickable table, full-page document card, three top tabs (Documents / Templates / Settings), light professional theme, desktop window via native mode.

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| NiceGUI | 3.9.0 | Full UI framework replacing Streamlit | Latest stable (released 2026-03-19). Based on FastAPI + Vue + Quasar + Tailwind. Provides clickable tables, native split-views, proper navigation without page reloads, desktop window mode. Streamlit fought the single-workspace architecture at every turn; NiceGUI embraces it. |
| pywebview | >=5.0.1, <7 | Desktop native window (macOS/Windows) | NiceGUI's optional `native` extra depends on pywebview 5.x. Wraps a system WebView in a borderless window — no Electron, no Chromium bundling. macOS uses WKWebView, Windows uses EdgeChromium. |
| Tailwind CSS | 4.x (bundled) | Utility-class styling | Built into NiceGUI v3. Applied via `.classes()` on any element. No separate install. v3 removed the Python `.tailwind()` wrapper — use `.classes()` directly. |
| Quasar | bundled | Component system under NiceGUI | Every NiceGUI element maps to a Quasar Vue component. Access full Quasar props via `.props()`. Color tokens (primary, secondary, accent) customizable via `ui.colors()`. |

### UI Component Map

| Component Needed | NiceGUI API | Notes |
|-----------------|-------------|-------|
| Clickable data table with sort/filter | `ui.aggrid` | AG Grid wrapped by NiceGUI. Column-level `filter`, `floatingFilter`, `sort`. Row click via `on_row_click`. Superior to `ui.table` for large datasets and inline filtering. |
| Simple static table | `ui.table` | Based on Quasar QTable. Use for small tables where AG Grid feels heavy (e.g., template list). Has `set_filter()`, sortable columns, row selection. |
| Top-level tab navigation | `ui.tabs` + `ui.tab_panels` | Declare tabs in header, bind panels below. Supports icon + label tabs. |
| Persistent top bar | `ui.header` | Renders above all content. Put `ui.tabs` inside it for top-level navigation. |
| Full-page view transition | `ui.sub_pages()` or `ui.navigate.to()` | `ui.sub_pages()` swaps content without browser reload (SPA pattern). `ui.navigate.to('/doc/123')` does a full page replace — fine for detail views. |
| Session / per-user state | `app.storage.user` | Persists across requests for one user. `app.storage.tab` for tab-isolated state. Use for current client selection, active filters, open document ID. |
| Two-pane split layout | `ui.splitter` | Resizable horizontal or vertical split. Good for list + detail, but full-page replace is simpler for the document card. |
| Card container | `ui.card` | Dropped shadow container. Use for document card header area, form sections in Settings. |
| Vertical / horizontal flex | `ui.column`, `ui.row` | Context-manager based. `ui.column().classes('w-full gap-4')` is the bread-and-butter layout. |
| Notification toast | `ui.notify()` | Built-in. Replaces `st.toast`. Accepts `type='warning'`, `type='positive'`, etc. |
| Light mode lock | `ui.dark_mode(value=False)` | Call once per page. Overrides global dark/system setting. Value=False = always light. |
| Custom CSS | `ui.add_head_html('<style>...</style>')` | For global resets, font-face, Tailwind component classes via `@layer components`. |
| Color theme | `ui.colors(primary='#...', secondary='#...')` | Sets Quasar color tokens globally. Call once at app startup. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| nicegui | 3.9.0 | Core UI | Always |
| nicegui[native] | 3.9.0 | Adds pywebview for desktop window | When building DMG/EXE deliverable. In dev, run without native=True. |
| pywebview | >=5.0.1 | macOS WKWebView / Windows EdgeChromium window | Installed automatically via `nicegui[native]`. |

No additional CSS framework, no JS bundler, no Vite. NiceGUI ships Tailwind + Quasar pre-bundled.

---

## Key API Patterns

### Table with Sort, Filter, Row Click (ui.aggrid)

```python
from nicegui import ui

columns = [
    {'headerName': 'Документ', 'field': 'name', 'filter': 'agTextColumnFilter', 'floatingFilter': True, 'flex': 2},
    {'headerName': 'Тип', 'field': 'doc_type', 'filter': 'agTextColumnFilter', 'floatingFilter': True, 'flex': 1},
    {'headerName': 'Статус', 'field': 'status', 'filter': 'agTextColumnFilter', 'floatingFilter': True, 'flex': 1},
    {'headerName': 'Срок', 'field': 'deadline', 'sortable': True, 'flex': 1},
]

grid = ui.aggrid({
    'columnDefs': columns,
    'rowData': rows,          # list of dicts from DocumentService
    'rowSelection': 'single',
    'defaultColDef': {'sortable': True, 'resizable': True},
}).classes('w-full h-full')

grid.on('rowClicked', lambda e: open_document(e.args['data']['id']))
```

**Data updates:** Assign directly to `grid.options['rowData']` then call `grid.update()`. Do NOT mutate the original `rows` list — NiceGUI v3 removed auto-detection of mutable object changes.

### Full-Page View Transitions

```python
from nicegui import ui, app

@ui.page('/')
def registry_page():
    # main registry with aggrid

@ui.page('/doc/{doc_id}')
def document_page(doc_id: int):
    doc = document_service.get(doc_id)
    # full-page card

# Navigate programmatically:
ui.navigate.to(f'/doc/{doc_id}')
ui.navigate.back()
```

For SPA-style swap without URL change, use `ui.sub_pages({'/': registry, '/doc': doc_card})`.

### Session State

```python
from nicegui import app

# Store selected client across navigation
app.storage.user['active_client_id'] = client_id

# Read
client_id = app.storage.user.get('active_client_id')
```

`app.storage.user` requires `app.storage.secret` set in `ui.run()`.

### App Shell with Persistent Header + Tabs

```python
from nicegui import ui

@ui.page('/')
def main():
    ui.dark_mode(value=False)

    with ui.header().classes('bg-white border-b border-gray-200 px-6 py-3'):
        ui.label('ЮрТэг').classes('text-lg font-semibold text-gray-900')
        with ui.tabs().classes('ml-8') as tabs:
            tab_docs = ui.tab('docs', label='Документы')
            tab_templates = ui.tab('templates', label='Шаблоны')
            tab_settings = ui.tab('settings', label='Настройки')

    with ui.tab_panels(tabs, value=tab_docs).classes('w-full flex-1'):
        with ui.tab_panel(tab_docs):
            build_registry()
        with ui.tab_panel(tab_templates):
            build_templates()
        with ui.tab_panel(tab_settings):
            build_settings()
```

### Theming — Light Mode, Professional Palette

```python
from nicegui import ui

# Called once at startup, before ui.run()
ui.colors(
    primary='#1A56DB',    # action blue — buttons, links, active states
    secondary='#6B7280',  # muted gray
    accent='#059669',     # status green (active contracts)
    dark='#111827',
    positive='#059669',
    negative='#DC2626',
    warning='#D97706',
    info='#1A56DB',
)

# Per-page: force light mode
ui.dark_mode(value=False)

# Global font and base styles
ui.add_head_html('''
<style type="text/tailwindcss">
  @layer base {
    body { font-family: 'Inter', system-ui, sans-serif; }
  }
  @layer components {
    .status-active { @apply bg-green-100 text-green-800 text-xs font-medium px-2 py-0.5 rounded; }
    .status-expiring { @apply bg-yellow-100 text-yellow-800 text-xs font-medium px-2 py-0.5 rounded; }
    .status-expired { @apply bg-red-100 text-red-800 text-xs font-medium px-2 py-0.5 rounded; }
  }
</style>
''')
```

### Integrating Existing Python Services

Services are plain Python objects — no special wiring needed. Pass them into page functions as closures or module-level singletons:

```python
# services.py — initialized once at module level
from modules.document_service import DocumentService
from modules.template_service import TemplateService

document_service = DocumentService(db_path='data/yurteg.db')
template_service = TemplateService(db_path='data/yurteg.db')
```

```python
# main.py
from services import document_service

@ui.page('/')
def registry():
    docs = document_service.list_all()   # direct call, no HTTP
    grid = ui.aggrid({'rowData': docs, ...})
```

`app.on_startup` for one-time initialization (e.g., starting the reminder scheduler):

```python
from nicegui import app

@app.on_startup
async def startup():
    reminder_service.start_scheduler()

@app.on_shutdown
async def shutdown():
    reminder_service.stop_scheduler()
```

Background work (non-blocking):

```python
from nicegui import background_tasks, run

# I/O-bound (e.g., calling llama-server)
result = await run.io_bound(ai_extractor.extract, text)

# CPU-bound (e.g., bulk anonymization)
result = await run.cpu_bound(anonymizer.process, text)

# Fire-and-forget
background_tasks.create(process_file_async(path))
```

### Desktop Native Mode

```python
# config at module level — NOT inside if __name__ == '__main__'
from nicegui import app

app.native.window_args['title'] = 'ЮрТэг'
app.native.window_args['min_size'] = (1024, 720)
app.native.settings['ALLOW_DOWNLOADS'] = True

ui.run(
    native=True,
    window_size=(1280, 800),
    title='ЮрТэг',
    storage_secret='yurteg-secret-key',
    reload=False,            # disable hot-reload in production builds
)
```

**Critical:** native configuration must be at module level, not inside `if __name__ == '__main__'` — native mode spawns a subprocess that ignores the main guard.

**Install for native mode:**
```bash
pip install "nicegui[native]==3.9.0"
# installs pywebview>=5.0.1 automatically
```

---

## Installation

```bash
# Core — browser-based dev
pip install "nicegui==3.9.0"

# With desktop window support
pip install "nicegui[native]==3.9.0"

# No other UI dependencies needed
# Streamlit can be removed from requirements.txt
```

Remove from requirements.txt after migration is confirmed working:
- `streamlit`
- `streamlit-server-state` (if used)

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| `ui.aggrid` for main registry | `ui.table` (Quasar QTable) | `ui.table` has set_filter() and sortable columns but no floating mini-filters in column headers. For 500+ document registries with per-column filtering, AG Grid is materially better UX. |
| `ui.table` for templates list | `ui.aggrid` | Templates list is small (10–30 rows), rarely filtered. Quasar QTable is lighter and feels more native for a simple list. |
| `ui.navigate.to('/doc/{id}')` | `ui.sub_pages` in-place swap | Full URL navigation is simpler, supports browser back button, and is easier to implement per-client state. Sub_pages is better for dashboards that need instant switching without URL changes. |
| NiceGUI | Streamlit | Streamlit's rerun model makes it impossible to have persistent UI state (like an open document card) alongside a running pipeline. Every interaction triggers a full script rerun. This caused the toolbar/state hacks in v0.4-v0.5. |
| NiceGUI | PyQt6 / Tkinter | Python GUI toolkits give no web renderer, no Tailwind, no Quasar components. Would require hand-building every table, tab, and toast. |
| NiceGUI | Electron + FastAPI | Requires Node.js, a bundler, and a separate frontend codebase. Three-lawyer team with no developer cannot maintain that split. |
| NiceGUI | Flet (Flutter) | Flet 0.x is Flutter-based — good mobile story, poor web/Tailwind story. Less ecosystem maturity than NiceGUI. No AG Grid equivalent. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `.tailwind()` method | Removed in NiceGUI v3. Raises AttributeError. | `.classes('tailwind-class-name')` |
| Mutating original `rows` list to update table | NiceGUI v3 no longer detects mutable object changes. Table will not update. | `grid.options['rowData'] = new_rows; grid.update()` |
| Placing native config inside `if __name__ == '__main__'` | Subprocess ignores main guard — config silently not applied. | Module-level `app.native.window_args[...]` |
| `ui.run(reload=True)` in production DMG | Hot-reload file watcher causes issues inside PyInstaller bundles. | `ui.run(reload=False)` |
| Streamlit patterns (st.session_state, st.rerun) | Do not exist in NiceGUI. | `app.storage.user`, reactive bindings, `ui.update()` |
| Global scope UI elements (v2 auto-index pattern) | Removed in NiceGUI v3. Shared auto-index client gone. | `@ui.page('/')` decorator for all pages |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| nicegui 3.9.0 | Python 3.10–3.13 | Minimum Python bumped to 3.10 in v3 |
| nicegui 3.9.0 | fastapi >=0.109.1 | FastAPI is a core dep, not optional |
| nicegui 3.9.0 | pywebview >=5.0.1, <7 | Optional, via `nicegui[native]` |
| nicegui 3.9.0 | pydantic-core >=2.35.0 | Pinned; do not downgrade pydantic for other deps |
| pywebview 5.x | macOS 12+ | WKWebView backend. Works on macOS 12 Monterey and later. |
| pywebview 5.x | Windows 10+ | EdgeChromium backend. .NET not required for pywebview 5.x (unlike older versions). |

**Existing stack compatibility:** NiceGUI brings its own FastAPI and uvicorn. If the project already uses FastAPI for services, they can share the same app instance via `app.include_router()`. The openai SDK, pdfplumber, natasha, sqlite3, and all other pipeline modules are unaffected — NiceGUI is purely a UI concern.

---

## Sources

- [NiceGUI official docs — nicegui.io/documentation](https://nicegui.io/documentation) — HIGH confidence
- [NiceGUI pyproject.toml — github.com/zauberzeug/nicegui/blob/main/pyproject.toml](https://github.com/zauberzeug/nicegui/blob/main/pyproject.toml) — HIGH confidence (verified pywebview >=5.0.1, fastapi >=0.109.1, Python >=3.10)
- [NiceGUI v3 changelog discussion — github.com/zauberzeug/nicegui/discussions/5331](https://github.com/zauberzeug/nicegui/discussions/5331) — HIGH confidence (.tailwind() removed, mutable objects change, auto-index removed)
- [ui.table docs — nicegui.io/documentation/table](https://nicegui.io/documentation/table) — HIGH confidence
- [ui.aggrid docs — nicegui.io/documentation/aggrid](https://nicegui.io/documentation/aggrid) — HIGH confidence
- [ui.navigate docs — nicegui.io/documentation/navigate](https://nicegui.io/documentation/navigate) — HIGH confidence
- [ui.dark_mode docs — nicegui.io/documentation/dark_mode](https://nicegui.io/documentation/dark_mode) — HIGH confidence
- [Section: Pages & Routing — nicegui.io/documentation/section_pages_routing](https://nicegui.io/documentation/section_pages_routing) — HIGH confidence (sub_pages, app.storage)
- [Section: Configuration & Deployment — nicegui.io/documentation/section_configuration_deployment](https://nicegui.io/documentation/section_configuration_deployment) — HIGH confidence (app.native, ui.run params)
- [Section: Styling & Appearance — nicegui.io/documentation/section_styling_appearance](https://nicegui.io/documentation/section_styling_appearance) — HIGH confidence (CSS layers, add_head_html, classes)

---

*Stack research for: ЮрТэг v0.6 — NiceGUI UI migration*
*Researched: 2026-03-21*
