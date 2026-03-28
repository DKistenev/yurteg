# Stack Research

**Domain:** Python desktop app — backend hardening (thread safety, atomic I/O, HTTP timeouts, config validation, concurrent test coverage)
**Researched:** 2026-03-28
**Confidence:** HIGH

---

## Context: This Is a Hardening Milestone, Not a Greenfield

The table below shows the locked existing stack. Nothing here changes.

| Technology | Version | Status |
|------------|---------|--------|
| Python | 3.10+ | locked |
| NiceGUI | 3.9.0 | locked |
| sqlite3 | stdlib | locked |
| openai SDK | 2.26.0 | locked |
| httpx | 0.27.0 | locked (openai dependency) |
| threading | stdlib | locked |
| pytest | installed | locked |

**Verified via:** `pip show openai` → 2.26.0; `cat requirements.txt` → httpx==0.27.0

The research below covers only the four backend problem areas from the audit.

---

## Area 1: Thread-Safe SQLite

### What Was Found in the Code

`database.py` already has `threading.Lock()` at `__init__` and uses it in `save_result()`, `get_contract_by_id()`, `get_contract_id_by_hash()`, `clear_all()`, `update_review()`.

**Missing locks:** `get_all_results()`, `get_stats()`, `is_processed()` — all execute `self.conn.execute(...)` without `with self._lock:`. With 5 parallel AI worker threads writing results while the UI thread reads the registry, this is a live race condition.

### Pattern: Extend Existing Lock to All Read Methods

No new library. No architecture change. Mechanical fix: wrap all `self.conn.execute()` calls in every public method with `with self._lock:`, and ensure `fetchall()` / `fetchone()` happen **inside** the lock.

```python
# WRONG — current state in get_all_results():
cursor = self.conn.execute("SELECT * FROM contracts ORDER BY processed_at")
rows = cursor.fetchall()

# CORRECT — cursor is tied to the connection; fetchall must be inside the lock
with self._lock:
    cursor = self.conn.execute("SELECT * FROM contracts ORDER BY processed_at")
    rows = cursor.fetchall()
```

**Why fetchall inside the lock:** `sqlite3.Cursor` holds a reference to the connection. Calling `fetchall()` after releasing the lock lets another thread execute on the same connection before results are collected — the cursor can see an inconsistent snapshot or raise `ProgrammingError`.

### Why Not WAL Mode or Per-Thread Connections?

- **WAL mode** (`PRAGMA journal_mode=WAL`) allows concurrent readers without blocking writers — but introduces a WAL file on disk and checkpoint management. Overkill for a desktop app with 5 write threads and low read latency requirements.
- **Per-thread connections** (`threading.local()`) eliminates the lock entirely but requires every method to open/close connections per-thread, complicating transaction semantics and the migration flow.

**Decision: keep single shared connection + extend lock to all public methods.**

---

## Area 2: Atomic Settings File Write

### What Was Found in the Code

`config.py::save_setting()`:

```python
def save_setting(key: str, value) -> None:
    s = load_settings()                    # read
    s[key] = value                         # modify
    _SETTINGS_FILE.write_text(...)         # write — NOT atomic
```

`Path.write_text()` opens, truncates, writes, closes. A crash between truncate and write produces a zero-byte or half-written settings file. On next launch `load_settings()` silently returns `{}`, losing all persisted settings.

### Pattern: Write-to-Temp-then-Replace

No new library. stdlib `tempfile` + `os.replace()`. Both are already available.

```python
import os
import tempfile

def save_setting(key: str, value) -> None:
    s = load_settings()
    s[key] = value
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Write to temp in same directory — same filesystem guarantees atomic rename
    fd, tmp_path = tempfile.mkstemp(dir=_SETTINGS_FILE.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(s, ensure_ascii=False, indent=2))
            f.flush()
            os.fsync(f.fileno())           # flush kernel buffer → disk
        os.replace(tmp_path, _SETTINGS_FILE)   # atomic on POSIX (rename(2) syscall)
    except Exception:
        try:
            os.unlink(tmp_path)            # clean up temp on failure
        except OSError:
            pass
        raise
```

**Why `os.replace()` not `Path.rename()`:** Both call `rename(2)` on POSIX (atomic). `os.replace()` is explicit about overwrite semantics and is documented as atomic when src/dst are on the same filesystem. Same filesystem is guaranteed by `dir=_SETTINGS_FILE.parent`.

**Why not `atomicwrites` library (PyPI):** Last release 2020. No Python 3.10+ CI. No maintenance. 10-line stdlib pattern achieves the same result with zero new dependency.

---

## Area 3: HTTP Timeout in openai SDK

### What Was Found in the Code

`OllamaProvider.__init__` (and equivalents in `ZaiProvider`, `OpenRouterProvider`):

```python
self._client = OpenAI(
    base_url=base_url,
    api_key="not-needed",
    # No timeout — default is 600 seconds (10 minutes)
)
```

With 5 `ThreadPoolExecutor` workers, one hung llama-server can stall a worker thread for up to 10 minutes. The app UI appears frozen.

### Pattern: httpx.Timeout at Client Construction

`httpx` 0.27.0 is already in `requirements.txt` (openai's HTTP backend). No new install.

```python
import httpx
from openai import OpenAI

# For OllamaProvider (local llama-server)
self._client = OpenAI(
    base_url=base_url,
    api_key="not-needed",
    timeout=httpx.Timeout(
        connect=5.0,    # llama-server is local — 5s connect is generous
        read=90.0,      # GBNF-constrained inference on CPU: 30–60s typical
        write=10.0,
        pool=5.0,
    ),
)

# For ZaiProvider / OpenRouterProvider (cloud)
self._client = OpenAI(
    base_url=base_url,
    api_key=api_key,
    timeout=httpx.Timeout(
        connect=10.0,
        read=120.0,     # cloud inference can be slower under load
        write=10.0,
        pool=5.0,
    ),
)
```

**What happens on timeout:** openai SDK raises `openai.APITimeoutError` (subclass of `openai.APIError`). Replace bare `except Exception` in provider `complete()` methods with `except openai.APITimeoutError` and `except openai.APIError` specifically.

### get_logprobs Contract in Base Class

`OllamaProvider` defines `get_logprobs()` but `LLMProvider` base class (`providers/base.py`) has no such method. The audit flagged: callers importing `LLMProvider` for type hints get an `AttributeError` at runtime if the provider doesn't implement it.

Fix: add a default implementation to `base.py`. Not abstract — most providers don't support logprobs.

```python
def get_logprobs(
    self, messages: list[dict], fields_to_check: list[str]
) -> dict[str, float]:
    """Logprob confidence scoring. Override in providers that support it.
    Default: returns empty dict (logprobs not supported).
    """
    return {}
```

No new dependency. Pure Python.

---

## Area 4: Config Validation via `__post_init__`

### What Was Found in the Code

`config.py` `Config` is a `@dataclass` with no `__post_init__`. The `active_model` property is hardcoded to `"glm-4.7"` regardless of `active_provider`. Invalid values silently pass through.

### Pattern: Dataclass __post_init__ with ValueError

No new library. Pure stdlib.

```python
VALID_PROVIDERS = frozenset({"zai", "openrouter", "ollama"})
VALID_VALIDATION_MODES = frozenset({"off", "selective", "full"})

def __post_init__(self) -> None:
    if self.active_provider not in VALID_PROVIDERS:
        raise ValueError(
            f"active_provider must be one of {VALID_PROVIDERS}, "
            f"got {self.active_provider!r}"
        )
    if self.fallback_provider not in VALID_PROVIDERS:
        raise ValueError(
            f"fallback_provider must be one of {VALID_PROVIDERS}, "
            f"got {self.fallback_provider!r}"
        )
    if self.validation_mode not in VALID_VALIDATION_MODES:
        raise ValueError(
            f"validation_mode must be one of {VALID_VALIDATION_MODES}, "
            f"got {self.validation_mode!r}"
        )
    if not 0.0 <= self.ai_temperature <= 2.0:
        raise ValueError(
            f"ai_temperature must be 0.0–2.0, got {self.ai_temperature}"
        )
    if self.ai_max_tokens < 1:
        raise ValueError(
            f"ai_max_tokens must be >= 1, got {self.ai_max_tokens}"
        )
    if self.max_workers < 1:
        raise ValueError(
            f"max_workers must be >= 1, got {self.max_workers}"
        )
    if self.confidence_high <= self.confidence_low:
        raise ValueError(
            f"confidence_high ({self.confidence_high}) must be > "
            f"confidence_low ({self.confidence_low})"
        )
```

**Fix `active_model` property:** Current hardcoded `return "glm-4.7"` ignores `active_provider`. Fix: map provider → model name, or remove the property and have each provider know its own model string.

```python
_PROVIDER_MODEL_MAP = {
    "zai": "glm-4.7",
    "openrouter": "arcee-ai/trinity-large-preview:free",
    "ollama": "local",
}

@property
def active_model(self) -> str:
    return _PROVIDER_MODEL_MAP.get(self.active_provider, "local")
```

---

## Area 5: Test Patterns for Coverage Gaps

### Concurrent Write/Read Safety Tests

Use stdlib `threading.Barrier` — not a plugin. Barrier ensures all threads start simultaneously, maximizing race window.

```python
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

def test_concurrent_save_no_corruption(tmp_db):
    db = Database(tmp_db)
    n = 20
    barrier = threading.Barrier(n)

    def write_one(i: int) -> None:
        barrier.wait()                      # all threads release at same instant
        result = make_fake_result(f"hash_{i:03d}")
        db.save_result(result)

    with ThreadPoolExecutor(max_workers=n) as pool:
        futures = [pool.submit(write_one, i) for i in range(n)]
        for fut in as_completed(futures):
            fut.result()                    # re-raises thread exceptions into test

    assert db.get_stats()["total"] == n
    db.close()
```

**Why `threading.Barrier`:** Guarantees the concurrent access window is real. Without it, threads execute sequentially and no race occurs. This is the standard Python free-threading test pattern per [py-free-threading.github.io](https://py-free-threading.github.io/testing/).

### Migration Idempotency Tests (v2–v9)

Current `test_migrations.py` only tests v1. Each migration must be idempotent (running twice must not raise).

```python
@pytest.mark.parametrize("version", range(1, 10))
def test_migration_idempotent(tmp_db, version):
    db = Database(tmp_db)   # applies all migrations
    db.close()
    db2 = Database(tmp_db)  # applies again — should silently skip already-applied
    db2.close()
```

### Atomic Write Failure Test

```python
def test_save_setting_atomic(tmp_path, monkeypatch):
    """If process crashes mid-write, existing file must survive intact."""
    settings_file = tmp_path / "settings.json"
    settings_file.write_text('{"existing_key": "value"}', encoding="utf-8")

    # Simulate crash by raising during write
    import builtins
    original_open = builtins.open
    call_count = [0]
    def flaky_open(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 2:      # second open = temp file write
            raise OSError("disk full")
        return original_open(*args, **kwargs)

    monkeypatch.setattr(builtins, "open", flaky_open)
    with pytest.raises(OSError):
        save_setting("new_key", "new_value")

    # Original file must still be intact
    assert json.loads(settings_file.read_text())["existing_key"] == "value"
```

### Config Validation Tests

```python
@pytest.mark.parametrize("bad_provider", ["gpt4", "", "OLLAMA", None])
def test_config_rejects_invalid_provider(bad_provider):
    with pytest.raises(ValueError, match="active_provider"):
        Config(active_provider=bad_provider)

def test_config_rejects_temperature_out_of_range():
    with pytest.raises(ValueError, match="ai_temperature"):
        Config(ai_temperature=5.0)
```

---

## Recommended Stack for This Milestone

### Core Technologies (no installs, all already present)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| sqlite3 | stdlib | Database | Extend existing Lock to all read methods |
| threading | stdlib | Concurrency primitives | Barrier for tests, existing Lock extended |
| tempfile + os | stdlib | Atomic file writes | mkstemp + os.replace = atomic on POSIX |
| httpx | 0.27.0 | HTTP timeout configuration | Already in requirements.txt as openai dep |
| openai | 2.26.0 | LLM client with timeout | Add timeout= at OpenAI() construction |

### Import Additions (no new pip installs)

| Import | Module | Used For |
|--------|--------|---------|
| `import httpx` | providers/ollama.py, providers/zai.py, providers/openrouter.py | `httpx.Timeout(...)` passed to `OpenAI()` |
| `import os, tempfile` | config.py | Atomic settings write |
| `from openai import APITimeoutError, APIError` | providers/*.py | Specific exception handling |

---

## Installation

No changes to `requirements.txt` for this milestone.

```bash
# Verify all needed modules are available:
python -c "import httpx, openai, tempfile, threading, sqlite3; print('all ok')"
```

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Extend threading.Lock to all methods | WAL mode (PRAGMA journal_mode=WAL) | WAL creates side files on disk; adds checkpoint management; overkill for 5 threads |
| Extend threading.Lock to all methods | Per-thread connections via threading.local() | Requires refactor of all Database callers; complicates migration flow |
| stdlib tempfile + os.replace | atomicwrites library (PyPI) | Abandoned since 2020, no Python 3.10+ CI |
| httpx.Timeout at client construction | Per-request timeout override | Client-level default is cleaner; per-request override still available when needed |
| threading.Barrier inside test | pytest-run-parallel plugin | Plugin runs whole tests concurrently; Barrier gives targeted control within one test |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| SQLAlchemy | 10+ MB bundle weight, ORM overkill for 8 tables | sqlite3 with proper locking |
| atomicwrites (PyPI) | Unmaintained, abandoned 2020 | stdlib tempfile + os.replace |
| pytest-run-parallel | Runs all tests concurrently — breaks fixtures that assume sequential isolation | threading.Barrier inside targeted concurrency tests |
| aiosqlite | Async SQLite wrapper — NiceGUI already wraps blocking calls in run.io_bound() | sqlite3 with Lock |
| pydantic | ~2MB bundle weight for a single Config dataclass | dataclass __post_init__ with ValueError |
| threading.RLock | Re-entrant lock unnecessary — no recursive DB calls in the codebase | threading.Lock (already used) |

---

## Version Compatibility

| Package | Version | Notes |
|---------|---------|-------|
| openai | 2.26.0 | `httpx.Timeout` passed to `OpenAI(timeout=...)` — supported since openai 1.0+ |
| httpx | 0.27.0 | `httpx.Timeout(connect, read, write, pool)` — all fields supported since httpx 0.20+ |
| sqlite3 | stdlib | `threading.Lock` pattern is version-independent; `check_same_thread=False` requires all write ops serialized by user |

---

## Sources

- [SQLite Threading Modes — sqlite.org](https://sqlite.org/threadsafe.html) — serialized/multi-thread/single-thread modes (HIGH confidence)
- [Python sqlite3 docs](https://docs.python.org/3/library/sqlite3.html) — `check_same_thread=False` note: "write operations should be serialized by the user" (HIGH confidence)
- [cpython issue #118172](https://github.com/python/cpython/issues/118172) — sqlite3 multithreading cache inconsistency discussion (MEDIUM confidence)
- [openai-python GitHub](https://github.com/openai/openai-python) — `timeout` param accepts `float | httpx.Timeout`; default 10 minutes (HIGH confidence)
- [openai community — timeout configuration](https://community.openai.com/t/configuring-timeout-for-chatcompletion-python/107226) — httpx.Timeout usage pattern confirmed (MEDIUM confidence)
- [python-atomicwrites PyPI](https://pypi.org/project/atomicwrites/) — last release 1.4.0 (2020), no 3.10+ CI — confirmed abandoned (HIGH confidence)
- [Python atomic write discussion](https://discuss.python.org/t/adding-atomicwrite-in-stdlib/11899) — stdlib tempfile + os.replace as canonical pattern (HIGH confidence)
- [py-free-threading.github.io/testing](https://py-free-threading.github.io/testing/) — threading.Barrier for concurrent test patterns (HIGH confidence)
- Installed versions verified via `pip show openai` → 2.26.0 and `cat requirements.txt` → httpx==0.27.0

---

*Stack research for: ЮрТэг v1.0 Backend Hardening — audit fixes*
*Researched: 2026-03-28*
