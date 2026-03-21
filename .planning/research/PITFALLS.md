# Pitfalls Research

**Domain:** Streamlit → NiceGUI migration, desktop Python app (legal document processing)
**Researched:** 2026-03-21
**Confidence:** HIGH (most pitfalls confirmed via official NiceGUI GitHub issues, FAQs, and verified bug reports)

> This file replaces the v0.4/v0.5 pitfalls doc and focuses on the v0.6 UI migration.
> Previous milestone pitfalls (deadline tracking, multi-provider AI) remain valid as business logic is unchanged.

---

## Critical Pitfalls

### Pitfall 1: Global Scope UI Elements Shared Across All Clients

**What goes wrong:**
Any `ui.*` element created at module level (outside a `@ui.page`-decorated function) is shared across all browser connections. In multi-client mode — one NiceGUI server serving several lawyers — client A sees client B's document registry. The registry becomes a shared mutable blob.

**Why it happens:**
Developers coming from Streamlit assume script-level code is per-session, because Streamlit reruns the entire script per user. NiceGUI is the opposite: module-level elements live once, globally, across all connections. There is no per-connection "rerun" model.

**How to avoid:**
Every page must be wrapped in a `@ui.page('/')` decorated function. All state — selected client DB, current document, filter values — must live in `app.storage.user` or inside the page function's local scope, never in module-level Python variables.

```python
# WRONG — shared across all clients
table = ui.table(columns=..., rows=...)

# RIGHT — isolated per client connection
@ui.page('/')
def index():
    table = ui.table(columns=..., rows=...)
```

**Warning signs:**
- One user's filter change affects another user's view in a different tab
- Multi-client mode shows one lawyer's documents to another

**Phase to address:** Phase 1 (app scaffold) — establish the `@ui.page` architecture before building any screens.

---

### Pitfall 2: Blocking the Async Event Loop with Synchronous SQLite Calls

**What goes wrong:**
Standard `sqlite3` is synchronous. Calling it directly inside an `async def` page handler or any async UI callback blocks the entire NiceGUI event loop. The UI freezes — no spinner, no button response — until the query finishes. With 500+ documents even a simple `SELECT *` causes a noticeable pause for all connected clients simultaneously.

**Why it happens:**
NiceGUI runs on FastAPI/Starlette's asyncio event loop. Any blocking call that takes >10ms stalls every connected client. The existing ЮрТэг codebase uses plain `sqlite3`, which was fine for Streamlit (which spawns a new OS thread per session) but breaks NiceGUI's single-threaded async model.

**How to avoid:**
Wrap every database call in `run.io_bound()`:

```python
from nicegui import run

async def load_documents(client_id: str):
    rows = await run.io_bound(db_service.get_all_documents, client_id)
    table.rows = rows
    table.update()
```

Alternatively migrate to `aiosqlite` for native async SQLite. For ЮрТэг, wrapping the existing `database.py` service calls with `run.io_bound()` is the lower-risk path — business logic remains unchanged.

**Warning signs:**
- UI becomes unresponsive during any data load
- NiceGUI WebSocket timeout errors appear in browser DevTools console
- Spinner component never animates (event loop blocked before it can render)

**Phase to address:** Phase 1 (DB integration layer) — establish the async wrapper pattern before wiring any UI element to data.

---

### Pitfall 3: llama-server Subprocess Leaked on App Close

**What goes wrong:**
`llama-server` is started as a `subprocess.Popen()` child. When the NiceGUI window closes in native mode, `app.on_shutdown()` is **not reliably called** — this is a confirmed, documented NiceGUI bug (issue #2107). The llama-server process keeps running in the background, consuming ~1.5 GB RAM and a CPU core indefinitely after the user has "closed" the app.

**Why it happens:**
`native=True` uses pywebview. When the OS window closes, the webview quits, but the underlying asyncio/FastAPI server does not always trigger the full shutdown lifecycle on macOS. This is a NiceGUI issue, not a user error.

**How to avoid:**
Register cleanup on both shutdown and disconnect hooks, plus `atexit` as a final safety net:

```python
app.on_disconnect(provider_manager.stop_local_server)
app.on_shutdown(provider_manager.stop_local_server)

import atexit
atexit.register(provider_manager.stop_local_server)
```

On macOS, also handle `signal.SIGTERM` since PyInstaller-packaged apps may receive SIGTERM instead of a graceful shutdown event.

**Warning signs:**
- `ps aux | grep llama` shows server running after the app window was closed
- RAM usage does not drop after closing the app
- Second app launch fails with "port already in use" on llama-server's port (default 8080)

**Phase to address:** Phase 2 (local LLM wiring) — implement triple-layer cleanup from day one, not as a post-launch fix.

---

### Pitfall 4: Double Initialization on Startup Launches llama-server Twice

**What goes wrong:**
With `reload=True` (NiceGUI's default setting), the main module runs twice: once in the parent process, once in the child subprocess. Any code at module level — including `subprocess.Popen(llama_server)`, HuggingFace model downloads, and DB schema initialization — executes twice. Two llama-server processes start simultaneously on the same port. The second one crashes and the error is silent.

**Why it happens:**
NiceGUI's hot-reload spawns a subprocess where `__name__ == '__mp_main__'`, bypassing the standard `if __name__ == '__main__'` guard. Import-time side effects in NiceGUI itself (FastAPI init, ~200 element class loading) also double-run (issue #5684).

**How to avoid:**
Always use `reload=False` in production. Wrap all startup side effects in `app.on_startup()`:

```python
app.on_startup(provider_manager.autostart_local_server)
ui.run(reload=False, native=True, host='127.0.0.1', port=8888)
```

**Warning signs:**
- Two llama-server processes visible in Activity Monitor immediately after launch
- "Address already in use" error on llama-server port in logs
- DB migration runs twice causing SQLite constraint errors in logs

**Phase to address:** Phase 1 (app entrypoint scaffolding) — set `reload=False` and move all startup logic to `app.on_startup` before any feature code is added.

---

### Pitfall 5: `ui.upload` Provides No File Path — Only Bytes in Memory

**What goes wrong:**
`ui.upload` does not expose the original file's path on disk. It delivers file content as bytes via the `on_upload` callback. The existing ЮрТэг pipeline (`scanner.py`, `extractor.py`, `controller.py`) works with `pathlib.Path` objects throughout. Wiring `ui.upload` directly to the pipeline breaks immediately at the type boundary.

**Why it happens:**
Browser security prevents JavaScript from accessing real filesystem paths, and NiceGUI's `ui.upload` follows browser semantics even in native desktop mode.

**How to avoid:**
Use the native OS file picker instead of `ui.upload` for the batch import use case:

```python
# Native file dialog — returns actual Path objects
result = await app.native.main_window.create_file_dialog(
    allow_multiple=True,
    file_types=['PDF files (*.pdf)', 'Word files (*.docx)']
)
paths = [Path(p) for p in result]
await run.io_bound(controller.process_files, paths)
```

For individual file drop scenarios, save bytes to `tempfile.NamedTemporaryFile` and pass the temp path to the pipeline.

**Warning signs:**
- `e.name` gives the filename but `e.content.read()` gives bytes with no path attribute
- Pipeline errors: `TypeError: expected str, bytes or os.PathLike object`

**Phase to address:** Phase 2 (file import screen) — choose native picker vs. upload widget as an explicit architecture decision before any import UI is built.

---

### Pitfall 6: Large File Downloads Block the Event Loop

**What goes wrong:**
`ui.download(content, filename)` where `content` is a large bytes object (Excel export of 300+ documents can reach 50–200 MB) freezes the entire NiceGUI event loop before the download starts. All other UI interactions halt. For files ≥1 GB (e.g., bulk PDF archive exports) the download silently fails with no error message shown (issue #3756).

**Why it happens:**
`ui.download()` serializes the full content synchronously in the async event loop before streaming to the browser. This is a known NiceGUI limitation with no built-in workaround.

**How to avoid:**
Serve large files via a FastAPI route. NiceGUI exposes its underlying FastAPI app as `app`:

```python
from fastapi.responses import FileResponse
from nicegui import app as nicegui_app

@nicegui_app.get('/export/registry')
async def export_registry(client_id: str):
    path = await run.io_bound(reporter.generate_excel, client_id)
    return FileResponse(str(path), filename='registry.xlsx',
                        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# In UI:
ui.link('Скачать реестр', '/export/registry?client_id=...')
```

**Warning signs:**
- UI hangs for 5–10 seconds after clicking "Export to Excel" with a large dataset
- Browser shows no download progress bar, then file appears suddenly
- With very large datasets, browser tab shows "Waiting for response…" indefinitely

**Phase to address:** Phase 3 (export/reporting features) — always route file downloads through FastAPI `FileResponse`, never through `ui.download` for any file that could exceed 5 MB.

---

### Pitfall 7: Tailwind Dynamic Class Names Silently Ignored

**What goes wrong:**
NiceGUI uses Tailwind CSS in JIT mode. Class names constructed dynamically in Python (e.g., `f'bg-{color}-500'`) are not present in the initial HTML, so Tailwind's JIT purger excludes them from the generated CSS. The class appears in the DOM via DevTools but has zero CSS rules attached — the style is silently not applied.

**Why it happens:**
Tailwind JIT scans source files for class name strings at build/startup time. Dynamically constructed strings are invisible to the scanner. This is documented Tailwind behavior that surprises Python developers who are not familiar with Tailwind's compilation model.

**How to avoid:**
Never construct Tailwind class names dynamically via string interpolation. Always use full, literal class name strings:

```python
# WRONG
status = 'expiring'
row.classes(f'bg-{status}-100')  # Tailwind never sees 'bg-expiring-100'

# RIGHT — use a lookup dict with literal strings
STATUS_COLORS = {
    'active':   'bg-green-50 text-green-700',
    'expiring': 'bg-yellow-50 text-yellow-700',
    'expired':  'bg-red-50 text-red-700',
}
row.classes(STATUS_COLORS[status])
```

For reusable component styles, define them via `ui.add_head_html('<style type="text/tailwindcss">@layer components { .doc-card { @apply rounded-lg border ... } }</style>')`.

**Warning signs:**
- Element has the expected class name in browser DevTools inspector
- No visual change — class has no associated CSS rule in the Styles panel
- Works with hardcoded class strings, breaks when class name is computed from a variable

**Phase to address:** Phase 2 (theming and component library) — document the styling conventions including this constraint before any screen is built.

---

### Pitfall 8: PyInstaller Misses NiceGUI Static Assets — App Crashes on Launch

**What goes wrong:**
PyInstaller-bundled app crashes on launch with `RuntimeError: Static directory does not exist` or shows blank pages. NiceGUI copies its `static/` and `templates/` directories (~15 MB of JS/CSS/font assets) to a temp path at startup, but PyInstaller doesn't include them unless explicitly told to (discussion #1135, issue #355).

**Why it happens:**
PyInstaller traces Python imports but ignores data files accessed via `__file__`-relative paths. NiceGUI's assets are non-Python files.

**How to avoid:**
Add explicit `datas` entries to the `.spec` file:

```python
import nicegui
datas = [
    (str(Path(nicegui.__file__).parent / 'static'), 'nicegui/static'),
    (str(Path(nicegui.__file__).parent / 'templates'), 'nicegui/templates'),
]
```

Also: never use `--noconsole` / `--windowed` flags with NiceGUI unless the server is explicitly started outside the console process — it will silently fail to bind without any visible error.

For macOS DMG: consider `briefcase` as an alternative to PyInstaller; it has better data-file handling and native macOS app bundle conventions. If staying with PyInstaller, test the `.app` bundle on a **clean machine without Python installed** before declaring packaging done.

**Warning signs:**
- App works with `python main.py` but crashes after PyInstaller build
- Error message mentions "static" or "templates" paths not found
- NiceGUI page loads completely blank (missing JS/CSS)

**Phase to address:** Phase 4 (DMG packaging milestone v0.7) — dedicate a full phase to packaging. Do not treat it as a last step that takes an hour.

---

### Pitfall 9: Streamlit State Patterns Mapped Wrong to NiceGUI Equivalents

**What goes wrong:**
`st.session_state['selected_doc_id'] = 123` is a common Streamlit pattern. Developers migrating try to replicate this with `app.storage.user['selected_doc_id']`. It partially works, but `app.storage.user` is persisted to disk as a JSON file, is unavailable outside an active page request context, and raises `RuntimeError: No storage available` when accessed from background tasks (pipeline callbacks, Telegram bot handlers, `app.on_startup`).

**Why it happens:**
`app.storage.user` requires an active HTTP session context (a browser cookie). Background workers and Telegram handlers have no request context. Streamlit's `st.session_state` was scoped to a single script rerun — a completely different model.

**How to avoid:**
Match storage to the right scope:

| Use case | Right tool |
|----------|-----------|
| Ephemeral UI state within a page (selected row, open tab) | Plain Python variable in `@ui.page` closure |
| State shared across page components within one session | Pass explicit object references or use a per-session class instance |
| Background pipeline writing progress to UI | Module-level dict keyed by session ID |
| Persistent user preferences (API key, default provider) | `app.storage.user` — fine here, it IS persistent by design |

```python
# Background pipeline can write here without request context:
_pipeline_progress: dict[str, float] = {}

async def run_pipeline(session_id: str):
    _pipeline_progress[session_id] = 0.0
    await run.io_bound(controller.process, session_id,
                       progress_callback=lambda p: _pipeline_progress.update({session_id: p}))
```

**Warning signs:**
- `RuntimeError: No storage available` in logs from a background task
- `app.storage.user` data survives app restart unexpectedly (because it's on-disk JSON)
- Telegram callback cannot read or write per-client UI state

**Phase to address:** Phase 1 (state architecture design) — document and enforce the state model before any feature implementation begins.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Call `db_service` directly in `async def` callback (no `run.io_bound`) | Faster to write | UI freezes on any real dataset; hard to retrofit across dozens of callbacks | Never — establish the pattern from day one |
| Module-level variables for per-client state | Simpler code | State leaks between clients; multi-client mode is broken by design | Never if multi-client is a product requirement |
| `ui.download(bytes_content)` for Excel export | Simple one-liner | Freezes UI for files >10 MB; silent failure >1 GB | Only for files guaranteed <1 MB (e.g., JSON config export) |
| `reload=True` during development | Hot-reload convenience | Starts llama-server twice per code change; 3–5 sec restart loop | Development only — never in production build or .app bundle |
| Tailwind dynamic class construction via f-strings | DRY-looking code | Styles silently absent in production | Never — use lookup dict with literal strings |
| Relying on `app.on_shutdown` alone for llama-server cleanup | Fewer lines of code | Orphaned server process on window close (documented NiceGUI bug) | Never |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `database.py` (SQLite) | Call sync service methods in `async def` callbacks | `await run.io_bound(db_service.method, *args)` for every DB call |
| llama-server subprocess | Trust `app.on_shutdown` alone for process cleanup | Triple-layer: `app.on_shutdown` + `app.on_disconnect` + `atexit.register` |
| Telegram bot | Access `app.storage.user` from bot handler thread | Module-level dict keyed by client/user ID; no request context in bot thread |
| Excel reporter | `ui.download(reporter.generate_excel())` for large registries | FastAPI `FileResponse` route for any output >5 MB |
| HuggingFace model download | Run at module import time | Run inside `app.on_startup` with a loading progress indicator |
| File import pipeline | Wire `ui.upload` bytes directly to `scanner.py` | Use native OS file picker in desktop mode; pipeline expects `pathlib.Path` objects |
| Multi-client DB switching | Single global `DatabaseService` instance | Each client session gets its own `DatabaseService(client_db_path)` instance stored per-session |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `ui.table` with 500+ rows, no pagination | Table renders slowly; scrolling is janky; memory pressure | Use `ui.table` with `pagination` prop or `virtual-scroll` | >200 rows |
| Refreshing entire table on every background update | Visible flicker every few seconds | Update only changed rows via `table.update_rows([changed_row])` | >50 rows with periodic background refresh |
| Running pipeline in main async loop without `run.io_bound` | UI completely unresponsive for entire processing duration | Always `await run.io_bound(controller.process, ...)` | Any dataset >1 file |
| Loading all document metadata eagerly on page load | Slow initial render; visible delay before first interaction | Paginate DB queries; load document details only on row click | >100 documents |
| Emitting UI progress update for every single file processed | WebSocket flooded; UI stutters | Batch updates — emit progress every N files or every 500ms | Pipeline with >20 files |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Binding NiceGUI server to `0.0.0.0` (default in some configs) | Other devices on the local network can access the document database without authentication | Always bind to `127.0.0.1`: `ui.run(host='127.0.0.1')` |
| Storing API keys in `app.storage.general` (disk JSON in home dir) | Keys visible as plaintext in `~/.local/share/nicegui/` | Use OS keychain via `keyring` library or environment variables |
| Logging anonymized document content to a file | Personal data leaks to log file | Log only filenames and document IDs; never log extracted text fields |
| Using `app.add_media_files()` for user-uploaded content | Memory exhaustion DoS — CVE-2026-33332 allows attacker to bypass chunked streaming and force full file into RAM | Avoid `add_media_files` for user content; use FastAPI routes with explicit `Content-Length` validation |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No progress feedback during pipeline run (can take 2–20 min for large archives) | User thinks app froze; force-quits; re-runs; double-processes files | Per-file progress with `ui.linear_progress` + file count label; show elapsed time |
| Streamlit-style full page reload to "refresh" data | Visible flicker; scroll position reset; any open document card closes | In-place table update: `table.rows = new_data; table.update()` |
| Raw Python exception messages shown to user | Confuses non-technical lawyers with tracebacks | Catch exceptions in every callback; show localized Russian message; log full traceback to file |
| NiceGUI native window shows blank/black for 3–5 sec during startup | User clicks the window, sees nothing, assumes crash | Show startup splash via `app.native.main_window.set_title('ЮрТэг — загрузка...')` during server init |
| File import requires knowing folder path | Non-technical users unsure what to type | Use native OS folder picker dialog — no typing required |

---

## "Looks Done But Isn't" Checklist

- [ ] **llama-server cleanup:** Close app window → run `ps aux | grep llama` → no orphan process. Check again after 30 seconds.
- [ ] **Multi-client isolation:** Open two browser tabs → switch active client in tab A → tab B must show zero change.
- [ ] **Async DB calls:** Load 500-document dataset → table renders without any UI freeze or WebSocket timeout error.
- [ ] **Large file download:** Export Excel with 300 docs → UI remains fully interactive during download → file arrives in browser.
- [ ] **Tailwind dynamic styles:** Open browser DevTools → Styles panel for any element using computed class names → CSS rules must exist, not just class names in DOM.
- [ ] **PyInstaller bundle:** Cold-start `.app` bundle on a Mac with no Python installed → app launches normally.
- [ ] **Telegram + NiceGUI state:** Send document via Telegram bot → confirm it appears in correct client's registry → NiceGUI UI must reflect the change without manual refresh.
- [ ] **Startup sequence:** Kill app mid-pipeline → relaunch → DB must not be in inconsistent state → pipeline resumes or reports error cleanly.
- [ ] **`reload=False` in production build:** Confirm only one llama-server process appears in Activity Monitor at startup.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Global state leaking between clients | HIGH | Audit every module-level variable; refactor all page code to `@ui.page` closures; re-test multi-client |
| Sync SQLite blocking event loop | MEDIUM | Add `run.io_bound` wrapper around each `database.py` call site in UI layer; no business logic change required |
| Orphaned llama-server after close | LOW | Add `app.on_disconnect` + `atexit` hooks; test on macOS specifically |
| Double init with `reload=True` | LOW | Set `reload=False`; move all side-effect code to `app.on_startup` |
| PyInstaller missing static files | MEDIUM | Add `--add-data` directives to `.spec`; retest on a clean machine without Python |
| Tailwind dynamic classes not applied | LOW | Replace all `f'class-{var}'` patterns with lookup dicts using literal strings |
| Large file download freezes UI | MEDIUM | Replace all `ui.download(bytes)` calls with FastAPI `FileResponse` routes |
| `app.storage.user` used in wrong context | MEDIUM | Audit all background tasks; replace with module-level state dicts keyed by session ID |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Global UI state shared across clients | Phase 1 — App scaffold & page architecture | Open two browser tabs; confirm fully isolated state |
| Sync SQLite blocking event loop | Phase 1 — DB integration layer | Load 500-doc dataset; confirm no UI freeze or WebSocket timeout |
| llama-server orphaned on close | Phase 2 — Local LLM wiring | Close app; `ps aux \| grep llama` shows zero processes |
| Double initialization with `reload=True` | Phase 1 — App entrypoint | Launch app; Activity Monitor shows exactly one llama-server |
| `ui.upload` gives no file path | Phase 2 — File import screen | Upload PDF via native picker; pipeline receives `Path` object |
| Large download freezes UI | Phase 3 — Export features | Export 300-doc Excel; UI stays interactive throughout |
| Tailwind dynamic classes ignored | Phase 2 — Theming and component library | DevTools Styles panel shows CSS rules for all status-based classes |
| PyInstaller misses NiceGUI static assets | Phase 4 — DMG packaging | Cold-start `.app` on clean Mac; no "static directory" error |
| `st.session_state` anti-pattern migration | Phase 1 — State architecture | Grep for `app.storage.user` in background task code; must be zero matches |

---

## Streamlit Patterns That Do Not Translate to NiceGUI

| Streamlit Pattern | What It Does | NiceGUI Replacement | Key Trap |
|-------------------|--------------|---------------------|----------|
| `st.rerun()` | Forces full script re-execution to refresh UI | Not needed — update element `.rows`, `.text`, `.value` directly | "Triggering rerun" means clearing all local state |
| `st.session_state` | Per-session ephemeral dict, any scope | Local variable in `@ui.page` closure; `app.storage.user` for persistence | `app.storage.user` is on-disk JSON, not ephemeral |
| `@st.cache_data` | Memoizes expensive function results | `functools.lru_cache` or module-level dict | No built-in equivalent in NiceGUI |
| `st.spinner()` context manager | Blocks script, shows spinner | `ui.linear_progress` shown/hidden explicitly around `await run.io_bound(...)` | NiceGUI spinner must be manually shown and hidden |
| `st.sidebar` | Auto-collapsible sidebar | `ui.left_drawer()` | Must explicitly manage open/close state |
| `st.file_uploader` | Upload → returns BytesIO with `.name` | `ui.upload` (bytes only) or native OS file picker (real Path) | Desktop use case → always use native picker |
| Linear script flow (top to bottom) | Execution order = layout render order | Callback-based: layout defined at load, behavior at event | Entire control flow must be rethought as event handlers |
| `st.columns([1, 2])` | Creates proportional column layout | `ui.row()` + Tailwind `w-1/3` / `w-2/3` classes | Column sizing syntax is completely different |

---

## Sources

- [NiceGUI FAQs Wiki — subprocess, reload, blocking, file upload path restriction](https://github.com/zauberzeug/nicegui/wiki/FAQs)
- [NiceGUI issue #2107 — on_shutdown not called in native mode](https://github.com/zauberzeug/nicegui/issues/2107)
- [NiceGUI issue #5684 — slow startup and code re-execution in multiprocessing contexts](https://github.com/zauberzeug/nicegui/issues/5684)
- [NiceGUI issue #3756 — large file download freezes event loop](https://github.com/zauberzeug/nicegui/issues/3756)
- [NiceGUI discussion #3220 — ui.upload stutters with large files](https://github.com/zauberzeug/nicegui/discussions/3220)
- [NiceGUI discussion #3568 — how to upload big files that don't fit in memory](https://github.com/zauberzeug/nicegui/discussions/3568)
- [NiceGUI discussion #836 — running a worker thread in background](https://github.com/zauberzeug/nicegui/discussions/836)
- [NiceGUI discussion #1888 — using non-async libraries for def endpoints](https://github.com/zauberzeug/nicegui/discussions/1888)
- [NiceGUI discussion #2082 — multiple clients from one browser](https://github.com/zauberzeug/nicegui/discussions/2082)
- [NiceGUI discussion #1029 — global data store, per-user UI state](https://github.com/zauberzeug/nicegui/discussions/1029)
- [NiceGUI issue #3753 — dark mode breaks Tailwind styling since NiceGUI 2.0](https://github.com/zauberzeug/nicegui/issues/3753)
- [NiceGUI discussion #5240 — NiceGUI v3 removed CSS customization ability](https://github.com/zauberzeug/nicegui/discussions/5240)
- [NiceGUI discussion #2337 — integrating Tailwind CSS components](https://github.com/zauberzeug/nicegui/discussions/2337)
- [NiceGUI discussion #1806 — styling methods overview](https://github.com/zauberzeug/nicegui/discussions/1806)
- [NiceGUI issue #355 — launching as executable with PyInstaller](https://github.com/zauberzeug/nicegui/issues/355)
- [NiceGUI discussion #1135 — PyInstaller: static directory does not exist](https://github.com/zauberzeug/nicegui/discussions/1135)
- [NiceGUI discussion #5331 — v3 breaking changes](https://github.com/zauberzeug/nicegui/discussions/5331)
- [NiceGUI storage documentation](https://nicegui.io/documentation/storage)
- [NiceGUI discussion #21 — why callbacks instead of Streamlit-like if-statements](https://github.com/zauberzeug/nicegui/discussions/21)
- [CVE-2026-33332 — NiceGUI media route memory exhaustion vulnerability](https://advisories.gitlab.com/pkg/pypi/nicegui/CVE-2026-33332/)
- [Oreate AI — NiceGUI page layout best practices](https://www.oreateai.com/blog/comprehensive-analysis-and-best-practices-guide-for-nicegui-page-layout/33d6025a4cc288327f2ed04df616323f)

---
*Pitfalls research for: ЮрТэг v0.6 — Streamlit → NiceGUI migration*
*Researched: 2026-03-21*
