# ЮрТэг

## What This Is

ЮрТэг — десктопное приложение на Python (NiceGUI) для автоматической обработки архивов юридических документов. Загрузка папки с PDF/DOCX → извлечение текста → AI-извлечение метаданных (локальная QWEN 1.5B или облако) → автосортировка по папкам → Excel-реестр. Плюс: статусы документов, версионирование, платёжный календарь, ревью против шаблонов, Telegram-бот, мультиклиентский режим. По умолчанию работает полностью локально — без отправки данных в облако.

## Core Value

Юрист загружает папку с документами и за 20 минут получает готовый реестр с метаданными — без ручного ввода, без обучения, без «проекта внедрения».

## Current State (после v0.9)

**Shipped:** v0.9 Backend Hardening (2026-03-27)
- Мёртвый код удалён: validator.py, reporter.py, deprecated AI functions
- Confidence через logprobs llama-server (двухзапросный flow)
- Word-level redline DOCX с track changes (w:ins/w:del)
- Кэш embeddings шаблонов (миграции v8, v9)
- UI: открытие файла, шаблоны, дедлайны, bulk delete
- 252 теста зелёные, 0 failures

<details>
<summary>v0.8 Hardening & Cleanup (2026-03-25)</summary>

- UPSERT вместо INSERT OR REPLACE — данные юриста не теряются
- FK enforcement, migration v7, деанонимизация subject
- Все кнопки UI работают (split panel, download, reprocess, settings)
- Streamlit удалён (2247 строк), legacy-код вычищен
- 315 тестов зелёные, офлайн-ресурсы бандлятся, зависимости пиннуты
</details>

**Next:** v0.8.1 UI Polish — полная переработка визуала по утверждённым мокапам

## Codebase

**LOC:** ~2 800 LOC app/ (NiceGUI UI) + ~9 500 LOC modules/services/tests = ~12 300 LOC Python
**Tests:** 252 passed
**Tech stack:** Python 3.10+, NiceGUI (native desktop), SQLite, openai SDK, pdfplumber, natasha, sentence-transformers, rapidfuzz, huggingface_hub
**AI:** QWEN 1.5B локальная (по умолчанию), ZAI GLM-4.7 (облако, архивный), OpenRouter (fallback, архивный)
**Inference:** llama-server (llama.cpp) с GBNF грамматикой per-request, logprobs confidence
**Доставка:** Планируется DMG для macOS, EXE для Windows

## Requirements

### Validated

- ✓ Реестр с фильтрами — ядро продукта — v0.4
- ✓ Автоматическая сортировка файлов по папкам — v0.4
- ✓ Извлечение метаданных из PDF/DOCX через AI — v0.4
- ✓ Анонимизация персональных данных — v0.4
- ✓ Валидация метаданных (L1–L5) — v0.4
- ✓ Excel-реестр на выходе — v0.4
- ✓ Статус документа (действует / истекает / истёк / ручной override) — v0.4
- ✓ Напоминания о сроках (in-app toast + Telegram-бот) — v0.4
- ✓ Мульти-провайдер AI (переключение через конфиг) — v0.4
- ✓ Сервис-слой отделён от UI — v0.4
- ✓ Версионирование документов с автосвязыванием — v0.4
- ✓ Платёжный календарь — v0.4
- ✓ AI-ревью против шаблона — v0.4
- ✓ Telegram-бот (приём документов + уведомления) — v0.4
- ✓ Мультиклиентский режим — v0.4
- ✓ Локальная LLM (QWEN 1.5B) как провайдер по умолчанию — v0.5
- ✓ llama-server + GBNF грамматика — v0.5
- ✓ Post-processing ответов модели — v0.5
- ✓ Пропуск анонимизации для локального провайдера — v0.5
- ✓ UI-переключатель провайдера — v0.5
- ✓ NiceGUI app scaffold с AppState и SPA-навигацией — v0.6 Phase 7
- ✓ llama-server тройная защита lifecycle — v0.6 Phase 7
- ✓ run.io_bound() паттерн для async DB-вызовов — v0.6 Phase 7
- ✓ AG Grid реестр с fuzzy search, статус-бейджами, hover-actions, версиями — v0.6 Phase 8
- ✓ Переключение клиента через header dropdown — v0.6 Phase 8
- ✓ Full-page карточка документа с AI-ревью, версиями, diff, заметками — v0.6 Phase 9
- ✓ Pipeline wiring: нативный folder picker, async обработка, real-time прогресс — v0.6 Phase 10
- ✓ Settings (macOS Preferences) + Templates (карточки с CRUD) — v0.6 Phase 11
- ✓ Onboarding: splash + wizard + empty state + guided tour — v0.6 Phase 12
- ✓ Design Polish: IBM Plex Sans, slate/indigo palette, animations, FullCalendar — v0.6 Phase 13
- ✓ Миграция UI на NiceGUI с архитектурой «реестр = приложение» — v0.6
- ✓ Светлая тема, утилитарный стиль, без AI slop — v0.6
- ✓ Full-page карточка документа с ревью, версиями, пометками — v0.6
- ✓ Управление шаблонами как отдельный таб — v0.6
- ✓ Страница настроек (провайдер, анонимизация, Telegram) — v0.6
- ✓ Empty state и onboarding при первом запуске — v0.6
- ✓ Календарь как переключатель вида реестра — v0.6
- ✓ Дизайн-система: tokens.css с --yt-* CSS variables, @layer discipline — v0.7
- ✓ Dark chrome header с лого-маркой «Ю» и filled indigo CTA — v0.7
- ✓ Hero splash с тёмным фоном и staggered entrance — v0.7
- ✓ Stats bar, filled status badges, AG Grid --ag-* theming — v0.7
- ✓ Rich empty state с CTA и карточками возможностей — v0.7
- ✓ Карточка документа: breadcrumbs, section dividers, amber AI-ревью — v0.7
- ✓ Color-coded template карточки с type icons и hover lift — v0.7
- ✓ Settings: structured sections, sidebar active state — v0.7
- ✓ Skeleton loading, card stagger, page fade, footer — v0.7
- ✓ Удаление validator.py и reporter.py (мёртвый облачный код) — v0.9
- ✓ Confidence через logprobs llama-server (двухзапросный flow) — v0.9
- ✓ GBNF грамматика v2: contract_number, строгие даты, без confidence — v0.9
- ✓ Whitelist аббревиатур NDA/SLA/GPS/ИНН в cyrillic_only — v0.9
- ✓ Word-level redline DOCX с track changes (w:ins/w:del) — v0.9
- ✓ Кэш embeddings шаблонов (миграции v8, v9) — v0.9
- ✓ Открытие файла из карточки документа — v0.9
- ✓ Сохранение как шаблон из карточки — v0.9
- ✓ Виджет дедлайнов в реестре — v0.9
- ✓ Bulk delete с обновлением дедлайнов — v0.9

## Current Milestone: v1.0 Hackathon-Ready

**Goal:** Устранить все баги из двойного аудита и довести каждый экран до демо-качества — приложение должно быть стабильным для живой демонстрации на хакатоне.

### Backend (CalmBridge — config.py, modules/, services/, providers/)
- [ ] Cross-scope фиксы: APP_VERSION, STATUS_LABELS с css_class, database → dict-only
- [ ] Thread safety: locks на все read-методы database.py, атомарные операции version_service
- [ ] Data integrity: contract_number миграция v10, атомарная запись settings, деанонимизация всех полей
- [ ] Error handling: bare excepts → конкретные, timeout на HTTP, fail-loud GBNF, redline реальная дата
- [ ] Config hardening: __post_init__() валидация, active_model fix, API key validation
- [ ] Provider cleanup: timeout, resource cleanup, get_logprobs контракт в base class
- [ ] Test coverage: 15 gaps — thread safety, миграции v2-v9, payment edges, ai_extractor helpers

### Frontend (VioletRiver — app/)
- [ ] P0 аудит-фиксы: шрифты 404 (add_static_files), AG Grid deprecated API, двойные вызовы
- [ ] P1 аудит-фиксы: settings dead code, hardcoded colors → tokens, bulk actions a11y, hover preview keyboard
- [ ] Cross-scope: единый STATUS_LABELS (после коммита CalmBridge), APP_VERSION в footer, убрать dict cast
- [ ] Error resilience: loading states и error boundaries — graceful degradation при падении бэкенда
- [ ] Реестр + split panel: доведение, поиск с иконкой, календарь
- [ ] Карточка документа: превью PDF/DOCX, визуальная плотность, feedback при сохранении заметок
- [ ] Шаблоны + Настройки: доведение карточек, visual consistency
- [ ] Онбординг: wizard и гид-тур — проверить и починить
- [ ] Финальный визуальный проход: spacing, typography, animations — консистентность

### Deferred

- [ ] Сборка DMG для macOS через PyInstaller + NiceGUI native mode
- [ ] Сборка EXE для Windows
- [ ] Автообновление или уведомление о новых версиях

### Out of Scope

- Google Drive автообработка — отложена, Telegram покрывает сценарий
- Совместный доступ нескольких юристов — требует серверной БД
- Аудит-лог — нет value без мультиюзера
- Docker-упаковка — DMG/EXE модель доставки
- API для внешних интеграций (Notion, CSV-экспорт) — v2+
- Мобильное приложение — web-first

## Context

### CustDev-результаты (19.03.2026)

9 интервью (3 реальных + 6 синтетических). Топ-боли: поиск документов (9/9), ручной реестр (7/9), пропущенные сроки (4/9), хаос нейминга (6/9). Главные барьеры: безопасность (снимается локальностью), «ещё одна система» (zero-onboarding), недоверие к AI (подсветка неуверенности).

### Будущие вехи

| # | Веха | Описание |
|---|------|----------|
| 1 | **Архитектура + функционал** | ✅ Завершена (v0.4) |
| 2 | **Локальная LLM** | ✅ Завершена (v0.5) |
| 3 | **UI-редизайн** | ✅ Завершена (v0.6) — NiceGUI, реестр-центричная архитектура, Impeccable polish |
| 4 | **Визуальный продукт** | ✅ Завершена (v0.7) — tokens.css, dark chrome, hero splash, visual density |
| 5 | **Hardening & Cleanup** | ✅ Завершена (v0.8) — баги, чистка, 315 тестов |
| 6 | **Backend Hardening** | ✅ Завершена (v0.9) — cleanup, AI pipeline, redline, vectors, UI wire-up |
| 7 | **Hackathon-Ready** | Аудит-фиксы + UI Polish + error resilience (v1.0) |
| 8 | DMG/EXE сборка | Доставка конечным пользователям (v1.1) |

## Constraints

- **Команда**: 3 юриста, нет разработчика — всё через Claude Code
- **Tech stack**: Python, NiceGUI (с v0.6, ранее Streamlit), SQLite
- **Design skills**: Impeccable skills (/audit, /arrange, /typeset, /colorize, /onboard и др.) как reference при реализации UI
- **AI SDK**: openai Python SDK — для совместимости с GLM, OpenRouter и llama-server
- **Доставка**: DMG/EXE для индивидуальных юристов, не Docker
- **Безопасность**: локальная обработка по умолчанию, анонимизация для облачных провайдеров

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| GLM как основной AI-провайдер | Самая доступная цена | ✓ Работает, теперь fallback |
| openai SDK вместо anthropic | Совместимость с GLM, OpenRouter, llama-server | ✓ Good |
| Напоминания — in-app + Telegram | Toast при запуске + единый бот на сервере | ✓ Done (v0.4) |
| Единый Telegram-бот на сервере | Юрист не создаёт бота, привязка через /start | ✓ Done (v0.4) |
| Мультиклиент через изолированные БД | Отдельный .db на клиента, надёжно и просто | ✓ Done (v0.4) |
| UI-редизайн — отдельная веха | Не мешать архитектуру и визуал | ✓ Good |
| llama-server вместо Ollama | GBNF grammar support, llamafile для бандлинга | ✓ Done (v0.5) |
| QWEN 1.5B как дефолт | Локальность = безопасность, 85% чистых ответов | ✓ Done (v0.5) |
| Пропуск анонимизации для локальной LLM | Данные не покидают машину — маскировка не нужна | ✓ Done (v0.5) |
| ORPO вместо SFT+DPO | Одна фаза обучения, лучше language control | ✓ Good (v3) |
| NiceGUI вместо Streamlit (v0.6) | Нативные split-view, кликабельные таблицы, Tailwind, desktop mode. Streamlit боролся с нужной архитектурой | ✓ Done (v0.6) |
| Реестр = приложение (v0.6) | Юрист работает с документами, не с дашбордами. Одно рабочее пространство вместо 5+ экранов | ✓ Done (v0.6) |
| Светлая тема (v0.6) | Убрать AI slop (cyan-on-dark, glassmorphism). Утилитарный стиль как Linear/Notion | ✓ Done (v0.6) |
| Design tokens + UI helpers (v0.6) | Извлечены повторяющиеся стили в app/styles.py + хелперы в ui_helpers.py | ✓ Done (v0.6) |
| AG Grid pagination (v0.6) | domLayout: normal + paginationAutoPageSize вместо autoHeight — предотвращает freeze на 500+ документов | ✓ Done (v0.6) |
| FullCalendar lazy-load (v0.6) | CDN грузится только при клике на календарь, а не при каждом запуске | ✓ Done (v0.6) |
| tokens.css + --yt-* prefix (v0.7) | Единая дизайн-система, --yt-* избегает --fc-* FullCalendar коллизий | ✓ Done (v0.7) |
| Dark chrome header (v0.7) | RunPod-стиль «dark chrome + light content» — 80% визуальной идентичности | ✓ Done (v0.7) |
| @layer discipline (v0.7) | components + overrides для безопасных Quasar переопределений | ✓ Done (v0.7) |
| AG Grid --ag-* theming (v0.7) | Отдельная система вне @layer — .ag-theme-quartz scope | ✓ Done (v0.7) |
| Фон slate-100 (v0.7) | Убрать «белую комнату» — карточки всплывают над серым фоном | ✓ Done (v0.7) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-28 — Milestone v1.0 Hackathon-Ready started (backend + frontend)*
