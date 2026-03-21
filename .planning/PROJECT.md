# ЮрТэг

## What This Is

ЮрТэг — десктопное приложение на Python (Streamlit) для автоматической обработки архивов юридических документов. Загрузка папки с PDF/DOCX → извлечение текста → AI-извлечение метаданных (локальная QWEN 1.5B или облако) → автосортировка по папкам → Excel-реестр. Плюс: статусы документов, версионирование, платёжный календарь, ревью против шаблонов, Telegram-бот, мультиклиентский режим. По умолчанию работает полностью локально — без отправки данных в облако.

## Core Value

Юрист загружает папку с документами и за 20 минут получает готовый реестр с метаданными — без ручного ввода, без обучения, без «проекта внедрения».

## Current Milestone: v0.6 UI-редизайн

**Goal:** Полная переделка UI — миграция на NiceGUI, архитектура «реестр = приложение», светлая тема, утилитарный стиль

**Target features:**
- Миграция UI с Streamlit на NiceGUI
- Архитектура «одно рабочее пространство» с реестром как центром
- Full-page transition для деталей документа
- Три таба верхнего уровня (Документы · Шаблоны · Настройки)
- Календарь как переключатель вида в реестре
- Светлая тема, профессиональный утилитарный стиль (без AI slop)
- Empty state с onboarding для первого запуска
- Кликабельные строки таблицы, фильтры, поиск
- Все существующие функции (ревью, версии, платежи, Telegram, мультиклиент) сохранены

**Design constraints:**
- Каждая фаза использует соответствующие Impeccable design skills (/onboard, /arrange, /typeset, /colorize и т.д.)
- Anti-pattern check: никакого cyan-on-dark, glassmorphism, gradient text, AI color palette
- Бизнес-логика (controller, modules, services) остаётся без изменений — меняется только UI-слой

## Current State (после v0.5)

**Codebase:** ~12 300 LOC Python, 223 теста
**Tech stack:** Python 3.10+, Streamlit → NiceGUI (v0.6), SQLite, openai SDK, pdfplumber, natasha, sentence-transformers, rapidfuzz, huggingface_hub
**AI:** QWEN 1.5B локальная (по умолчанию), ZAI GLM-4.7 (облако), OpenRouter (fallback)
**Inference:** llama-server (llama.cpp) с GBNF грамматикой, автоскачивание модели с HuggingFace
**Доставка:** DMG для macOS через PyInstaller, планируется .exe для Windows

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

### Active

- [ ] Миграция UI на NiceGUI с архитектурой «реестр = приложение»
- [ ] Светлая тема, утилитарный стиль, без AI slop
- [ ] Full-page карточка документа с ревью, версиями, пометками
- [ ] Управление шаблонами как отдельный таб
- [ ] Страница настроек (провайдер, анонимизация, Telegram)
- [ ] Empty state и onboarding при первом запуске
- [ ] Календарь как переключатель вида реестра
- [ ] Сборка DMG/EXE для конечных пользователей (v0.7)

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
| 3 | **UI-редизайн** | ◆ В работе (v0.6) — миграция на NiceGUI, реестр-центричная архитектура |
| 4 | DMG/EXE сборка | Доставка конечным пользователям (v0.7) |

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
| NiceGUI вместо Streamlit (v0.6) | Нативные split-view, кликабельные таблицы, Tailwind, desktop mode. Streamlit боролся с нужной архитектурой | — Pending |
| Реестр = приложение (v0.6) | Юрист работает с документами, не с дашбордами. Одно рабочее пространство вместо 5+ экранов | — Pending |
| Светлая тема (v0.6) | Убрать AI slop (cyan-on-dark, glassmorphism). Утилитарный стиль как Linear/Notion | — Pending |

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
*Last updated: 2026-03-22 after Phase 8 completion*
