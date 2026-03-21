# Phase 7: App Scaffold + State Architecture - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Приложение запускается на NiceGUI в нативном окне с тремя пустыми табами (Документы · Шаблоны · Настройки). Архитектурные паттерны зафиксированы до построения любых экранов — предотвращение трёх дорогостоящих паттернов: global state leak, async блокировка, двойная инициализация. Старый Streamlit main.py архивируется в отдельную ветку.

</domain>

<decisions>
## Implementation Decisions

### App structure
- **D-01:** Создать `app/` директорию с `main.py`, `state.py`, `pages/`, `components/`
- **D-02:** Каждая страница — модуль с функцией `build()` внутри `@ui.page` декоратора
- **D-03:** `ui.sub_pages` для SPA-навигации — URL обновляется, header остаётся

### State management
- **D-04:** `AppState` dataclass в `app/state.py` — единственный источник правды для UI-состояния
- **D-05:** `app.storage.client['state']` для хранения AppState (per-connection, in-memory)
- **D-06:** Persistent settings (провайдер, Telegram) остаются в `~/.yurteg/settings.json` — без изменений

### Async patterns
- **D-07:** Все DB-вызовы из UI обёрнуты в `await run.io_bound()` — шаблон зафиксирован до написания любых обработчиков
- **D-08:** `reload=False` в `ui.run()` — предотвращение двойной инициализации

### llama-server lifecycle
- **D-09:** Module-level singleton, инициализация в `app.on_startup`
- **D-10:** Тройная защита при закрытии: `app.on_shutdown` + `app.on_disconnect` + `atexit.register`
- **D-11:** `ensure_model()` и `start()` через `run.io_bound()` — не блокируют event loop

### Header layout
- **D-12:** Минималистичный текстовый header без иконок у табов
- **D-13:** Слева — текстовый лого «ЮрТэг», центр — табы «Документы · Шаблоны · ⚙», справа — иконка профиля клиента 👤▾
- **D-14:** Header persistent — остаётся при навигации между sub_pages

### Old Streamlit UI
- **D-15:** Старый `main.py` архивируется в ветку `archive/streamlit-ui`, не удаляется и не переименовывается в main branch

### NiceGUI run config
- **D-16:** `ui.run(native=True, dark=False, reload=False, host='127.0.0.1', title='ЮрТэг', window_size=(1400, 900), storage_secret='yurteg-desktop-secret')`

### Claude's Discretion
- Exact AppState fields (based on existing session_state keys analysis)
- File structure within `app/components/`
- Error handling strategy for llama-server startup failures
- NiceGUI version pinning

</decisions>

<specifics>
## Specific Ideas

- Header должен выглядеть как Linear/Notion — чистый, утилитарный, без декораций
- `dark=False` — светлая тема с самого начала, не добавлять тёмную тему
- Табы в header — не Quasar ui.tabs визуально, а custom text links с подчёркиванием активного

</specifics>

<canonical_refs>
## Canonical References

### NiceGUI architecture
- `.planning/research/ARCHITECTURE.md` — полная архитектура миграции: файловая структура, паттерны state/routing/singleton, data flow diagrams
- `.planning/research/ARCHITECTURE.md` §Pattern 1-5 — конкретные code examples для AppState, sub_pages, LlamaServerManager, pipeline, aggrid

### Pitfalls to avoid
- `.planning/research/PITFALLS.md` — 9 критических питфолов с prevention strategies
- `.planning/research/PITFALLS.md` §Pitfall 1 — global scope UI elements (Phase 7 must prevent)
- `.planning/research/PITFALLS.md` §Pitfall 2 — sync SQLite blocking (Phase 7 must establish pattern)
- `.planning/research/PITFALLS.md` §Pitfall 4 — double init with reload=True (Phase 7 must set reload=False)
- `.planning/research/PITFALLS.md` §Pitfall 9 — wrong state pattern migration (Phase 7 must define state model)

### NiceGUI stack
- `.planning/research/STACK.md` — NiceGUI v3.9.0 components, APIs, v3 breaking changes

### Design direction
- `.planning/PROJECT.md` §Current Milestone — design constraints, Impeccable skills per phase

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `services/llama_server.py` — LlamaServerManager полностью готов, только обёртка вызовов меняется (st.cache_resource → module singleton)
- `config.py` — Config dataclass, `active_provider`, `llama_server_port` — используется без изменений
- `modules/postprocessor.py` — `get_grammar_path()` для llama-server grammar — используется без изменений
- `services/client_manager.py` — `ClientManager.list_clients()` для header profile selector

### Established Patterns
- Все сервисы (`pipeline_service`, `lifecycle_service`, `version_service`, `payment_service`, `review_service`) — чистый Python, NO import streamlit. Вызываются напрямую из NiceGUI handlers
- `~/.yurteg/settings.json` — persistence для active_provider, warning_days. Читается через `config.py`

### Integration Points
- `main.py` (2247 LOC) → полностью заменяется на `app/main.py` (~50 LOC entrypoint)
- `requirements.txt` → удалить streamlit/streamlit-calendar, добавить nicegui
- 45 `st.session_state` ключей → маппятся в поля AppState dataclass

</code_context>

<deferred>
## Deferred Ideas

- Splash screen с onboarding wizard при первом запуске — Phase 12 (Onboarding)
- Настройка Telegram во время загрузки модели — Phase 12 (Onboarding)
- Светлая тема и типографика — Phase 13 (Design Polish)
- Empty state реестра — Phase 12 (Onboarding)

</deferred>

---

*Phase: 07-app-scaffold*
*Context gathered: 2026-03-22*
