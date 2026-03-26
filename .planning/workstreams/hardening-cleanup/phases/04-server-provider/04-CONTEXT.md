# Phase 4: Сервер и провайдер - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Локальная QWEN 1.5B (GGUF) стартует вместе с приложением через llama-server и принимает запросы через реализованный OllamaProvider. Модель и сервер скачиваются автоматически при первом запуске. Локальный провайдер = дефолт.

</domain>

<decisions>
## Implementation Decisions

### Запуск сервера
- **D-01:** llama-server скачивается автоматически с GitHub releases при первом запуске, если не найден
- **D-02:** GGUF модель скачивается с HuggingFace (SuperPuperD/yurteg-1.5b-v3-gguf, Q4_K_M, ~940MB)
- **D-03:** Оба файла сохраняются в `~/.yurteg/`
- **D-04:** llama-server стартует как subprocess при запуске приложения
- **D-05:** llama-server останавливается при закрытии приложения (atexit handler)
- **D-06:** Если llama-server недоступен (не скачан, ошибка старта) — fallback на облачный провайдер с warning

### Скачивание модели
- **D-07:** Прогресс-бар в Streamlit UI при скачивании модели (~940MB)
- **D-08:** Прогресс-бар при скачивании llama-server бинарника

### GBNF грамматика и post-processing
- **D-09:** GBNF грамматика гарантирует валидный JSON + enum-значения (payment_frequency, payment_direction)
- **D-10:** Post-processing по полям с профилями допустимых символов:
  - Только кириллица: `contract_type`, `special_conditions`
  - Кириллица + латиница: `counterparty`, `parties`, `subject`, `amount`, `payment_terms`
  - Строго enum: `payment_frequency` (monthly/quarterly/yearly/once), `payment_direction` (income/expense)
- **D-11:** Гибкая система: каждое поле имеет свой профиль допустимых символов, post-processing применяется после получения ответа

### Конфиг по умолчанию
- **D-12:** `active_provider` в config.py меняется с `"zai"` на `"ollama"` — все новые запуски сразу локальные
- **D-13:** Существующие конфиги пользователей не мигрируются — просто новый дефолт

### Claude's Discretion
- Конкретная реализация subprocess менеджера для llama-server
- Порт для llama-server (стандартный 8080 или другой)
- Обработка конфликтов портов
- Детали GBNF грамматики (конкретный синтаксис)
- Стратегия retry при недоступности сервера после старта

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Провайдер и AI
- `providers/base.py` — ABC интерфейс LLMProvider (complete, verify_key, name)
- `providers/ollama.py` — Текущий stub, нужно реализовать
- `providers/__init__.py` — Factory get_provider(), уже знает про 'ollama' кейс
- `config.py` — Config dataclass, active_provider и связанные поля

### AI extraction
- `modules/ai_extractor.py` — extract_metadata(), промпты, fallback логика
- `modules/models.py` — ContractMetadata dataclass (все поля и типы)

### Pipeline
- `controller.py` — _run_pipeline(), _ai_task(), как провайдеры используются

### Модель
- HuggingFace: `SuperPuperD/yurteg-1.5b-v3-gguf` — GGUF Q4_K_M (~940MB)
- Modelfile в корне проекта — параметры запуска (temperature, min_p, num_ctx, system prompt)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `LLMProvider` ABC (`providers/base.py`): `complete()`, `verify_key()`, `name` — OllamaProvider реализует этот интерфейс
- `get_provider()` / `get_fallback_provider()` (`providers/__init__.py`): Factory уже обрабатывает case "ollama"
- `ZAIProvider` (`providers/zai.py`): Использует openai SDK — llama-server тоже OpenAI-совместимый, можно переиспользовать паттерн
- `Config` dataclass (`config.py`): Уже имеет `active_provider`, `fallback_provider`, `ai_temperature`, `ai_max_tokens`

### Established Patterns
- Провайдеры stateless, создаются один раз в `Controller.__init__` и шарятся между потоками
- openai Python SDK используется во всех провайдерах — llama-server совместим с OpenAI API
- `_legacy_mode` в ai_extractor.py — fallback для прямых вызовов без провайдера

### Integration Points
- `Controller.__init__`: создание провайдера через `get_provider(config)`
- `Controller._ai_task`: вызов `extract_metadata()` с provider
- `config.py`: добавить поля для llama-server (порт, путь к бинарнику, путь к модели)
- `main.py`: запуск/остановка llama-server при старте/выходе приложения

</code_context>

<specifics>
## Specific Ideas

- Modelfile уже определяет параметры модели: temperature 0.05, min_p 0.05, num_ctx 4096, num_predict 512
- System prompt: "Извлеки метаданные из юридического документа. Ответ строго на русском языке."
- При будущей сборке DMG llama-server будет встроен в пакет — сейчас скачиваем отдельно

</specifics>

<deferred>
## Deferred Ideas

- DMG/EXE бандлинг с llama-server внутри — отдельная веха доставки
- Автоматический fallback на облако при низком качестве ответа — v2+
- Логирование уверенности модели для мониторинга — v2+

</deferred>

---

*Phase: 04-server-provider*
*Context gathered: 2026-03-21*
