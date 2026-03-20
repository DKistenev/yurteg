---
gsd_state_version: 1.0
milestone: v0.4
milestone_name: milestone
status: unknown
stopped_at: Completed 03-09-PLAN.md (Wire push_deadlines in main.py — INTG-02 gap closed)
last_updated: "2026-03-20T15:35:23.148Z"
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 24
  completed_plans: 24
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-19)

**Core value:** Юрист загружает папку с документами и за 20 минут получает готовый реестр — без ручного ввода, без обучения, без «проекта внедрения»
**Current focus:** Phase 03 — integrations-multitenancy

## Current Position

Phase: 03 (integrations-multitenancy) — EXECUTING
Plan: 8 of 9

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01-infrastructure P01 | 2 | 2 tasks | 2 files |
| Phase 01-infrastructure P04 | 5 | 2 tasks | 2 files |
| Phase 02 P00 | 1 | 2 tasks | 3 files |
| Phase 02-document-lifecycle P01 | 2 | 2 tasks | 4 files |
| Phase 02 P02 | 2 | 2 tasks | 1 files |
| Phase 02-document-lifecycle P03 | 8 | 2 tasks | 4 files |
| Phase 02-document-lifecycle P05 | 5 | 2 tasks | 5 files |
| Phase 02-document-lifecycle P06 | 10 | 2 tasks | 2 files |
| Phase 02-document-lifecycle P07 | 4 | 2 tasks | 2 files |
| Phase 02-document-lifecycle P04 | 10 | 2 tasks | 2 files |
| Phase 02-document-lifecycle P04 | 10 | 2 tasks | 2 files |
| Phase 03-integrations-multitenancy P07 | 48s | 1 tasks | 0 files |
| Phase 03-integrations-multitenancy P00 | 2min | 1 tasks | 3 files |
| Phase 03-integrations-multitenancy P01 | 5min | 2 tasks | 2 files |
| Phase 03-integrations-multitenancy P05 | 2min | 2 tasks | 3 files |
| Phase 03-integrations-multitenancy P02 | 2min | 2 tasks | 6 files |
| Phase 03-integrations-multitenancy P04 | 5min | 2 tasks | 4 files |
| Phase 03-integrations-multitenancy P03 | 8min | 2 tasks | 3 files |
| Phase 03-integrations-multitenancy P08 | 5min | 2 tasks | 2 files |
| Phase 03-integrations-multitenancy P06 | 5min | 2 tasks | 2 files |
| Phase 03-integrations-multitenancy P10 | 74s | 1 tasks | 1 files |
| Phase 03-integrations-multitenancy P11 | 5min | 1 tasks | 1 files |
| Phase 03-integrations-multitenancy P09 | 3min | 1 tasks | 1 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Provider abstraction и schema migrations — Phase 1, блокируют всё остальное
- [Roadmap]: FastAPI отложен — сервис-слой достаточен для Milestone 1
- [Roadmap]: Напоминания канал решён — in-app (Phase 3) + Telegram (Phase 3)
- [Research]: LOCAL_ONLY enforcement через httpx transport — требует spike в Phase 4
- [Phase 01-infrastructure]: Indexes extracted from _SCHEMA into _INDEXES list — prevents OperationalError when upgrading minimal v0.4 schema
- [Phase 01-infrastructure]: Backup trigger: only when DB is non-empty AND schema_migrations absent — avoids duplicate backups
- [Phase 01-infrastructure]: extra_body thinking:disabled изолирован только в ZAIProvider — не утекает в OpenRouter
- [Phase 01-infrastructure]: OllamaProvider — stub с NotImplementedError, реализация в Вехе 3
- [Phase 01-infrastructure]: services/ не импортирует streamlit — Telegram-бот и CLI вызывают pipeline_service без UI (FUND-02)
- [Phase 01-infrastructure]: extract_metadata() принимает provider/fallback_provider с None-дефолтами — обратная совместимость до Phase 2
- [Phase 01-infrastructure]: _RU_MONTHS + _translate_ru_months() для перевода русских месяцев перед dateutil — dateutil не парсит русский нативно
- [Phase 01-infrastructure]: Year-only guard: isdigit() + len<=4 перед dateutil — parse('2025') возвращает today's month/day
- [Phase 02]: xfail strict=False: тесты помечены XFAIL до реализации — CI безопасен
- [Phase 02]: Wave 0 skeleton pattern: тест-файлы с xfail создаются до сервисов, assertions заполняются после
- [Phase 02-document-lifecycle]: lifecycle_service использует db.conn (публичный атрибут Database) — не db._conn
- [Phase 02-document-lifecycle]: get_attention_required исключает manual_status документы — юрист берёт их под контроль явно
- [Phase 02-document-lifecycle]: Статус expiring/expired вычисляется через SQL julianday без Python datetime в сервисном слое
- [Phase 02]: computed_status вычисляется отдельным SQL-запросом в tab_registry (не через get_all_results) — чистое разделение ответственности
- [Phase 02]: db открывается новым контекстным менеджером для каждого lifecycle lifecycle-вызова — безопасно при Streamlit reruns
- [Phase 02-document-lifecycle]: version_service использует db.conn (публичный), не db._conn — аналогично lifecycle_service
- [Phase 02-document-lifecycle]: Хук версионирования добавлен в controller.py — pipeline_service является тонкой обёрткой, save_result реально в controller
- [Phase 02-document-lifecycle]: find_version_match фильтрует кандидатов по contract_type + counterparty перед cosine_sim — O(1) SQL вместо O(N)
- [Phase 02-document-lifecycle]: save_payments hook живёт в controller.py — единственное место с доступом к db объекту
- [Phase 02-document-lifecycle]: Идемпотентность save_payments через DELETE+INSERT — гарантирует актуальность данных при переобработке
- [Phase 02-document-lifecycle]: Graceful import guard (_HAS_CALENDAR) для streamlit_calendar — приложение запускается без зависимости
- [Phase 02-document-lifecycle]: tab_payments фильтрует платежи по contract_id через list comprehension — без доп. SQL
- [Phase 02-document-lifecycle]: review_service использует db.conn (публичный), не db._conn — последовательно с lifecycle_service и version_service
- [Phase 02-document-lifecycle]: Вкладка Шаблоны добавлена как 5-й top-level таб рядом с Сводка/Реестр/Детали/Платёжный календарь
- [Phase 02-document-lifecycle]: review_against_template использует subject поля контракта как текст документа — полного текста в БД нет
- [Phase 02-document-lifecycle]: Карточка документа структурирована в 4 вкладки — tab_main содержит карточку + замечания + пометки юриста
- [Phase 02-document-lifecycle]: generate_redline_docx использует subject договора как текст — полный текст не хранится в contracts
- [Phase 02-document-lifecycle]: generate_redline_docx использует subject договора как текст — полный текст не хранится в contracts
- [Phase 03-integrations-multitenancy]: INTG-03 (Google Drive) deferred to v2 — Telegram-бот покрывает сценарий, Google Drive требует серверной инфраструктуры
- [Phase 03-integrations-multitenancy]: PROF-02 (совместный доступ юристов) deferred to v2 — требует PostgreSQL/Supabase вместо local SQLite
- [Phase 03-integrations-multitenancy]: Wave 0 xfail skeletons — server/ пакет намечен: queue_service, binding_service, deadline_service; services/client_manager интерфейс определён
- [Phase 03-integrations-multitenancy]: INTG-04 переиспользует get_attention_required из lifecycle_service — no new service layer needed, только UI слой
- [Phase 03-integrations-multitenancy]: INTG-04 toast uses computed_status field on DeadlineAlert, not alert_type — maps expiring/expired correctly
- [Phase 03-integrations-multitenancy]: Stateless client switching via Streamlit selectbox — db_path resolved from get_db_path(_selected_client), no mutable state on ClientManager
- [Phase 03-integrations-multitenancy]: rapidfuzz imported inside try/except in ClientManager.find_client_by_counterparty — graceful degradation if not installed
- [Phase 03-integrations-multitenancy]: bot_data[db] pattern: ServerDatabase stored in Application.bot_data so handlers access via context.bot_data['db']
- [Phase 03-integrations-multitenancy]: consume_pending_binding atomic: SELECT+DELETE inside single threading.Lock prevents double-consume race
- [Phase 03-integrations-multitenancy]: Single daily cron at 09:00 UTC — per-user digest_hour scheduling is v2; single daily run sufficient for MVP
- [Phase 03-integrations-multitenancy]: Scheduler started only inside BOT_TOKEN guard — avoids startup crash in dev without token
- [Phase 03-integrations-multitenancy]: TelegramSync.bind() uses JSON body POST — matches actual bot_server /api/bind that reads request.json()
- [Phase 03-integrations-multitenancy]: notify_processed() graceful degradation: /api/notify not yet in bot_server, logs warning and returns False
- [Phase 03-integrations-multitenancy]: Auto-process uses pipeline_service.process_archive() module function (not PipelineService class) — returns dict with done/errors/total
- [Phase 03-integrations-multitenancy]: auto_bind_results checks result.status == 'done' (ProcessingResult has no .success attr); move_record_to_client uses raw db.conn SQL (Database has no get/delete by id methods)
- [Phase 03-integrations-multitenancy]: test_telegram_bot.py rewired to use ServerDatabase directly — server.queue_service/binding_service stubs obsolete
- [Phase 03-integrations-multitenancy]: test_switch_client uses get_db() path comparison — ClientManager has no switch_client/active_db_path API
- [Phase 03-integrations-multitenancy]: Provider instances created once in Controller.__init__ and shared across parallel _ai_task threads — avoids per-call instantiation, thread-safe since providers are stateless
- [Phase 03-integrations-multitenancy]: _legacy_mode in ai_extractor.py retained as safe fallback for direct calls without provider (tests, scripts) — not removed as plan specified
- [Phase 03-integrations-multitenancy]: Confirmation button placed inside bindings guard, nested Database contexts for move_record_to_client, st.rerun() only on successful moves
- [Phase 03-integrations-multitenancy]: push_deadlines block placed outside tg_queue_fetched guard — runs independently on every app load; try/except NameError used to detect _alerts from toast block; empty list pushed to clear stale server data

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 3]: APScheduler + Streamlit threading caveats — нужна проверка против текущей версии Streamlit перед реализацией
- [Phase 4]: LOCAL_ONLY блокировка HTTP — нужен spike: достаточно ли патча httpx transport для openai SDK + python-telegram-bot

## Session Continuity

Last session: 2026-03-20T15:35:23.143Z
Stopped at: Completed 03-09-PLAN.md (Wire push_deadlines in main.py — INTG-02 gap closed)
Resume file: None
