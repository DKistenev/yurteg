# Pitfalls Research

**Domain:** Backend hardening — добавление thread safety, валидации, error handling в существующее Python desktop приложение (NiceGUI + SQLite + llama-server)
**Researched:** 2026-03-28
**Confidence:** HIGH — все паттерны основаны на прямой инспекции кодовой базы + известные Python threading/SQLite паттерны

> Этот файл фокусируется на v1.0 Backend hardening milestone: 83 баги + 15 test coverage gaps.
> Предыдущие UI pitfalls (NiceGUI @layer, AG Grid, Quasar) остаются в силе для frontend слоя.

---

## Critical Pitfalls

### Pitfall 1: Вложенный `with db._lock` → deadlock

**What goes wrong:**
`threading.Lock()` в Python **не реентрантен**. Если функция A берёт `db._lock`, а внутри вызывает функцию B, которая тоже берёт `db._lock` — поток зависает навсегда.

В этой кодовой базе риск реальный: `find_version_match()` в `version_service.py` берёт `with db._lock` для загрузки кандидатов, потом внутри цикла снова берёт `with db._lock` для `_load_embedding()`. Сейчас это работает, потому что между двумя блоками lock освобождается. Один неосторожный рефакторинг (например, обернуть весь цикл в один `with db._lock`) — и deadlock без ошибки, просто зависание.

При добавлении locks на read-методы (`get_all_results`, `get_stats`) появится новая цепочка: любой сервис, вызывающий эти методы внутри уже залоченного контекста, дедлочится.

**Why it happens:**
Разработчик видит «здесь делаем чтение из БД» и добавляет `with db._lock`, не проверяя стек вызовов. Особенно опасно при вложенных вызовах между service-функциями.

**How to avoid:**
Два варианта — выбрать один и придерживаться:

Вариант A (рекомендуемый): заменить `threading.Lock()` на `threading.RLock()` в `Database.__init__`. RLock реентрантен — один поток может взять его несколько раз без deadlock.

Вариант B: строгий invariant — lock берётся только внутри методов класса `Database`, сервисы (`lifecycle_service`, `version_service`) никогда не обращаются к `db._lock` напрямую. Сейчас несколько сервисов уже нарушают это правило (`set_manual_status`, `ensure_embedding`).

**Warning signs:**
- Тест с двумя потоками зависает (timeout) вместо того, чтобы упасть с ошибкой
- `threading.Lock` в `Database.__init__` (а не `RLock`)
- `grep "db._lock" services/` показывает прямые вызовы lock из сервисов

**Phase to address:**
Thread safety phase — первым делом, до добавления locks на read-методы.

---

### Pitfall 2: `get_all_results()` и `get_stats()` без lock — `OperationalError: database is locked`

**What goes wrong:**
`get_all_results()` и `get_stats()` в `database.py` используют `self.conn.execute()` без `with self._lock`. При параллельной обработке пайплайн вызывает `save_result()` (с lock + commit) в 5 потоках (`max_workers=5`), пока UI читает `get_all_results()` для обновления реестра. В дефолтном режиме SQLite (не WAL) writer блокирует весь файл на время COMMIT — reader получает `OperationalError: database is locked`.

**Why it happens:**
Читающие методы кажутся «безопасными» — мы же только читаем. Но SQLite не разделяет read-lock и write-lock при `journal_mode=DELETE` (по умолчанию).

**How to avoid:**
Два подхода:

Подход A: добавить `with self._lock` во все методы `Database`. Просто, предсказуемо, но читатели блокируются на время записи.

Подход B: включить WAL mode в `__init__`:
```python
self.conn.execute("PRAGMA journal_mode=WAL")
```
WAL позволяет параллельные reads во время write без блокировки. Для desktop app с одним пользователем это оптимально. Минус: создаёт дополнительные `.wal` и `.shm` файлы рядом с `.db`.

**Warning signs:**
- `sqlite3.OperationalError: database is locked` в логах при обработке папки с 20+ файлами
- Тест с параллельными write/read падает недетерминированно

**Phase to address:**
Thread safety phase.

---

### Pitfall 3: Миграция v10 — три места для обновления, обычно забывают одно

**What goes wrong:**
`save_result()` содержит жёстко прописанный INSERT с явным перечислением 25 колонок и соответствующим tuple значений. После добавления `contract_number` (миграция v10) нужно синхронно обновить **три места**:
1. `_migrate_v10_contract_number()` — `ALTER TABLE contracts ADD COLUMN contract_number TEXT`
2. `save_result()` — добавить `contract_number` в column list и в tuple `data`
3. `ON CONFLICT DO UPDATE SET` — добавить `contract_number = excluded.contract_number`

Пропуск любого шага: молчаливая потеря данных (contract_number не сохраняется), или `OperationalError: table has N columns but N+1 values were supplied`.

Особая опасность: tuple `data` в `save_result()` строится по позиции — несоответствие числа `?` и значений → ошибка только в runtime, не при парсинге.

**Why it happens:**
Разработчик добавляет ALTER TABLE, видит что тесты не падают (потому что тест для v10 ещё не написан), считает работу завершённой.

**How to avoid:**
Писать тест ДО изменения (TDD):
```python
def test_v10_contract_number_saved(tmp_db):
    db = Database(tmp_db)
    # создать ProcessingResult с contract_number="12345/2026"
    # save_result(result)
    # get_contract_by_id → проверить contract_number == "12345/2026"
```
Тест даёт красный. Потом обновить все три места. Тест зеленеет.

**Warning signs:**
- `get_contract_by_id()` возвращает `contract_number: None` для только что обработанного файла
- Тест пишет контракт с contract_number, читает обратно — получает None
- `grep "contract_number" modules/database.py` показывает ALTER TABLE, но не INSERT

**Phase to address:**
Data integrity phase (миграция v10).

---

### Pitfall 4: `save_setting()` — гонка read-modify-write на файле

**What goes wrong:**
`save_setting()` в `config.py` делает read → modify → write:
```python
s = load_settings()     # читает JSON
s[key] = value          # меняет один ключ
_SETTINGS_FILE.write_text(json.dumps(s, ...))  # пишет обратно
```
Если два потока (UI сохраняет API key, Telegram sync пишет chat_id) вызывают `save_setting()` одновременно — второй поток перезапишет файл версией, прочитанной до записи первого. Один ключ будет потерян молча.

**Why it happens:**
Файловое I/O кажется «медленным и последовательным». GIL Python не защищает от этой гонки — между `load_settings()` и `write_text()` три Python-операции, GIL может переключить поток на каждой.

**How to avoid:**
Добавить module-level lock в `config.py`:
```python
_settings_lock = threading.Lock()

def save_setting(key: str, value) -> None:
    with _settings_lock:
        s = load_settings()
        s[key] = value
        _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _SETTINGS_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
```

**Warning signs:**
- API ключ или chat_id периодически пропадает после сохранения настроек
- Тест с двумя потоками, пишущими разные ключи — иногда теряет один

**Phase to address:**
Data integrity phase (атомарная запись settings).

---

### Pitfall 5: `Config.__post_init__()` с `raise` ломает существующие `settings.json`

**What goes wrong:**
Если добавить строгую валидацию:
```python
def __post_init__(self):
    if self.active_provider not in {"zai", "openrouter", "ollama"}:
        raise ValueError(f"Unknown provider: {self.active_provider}")
```
то пользователи с `~/.yurteg/settings.json`, содержащим старые значения (например, `"active_provider": "local"` из предыдущих версий, или опечатку) — не смогут запустить приложение. Crash при старте, непонятная ошибка.

**Why it happens:**
Разработчик добавляет валидацию для «защиты от дурака», не думая о forward/backward compatibility. Фокус на новом коде, а не на существующих данных пользователей.

**How to avoid:**
`__post_init__()` должен **исправлять** невалидные значения, не падать:
```python
def __post_init__(self):
    _VALID_PROVIDERS = {"zai", "openrouter", "ollama"}
    if self.active_provider not in _VALID_PROVIDERS:
        logger.warning("Неизвестный провайдер %r, использую ollama", self.active_provider)
        self.active_provider = "ollama"
    if self.llama_server_port <= 0 or self.llama_server_port > 65535:
        logger.warning("Неверный порт %d, использую 8080", self.llama_server_port)
        self.llama_server_port = 8080
```
`raise` только для критических несовместимостей, которые невозможно исправить автоматически.

**Warning signs:**
- `Config(active_provider="legacy_value")` поднимает `ValueError` в тесте
- Приложение не стартует после обновления у пользователя с кастомным settings.json

**Phase to address:**
Config hardening phase.

---

### Pitfall 6: `active_model` property хардкодит `"glm-4.7"` независимо от провайдера

**What goes wrong:**
```python
@property
def active_model(self) -> str:
    return "glm-4.7"  # всегда
```
`OllamaProvider.complete()` использует `model="local"` напрямую, игнорируя `config.active_model`. Это значит что `model_used` в логах и БД будет `"glm-4.7"` для документов, обработанных локальной моделью. Если хардинг добавляет логику через `active_model` (например, выбор параметров запроса) — она будет работать неверно для ollama.

**Why it happens:**
Property добавлялся как placeholder. Разработчик не отследил что `OllamaProvider` его не использует.

**How to avoid:**
Исправить property на основе `active_provider`:
```python
@property
def active_model(self) -> str:
    if self.active_provider == "ollama":
        return "local"
    elif self.active_provider == "openrouter":
        return self.model_fallback
    return "glm-4.7"
```
После исправления — проверить `model_used` в `save_result()`, он должен отражать реальную модель.

**Warning signs:**
- `model_used = "glm-4.7"` в БД для контракта, обработанного ollama
- `config.active_model` возвращает `"glm-4.7"` когда `active_provider == "ollama"`

**Phase to address:**
Config hardening phase (active_model fix).

---

### Pitfall 7: Добавление `get_logprobs` как `abstractmethod` ломает ZAI и OpenRouter провайдеры

**What goes wrong:**
`ai_extractor.py` проверяет `if not hasattr(provider, "get_logprobs")` — workaround, потому что метод есть только у `OllamaProvider`. Если при хардинге добавить `get_logprobs` как `@abstractmethod` в `LLMProvider` base class — `ZaiProvider` и `OpenrouterProvider` упадут с `TypeError: Can't instantiate abstract class` при старте.

Обратный сценарий: убрать `hasattr` без добавления метода в base class → `AttributeError` для non-ollama провайдеров в runtime.

**Why it happens:**
Метод добавлялся как расширение одного провайдера, не как часть контракта. hasattr — быстрый workaround, который работает пока.

**How to avoid:**
Добавить `get_logprobs` в базовый класс как **non-abstract** метод с default implementation:
```python
def get_logprobs(self, messages: list[dict], fields_to_check: list[str]) -> dict[str, float]:
    """Logprobs не поддерживаются этим провайдером. Override в OllamaProvider."""
    return {}
```
Тогда `hasattr` можно убрать — все провайдеры имеют метод. `OllamaProvider` переопределяет его реальной логикой.

**Warning signs:**
- `AttributeError: 'ZaiProvider' object has no attribute 'get_logprobs'` в runtime
- `TypeError: Can't instantiate abstract class ZaiProvider` после добавления abstractmethod
- Тест `test_providers.py` падает при создании ZAI/OpenRouter provider

**Phase to address:**
Provider cleanup phase (get_logprobs контракт в base class).

---

### Pitfall 8: Timeout для ollama — слишком короткий read timeout переключает на fallback

**What goes wrong:**
Если добавить `timeout=30` к `self._client.chat.completions.create(...)` (как для облачных провайдеров), то при холодном старте llama-server или первом inference на CPU — запрос упадёт с `openai.APITimeoutError`. Retry логика в `ai_extractor.py` поймает это как ошибку провайдера и переключится на ZAI fallback, тратя API кредиты. llama-server при этом работает нормально, просто медленно.

Реальное время inference QWEN 1.5B: ~2-5 сек на M1, ~15-30 сек на CPU Intel, до 60 сек на первый запрос после cold start.

**Why it happens:**
Timeout 30 сек разумен для облачных API. Разработчик применяет одну константу ко всем провайдерам.

**How to avoid:**
Разделить timeout для ollama:
```python
# В OllamaProvider.__init__
from openai import OpenAI
import httpx

self._client = OpenAI(
    base_url=base_url,
    api_key="not-needed",
    timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=5.0),
)
```
Для ZAI/OpenRouter — стандартный `timeout=30` достаточен.

**Warning signs:**
- `openai.APITimeoutError` в логах при первом документе после запуска llama-server
- Приложение переключается на ZAI хотя ollama работает (проверить через `ollama list`)
- Тест мокирует задержку 5 сек и видит timeout

**Phase to address:**
Provider cleanup phase (timeout).

---

### Pitfall 9: Замена bare `except` на конкретные исключения ломает тесты с `pytest.raises(RuntimeError)`

**What goes wrong:**
Если тест делает `with pytest.raises(RuntimeError)` и при хардинге bare except заменяется на `except openai.APIConnectionError` без wrap — тест начинает падать с `DID NOT RAISE`. Или наоборот: `openai.APIConnectionError` является подклассом `Exception`, тест с `pytest.raises(Exception)` проходит, но код, ожидающий `RuntimeError` в вызывающем коде, получает неожиданный тип.

Конкретный риск: `test_providers.py` и `test_ai_extractor_wiring.py` — проверить через `grep -n "pytest.raises" tests/test_providers.py tests/test_ai_extractor_wiring.py`.

**Why it happens:**
Тесты написаны под старое поведение. При изменении контракта исключений тесты не обновляются — они просто падают с неочевидным сообщением.

**How to avoid:**
При замене bare except использовать **wrap pattern** — сохраняет контракт исключений:
```python
# Было:
try:
    response = self._client.chat.completions.create(...)
except Exception as e:
    raise RuntimeError(f"Provider error: {e}") from e

# Стало (конкретное + wrap):
try:
    response = self._client.chat.completions.create(...)
except openai.APIConnectionError as e:
    raise RuntimeError(f"Нет связи с провайдером: {e}") from e
except openai.APITimeoutError as e:
    raise RuntimeError(f"Таймаут провайдера: {e}") from e
```
Тесты с `pytest.raises(RuntimeError)` продолжают работать. При необходимости добавить тест на конкретный тип.

**Warning signs:**
- `grep -r "pytest.raises(RuntimeError)" tests/` показывает тесты в provider/extractor тестах
- После изменения error handling тест падает с `DID NOT RAISE` или с `raises unexpected <type>`
- `test_providers.py` проходил ДО, падает ПОСЛЕ изменения

**Phase to address:**
Error handling phase + test coverage phase (запускать tests после каждого изменения).

---

### Pitfall 10: Concurrent тесты загрязняют друг друга через глобальный embedding singleton

**What goes wrong:**
`version_service.py` содержит глобальный singleton:
```python
_model = None
_model_lock = threading.Lock()
```
Он инициализируется лениво при первом вызове `get_embedding_model()` и **не сбрасывается** между тестами. Если один тест делает monkeypatch на `SentenceTransformer` или на `_model` — следующий тест в том же процессе получит или мок-объект, или реальную модель в зависимости от порядка запуска.

Симптом: тест проходит при `pytest tests/test_versioning.py`, падает при `pytest` (полный suite).

**Why it happens:**
Глобальное состояние модуля не сбрасывается автоматически между тестами. `importlib.reload()` помогает, но требует явной фикстуры.

**How to avoid:**
Добавить autouse фикстуру в `conftest.py`:
```python
@pytest.fixture(autouse=True)
def reset_embedding_singleton(monkeypatch):
    import services.version_service as vs
    monkeypatch.setattr(vs, "_model", None)
    yield
    monkeypatch.setattr(vs, "_model", None)
```
Для thread safety тестов: использовать `threading.Barrier` для детерминированного старта потоков, иначе гонка может не воспроизводиться.

**Warning signs:**
- Тест падает только при запуске всего suite, но проходит в изоляции
- `get_embedding_model()` возвращает mock из предыдущего теста
- `AttributeError` на mock-объекте в тесте, который вообще не мокирует embedding

**Phase to address:**
Test coverage phase (test isolation).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| `except Exception: pass` в миграциях для идемпотентности | Миграции не падают повторно | Скрывает реальные ошибки (диск полон, права, corrupt БД) | Только для `sqlite3.OperationalError` — нужно ловить только его |
| `check_same_thread=False` без WAL | Один connection на всё приложение | Требует явного lock на каждой операции; пропуск = гонка | Приемлемо при строгой lock-дисциплине |
| `hasattr(provider, "get_logprobs")` | Не трогать ZAI/OpenRouter | Хрупко при рефакторинге провайдеров | Временно — нужен default в базовом классе |
| Глобальный `_model` singleton | Однократная загрузка модели (5-10 сек) | Тесты загрязняют друг друга без reset-фикстуры | В production приемлемо, в тестах — только с autouse фикстурой |
| `active_model` возвращает хардкод | Быстро написать | Логи и БД врут о реальной модели | Never — нужно исправить |
| Timeout одинаковый для всех провайдеров | Простой код | ollama на CPU переключается на fallback при нормальной работе | Never для production |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| llama-server + openai SDK | `timeout=30` как для облака | `httpx.Timeout(connect=10, read=120)` — inference на CPU медленный |
| SQLite + threading | `with db._lock` в сервисе внутри уже залоченного метода | Заменить `Lock()` → `RLock()` в `Database.__init__` |
| pytest + глобальный singleton | Тест меняет `_model`, следующий получает грязное состояние | `monkeypatch.setattr(module, "_model", None)` в autouse-фикстуре |
| `Config.__post_init__` + `settings.json` | `raise ValueError` на невалидных полях | `logger.warning + fallback` к дефолту |
| SQLite `ALTER TABLE` в миграциях | `ALTER TABLE` внутри транзакции → OperationalError | В SQLite `ALTER TABLE` нельзя в явной транзакции — уже решено через отдельные `conn.execute()` без `BEGIN` |
| openai SDK + bare `except Exception` | Замена на конкретные ломает тесты | Wrap pattern: `except SpecificError as e: raise RuntimeError(...) from e` |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `get_all_results()` без lock — dirty read | `OperationalError: database is locked` в логах | WAL mode или lock на чтение | При параллельной обработке 10+ файлов |
| Embedding модель загружается в UI потоке | Freeze интерфейса 2-10 сек | Вызывать только из pipeline потоков, не из UI callback | При первом открытии карточки с версионированием |
| Backup при каждом апгрейде большой БД | Старт занимает несколько секунд (копирование файла) | Backup только при первом апгрейде — уже реализовано, не ломать | При БД > 100MB |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| API ключи в `settings.json` plaintext | При синхронизации папки в облако — утечка | Для desktop app приемлемо, достаточно предупреждения в UI |
| `f"ALTER TABLE contracts ADD COLUMN {col}"` | SQL injection | Приемлемо — `col` это константа в коде, не user input |

---

## "Looks Done But Isn't" Checklist

- [ ] **Миграция v10:** `ALTER TABLE` добавлен И `save_result()` обновлён И `ON CONFLICT DO UPDATE` обновлён — проверить `grep "contract_number" modules/database.py` показывает все три места
- [ ] **Thread safety read-методов:** `get_all_results()`, `get_stats()`, `is_processed()` имеют `with self._lock` — проверить `grep "def get_\|def is_" modules/database.py`
- [ ] **Config валидация:** `Config(active_provider="old_unknown_value")` — не поднимает исключений, возвращает `active_provider == "ollama"`
- [ ] **get_logprobs в base class:** `ZaiProvider().get_logprobs([], [])` — возвращает `{}`, не `AttributeError`
- [ ] **active_model fix:** `Config(active_provider="ollama").active_model` — не возвращает `"glm-4.7"`
- [ ] **Timeout разделён:** `OllamaProvider` использует `httpx.Timeout(read=120)`, облачные провайдеры — `timeout=30`
- [ ] **Test isolation:** все тесты проходят при `pytest --randomly-seed=12345` (рандомный порядок) — проверяет отсутствие зависимости от порядка

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Deadlock от вложенных locks | HIGH (зависание без ошибки) | Переключить `Lock` → `RLock` в `Database.__init__`, перезапустить |
| Миграция v10 не обновила INSERT | MEDIUM | Написать fix-миграцию v10b для backfill из AI re-parse; или принять потерю contract_number в уже обработанных записях |
| settings.json повреждён гонкой | LOW | Удалить `~/.yurteg/settings.json` — приложение создаст дефолтный; пользователь вводит настройки заново |
| Тесты сломаны из-за изменения контракта исключений | LOW | Обновить тесты: `pytest.raises(RuntimeError)` или применить wrap pattern в провайдерах |
| Timeout слишком короткий для ollama | LOW | Увеличить `read` timeout в конфиге OllamaProvider + добавить прогресс-индикатор |
| Глобальный singleton загрязняет тесты | LOW | Добавить autouse фикстуру в conftest.py + перезапустить suite |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Вложенный lock → deadlock | Thread safety: database.py locks | Тест: два потока параллельно вызывают `save_result` + `find_version_match` — не зависает |
| `get_all_results` без lock | Thread safety: read-методы | Тест: concurrent reads во время write — нет `OperationalError` |
| Миграция v10 неполная | Data integrity: contract_number | Тест пишет запись с contract_number, читает обратно — не None |
| save_setting гонка | Data integrity: атомарная запись | Тест: два потока пишут разные ключи — оба ключа в файле |
| `__post_init__` ломает старый settings.json | Config hardening | `Config(active_provider="deprecated")` — не поднимает исключений |
| active_model hardcode | Config hardening | `Config(active_provider="ollama").active_model != "glm-4.7"` |
| get_logprobs не в base class | Provider cleanup | `ZaiProvider().get_logprobs([], []) == {}` |
| Timeout ломает ollama fallback | Provider cleanup: timeout | Тест с mock задержкой 5 сек — fallback не срабатывает |
| Test isolation через singleton | Test coverage | `pytest --randomly-seed=999` — все тесты зелёные |
| Исключения меняются → тесты ломаются | Error handling + test coverage | Запускать полный suite после каждого изменения error handling |

---

## Sources

- Прямая инспекция кодовой базы: `modules/database.py`, `config.py`, `services/lifecycle_service.py`, `services/version_service.py`, `providers/ollama.py`, `providers/base.py`
- Существующие тесты: `tests/test_lifecycle.py`, `tests/test_migrations.py`, `tests/test_providers.py`
- Python threading docs: `threading.Lock` vs `threading.RLock` (реентрантность) — HIGH confidence
- SQLite docs: WAL mode, `check_same_thread`, `journal_mode=DELETE` поведение при concurrent access — HIGH confidence
- openai-python SDK: `httpx.Timeout` для разделения connect/read timeout — HIGH confidence
- pytest docs: `monkeypatch.setattr`, `autouse` фикстуры для изоляции глобального состояния — HIGH confidence

---
*Pitfalls research for: backend hardening — Python desktop app (NiceGUI + SQLite + llama-server)*
*Researched: 2026-03-28*
