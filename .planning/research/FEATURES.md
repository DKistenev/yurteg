# Feature Research

**Domain:** Backend hardening — Python desktop application (NiceGUI + SQLite)
**Researched:** 2026-03-28
**Confidence:** HIGH (existing codebase provides ground truth; patterns are well-established Python idioms)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Missing any of these = the milestone is not "hardening." These are the definition of correctness.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Input validation in `Config.__post_init__()` | Конфиг с невалидными значениями (отрицательный порт, неизвестный провайдер) вызывает `AttributeError` глубоко в стеке вместо понятного сообщения об ошибке | LOW | `__post_init__` вызывается dataclass-ом автоматически; проверить `active_provider in {"ollama","zai","openrouter"}`, `0 < llama_server_port < 65536`, `0.0 <= confidence_high <= 1.0` |
| Thread-safe read-методы в `database.py` | `Database._lock` есть, но `get_contracts`, `get_contract`, `get_templates`, `get_payments` читают без блокировки — при `ThreadPoolExecutor(max_workers=5)` гонка на `self.conn` возможна | MEDIUM | `with self._lock` на всех публичных методах включая read-only; dict-cast делать вне lock |
| Атомарная запись settings.json | Запись JSON без tmp-rename теряет данные при Force Quit в момент записи | LOW | Писать в `settings.tmp`, затем `os.replace(tmp, target)` — атомарна на POSIX и Windows |
| Bare `except` → конкретные исключения | `except Exception` проглатывает `NameError`, `AttributeError` — программные баги становятся невидимыми в логах | LOW | Заменить на `sqlite3.OperationalError`, `json.JSONDecodeError`, `httpx.TimeoutException`, `openai.APIError` по контексту |
| Timeout на HTTP-запросы к провайдерам | Без timeout зависший llama-server блокирует поток навсегда; UI замерзает | LOW | `httpx.Timeout(connect=5.0, read=90.0)` через `http_client=httpx.Client(timeout=...)` в openai SDK |
| `contract_number` — миграция v10 | AI возвращает номер договора без нормализации; поиск и версионирование по номеру ненадёжны | MEDIUM | Добавить колонку `contract_number TEXT` в `contracts`, нормализация: strip + upper; _run_migrations() уже поддерживает добавление |
| Деанонимизация всех полей | Анонимизация заменяет "ООО Ромашка" → "[COMPANY_1]"; сейчас деанонимизируется только `subject`; `counterparty`, `parties` остаются с масками | MEDIUM | Pipeline передаёт маппинг только в рамках одного вызова; нужно применять reverse-mapping ко всем полям перед сохранением в БД |

### Differentiators (Competitive Advantage)

Отличают надёжный продукт от "работает на моей машине".

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `get_logprobs` в базовом классе `LLMProvider` | Сейчас метод есть только у `OllamaProvider`; `ai_extractor.py` вызывает через `hasattr()` — неявный контракт, хрупко | LOW | Добавить в `base.py` default impl `return {}` — не ломает существующих провайдеров, делает контракт явным |
| Fail-loud GBNF валидация | При невалидном GBNF llama-server возвращает мусор молча; ошибка обнаруживается только при парсинге downstream | LOW | После `complete()` проверить что ответ парсится как JSON; если нет — `logger.warning` с первыми 200 символами ответа |
| Реальная дата в redline-документах | `review_service.py` использует захардкоженную дату вместо `datetime.now()` — юрист видит неправильную дату в track-changes | LOW | Однострочный fix; прямое влияние на доверие к документу |
| Единый `STATUS_LABELS` с `css_class` | UI и backend определяют статусные метки независимо; `lifecycle_service.py` имеет `STATUS_LABELS` без `css_class` — UI дублирует и рассинхронизируется | MEDIUM | Добавить `css_class` в `STATUS_LABELS` в `lifecycle_service.py`; импортировать в UI вместо дублирования |
| `APP_VERSION` в одном месте | Версия хардкодится в нескольких файлах; расхождение при релизе создаёт путаницу | LOW | Определить как константу в `config.py`, импортировать везде |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| WAL mode для SQLite | "Улучшает параллелизм" | Для desktop-приложения с одним писателем WAL добавляет сложность без реального выигрыша; Python-level `_lock` уже решает проблему | Оставить default journal mode, усилить Python-level locking |
| Async SQLite (aiosqlite) | "Не блокирует event loop" | NiceGUI уже использует `run.io_bound()` для DB-вызовов; миграция на aiosqlite — переписывание всего `database.py` ради маргинального выигрыша | Оставить sync SQLite + `run.io_bound()` |
| Connection pool для SQLite | "Масштабируемость" | SQLite — embedded база, connection pool не имеет смысла; одно соединение с `check_same_thread=False` + `threading.Lock` — правильный паттерн | Один `self.conn` + `_lock` (уже так) |
| Полная retry-логика в каждом провайдере | "Надёжность" | `ai_extractor.py` уже реализует retry и fallback между провайдерами; retry на уровне провайдера создаёт двойные ожидания | Retry только в `ai_extractor.py`; провайдеры бросают исключения сразу |
| Отдельный лог-файл на провайдер | "Диагностика" | Разрастается в десятки файлов; стандартный Python logging с уровнями достаточен | `logging.getLogger(__name__)` с уровнем WARNING в продакшне |

---

## Feature Dependencies

```
Config.__post_init__ валидация
    └──independent──> (не зависит от других изменений)

STATUS_LABELS с css_class
    └──requires──> коммит в lifecycle_service.py ПЕРЕД изменением UI-импорта
    └──conflicts──> параллельное редактирование UI и backend этой же структуры

Thread-safe reads
    └──requires──> существующий self._lock (уже есть)
    └──independent──> от всех других фич

Атомарная запись settings.json
    └──requires──> знание пути settings.json (уже в config.py)

get_logprobs в base class
    └──requires──> OllamaProvider.get_logprobs остаётся как override
    └──enhances──> ai_extractor.py — убрать hasattr() паттерн

Миграция v10 (contract_number)
    └──requires──> _run_migrations() — уже поддерживает добавление новых версий
    └──enhances──> version_service.py — улучшает матчинг версий по номеру

Деанонимизация всех полей
    └──requires──> pipeline передаёт маппинг до сохранения в БД
    └──conflicts──> изменение сигнатуры pipeline-функций (cross-scope)
```

### Dependency Notes

- **STATUS_LABELS** — классический cross-scope change: backend определяет структуру, UI импортирует. Нужна координация между backend и frontend агентами.
- **Деанонимизация** — самая сложная зависимость: затрагивает `anonymizer.py`, `ai_extractor.py`, `controller.py`. Маппинг живёт в памяти в рамках одного вызова — нужно проследить цепочку передачи.
- **Thread-safe reads независимы** — можно реализовать изолированно без риска сломать другие компоненты.

---

## MVP Definition

### Обязательно для milestone "Backend Hardening v1.0"

- [ ] Thread-safe все методы database.py — без этого параллельная обработка 5 документов может corrupted БД
- [ ] HTTP timeout на провайдеры — без этого один зависший запрос блокирует UI навсегда
- [ ] Bare except → конкретные исключения — без этого программные баги проглатываются логом
- [ ] `Config.__post_init__` валидация — без этого невалидный active_provider падает с `AttributeError` глубоко в стеке
- [ ] Атомарная запись settings.json — без этого настройки теряются при Force Quit
- [ ] `get_logprobs` контракт в `base.py` — без этого `hasattr()` в `ai_extractor.py` — неявный хрупкий контракт
- [ ] Реальная дата в redline — однострочный fix с прямым влиянием на доверие юриста

### Добавить в v1.0 (чистка + тесты)

- [ ] APP_VERSION единый в `config.py` — 30 минут, убирает путаницу на хакатоне
- [ ] Fail-loud GBNF валидация — помогает диагностировать деградацию модели
- [ ] STATUS_LABELS с css_class — нужен для cross-scope консистентности UI (координация с frontend)
- [ ] Миграция v10 contract_number — улучшает версионирование

### Покрытие тестами (15 gaps)

- [ ] Thread safety — `threading.Thread` × 10 параллельных вставок + reads, проверить integrity
- [ ] Миграции v2–v9 — тест идемпотентности: применить дважды, схема идентична
- [ ] Payment edge cases — платёж без суммы, дата в прошлом, periodic без frequency
- [ ] `ai_extractor` helpers — `sanitize_metadata`, `_parse_date`, `_normalize_amount` в изоляции
- [ ] Config validation — невалидные значения поднимают `ValueError` в `__post_init__`
- [ ] Atomic settings write — mock FileNotFoundError в mid-write, проверить что partial write не читается

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Thread-safe reads | HIGH (data integrity) | LOW | P1 |
| HTTP timeout | HIGH (UX — не зависает) | LOW | P1 |
| Bare except cleanup | HIGH (debuggability) | LOW | P1 |
| Config `__post_init__` | MEDIUM (fail-fast) | LOW | P1 |
| Atomic settings write | MEDIUM (data safety) | LOW | P1 |
| `get_logprobs` в base class | MEDIUM (correctness) | LOW | P1 |
| Реальная дата в redline | MEDIUM (trust) | LOW | P1 |
| Тесты thread safety | HIGH (regression prevention) | MEDIUM | P1 |
| Тесты миграций v2-v9 | HIGH (regression prevention) | MEDIUM | P1 |
| `STATUS_LABELS` css_class | MEDIUM (cross-scope sync) | LOW | P2 |
| Миграция v10 contract_number | MEDIUM (search quality) | MEDIUM | P2 |
| APP_VERSION единый | LOW (polish) | LOW | P2 |
| Fail-loud GBNF | LOW (diagnostics) | LOW | P2 |
| Тесты payment edges | MEDIUM | LOW | P2 |
| Тесты ai_extractor helpers | MEDIUM | LOW | P2 |

---

## Implementation Patterns

Конкретные паттерны для этого проекта (Python 3.10+, SQLite, openai SDK):

**Thread-safe читатель:**
```python
def get_contracts(self, ...) -> list[dict]:
    with self._lock:
        rows = self.conn.execute("SELECT ...", (...,)).fetchall()
    return [dict(r) for r in rows]  # dict cast вне lock — безопасно
```

**Атомарная запись JSON:**
```python
import os
tmp = settings_path.with_suffix(".tmp")
tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
os.replace(tmp, settings_path)  # атомарна на POSIX и Windows
```

**Config validation в `__post_init__`:**
```python
def __post_init__(self) -> None:
    valid_providers = {"ollama", "zai", "openrouter"}
    if self.active_provider not in valid_providers:
        raise ValueError(f"active_provider must be one of {valid_providers}, got {self.active_provider!r}")
    if not (0 < self.llama_server_port < 65536):
        raise ValueError(f"llama_server_port must be 1-65535, got {self.llama_server_port}")
    if not (0.0 <= self.confidence_high <= 1.0):
        raise ValueError(f"confidence_high must be 0-1, got {self.confidence_high}")
```

**HTTP timeout для openai SDK:**
```python
import httpx
from openai import OpenAI
client = OpenAI(
    base_url=...,
    api_key=...,
    http_client=httpx.Client(
        timeout=httpx.Timeout(connect=5.0, read=90.0, write=10.0, pool=5.0)
    )
)
```

**`get_logprobs` в base class:**
```python
# providers/base.py
def get_logprobs(self, messages: list[dict], fields_to_check: list[str]) -> dict[str, float]:
    """Default: логпробы недоступны. Override в провайдерах с поддержкой (OllamaProvider)."""
    return {}
```

**Тест thread safety:**
```python
import threading
def test_concurrent_inserts(tmp_db):
    errors = []
    def insert(i):
        try:
            tmp_db.save_result(make_result(i))
        except Exception as e:
            errors.append(e)
    threads = [threading.Thread(target=insert, args=(i,)) for i in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert not errors
    assert len(tmp_db.get_contracts()) == 10
```

---

## Sources

- Кодовая база — прямой анализ `modules/database.py`, `providers/ollama.py`, `providers/base.py`, `config.py`, `services/lifecycle_service.py` — HIGH confidence
- `.planning/PROJECT.md` — milestone scope, список 83 багов и 15 test gaps — HIGH confidence
- Python stdlib: `threading.Lock`, `os.replace`, `dataclasses.__post_init__` — standard library, HIGH confidence
- openai SDK docs: `http_client=httpx.Client(timeout=...)` — стандартный паттерн, MEDIUM confidence

---

*Feature research for: ЮрТэг v1.0 — Backend Hardening (fixes + test coverage)*
*Researched: 2026-03-28*
