# Milestones

## v1.1 Bug Sweep (Shipped: 2026-03-29)

**Phases completed:** 1 phase (PR #3)

**Key accomplishments:**

- 35 багов из аудита устранены: P0 (pipeline БД, clear_all, auth, анонимизация), P1 (settings runtime, workspace routes, cascade, race conditions), P2 (health-check, off-by-one, scheduler)
- Desktop reliability fixes merged (commit 1243a89)

---

## v1.0 Hackathon-Ready (Shipped: 2026-03-29)

**Phases completed:** 12 phases (32–43)

**Key accomplishments:**

- P0 Critical Fixes: шрифты, AG Grid API, двойные вызовы дедлайнов
- Code Quality: inline colors → tokens, a11y bulk actions, loading/error states
- Registry & Document Card: поиск с иконкой, календарь, превью PDF/DOCX, feedback при сохранении
- Templates, Settings & Onboarding: visual consistency, wizard end-to-end
- Cross-Scope Integration: STATUS_LABELS, APP_VERSION, убран dict cast
- Final Visual Pass: spacing, typography, animations — консистентность по всем экранам
- Config Hardening: __post_init__ валидация, atomic settings, active_model fix
- Provider Cleanup: timeout, get_logprobs контракт, API key validation
- Data Integrity: contract_number миграция v10, деанонимизация всех полей, redline дата
- Thread Safety: RLock, locks на read-методы, атомарные операции
- Error Handling: bare excepts → конкретные, input validation, GBNF fail-loud
- Test Coverage: 15 gaps закрыты — concurrent writes, migrations, payment edges

---

## v0.9 Backend Hardening (Shipped: 2026-03-27)

**Phases completed:** 4 phases, 11 plans, 9 tasks

**Key accomplishments:**

- One-liner:
- Task 1 — atexit.register() out of retry loop (`services/llama_server.py`)
- One-liner:
- One-liner:
- Protect/restore механизм для NDA/SLA/GPS в cyrillic_only постпроцессоре через placeholder замену и word-boundary regex
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- Amber collapsible deadline widget в registry.py с данными из lifecycle_service.get_attention_required(), обновляющийся после bulk delete

---

## v0.8 Hardening & Cleanup (Shipped: 2026-03-25)

**Phases completed:** 4 phases, 7 plans, 315 tests green

**Key accomplishments:**

- INSERT OR REPLACE → UPSERT — заметки и статусы юриста больше не стираются при повторной обработке документов
- Foreign keys enforced + migration v7 — платёжные данные сохраняются, связи между документами не рвутся
- Все кнопки UI работают: split panel, скачивание PDF, переобработка, настройки, массовая смена статуса
- Streamlit UI (2247 строк) и legacy-функции удалены — кодовая база чистая, одна точка входа
- 315 тестов зелёные (было 268 с 15 FAIL и 8 xfail) — +47 новых тестов для scanner, extractor, reporter, postprocessor, controller
- Шрифты и FullCalendar бандлятся локально — приложение работает полностью офлайн
- Все зависимости пиннуты с ==, numpy и httpx добавлены — воспроизводимая установка
- L5 verification и OllamaProvider используют провайдер-систему вместо legacy-кода

---

## v0.7.1 UI Polish & Fixes (Shipped: 2026-03-22)

**Phases completed:** 2 phases, 6 plans, 7 tasks

**Key accomplishments:**

- One-liner:
- Logo upgraded to «Юр» in indigo rect + «Тэг» wordmark; add-workspace dialog restyled with indigo header band; templates/settings pages centered and no longer locked to viewport height
- One-liner:
- One-liner:
- One-liner:
- pick_folder() and _pick_file() protected with try/except (ImportError, AttributeError) — app no longer crashes in web mode without pywebview

---

## v0.7 Визуальный продукт (Shipped: 2026-03-22)

**Phases completed:** 4 phases, 10 plans, 3 tasks

**Key accomplishments:**

- One-liner:
- One-liner:
- 1. [Rule — Minor] 5 hero-enter элементов вместо 4
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- One-liner:

---

## v0.6 UI-редизайн (Shipped: 2026-03-22)

**Phases completed:** 7 phases, 18 plans, 24 tasks

**Key accomplishments:**

- AppState dataclass (20 typed fields) + four NiceGUI page placeholders + persistent Linear-style header — the typed state model and page pattern all phases 8-13 build upon
- NiceGUI entrypoint app/main.py with SPA routing via ui.sub_pages, triple llama-server shutdown protection, and run.io_bound() pattern established as canonical async template for all future phases
- AG Grid registry table with live SQLite data, computed status badges via JS cellRenderer, and rapidfuzz multi-word AND-logic fuzzy search
- Registry page fully interactive: debounced search + three segment filters toggle live data, row clicks navigate to document cards, and header dropdown switches clients with filter reset
- AG Grid registry with ⋯ context menu (Открыть/Скачать/Переобработать/Удалить), quick status change via MANUAL_STATUSES, and lazy ▶/▼ expand/collapse for versioned documents
- One-liner:
- NiceGUI document card completed with AI review via match_template + review_against_template, collapsible version history with diff table, and FastAPI redline .docx download route.
- Native macOS folder picker + async pipeline runner wired to persistent header upload button via run.io_bound and call_soon_threadsafe
- Progress section wired into registry page above the table — upload button triggers real-time pipeline progress (bar + count + filename + error log) with auto-table-refresh on completion
- Settings persistence centralized in config.py (load_settings/save_setting) with delete_template/update_template service methods and check_connection health check — 14 unit tests, all passing
- Страница настроек с macOS Preferences layout — левая nav (AI/Обработка/Telegram), правая панель с тремя полными секциями, персистенция через settings.json
- Full Templates page with 2-column card grid, native OPEN_DIALOG file picker, run.io_bound text extraction, and edit/delete dialogs wired to review_service CRUD
- Full-page onboarding splash с прогресс-баром загрузки GGUF модели и 2-шаговым wizard (приветствие + Telegram) — splash gate в main.py делает early return при первом запуске
- Empty state
- IBM Plex Sans font + FullCalendar CDN + row/page animations injected globally; _STATUS_CSS/_ACTIONS_CSS migrated from gray to slate/indigo; AppState gets calendar_visible field; 7-test design polish scaffold GREEN
- registry.py:
- List/Calendar view toggle in registry with FullCalendar rendering contract end dates (indigo) and payments (slate-400) from live DB data
- Full test suite green (266 passed), zero gray Tailwind classes in app/, and all DSGN-01 through DSGN-05 requirements verified via automated tests

---

## v0.5 Локальная LLM (Shipped: 2026-03-21)

**Phases completed:** 3 phases, 4 plans, 4 tasks

**Key accomplishments:**

- llama-server download manager (GitHub Releases + HuggingFace Hub) and GBNF grammar + field-level Cyrillic sanitizer for local model output
- OllamaProvider с openai SDK для llama-server, дефолт active_provider='ollama' и автозапуск сервера через @st.cache_resource при старте Streamlit
- One-liner:
- One-liner:

---

## v0.4 Архитектура и функционал (Shipped: 2026-03-20)

**Phases completed:** 3 phases, 24 plans
**Timeline:** 29 дней (2026-02-19 → 2026-03-20)
**Codebase:** 11 353 LOC Python, 109 коммитов

**Key accomplishments:**

1. Версионированные миграции SQLite — обновления не ломают БД пользователя
2. Мультипровайдер AI (ZAI/OpenRouter/Ollama stub) с переключением через конфиг
3. Сервис-слой без Streamlit — pipeline_service, lifecycle_service и другие вызываются из бота, CLI, тестов
4. Полный жизненный цикл документа — автостатусы, ручной override, версионирование с эмбеддингами, diff + redline .docx
5. Платёжный календарь — периодические платежи разворачиваются в сетку, streamlit-calendar
6. AI-ревью договора — библиотека шаблонов, автоподбор, подсветка отступлений
7. Telegram-бот @YurTagBot — приём документов, ежедневный дайджест сроков, привязка через /start
8. Мультиклиентский режим — изолированные БД, fuzzy-автопривязка по контрагенту

**Deferred to v2:**

- INTG-03: Google Drive автообработка
- PROF-02: Совместный доступ нескольких юристов
- SECR-01: Аудит-лог (нет value без мультиюзера)
- SECR-02: Docker-упаковка (DMG/EXE модель доставки)

---
