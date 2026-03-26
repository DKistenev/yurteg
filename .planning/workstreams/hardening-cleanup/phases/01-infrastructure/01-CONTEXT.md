# Phase 1: Инфраструктура - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Безопасные обновления базы данных, абстракция AI-провайдеров, выделение сервис-слоя из UI, нормализация дат. Чисто техническая фаза — никаких UI-изменений, никаких новых фичей для пользователя. Результат: фундамент, на котором строятся фазы 2–4.

</domain>

<decisions>
## Implementation Decisions

### Поведение AI-провайдера
- До вехи 3 (локальная LLM) — автопереключение на запасной провайдер (GLM → OpenRouter) при недоступности основного
- После вехи 3 — локальная QWEN всегда доступна, проблема отпадает
- При мусорном ответе AI — повторная попытка с другим промптом, затем отметка в реестре
- Провайдеры переключаются через конфиг (одна строка), не через UI-кнопку

### Нормализация дат
- Задача — только нормализация формата (приведение к ISO 8601), НЕ валидация корректности
- Валидация корректности дат уже работает на стадии L2-верификации — не дублировать
- «01 января 2025», «01.01.2025», «January 1, 2025» → всё в единый формат

### Миграции БД
- Заменить текущий try/except на версионированные миграции
- Обновление не должно ломать существующую базу пользователя — это абсолютный приоритет

### Сервис-слой
- Отделить бизнес-логику от Streamlit — pipeline_service, registry_service
- Цель: логика вызывается без запуска UI (для будущих интеграций — Telegram-бот, API, тесты)

### Claude's Discretion
- Конкретная реализация системы миграций (Alembic vs ручная)
- Структура providers/ пакета (ABC vs Protocol)
- Как именно разделить main.py на сервисы
- Формат хранения промптов (YAML vs отдельные .txt файлы)
- Детали fallback-логики при переключении провайдеров

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Текущая архитектура
- `.planning/codebase/ARCHITECTURE.md` — текущий паттерн пайплайна, слои, data flow
- `.planning/codebase/CONCERNS.md` — техдолг: монолитный main.py, хардкод промптов, хрупкие миграции
- `.planning/codebase/STACK.md` — технологии, версии, зависимости

### Ресёрч
- `.planning/research/STACK.md` — рекомендации по стеку: тонкий провайдер-враппер, APScheduler, dateutil
- `.planning/research/ARCHITECTURE.md` — целевая архитектура: сервис-слой вместо HTTP API, providers/ пакет
- `.planning/research/PITFALLS.md` — бомба миграций, threading + Streamlit, кривые даты

### Требования
- `.planning/REQUIREMENTS.md` — FUND-01 через FUND-04

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `modules/ai_extractor.py` — уже содержит fallback-логику (_try_model, _create_client), можно извлечь в providers/
- `modules/models.py` — чистые dataclasses для межмодульной коммуникации, оставить как есть
- `controller.py` — `process_archive()` и `_run_pipeline()` — основа для pipeline_service
- `config.py` — Config dataclass, расширить для провайдер-настроек

### Established Patterns
- Модули общаются через dataclasses (FileInfo → ExtractedText → AnonymizedText → ContractMetadata)
- Каждый модуль — отдельный файл, чистые функции (кроме database)
- ThreadPoolExecutor для параллельной обработки AI-запросов
- SQLite с Lock для thread-safety

### Integration Points
- `main.py` → `controller.py` — здесь нужно вставить сервис-слой между ними
- `ai_extractor.py` → openai SDK — здесь нужно вставить провайдер-абстракцию
- `database.py` → SQLite schema — здесь нужно заменить на версионированные миграции

</code_context>

<specifics>
## Specific Ideas

- Локальная LLM (QWEN) будет всегда доступна — архитектура провайдеров должна это учитывать (Ollama-совместимый endpoint)
- Провайдер-абстракция через конфиг, а не через UI — пользователь не должен думать о моделях
- Принцип автоматизации: всё что можно сделать без участия пользователя — делать без участия

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-infrastructure*
*Context gathered: 2026-03-19*
