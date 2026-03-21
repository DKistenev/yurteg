# Project Research Summary

**Project:** ЮрТэг v0.6 — NiceGUI UI Migration
**Domain:** Legal document processing desktop app — Streamlit → NiceGUI UI layer replacement
**Researched:** 2026-03-21
**Confidence:** HIGH

## Executive Summary

ЮрТэг v0.6 is a targeted UI-layer replacement, not a feature milestone. The business logic built across v0.4–v0.5 (pipeline, services, AI providers, SQLite) is completely untouched. The only structural change is replacing a 2247-line Streamlit monolith (`main.py`) with a modular NiceGUI application. The recommended framework is NiceGUI 3.9.0, the latest stable release as of 2026-03-19, built on FastAPI + Vue + Quasar + Tailwind. It provides the SPA navigation, clickable ag-grid tables, and persistent header that Streamlit structurally cannot support. The new UI architecture follows the "registry = app" pattern: the document registry is always visible as the primary workspace, rows navigate to full-page document cards, and settings are a first-class tab — not a sidebar dropdown.

The recommended implementation is a flat `app/` directory containing `main.py`, `state.py`, four page modules, and three shared components. State management replaces 45 scattered `st.session_state` keys with a single typed `AppState` dataclass stored in `app.storage.client`. Long-running pipeline calls use `await run.io_bound()` to stay off the asyncio event loop. The header, tabs, and navigation render once and persist across sub-page swaps via `ui.sub_pages()`. All existing services are called directly as Python function calls — no HTTP adapter layer needed.

The primary risk cluster is three NiceGUI-specific pitfalls that are easy to introduce and expensive to retrofit: global-scope UI elements shared across clients, synchronous SQLite calls blocking the async event loop, and the llama-server subprocess not being cleaned up on window close. All three must be hardened in Phase 1 (app scaffold and state architecture) before any feature screens are built. A secondary risk is PyInstaller packaging, which requires explicit NiceGUI static asset inclusion and must be treated as a dedicated future phase, not a finishing step.

---

## Key Findings

### Recommended Stack

The UI framework is NiceGUI 3.9.0. It is built on FastAPI + Vue + Quasar + Tailwind and provides a Python-first API for every component needed: clickable ag-grid tables, tab navigation, persistent headers, reactive state, and a native desktop window via pywebview. The critical version note: NiceGUI v3 removed the `.tailwind()` method and the global auto-index page — all pages must use `@ui.page` decorators, and all styling must use `.classes()` with literal Tailwind class names.

**Core technologies:**
- **NiceGUI 3.9.0**: Full UI framework — replaces Streamlit; provides SPA navigation, clickable tables, native window
- **ui.aggrid**: AG Grid wrapper — main registry table with per-column filtering, sort, and row click; superior to `ui.table` for 100+ rows
- **ui.sub_pages**: SPA routing primitive — content area swaps without full page reload; header stays persistent
- **pywebview (via nicegui[native])**: macOS WKWebView / Windows EdgeChromium — no Electron, no Node.js
- **app.storage.client**: Per-connection in-memory state — replaces `st.session_state`; `app.storage.user` for persistent preferences
- **run.io_bound / run.cpu_bound**: Background thread wrappers — mandatory for any blocking call (SQLite, pipeline, llama-server)

See `STACK.md` for full API patterns and version compatibility matrix.

### Expected Features

This is a UI architecture milestone. All six feature areas below already exist as business logic — the question is how they surface in the new "registry = app" architecture.

**Must have (table stakes — blocks milestone if missing):**
- Clickable rows navigating to full-page document detail — any modern list UI; a row that does nothing on click feels broken
- Sort by column header click — standard since the 90s; already expected
- Active filter chips visible above table — users forget filters are active without visual indication
- Document count in header ("Показано 12 из 47") — baseline trust signal
- Loading state during pipeline processing — AI extraction takes 2–30 seconds; silence reads as crash
- Empty state for first launch with clear CTA — critical for hackathon demo first impression

**Should have (differentiators beyond Russian legal tool competitors):**
- Full-page transition to document detail (Linear pattern) — feels native desktop, not modal-heavy web app
- Inline status badge with quick-change dropdown — status change without entering detail view
- Scroll position memory on back navigation — users return to same row; losing position is a known frustration
- Calendar view toggle (month view) — differentiator for contract expiry tracking; FullCalendar.js via JS interop
- Settings page as proper top-level tab — provider switching, notification threshold, Telegram config

**Defer to v0.7:**
- Keyboard navigation within table (arrow keys) — nice to have, not blocking
- Persistent column widths — cosmetic polish
- Row density toggle — post-launch preference
- Context menu on right-click — three-dot hover menu covers same actions

See `FEATURES.md` for full pattern specifications and reference app analysis (Linear, Notion, Finder).

### Architecture Approach

The new UI layer follows a strict separation: `app/` directory contains only NiceGUI code; everything outside `app/` (controller, modules, services, providers, config, SQLite) is unchanged. Page modules each export a single `build(state: AppState)` function and call services as direct Python function calls — no HTTP layer. The `AppState` dataclass is the single source of truth for all ephemeral UI state (current client, active filters, selected document ID, processing status). Persistent settings (provider choice, warning days, Telegram token) continue to use `~/.yurteg/settings.json` via `config.py`.

**Major components:**
1. **`app/main.py`** — `ui.run()` entry point, `app.on_startup` hooks (llama-server, Telegram sync), `ui.sub_pages` routing table
2. **`app/state.py`** — `AppState` dataclass definition + `get_state()` accessor; replaces 45 `st.session_state` keys
3. **`app/pages/registry.py`** — core view: ag-grid table, filter chips, search bar, client selector, calendar toggle
4. **`app/pages/document.py`** — full-page card: 5 tabs (metadata, versions, review, notes, payments), status override
5. **`app/pages/settings.py`** — provider selector, anonymization toggle, notifications, Telegram config
6. **`app/components/header.py`** — persistent top navigation shared across all sub-pages
7. **`app/components/table.py`** — `ui.aggrid` wrapper encapsulating column definitions and row click handler
8. **`app/components/process.py`** — folder picker (native OS dialog), process button, progress bar

See `ARCHITECTURE.md` for data flow diagrams, full API examples, build order, and the complete Streamlit-to-NiceGUI API mapping table (262 `st.*` calls mapped).

### Critical Pitfalls

1. **Global-scope UI elements shared across clients** — Any `ui.*` created outside a `@ui.page` function is shared across all browser connections. Prevention: every screen inside a `@ui.page` decorated function; all state in `app.storage.client`. Must be established in Phase 1 — it is HIGH-cost to retrofit.

2. **Synchronous SQLite calls blocking the async event loop** — Plain `sqlite3` calls inside `async def` handlers freeze the entire NiceGUI event loop. Prevention: wrap every `database.py` call with `await run.io_bound(...)`. Establish the pattern in Phase 1 before any data is wired to UI.

3. **llama-server subprocess orphaned on window close** — `app.on_shutdown` is not reliably called in native mode (confirmed NiceGUI issue #2107). Prevention: triple-layer cleanup — `app.on_shutdown` + `app.on_disconnect` + `atexit.register`. Address in Phase 2.

4. **Double initialization with reload=True** — NiceGUI hot-reload spawns a subprocess where module-level code runs twice; two llama-server instances start on the same port. Prevention: always `reload=False` in production; all startup side effects in `app.on_startup()`.

5. **Tailwind dynamic class names silently ignored** — JIT mode only includes class names present as literal strings in source. `f'bg-{color}-500'` constructs produce zero CSS. Prevention: always use lookup dicts with full literal class strings. No exceptions.

6. **ui.upload gives bytes only, no file path** — The existing pipeline expects `pathlib.Path` objects. Prevention: use native OS file picker (`app.native.main_window.create_file_dialog()`) for all batch import.

7. **Large file downloads freeze the event loop** — `ui.download(bytes)` serializes content synchronously. Prevention: route all file downloads through a FastAPI `FileResponse` endpoint.

8. **PyInstaller misses NiceGUI static assets** — App crashes on clean launch with "static directory does not exist". Prevention: explicit `datas` entries in `.spec` file; test on a machine with no Python installed. Treat as a dedicated v0.7 phase.

See `PITFALLS.md` for full recovery strategies, tech debt table, integration gotchas, and the "Looks Done But Isn't" checklist.

---

## Implications for Roadmap

Based on combined research, a six-phase implementation order is recommended. The ordering is driven by: (1) pitfalls that must be prevented from Phase 1 or become expensive to retrofit; (2) the dependency chain from navigation skeleton → data layer → features; (3) the architecture research's explicit build order.

### Phase 1: App Scaffold + State Architecture

**Rationale:** The three most expensive pitfalls (global state, async SQLite, double init) must be encoded in the app's skeleton before any feature screen is built. Retrofitting `@ui.page` wrappers and `run.io_bound` calls across dozens of UI event handlers is a HIGH-recovery-cost operation. Establish the pattern once; all subsequent phases inherit it.
**Delivers:** App launches in native window. Navigation between three empty tabs works. `AppState` dataclass defined. `get_state()` accessor enforced. `reload=False` set. `app.on_startup` wiring in place. All `@ui.page` decorators established.
**Addresses:** First-launch empty state — needed as soon as the app renders.
**Avoids:** Global UI state leak (Pitfall 1), double initialization (Pitfall 4), storage scope mismatch (Pitfall 9).
**Research flag:** Standard patterns — skip research phase. NiceGUI docs are authoritative and complete for this scope.

### Phase 2: Registry View (Core Product)

**Rationale:** The registry IS the product. Everything else (document card, settings, calendar) hangs off rows in this table. Wire real data to the ag-grid before building detail views — validating the data model early catches schema issues before they ripple into five downstream tabs.
**Delivers:** Existing documents from SQLite display in the registry. Column sort and per-column filters work. Filter chips render above table. Search bar with 300ms debounce queries SQLite via `run.io_bound`. Inline status badge with dropdown. Document count in header. Client selector wired to `client_manager`.
**Uses:** `ui.aggrid`, `run.io_bound` for all DB calls, `AppState.filter_*` fields, `lifecycle_service.get_computed_status_sql()`.
**Avoids:** Sync SQLite blocking the event loop (Pitfall 2), Tailwind dynamic class names for status badges (Pitfall 7).
**Research flag:** Standard patterns — fully documented in NiceGUI docs and ARCHITECTURE.md. No additional research needed.

### Phase 3: Document Detail Card

**Rationale:** Once the registry renders real data and rows are clickable, the full-page document card is the natural next step. All five tab content types pull from existing services — no new business logic. This phase validates the `ui.navigate.to('/document/{id}')` routing and scroll position memory pattern.
**Delivers:** Clicking a registry row opens a full-page document card. Five tabs: Обзор, Ревью по шаблону, Версии, Платежи, Заметки. Breadcrumb "← Реестр" with scroll position memory. Manual status override (`lifecycle_service.set_manual_status`). Lawyer notes with auto-save on blur.
**Avoids:** Modal anti-pattern (FEATURES.md explicitly rejects modals for detail view), inline row expand accordion.
**Research flag:** Standard patterns. `ui.tabs` + `ui.tab_panels` is straightforward. Version diff rendering may need a targeted spike if complex visual diff output is needed.

### Phase 4: Pipeline Wiring + Local LLM

**Rationale:** Processing new documents is the core action of the app. This phase completes the async pipeline wiring and establishes the llama-server lifecycle management. Must come after the UI skeleton is solid — progress callbacks and `loop.call_soon_threadsafe` patterns require a working event loop to test against.
**Delivers:** Native OS folder picker wired to pipeline. Process button triggers `await run.io_bound(pipeline_service.process_archive, ...)`. Real-time progress bar updates via `loop.call_soon_threadsafe`. `LlamaServerManager` singleton initialized in `app.on_startup`. Startup splash shown during model load.
**Avoids:** `ui.upload` bytes-only pitfall (Pitfall 5) — native picker used instead. llama-server orphaned process (Pitfall 3) — triple-layer cleanup established. Blocking event loop during pipeline (Anti-Pattern 3 from ARCHITECTURE.md).
**Research flag:** Triple-layer cleanup behavior (`app.on_disconnect`) in `native=True` mode on macOS is not definitively confirmed — deserves a focused test or community issue search before building Phase 4.

### Phase 5: Settings + Templates + Export

**Rationale:** Settings page enables provider switching and Telegram configuration that are already functional in the Streamlit version. Export (Excel registry) requires the FastAPI `FileResponse` pattern to avoid the large-download event-loop freeze. These are lower-risk, form-heavy features that belong after the core registry/document flow is stable.
**Delivers:** Settings page with left-nav sections (AI provider, обработка, уведомления, Telegram, интерфейс, о программе). Changes save on blur (macOS System Preferences pattern). Templates list with add/delete. Excel export via FastAPI `FileResponse` route.
**Avoids:** Large file download freeze (Pitfall 6) — FastAPI route from day one for Excel export.
**Research flag:** Standard patterns. Settings forms are `ui.input` / `ui.select` / `ui.toggle` — no research needed.

### Phase 6: Design Polish + Calendar View

**Rationale:** Design polish comes last — not because it is unimportant, but because it requires stable components to apply to. Color system, typography, empty states, and hover interactions need real content to evaluate against. Calendar view (FullCalendar.js via JS interop) is a differentiator but depends on filter state being fully functional in Phase 2.
**Delivers:** Full Tailwind/Quasar color system applied. Light mode locked. Empty states for all three scenarios (first launch, no results, empty tab). Hover-reveal actions on registry rows. Calendar view toggle (FullCalendar.js integration, month view). Attention panel for expiring documents.
**Avoids:** Tailwind dynamic class names (Pitfall 7) — all status colors use literal class lookup dicts baked into the component library.
**Research flag:** FullCalendar.js JS interop pattern with NiceGUI needs a targeted proof-of-concept during phase planning. FEATURES.md recommends this approach but the exact `ui.add_head_html` + event callback wiring needs validation before committing. Fallback: custom NiceGUI grid layout.

### Phase Ordering Rationale

- Phases 1–2 establish the non-negotiable architectural constraints. Any deviation here forces a full audit of all subsequent phases.
- Phase 3 depends on Phase 2's routing and data model being stable.
- Phase 4 depends on the async event loop patterns from Phase 1 being enforced — pipeline callbacks touch the UI thread directly.
- Phase 5 is deliberately late because settings only become meaningful once there is real processing to configure.
- Phase 6 is always last — design polish applied to moving targets produces rework.
- PyInstaller/DMG packaging is out of scope for v0.6 and should be treated as Phase 7 (v0.7 milestone) with a dedicated research phase per PITFALLS.md Pitfall 8.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4:** llama-server triple-layer cleanup behavior in `native=True` mode on macOS — `app.on_disconnect` reliability in pywebview native mode is not definitively confirmed; requires targeted testing.
- **Phase 6:** FullCalendar.js integration via `ui.add_head_html` — the Python-to-JS data bridge and event callback pattern needs a working proof-of-concept before committing to it in the phase plan.

Phases with standard patterns (skip research phase):
- **Phase 1:** `@ui.page`, `app.storage.client`, `ui.sub_pages`, `ui.run` — all documented with official examples.
- **Phase 2:** `ui.aggrid`, `run.io_bound`, filter state management — in official docs and verified in STACK.md and ARCHITECTURE.md.
- **Phase 3:** `ui.tabs`, `ui.tab_panels`, `ui.navigate` — standard NiceGUI patterns.
- **Phase 5:** Settings forms, FastAPI `FileResponse` — well-documented.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | NiceGUI 3.9.0 verified via official docs and pyproject.toml. All API examples cross-checked against nicegui.io. Version compatibility matrix confirmed (Python >=3.10, pywebview >=5.0.1, fastapi >=0.109.1). |
| Features | HIGH | UX patterns verified against Pencil & Paper research, Nielsen Norman Group, and direct reference app analysis (Linear, Notion, Finder). CustDev findings (9 interviews) validate filter/search as top pain point (9/9). |
| Architecture | HIGH | Codebase analyzed directly — 2247-line main.py confirmed with 262 `st.*` calls, 45 `st.session_state` uses. All service layer interfaces verified as unchanged. NiceGUI patterns confirmed via official docs. |
| Pitfalls | HIGH | 8 of 9 critical pitfalls confirmed via official GitHub issues and FAQs with issue numbers. One CVE (CVE-2026-33332) verified via GitLab advisory. One pitfall (llama-server orphan) confirmed by issue #2107. |

**Overall confidence:** HIGH

### Gaps to Address

- **FullCalendar.js interop in NiceGUI native mode:** FEATURES.md recommends it but no working proof-of-concept exists yet. Build a spike in Phase 6 planning before committing. Fallback: custom NiceGUI grid layout.
- **`app.on_disconnect` in native=True mode:** The triple-layer cleanup relies on this hook, but its reliability in pywebview native mode is not definitively confirmed (Pitfall 3 cites issue #2107 for `app.on_shutdown`; `on_disconnect` behavior may differ). Verify with a minimal test before Phase 4.
- **Multi-tab isolation in single-user mode:** Architecture assumes single-user desktop, but the Pitfall 1 isolation requirement applies even in single-user mode when the user opens multiple browser tabs pointing at the same NiceGUI server. Confirm the `@ui.page` + `app.storage.client` pattern fully isolates tabs.

---

## Sources

### Primary (HIGH confidence)
- [NiceGUI official docs — nicegui.io/documentation](https://nicegui.io/documentation) — all core API patterns (aggrid, sub_pages, storage, navigate, run, dark_mode, colors)
- [NiceGUI pyproject.toml — github.com/zauberzeug/nicegui](https://github.com/zauberzeug/nicegui/blob/main/pyproject.toml) — version pinning verified
- [NiceGUI v3 breaking changes — discussion #5331](https://github.com/zauberzeug/nicegui/discussions/5331) — `.tailwind()` removal, auto-index removal, mutable object detection removal
- [NiceGUI issue #2107](https://github.com/zauberzeug/nicegui/issues/2107) — on_shutdown not called in native mode (confirmed)
- [NiceGUI issue #5684](https://github.com/zauberzeug/nicegui/issues/5684) — double initialization with reload=True
- [NiceGUI issue #3756](https://github.com/zauberzeug/nicegui/issues/3756) — large file download freezes event loop
- [NiceGUI issue #355 + discussion #1135](https://github.com/zauberzeug/nicegui/issues/355) — PyInstaller static asset bundling
- [CVE-2026-33332 — media route memory exhaustion](https://advisories.gitlab.com/pkg/pypi/nicegui/CVE-2026-33332/) — security pitfall for `add_media_files`
- Current codebase — `main.py` directly analyzed (2247 lines, 262 `st.*` calls, 45 `st.session_state` uses)
- CustDev findings — 9 interviews; поиск документов 9/9, хаос нейминга 6/9

### Secondary (MEDIUM confidence)
- [Pencil & Paper — Enterprise Data Tables UX](https://www.pencilandpaper.io/articles/ux-pattern-analysis-enterprise-data-tables) — hover state and row interaction patterns
- [Pencil & Paper — Enterprise Filtering UX](https://www.pencilandpaper.io/articles/ux-pattern-analysis-enterprise-filtering) — filter chip pattern
- [Nielsen Norman Group — Empty States](https://www.nngroup.com/articles/empty-state-interface-design/) — empty state design principles
- [Linear Blog — UI Redesign](https://linear.app/now/how-we-redesigned-the-linear-ui) — full-page transition vs split pane rationale
- [NiceGUI discussion #836](https://github.com/zauberzeug/nicegui/discussions/836) — background thread patterns
- [Talk Python episode #525 — NiceGUI 3.0](https://talkpython.fm/episodes/show/525/nicegui-goes-3.0) — v3 architecture patterns

### Tertiary (LOW confidence)
- [uxpatterns.dev — Calendar View Pattern](https://uxpatterns.dev/patterns/data-display/calendar) — calendar UX conventions; consistent with other sources
- [Setproduct — Settings UI Design](https://www.setproduct.com/blog/settings-ui-design) — settings page pattern; consistent with macOS HIG

---

*Research completed: 2026-03-21*
*Ready for roadmap: yes*
