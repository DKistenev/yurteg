# Project Research Summary

**Project:** ЮрТэг v1.0 — Backend Hardening
**Domain:** Python desktop app hardening (NiceGUI + SQLite + LLM pipeline thread safety, atomic I/O, config validation, test coverage)
**Researched:** 2026-03-28
**Confidence:** HIGH

## Executive Summary

ЮрТэг — зрелый MVP с полноценным AI-пайплайном, который работает, но несёт конкретные дефекты надёжности: гонки при параллельном чтении из SQLite, незащищённая запись settings.json, HTTP-запросы без таймаута, безмолвно проглатываемые ошибки. Это milestone hardening, а не greenfield — стек заморожен, структура не меняется. Все 83 задокументированных бага — точечные правки в существующих функциях, 15 test gaps закрываются без нового инфраструктурного кода.

Рекомендуемый подход — волновое исправление с жёсткой последовательностью в Wave 2: сначала обновить `ContractMetadata` в `models.py`, потом миграцию v10 в `database.py`, потом INSERT SQL. Остальные группы (config, providers, services, controller) независимы внутри своей волны. Никаких новых зависимостей в `requirements.txt` не нужно — все паттерны реализуются через уже установленные stdlib и имеющиеся пакеты (httpx 0.27.0, openai 2.26.0, threading, tempfile).

Главные риски: (1) deadlock от вложенных `with db._lock` при добавлении locks на read-методы без перехода на `RLock`; (2) неполная миграция v10 — три места для обновления, пропуск любого даёт молчаливую потерю данных; (3) слишком короткий таймаут для ollama на CPU спровоцирует ложный fallback на облачный провайдер. Все три риска имеют проверенные решения и верифицируются одним тестом каждый.

---

## Key Findings

### Recommended Stack

Стек заморожен — никаких новых установок. Все исправления покрываются уже присутствующими модулями. Верификация: `python -c "import httpx, openai, tempfile, threading, sqlite3"` — всё доступно без `pip install`.

**Core technologies:**
- `sqlite3` + `threading.RLock`: thread-safe доступ — RLock вместо Lock предотвращает deadlock при вложенных вызовах из сервисов
- `tempfile + os.replace`: атомарная запись settings.json — POSIX rename(2) гарантирует атомарность на том же filesystem
- `httpx.Timeout` (0.27.0): таймаут на HTTP-клиентах — уже в requirements.txt как зависимость openai SDK
- `openai` (2.26.0): `OpenAI(timeout=httpx.Timeout(...))` принимает объект Timeout при конструировании клиента
- `dataclasses.__post_init__`: валидация Config — без новых зависимостей, graceful fallback вместо raise

### Expected Features

**Must have (table stakes):**
- Thread-safe read-методы `database.py` (`get_all_results`, `get_stats`, `is_processed`) — при `max_workers=5` гонка активна прямо сейчас
- HTTP timeout на всех трёх LLM провайдерах — зависший llama-server блокирует поток навсегда, UI замерзает
- Замена `bare except` на конкретные исключения — программные баги проглатываются, становятся невидимыми
- `Config.__post_init__` валидация с graceful fallback (не raise) — невалидный settings.json не должен ломать старт
- Атомарная запись settings.json — потеря настроек при Force Quit
- `get_logprobs` в базовом классе `LLMProvider` с default `return {}` — хрупкий `hasattr` workaround в `ai_extractor.py`
- Реальная дата в redline-документах (`review_service.py`) — однострочный fix, прямое влияние на доверие юриста

**Should have (differentiators):**
- `STATUS_LABELS` с `css_class` в `lifecycle_service.py` — устраняет дублирование с UI, предотвращает рассинхронизацию
- Миграция v10 — колонка `contract_number` в `contracts` — устраняет первопричину ошибок версионирования
- `APP_VERSION` единый в `config.py` — убирает расхождение версий на хакатоне
- Полная деанонимизация всех строковых полей в `controller.py` — сейчас 4 из 8 полей деанонимизируются
- Fail-loud GBNF валидация после `complete()` — облегчает диагностику деградации модели

**Defer (v2+):**
- WAL mode (`PRAGMA journal_mode=WAL`) — оверкилл для desktop с 5 потоками и Python-level lock
- Async SQLite / aiosqlite — переписывание всего `database.py` без реального выигрыша
- Per-provider retry логика — дублирует уже существующий retry в `ai_extractor.py`
- Connection pool для SQLite — не имеет смысла для embedded базы с одним процессом

### Architecture Approach

Архитектура остаётся без изменений: UI → Service → Controller → Module → Provider → Data. Все правки — точечные модификации внутри существующих функций. Единственное аддитивное изменение — миграция v10 в `database.py`, которая следует уже установленному numbered-migration pattern (v1–v9). Критическая сборочная последовательность Wave 2: `models.py` → migration → save_result SQL — нарушение порядка даёт `OperationalError` в runtime.

**Major components и что меняется:**
1. `config.py` — `__post_init__` + fix `active_model` property + `APP_VERSION` + атомарная `save_setting`
2. `modules/database.py` — `RLock` + lock на 3 read-методах + migration v10 + обновление INSERT SQL
3. `providers/base.py + *.py` — `get_logprobs` default impl + `httpx.Timeout` на всех клиентах
4. `services/lifecycle_service.py` — `db._lock` в `get_attention_required` + `css_class` в `STATUS_LABELS`
5. `controller.py` — деанонимизация всех 8 строковых полей вместо текущих 4
6. Тесты (Wave 5) — thread safety с `threading.Barrier`, migration idempotency v2-v9, payment edges, ai_extractor helpers

### Critical Pitfalls

1. **Deadlock от вложенных `with db._lock`** — заменить `Lock()` на `RLock()` в `Database.__init__` до добавления locks на read-методы; `lifecycle_service.get_attention_required` вызывает `db.conn.execute()` напрямую и создаёт вложенную цепочку
2. **Неполная миграция v10 (три места)** — писать TDD тест перед правкой; нужно обновить: `ALTER TABLE` + `save_result INSERT` + `ON CONFLICT DO UPDATE SET contract_number = excluded.contract_number`; пропуск любого = молчаливая потеря данных
3. **Ollama timeout слишком короткий → ложный fallback** — `httpx.Timeout(connect=10, read=120)` для OllamaProvider; `timeout=30` только для облачных; cold start QWEN на CPU Intel = до 60 сек
4. **`Config.__post_init__` с `raise` ломает старые `settings.json`** — graceful fallback (`logger.warning + self.active_provider = "ollama"`), не `raise ValueError`; исключение только для логически невозможных состояний (`confidence_high <= confidence_low`)
5. **Глобальный embedding singleton загрязняет тесты** — `autouse` фикстура в `conftest.py` с `monkeypatch.setattr(version_service, "_model", None)`; симптом: тест проходит в изоляции, падает в полном suite

---

## Implications for Roadmap

На основе dependency graph из ARCHITECTURE.md — 5 волн исполнения.

### Phase 1: Config Hardening
**Rationale:** Полностью независим от других изменений; быстрые wins с высокой ценностью; тесты для Config пишутся без зависимостей от DB schema.
**Delivers:** Безопасный старт с любым `settings.json`; корректный `active_model`; атомарная запись настроек; единый `APP_VERSION`.
**Addresses:** `Config.__post_init__` graceful validation, `active_model` fix (Pitfall 6), `save_setting` atomic write, `APP_VERSION` constant.
**Avoids:** Pitfall 4 (raise vs graceful fallback), Pitfall 3 в части save_setting race condition.

### Phase 2: Provider Cleanup
**Rationale:** Независим от DB layer; разблокирует весь pipeline от зависания; исправляет хрупкий `hasattr` контракт в `ai_extractor`.
**Delivers:** LLM провайдеры с таймаутом и явным контрактом методов; конкретная обработка исключений вместо bare except.
**Uses:** `httpx.Timeout` (уже в requirements.txt), `openai.APITimeoutError`, `openai.APIError`.
**Implements:** Явный контракт `LLMProvider` base class через non-abstract `get_logprobs()` с default `return {}`.
**Avoids:** Pitfall 7 (abstractmethod сломает ZAI/OpenRouter), Pitfall 8 (единый timeout провоцирует ложный ollama fallback).

### Phase 3: Data Integrity (строго последовательно)
**Rationale:** Жёсткая зависимость: `models.py` → migration → INSERT SQL. `version_service` автоматически чинится после миграции без изменений кода. Должна предшествовать Phase 4.
**Delivers:** `contract_number` в модели + БД + корректное сохранение; версионирование документов работает корректно.
**Addresses:** Миграция v10, `ContractMetadata.contract_number`, `save_result` SQL update, `ON CONFLICT DO UPDATE`.
**Avoids:** Pitfall 2 (три места для обновления — TDD перед правкой).

### Phase 4: Thread Safety + Services
**Rationale:** Зависит от Phase 3 (актуальная схема БД); `RLock` устанавливается первым действием до добавления locks на read-методы.
**Delivers:** Параллельная обработка 5+ документов без `OperationalError`; `lifecycle_service` и `version_service` корректно работают с lock; `STATUS_LABELS css_class`.
**Addresses:** `database.py` read-методы, `lifecycle_service.get_attention_required` lock, `STATUS_LABELS css_class`, `payment_service` edge cases.
**Avoids:** Pitfall 1 (deadlock — `RLock` первым делом в этой фазе).

### Phase 5: Controller + Test Coverage
**Rationale:** `controller.py` зависит от корректной схемы (Phase 3) и сервисов (Phase 4); тесты верифицируют всё выше, пишутся последними.
**Delivers:** Полная деанонимизация всех 8 полей; 15 закрытых test gaps (thread safety, migration idempotency v2-v9, payment edges, ai_extractor helpers).
**Addresses:** `controller.py` deanonymize fix, concurrent tests с `threading.Barrier`, migration v2-v9 idempotency tests, embedding singleton isolation.
**Avoids:** Pitfall 5 (autouse fixture для embedding singleton), Pitfall 9 (wrap pattern сохраняет `pytest.raises(RuntimeError)` контракт).

### Phase Ordering Rationale

- Config и Provider фазы независимы — устраняют баги без затрагивания DB schema, начинать немедленно.
- Data Integrity обязана предшествовать Thread Safety — thread safety тесты пишутся против актуальной схемы с `contract_number`.
- `RLock` — первое действие Phase 4, иначе добавление locks на read-методы немедленно создаёт deadlock в `lifecycle_service.get_attention_required`.
- Тесты Phase 5 идут последними как сквозная верификация, но тесты для Config/Providers допустимо писать параллельно с Phase 1-2.

### Research Flags

Phases with standard patterns (skip research-phase):
- **Phase 1 (Config):** `dataclasses.__post_init__`, `os.replace` — стандартная stdlib. Документация не нужна.
- **Phase 2 (Providers):** `httpx.Timeout` задокументирован в STACK.md с конкретными значениями. Wrap pattern для исключений — стандарт.
- **Phase 3 (Data Integrity):** Numbered migration pattern реализован через v1-v9. Следовать существующему образцу.
- **Phase 4 (Thread Safety):** `threading.RLock` — stdlib, поведение известно. Pattern уже в кодовой базе.
- **Phase 5 (Tests):** `threading.Barrier` pattern задокументирован в STACK.md. `monkeypatch.setattr` — pytest stdlib.

Phases needing additional validation (не full research, одна проверка):
- **Phase 4:** Перед добавлением `db._lock` в `lifecycle_service` и `version_service` — выполнить `grep "db._lock\|db.conn" services/` для полной карты прямых обращений к lock из сервисов. Может оказаться больше трёх мест.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Все версии верифицированы через `pip show` и `requirements.txt`; паттерны из официальной документации Python/SQLite/openai |
| Features | HIGH | Ground truth — прямая инспекция кодовой базы; баги подтверждены конкретными строками кода |
| Architecture | HIGH | Все findings из прямого анализа 10+ файлов; dependency graph строго выведен из import-цепочек |
| Pitfalls | HIGH | Реальные баги с воспроизводимыми симптомами; каждый pitfall — конкретная строка кода и конкретный тест-верификатор |

**Overall confidence:** HIGH

### Gaps to Address

- **`RLock` vs WAL mode** — оба подхода валидны для thread safety reads. Исследование рекомендует RLock (проще, нет side files на диске). Зафиксировать выбор в DECISIONS.jsonl при начале Phase 4.
- **`Config.__post_init__` raise vs graceful** — STACK.md и PITFALLS.md расходятся: STACK.md приводит примеры с `raise ValueError`, PITFALLS.md настаивает на graceful fallback. Решение: graceful для `active_provider`/`llama_server_port` (могут быть в старом settings.json), `raise` для `confidence_high <= confidence_low` (всегда баг, не legacy).
- **Деанонимизация сигнатуры** — FEATURES.md отмечает cross-scope изменение; конкретная сигнатура pass-through маппинга требует проверки `controller.py` → `anonymizer.py` → `ai_extractor.py` перед имплементацией Phase 5.

---

## Sources

### Primary (HIGH confidence)
- Прямая инспекция кодовой базы — `modules/database.py`, `config.py`, `controller.py`, `services/lifecycle_service.py`, `services/version_service.py`, `providers/base.py`, `providers/ollama.py`, `modules/models.py`
- Python stdlib docs: `threading.Lock/RLock`, `dataclasses.__post_init__`, `os.replace`, `tempfile.mkstemp`
- SQLite docs: `check_same_thread=False`, `journal_mode=DELETE` concurrent access behavior
- openai-python SDK: `OpenAI(timeout=httpx.Timeout(...))` — verified against installed version 2.26.0
- httpx docs: `httpx.Timeout(connect, read, write, pool)` — verified against 0.27.0
- py-free-threading.github.io/testing — `threading.Barrier` pattern для concurrent tests

### Secondary (MEDIUM confidence)
- cpython issue #118172 — sqlite3 multithreading cache inconsistency discussion
- openai community — httpx.Timeout usage confirmation pattern

---
*Research completed: 2026-03-28*
*Ready for roadmap: yes*
