---
gsd_state_version: 1.0
milestone: v0.4
milestone_name: milestone
status: unknown
stopped_at: "Checkpoint: 02-04 tasks done, awaiting human-verify for versions tab UI"
last_updated: "2026-03-19T22:41:10.450Z"
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 12
  completed_plans: 12
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-19)

**Core value:** Юрист загружает папку с документами и за 20 минут получает готовый реестр — без ручного ввода, без обучения, без «проекта внедрения»
**Current focus:** Phase 02 — document-lifecycle

## Current Position

Phase: 02 (document-lifecycle) — EXECUTING
Plan: 2 of 8

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

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 3]: APScheduler + Streamlit threading caveats — нужна проверка против текущей версии Streamlit перед реализацией
- [Phase 4]: LOCAL_ONLY блокировка HTTP — нужен spike: достаточно ли патча httpx transport для openai SDK + python-telegram-bot

## Session Continuity

Last session: 2026-03-19T22:41:10.447Z
Stopped at: Checkpoint: 02-04 tasks done, awaiting human-verify for versions tab UI
Resume file: None
