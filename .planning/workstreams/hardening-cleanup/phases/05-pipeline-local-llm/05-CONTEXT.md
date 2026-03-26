# Phase 5: Пайплайн с локальной моделью - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Обработка документов работает end-to-end через локальную LLM: post-processing ответов модели подключён в ai_extractor.py, анонимизация пропускается для локального провайдера, и пользователь может переключиться на облачный провайдер через UI.

</domain>

<decisions>
## Implementation Decisions

### Post-processing интеграция
- **D-01:** `sanitize_metadata()` вызывается в `ai_extractor.py` после получения ответа от OllamaProvider (уже создан в Phase 4, модуль `modules/postprocessor.py`)
- **D-02:** Post-processing применяется только для локального провайдера (облачные провайдеры уже возвращают чистые ответы)

### Пропуск анонимизации
- **D-03:** Полный пропуск — `anonymize()` НЕ вызывается для локального провайдера (без NER, без масок)
- **D-04:** Определяется по `config.active_provider == "ollama"`
- **D-05:** Де-анонимизация тоже пропускается (маски не создавались, replacements пуст)
- **D-06:** AnonymizedText с пустым replacements создаётся для совместимости интерфейса пайплайна

### UI-переключатель провайдера
- **D-07:** Временный переключатель в expander «Настройки» в sidebar (спрятан по дефолту)
- **D-08:** Сохраняется в config файл — переживает перезапуск приложения
- **D-09:** Переключение без перезапуска — следующие документы идут через выбранный провайдер

### Claude's Discretion
- Конкретная реализация config persistence (JSON файл, путь)
- Как именно AnonymizedText создаётся без вызова anonymize (обёртка или прямая конструкция)
- Точное размещение selectbox внутри expander
- Нужна ли перезагрузка llama-server при переключении обратно на локальный

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Pipeline и анонимизация
- `controller.py` — `_run_pipeline()`: Этап A (anonymize), Этап B (_ai_task), де-анонимизация после AI
- `modules/anonymizer.py` — `anonymize()` функция, `AnonymizedText` dataclass
- `modules/ai_extractor.py` — `extract_metadata()`, куда подключить sanitize_metadata

### Post-processing (из Phase 4)
- `modules/postprocessor.py` — `sanitize_metadata()`, `FIELD_PROFILES`, профили полей
- `providers/ollama.py` — OllamaProvider, docstring про sanitize в Phase 5

### Config и UI
- `config.py` — Config dataclass, `active_provider` поле
- `main.py` — sidebar с expanders (Telegram, Управление клиентами), `_get_llama_manager()`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `sanitize_metadata()` в `modules/postprocessor.py` — готов к вызову, 189 строк, протестирован
- `AnonymizedText` dataclass в `modules/anonymizer.py` — можно создать с пустыми replacements
- Sidebar expanders в `main.py` — паттерн `st.sidebar.expander("Название", expanded=False)` уже используется

### Established Patterns
- `controller._run_pipeline()` — чёткое разделение на Этапы A/B/C
- `config.active_provider` — строка "zai"/"openrouter"/"ollama", определяет провайдер
- `@st.cache_resource` — используется для llama-server менеджера (не пересоздаётся при reruns)

### Integration Points
- `controller.py:160` — `anonymize()` вызов, нужно обернуть в условие
- `controller.py:179-183` — `extract_metadata()` вызов, после него вызвать sanitize_metadata
- `controller.py:196-206` — де-анонимизация, нужно обернуть в условие (если были маски)
- `main.py:609-730` — sidebar блок, добавить expander «Настройки» с selectbox провайдера

</code_context>

<specifics>
## Specific Ideas

- Переключатель — временный (D-07), будет убран когда локальная модель станет единственным вариантом
- При переключении на облако нужно проверить наличие API-ключа (ZAI/OpenRouter)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-pipeline-local-llm*
*Context gathered: 2026-03-21*
