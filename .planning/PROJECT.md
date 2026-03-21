# ЮрТэг

## What This Is

ЮрТэг — десктопное приложение на Python (Streamlit) для автоматической обработки архивов юридических документов. Загрузка папки с PDF/DOCX → извлечение текста → анонимизация ПД → AI-извлечение метаданных → автосортировка по папкам → Excel-реестр. Плюс: статусы документов, версионирование, платёжный календарь, ревью против шаблонов, Telegram-бот для приёма документов и уведомлений, мультиклиентский режим.

## Core Value

Юрист загружает папку с документами и за 20 минут получает готовый реестр с метаданными — без ручного ввода, без обучения, без «проекта внедрения».

## Current State (после v0.4)

**Codebase:** 11 353 LOC Python, 219 тестов
**Tech stack:** Python 3.10+, Streamlit, SQLite, openai SDK, pdfplumber, natasha, sentence-transformers, rapidfuzz
**AI:** ZAI GLM-4.7 (основной), OpenRouter (fallback), Ollama stub для будущей локальной LLM
**Доставка:** DMG для macOS через PyInstaller, планируется .exe для Windows

### Что построено в v0.4:

- Модульный пайплайн: scanner → extractor → anonymizer → ai_extractor → validator → database → organizer → reporter
- Версионированные миграции SQLite (6 миграций, автобэкап)
- Провайдер-абстракция AI (ZAI/OpenRouter/Ollama) с переключением через конфиг
- Сервис-слой без Streamlit (pipeline_service, lifecycle_service, version_service, payment_service, review_service, client_manager, telegram_sync)
- Автостатусы документов (действует/истекает/истёк) + ручной override
- Версионирование документов через MiniLM эмбеддинги + diff + redline .docx
- Платёжный календарь с разворотом периодических платежей
- AI-ревью договора против шаблона-эталона
- Telegram-бот: приём документов, ежедневный дайджест сроков, привязка через /start
- Мультиклиентский режим: изолированные БД, fuzzy-автопривязка по контрагенту

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

### Active

- [x] Интеграция локальной QWEN 1.5B как провайдера по умолчанию (v0.5, Phase 4)
- [x] llama-server + GBNF грамматика (v0.5, Phase 4)
- [x] Post-processing ответов локальной модели (v0.5, Phase 4)
- [ ] Пропуск анонимизации для локального провайдера (v0.5, Phase 5)
- [ ] UI-редизайн — уйти от AI-like интерфейса (веха будущая)
- [ ] Сборка DMG/EXE для конечных пользователей

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

## Current Milestone: v0.5 Локальная LLM

**Goal:** Интегрировать дообученную QWEN 1.5B как провайдер по умолчанию — юрист ничего не настраивает, всё работает локально из коробки.

**Target features:**
- llama-server + GBNF грамматика (кириллица-only) вместо Ollama
- Реализация OllamaProvider (сейчас stub)
- Post-processing ответов модели ("None" → null, санитайзер)
- Пропуск анонимизации для локального провайдера
- Локальная модель = провайдер по умолчанию

### Будущие вехи

| # | Веха | Описание |
|---|------|----------|
| 1 | **Архитектура + функционал** | ✅ Завершена (v0.4) |
| 2 | **Локальная LLM** | ◆ v0.5 — текущая |
| 3 | UI-редизайн | Уйти от AI-like интерфейса |

## Constraints

- **Команда**: 3 юриста, нет разработчика — всё через Claude Code
- **Tech stack**: Python, Streamlit, SQLite — менять стек нецелесообразно
- **AI SDK**: openai Python SDK — для совместимости с GLM, OpenRouter и будущей Ollama
- **Доставка**: DMG/EXE для индивидуальных юристов, не Docker
- **Безопасность**: локальная обработка по умолчанию, анонимизация как дополнительный слой

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| GLM как основной AI-провайдер | Самая доступная цена | ✓ Работает, fallback на OpenRouter |
| openai SDK вместо anthropic | Совместимость с GLM, OpenRouter, Ollama | ✓ Good |
| Напоминания — in-app + Telegram | Toast при запуске + единый бот на сервере | ✓ Done (v0.4) |
| Единый Telegram-бот на сервере | Юрист не создаёт бота, привязка через /start | ✓ Done (v0.4) |
| Мультиклиент через изолированные БД | Отдельный .db на клиента, надёжно и просто | ✓ Done (v0.4) |
| Phase 4 (Docker/аудит/LOCAL_ONLY) отложена | Фокус на индивидуальных юристов, не B2B | ✓ Правильно |
| UI-редизайн — отдельная веха | Не мешать архитектуру и визуал | ✓ Good |
| Локальная QWEN — отдельная веха | Дистилляция 7B → 1.5B — отдельный трек | ✓ Good |

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
*Last updated: 2026-03-21 after Phase 4 completion*
