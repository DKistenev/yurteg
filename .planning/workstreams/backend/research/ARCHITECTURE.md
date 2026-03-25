# Architecture: v0.9 Backend Hardening Integration

**Milestone:** v0.9 Backend Hardening
**Researched:** 2026-03-26
**Confidence:** HIGH (direct codebase analysis, all source files verified)

---

## Current Architecture (baseline)

```
Pipeline:
  Scanner → Extractor → [Anonymizer skip для ollama] → AI Extractor
         → PostProcessor → Validator → Database → Organizer → Reporter

Provider Stack:
  OllamaProvider (primary, llama-server)
  ZAIProvider / OpenRouterProvider (archive, не поддерживаются)

Services:
  lifecycle_service  — статусы документов
  review_service     — ревью против шаблона (HTML diff)
  version_service    — версионирование + redline DOCX (заглушка)
  payment_service    — платёжный календарь
  client_manager     — мультиклиентский режим
  llama_server       — жизненный цикл llama-server

Database (SQLite, 7 миграций):
  contracts, embeddings, document_versions, payments, templates

UI (NiceGUI):
  registry.py → document.py → templates.py → settings.py
```

---

## Feature Integration Map

### 1. Удаление validator.py

**Статус:** Полное удаление

**Где используется сейчас:**
- `controller.py` lines 26, 228, 264, 334 — `validate_metadata`, `validate_batch` вызываются внутри `_run_pipeline()`
- `tests/stress_test.py` — ~30 прямых импортов и вызовов
- `tests/test_controller.py` — патчи `controller.validate_metadata` / `controller.validate_batch`

**Что меняется:**
- `controller.py`: удалить оба импорта и два блока вызовов (строки L228-268 L5-верификации и L331-338 L4-batch)
- `ProcessingResult.validation` (dataclass) — поле остаётся, просто больше не заполняется через validator; может понадобиться для хранения logprobs confidence
- `modules/models.py` — `ValidationResult` dataclass: оставить или перепрофилировать как `ConfidenceResult`
- БД: поля `validation_status`, `validation_warnings`, `validation_score` в таблице contracts — либо удалить миграцией, либо оставить и не заполнять (безопаснее)
- `reporter.py` уже к этому моменту удалён (см. ниже)

**Новая зависимость:** GBNF грамматика берёт на себя гарантию структуры ответа. Confidence берётся из logprobs. Логика-ошибки "L1 mandatory fields missing" → теперь null в ContractMetadata без шума.

**Тест-долг:** stress_test.py и test_validator.py станут мёртвыми файлами — удалить или переписать как тесты GBNF/logprobs.

---

### 2. Удаление reporter.py (Excel)

**Статус:** Полное удаление

**Где используется сейчас:**
- `controller.py` line 24, 342 — единственный вызов `generate_report(all_data, output_dir)` в конце `_run_pipeline()`
- `tests/test_reporter.py` — 7 тест-функций
- `app/components/bulk_actions.py` — кнопка "Экспорт в Excel" (есть кнопка, её тоже убирать)

**Что меняется:**
- `controller.py`: удалить импорт и вызов, убрать `report_path` из возвращаемого stats dict (или оставить как `None`)
- `bulk_actions.py`: убрать кнопку Excel из bulk toolbar
- Зависимости `pandas` + `openpyxl` становятся неиспользуемыми — убрать из `requirements.txt`
- `tests/test_reporter.py` — удалить

**Замена:** Реестр живёт в AG Grid (уже есть). Download через `/download/{doc_id}` маршрут (уже есть).

---

### 3. Logprobs в OllamaProvider

**Статус:** Новая функциональность, изменение существующего файла

**Текущее состояние:** `OllamaProvider.complete()` вызывает `client.chat.completions.create()` и возвращает только `.content`. Logprobs не запрашиваются.

**Что добавить в `providers/ollama.py`:**
```python
def complete(self, messages, *, return_logprobs=False, **kwargs) -> str | tuple[str, float]:
    response = self._client.chat.completions.create(
        model="local",
        temperature=0.05,
        max_tokens=512,
        messages=messages,
        logprobs=return_logprobs,        # llama-server поддерживает через OpenAI API
        top_logprobs=1 if return_logprobs else None,
    )
    content = response.choices[0].message.content
    if return_logprobs:
        confidence = _compute_confidence(response.choices[0].logprobs)
        return content, confidence
    return content
```

**Вычисление confidence из logprobs:**
- Берём token logprobs первых ~20 токенов JSON-ответа (это ключевые поля)
- `confidence = exp(mean(logprobs))` → вероятность 0..1
- Альтернатива: min(exp(logprob)) по ключевым токенам (более консервативная оценка)

**Интеграция с ai_extractor.py:**
- `_try_provider()` вызывает `provider.complete(messages)` — сейчас всегда без logprobs
- Нужен второй путь: `provider.complete(messages, return_logprobs=True)` → `(raw_text, confidence)`
- `ContractMetadata.confidence` заполняется из logprobs вместо того чтобы приходить из JSON-поля модели

**Что меняется в контракте `LLMProvider` (base.py):**
- Добавить `complete(..., return_logprobs=False)` в абстрактный метод
- ZAI/OpenRouter провайдеры: logprobs они не поддерживают надёжно — вернуть `confidence=0.0` как fallback

**Затронутые файлы:**
- `providers/base.py` — обновить сигнатуру
- `providers/ollama.py` — реализовать logprobs
- `providers/zai.py`, `providers/openrouter.py` — добавить заглушку `return_logprobs=False → ignore`
- `modules/ai_extractor.py` — обновить `_try_provider()`, убрать `confidence` из JSON-промпта (или игнорировать поле из ответа)

---

### 4. Улучшение GBNF грамматики

**Статус:** Изменение существующей конфигурации + нового файла

**Где живёт сейчас:** `data/contract_05b.gbnf` (новый файл в git, не в modules/) — используется при запуске llama-server через `services/llama_server.py`

**Текущая проблема:** GBNF гарантирует структуру, но не качество — model может генерировать валидный JSON с бессмысленными значениями. Улучшение GBNF = ограничить enum-значения там где это возможно (document_type из known list, payment_frequency из ['monthly','quarterly','yearly','once'], etc.)

**Структура изменений:**
- `data/contract_05b.gbnf` или новый `data/contract_v2.gbnf` — обновить грамматику
- `services/llama_server.py` — убедиться что путь к grammar файлу конфигурируется
- `config.py` — добавить поле `gbnf_path: str` если его ещё нет

**Зависимость:** GBNF работает только с ollama (llama-server). ZAI/OpenRouter получают грамматику через промпт-инструкции в SYSTEM_PROMPT.

---

### 5. Redline-движок (полноценный)

**Статус:** Доработка существующей заглушки

**Текущее состояние:** `generate_redline_docx()` уже существует в `services/version_service.py` (строки 231-306). Реализован через `difflib.SequenceMatcher` на уровне предложений + python-docx track changes XML (`w:ins` / `w:del`).

**Проблемы текущей реализации:**
1. Гранулярность: разбивка по предложениям (`re.split(r'(?<=[.!?])\s+', ...)`) — грубая, не работает для юридических нумерованных списков
2. `_add_inserted_run()` — XPath манипуляция с `run._r.getparent().remove(run._r)` нестабильна в python-docx
3. Функция не вызывается из UI нигде кроме `/download/redline/{id}/{other_id}` маршрута

**Что улучшать:**
- Разбивка текста: добавить уровень "клаузы" (нумерованные пункты `\n\d+\.`) до уровня предложений
- Атрибуция: author/date в w:ins/w:del — параметризовать (сейчас хардкод '2026-01-01')
- Унификация: одна функция используется для версии vs. версии И для документа vs. шаблона (сейчас только версия vs. версия)
- Тест: покрыть unit-тестом с примером

**Для шаблон-ревью:** `review_service.review_against_template()` возвращает HTML diff (list[dict]). Нужна вторая точка входа — `generate_redline_docx(template_text, doc_text)` — уже существует, надо проверить что она правильно вызывается из document.py при ревью.

**Затронутые файлы:**
- `services/version_service.py` — улучшить `generate_redline_docx()`
- `app/main.py` — маршрут `/download/redline/` уже есть, убедиться что передаёт правильные тексты
- `app/pages/document.py` — кнопка "Скачать редлайн" уже есть (line 575)

---

### 6. Векторная система — версии + шаблоны

**Статус:** Расширение существующей системы

**Текущее состояние:**
- `version_service.ensure_embedding()` / `find_version_match()` — работает для версий договоров
- `review_service.match_template()` — работает для шаблонов, но embeddings для шаблонов не кэшируются (пересчитываются каждый раз)

**Проблема:** `match_template()` вызывает `compute_embedding(tmpl.content_text)` в цикле по всем шаблонам без кэширования. При 50+ шаблонах это медленно.

**Что добавить:**
- Таблица `template_embeddings` (новая) или дополнительный индекс в `embeddings` с `template_id` — нужна миграция v8
- `ensure_template_embedding(db, template_id, content_text)` по аналогии с `ensure_embedding()`
- `match_template()` использует кэшированные векторы

**Для "создать шаблон из версий":**
- В UI: кнопка "Сделать эталоном" на карточке документа → `review_service.mark_contract_as_template(db, contract_id)`
- Эта функция уже реализована (review_service.py line 48-71), но не подключена к UI
- Проблема: `mark_contract_as_template` копирует только `subject` как content_text, а не полный текст документа — нужно передавать полный текст из `contracts.original_path`

**Затронутые файлы:**
- `services/review_service.py` — добавить кэширование embeddings + исправить `mark_contract_as_template` (читать полный текст)
- `modules/database.py` — миграция v8 для `template_embeddings`
- `app/pages/document.py` — подключить кнопку "Сделать эталоном"

---

### 7. Подключение unwired методов к UI

**Статус:** Мелкие доработки, несколько точек

**Инвентаризация неподключённого:**

| Функция | Файл | Что нужно в UI |
|---------|------|----------------|
| `mark_contract_as_template()` | review_service | Кнопка в document.py |
| `bulk delete` | bulk_actions.py | `_delete_bulk` callback — уже есть show_bulk_delete_dialog, но нет реализации db.delete() |
| Открыть оригинал нативно | — | Нет функционала — нужен `subprocess.run(['open', path])` на macOS |
| Ручные дедлайны | lifecycle_service | `set_deadline()` — есть в lifecycle_service, не вызывается из UI |
| Redline template vs. doc | document.py | Кнопка "Скачать редлайн с шаблоном" — нет |

**Bulk delete:** В `bulk_actions.py` диалог есть, callback `on_confirm` передаётся, но `_delete_bulk` в `registry.py` нужно реализовать через `db.delete_contracts(ids: list[int])` — этого метода в `database.py` нет.

**Открыть файл нативно:** `document.py` имеет "Скачать PDF" через браузерный download (`/download/{id}`), но "Открыть оригинал в приложении" — нет. Нужно: кнопка → `subprocess.run(['open', original_path])` (macOS) / `os.startfile(path)` (Windows).

---

## Компоненты: новые vs. модифицированные

| Компонент | Действие | Затронутые файлы |
|-----------|----------|-----------------|
| `modules/validator.py` | УДАЛИТЬ полностью | `controller.py`, тесты |
| `modules/reporter.py` | УДАЛИТЬ полностью | `controller.py`, `bulk_actions.py`, тесты, `requirements.txt` |
| `providers/ollama.py` | ИЗМЕНИТЬ — добавить logprobs | `providers/base.py`, `ai_extractor.py` |
| `providers/base.py` | ИЗМЕНИТЬ — обновить сигнатуру | все провайдеры |
| `providers/zai.py` | ИЗМЕНИТЬ — заглушка logprobs | — |
| `providers/openrouter.py` | ИЗМЕНИТЬ — заглушка logprobs | — |
| `modules/ai_extractor.py` | ИЗМЕНИТЬ — confidence из logprobs | — |
| `modules/models.py` | ИЗМЕНИТЬ — перепрофилировать ValidationResult | — |
| `data/contract_v2.gbnf` | НОВЫЙ | `services/llama_server.py` |
| `services/version_service.py` | ИЗМЕНИТЬ — улучшить redline | `app/main.py` |
| `services/review_service.py` | ИЗМЕНИТЬ — кэш embeddings, fix mark_as_template | `modules/database.py` |
| `modules/database.py` | ИЗМЕНИТЬ — миграция v8, `delete_contracts()` | — |
| `controller.py` | ИЗМЕНИТЬ — убрать validator+reporter вызовы | — |
| `app/pages/document.py` | ИЗМЕНИТЬ — кнопки "Эталон", "Открыть", redline | — |
| `app/components/bulk_actions.py` | ИЗМЕНИТЬ — убрать Excel, реализовать delete | — |

**Итого:** 0 полностью новых модулей (кроме gbnf файла). Всё — доработка существующего.

---

## Data Flow после изменений

```
Старый:
  AI Extractor → PostProcessor → Validator → Database

Новый:
  AI Extractor (+ logprobs) → PostProcessor → Database
                     ↑
              OllamaProvider.complete(return_logprobs=True)
              → (json_text, confidence_float)
              ContractMetadata.confidence = confidence_float (не из JSON)
```

```
Старый пайплайн в controller._run_pipeline():
  ... → validate_metadata() → ... → validate_batch() → generate_report()

Новый:
  ... → db.save_result() [без validation] → (done)
```

---

## Зависимости между задачами (порядок сборки)

Порядок важен — некоторые задачи разблокируют другие:

```
Уровень 1 (независимые, можно параллельно):
  A. Удалить reporter.py         → разблокирует: чистые тесты
  B. Улучшить GBNF грамматику   → независимо от кода

Уровень 2 (зависит от уровня 1 или независимые):
  C. Удалить validator.py        → после A (иначе controller.py надо патчить дважды)
  D. Logprobs в OllamaProvider   → независимо

Уровень 3 (зависит от C, D):
  E. Обновить ai_extractor.py (confidence из logprobs)
     → зависит от D (OllamaProvider.complete с return_logprobs)
     → зависит от C (убрать L3/L5 валидацию из контроллера)

Уровень 4 (независимые сервисы):
  F. Улучшить redline (version_service)    → независимо
  G. Кэш embeddings (review_service)       → зависит от: миграция v8

Уровень 5 (UI wire-up, зависит от сервисов):
  H. Подключить unwired к UI              → зависит от E, F, G + delete_contracts() в DB
```

**Рекомендуемый порядок фаз:**

1. **Phase 1: Снос** — удалить validator.py и reporter.py, вычистить controller.py, удалить тесты, убрать pandas/openpyxl из зависимостей. Минимальные изменения, максимальная очистка.

2. **Phase 2: GBNF + Logprobs** — улучшить грамматику, добавить logprobs в OllamaProvider, обновить ai_extractor.py. Confidence теперь реальный, не придуманный моделью.

3. **Phase 3: Redline + Vector** — улучшить generate_redline_docx(), кэш embeddings для шаблонов, миграция v8, исправить mark_as_template с полным текстом.

4. **Phase 4: UI Wire-up** — подключить всё к UI: кнопка "Эталон", bulk delete, открыть нативно, redline для шаблон vs. документ.

---

## Критические точки интеграции

### Логика confidence после удаления validator

`ValidationResult` dataclass используется в `ProcessingResult.validation`. После удаления validator поле `validation` перестанет заполняться. Но:
- БД хранит `validation_status` — нужно либо удалить столбцы (миграция), либо оставить пустыми
- UI (`registry_table.py`) возможно отображает `validation_status` — нужна проверка

**Решение:** Не удалять колонки БД (безопаснее), заполнять `validation_status = null` или не заполнять. UI должен обработать `null` без взрыва.

### Logprobs и confidence в промпте

Текущий SYSTEM_PROMPT просит модель вернуть `confidence` как поле JSON. После перехода на logprobs это поле станет избыточным. Варианты:
- Убрать из промпта → модель не генерирует лишний токен, GBNF упрощается
- Оставить как есть → две метрики, logprobs приоритетнее

**Рекомендация:** убрать `confidence` из JSON-схемы промпта и GBNF после внедрения logprobs.

### Embedding-кэш для шаблонов

`embeddings` таблица сейчас хранит только `contract_id`. Шаблоны имеют `template_id`. Варианты:
- Добавить колонку `template_id` и nullable `contract_id` в существующую таблицу (миграция v8)
- Создать отдельную таблицу `template_embeddings`

**Рекомендация:** отдельная таблица — чище, без NULL в существующих строках.

---

## Риски

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| llama-server не возвращает logprobs в ожидаемом формате | MEDIUM | Проверить через `curl` до реализации. Fallback: confidence=0.7 (константа) |
| Stress_test.py большой объём тестов validator — много удалять | HIGH | Удалить весь файл, написать новые тесты для logprobs отдельно |
| python-docx track changes несовместимость с некоторыми версиями Word | LOW | Тест redline вручную перед финалом фазы |
| `delete_contracts()` не в Database — риск что cascade delete сломает embeddings/versions | MEDIUM | Реализовать через транзакцию с удалением из всех связанных таблиц |

---

*Confidence: HIGH — весь анализ основан на прямом чтении кода, без предположений.*
