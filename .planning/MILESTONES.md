# Milestones

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
