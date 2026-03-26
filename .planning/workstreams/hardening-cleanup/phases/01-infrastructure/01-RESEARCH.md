# Phase 1: Инфраструктура — Research

**Researched:** 2026-03-19
**Domain:** Python/SQLite migrations, AI provider abstraction, service-layer extraction, date normalization
**Confidence:** HIGH (codebase analyzed directly; patterns from prior research docs verified against actual source files)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- До вехи 3 (локальная LLM) — автопереключение на запасной провайдер (GLM → OpenRouter) при недоступности основного
- После вехи 3 — локальная QWEN всегда доступна, проблема отпадает
- При мусорном ответе AI — повторная попытка с другим промптом, затем отметка в реестре
- Провайдеры переключаются через конфиг (одна строка), не через UI-кнопку
- Нормализация дат — только нормализация формата (ISO 8601), НЕ валидация корректности
- Валидация корректности дат уже работает на стадии L2-верификации — не дублировать
- Заменить текущий try/except на версионированные миграции
- Обновление не должно ломать существующую базу пользователя — абсолютный приоритет
- Отделить бизнес-логику от Streamlit — pipeline_service, registry_service
- Цель: логика вызывается без запуска UI (для будущих интеграций — Telegram-бот, API, тесты)

### Claude's Discretion
- Конкретная реализация системы миграций (Alembic vs ручная)
- Структура providers/ пакета (ABC vs Protocol)
- Как именно разделить main.py на сервисы
- Формат хранения промптов (YAML vs отдельные .txt файлы)
- Детали fallback-логики при переключении провайдеров

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FUND-01 | Обновление приложения не ломает существующую базу данных пользователя — версионированные миграции схемы | Versioned migration table pattern (60 lines, no deps); backup before migration; backfill safe defaults |
| FUND-02 | Бизнес-логика обработки документов отделена от интерфейса и может вызываться независимо (сервис-слой) | pipeline_service + registry_service wrapping controller; zero Streamlit imports enforced |
| FUND-03 | AI-провайдер переключается через конфигурацию (GLM / OpenRouter / будущая Ollama) без изменения кода | ABC LLMProvider + config.active_provider; openai SDK base_url pattern; all 3 targets are OpenAI-compatible |
| FUND-04 | Даты, извлечённые AI, нормализуются и проверяются на корректность перед сохранением | python-dateutil 2.9.0 already installed; parse → ISO 8601 or None; log raw original |
</phase_requirements>

---

## Summary

Phase 1 is a pure technical infrastructure phase — no new UI features, no new user-visible behavior. It resolves four pre-existing fragilities in the codebase that block all subsequent feature phases. The existing code is clean and modular; the refactors are surgical, not rewrites.

The highest-risk item is the database migration replacement. The existing silent `try/except OperationalError` pattern in `database.py` (lines 68–73) has no migration history, no rollback, and no backfill. Any user upgrading from v0.4 with an existing `yurteg.db` could silently get `NULL` in new columns. A versioned migration table (`schema_migrations`) with numbered functions and a pre-migration backup eliminates this entire class of bugs in ~60 lines of pure stdlib Python.

The AI provider abstraction is simpler than it looks. All three target providers (ZAI GLM, OpenRouter, future Ollama) speak the OpenAI wire format. The existing `ai_extractor.py` already has `_create_client(config, use_fallback=bool)` — the extraction is mechanical: lift that logic into a `providers/` package with an ABC, keep all prompts and JSON parsing in `ai_extractor.py`. The service layer is equally mechanical: wrap `controller.process_archive()` in a thin `pipeline_service.py` that has zero Streamlit imports. Date normalization leverages `python-dateutil` which is already installed (version 2.9.0.post0).

**Primary recommendation:** Complete migrations first (prerequisite — if it corrupts a user DB, everything else is moot), then provider abstraction and service layer in parallel, then date normalization (isolated to `ai_extractor.py` output path).

---

## Standard Stack

### Core (already installed — no new dependencies needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-dateutil | 2.9.0.post0 (confirmed installed) | Parse arbitrary date strings to ISO 8601 | Handles "31 декабря 2025 г.", "31.12.25", "January 1, 2025" and hundreds of formats including Russian month names. `dateutil.parser.parse(raw, dayfirst=True)` is the single call needed |
| openai SDK | 1.30.0+ (confirmed installed) | Unified client for all AI providers via `base_url` override | All three target providers (ZAI GLM, OpenRouter, Ollama) expose OpenAI-compatible `/v1/chat/completions`. No new dependency |
| sqlite3 | stdlib | Versioned migration table | No ORM needed; migration tracking requires one extra table and numbered functions |
| abc | stdlib | `LLMProvider` abstract base class | ABC enforces the `complete()` + `verify_key()` contract at class definition; fails fast if a provider omits a required method |
| pytest | 7.4.4 (confirmed installed) | Unit tests for all four FUND requirements | Already configured via `pytest.ini` at project root |

### No New Dependencies Required

This phase adds **zero new packages**. `python-dateutil` is already installed. The provider abstraction, migration system, and service layer are pure Python refactors of existing code.

**Verify:**
```bash
pip show python-dateutil openai pytest
# python-dateutil: 2.9.0.post0
# openai: 1.30.0+
# pytest: 7.4.4
```

### Alternatives Considered and Rejected

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual versioned migrations | Alembic | Alembic requires SQLAlchemy ORM setup; the project uses raw sqlite3. For 3-4 schema versions, 60 lines of plain Python is more transparent and easier to debug without a framework |
| `abc.ABC` for LLMProvider | `typing.Protocol` | Protocol is structural (duck typing); ABC fails at class definition if abstract methods are missing. For a non-developer team, ABC's explicit errors are more debuggable |
| `dateutil.parser.parse()` | Custom regex for Russian months | Custom regex always has edge cases (genitive "декабря" vs nominative "декабрь", abbreviated months, locale-specific separators). dateutil handles all of these |
| Thin service layer functions | FastAPI HTTP API | FastAPI introduces a second process, port management, and HTTP overhead with no current benefit. Service layer is callable Python in the same process. FastAPI can wrap these services later when needed |

---

## Architecture Patterns

### Recommended Project Structure (delta from current)

```
yurteg/
├── main.py                        # Streamlit UI — call services instead of controller
├── controller.py                  # Unchanged pipeline orchestrator
├── config.py                      # Add: active_provider, fallback_provider fields
├── modules/
│   ├── ai_extractor.py            # Refactor: delegate to LLMProvider; add _normalize_date()
│   ├── database.py                # Replace try/except with _run_migrations() system
│   └── ... (rest unchanged)
│
├── providers/                     # NEW package
│   ├── __init__.py                # get_provider(config) factory function
│   ├── base.py                    # Abstract LLMProvider (abc.ABC)
│   ├── zai.py                     # ZAIProvider — extracted from current _create_client()
│   ├── openrouter.py              # OpenRouterProvider — includes _merge_system_into_user
│   └── ollama.py                  # OllamaProvider — stub for Веха 3
│
└── services/                      # NEW package
    ├── __init__.py
    ├── pipeline_service.py        # process_archive() facade, zero Streamlit imports
    └── registry_service.py        # get_contracts(), generate_report() facade
```

---

### Pattern 1: Versioned Migration Table (FUND-01)

**What:** Replace `try/except OperationalError` with a `schema_migrations` table. Each migration is a numbered function that checks if already applied, runs its DDL, and records itself. A pre-migration backup protects against mid-migration failures.

**When to use:** Every schema change from this phase forward.

```python
# modules/database.py — replace existing migration pattern

import shutil, time

def _backup_database(db_path: Path) -> Path:
    """Creates timestamped backup before any migration. Returns backup path."""
    ts = int(time.time())
    backup = db_path.parent / f"{db_path.stem}_backup_{ts}.sqlite"
    shutil.copy2(db_path, backup)
    logger.info("DB backup created: %s", backup)
    return backup

def _ensure_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()

def _is_migration_applied(conn: sqlite3.Connection, version: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM schema_migrations WHERE version = ?", (version,)
    ).fetchone()
    return row is not None

def _mark_migration_applied(conn: sqlite3.Connection, version: int) -> None:
    conn.execute("INSERT OR IGNORE INTO schema_migrations (version) VALUES (?)", (version,))
    conn.commit()
    logger.info("Migration v%d applied", version)
```

**Migration 1 — carry forward existing v0.3 columns:**
```python
def _migrate_v1_review_columns(conn: sqlite3.Connection) -> None:
    """v1: Add review_status and lawyer_comment (replaces prior try/except pattern)."""
    if _is_migration_applied(conn, 1):
        return
    # ALTER TABLE does not work inside a transaction in SQLite.
    # Use individual execute() with try/except for idempotency:
    for col, default in [("review_status", "'not_reviewed'"), ("lawyer_comment", "''")]:
        try:
            conn.execute(f"ALTER TABLE contracts ADD COLUMN {col} TEXT DEFAULT {default}")
        except sqlite3.OperationalError:
            pass  # Column already exists — safe
    conn.commit()
    _mark_migration_applied(conn, 1)

def _run_migrations(db_path: Path, conn: sqlite3.Connection) -> None:
    """Run all pending migrations in order. Call from __init__ after schema creation."""
    _ensure_migrations_table(conn)
    # Only backup if DB file exists and has data (not a fresh DB)
    if db_path.exists() and db_path.stat().st_size > 0:
        _backup_database(db_path)
    _migrate_v1_review_columns(conn)
    # Future phases add _migrate_v2_*, _migrate_v3_* here
```

**Critical SQLite constraint:** `executescript()` issues an implicit COMMIT before running, which breaks transactions. For `ALTER TABLE` migrations, use individual `execute()` calls. For `INSERT/UPDATE` data migrations, `executescript()` is fine.

---

### Pattern 2: LLMProvider ABC (FUND-03)

**What:** Abstract base class with `complete()` and `verify_key()`. Concrete providers wrap `openai.OpenAI(base_url=..., api_key=...)`. ZAI-specific parameters (`extra_body thinking:disabled`) live only in `ZAIProvider.complete()`. `_merge_system_into_user()` lives only in `OpenRouterProvider.complete()`.

**Config changes required:**
```python
# config.py — add two fields to Config dataclass
active_provider: str = "zai"        # "zai" | "openrouter" | "ollama"
fallback_provider: str = "openrouter"  # used automatically if active fails
```

```python
# providers/base.py
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier for logging: 'zai', 'openrouter', 'ollama'."""
        ...

    @abstractmethod
    def complete(self, messages: list[dict], **kwargs) -> str:
        """Returns raw text response. Raises RuntimeError on unrecoverable failure."""
        ...

    @abstractmethod
    def verify_key(self) -> bool:
        """Returns True if credentials are valid. Does NOT raise."""
        ...
```

```python
# providers/zai.py
import os
from openai import OpenAI
from providers.base import LLMProvider
from config import Config

class ZAIProvider(LLMProvider):
    name = "zai"

    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = OpenAI(
            base_url=config.ai_base_url,
            api_key=os.environ.get("ZAI_API_KEY") or os.environ.get("ZHIPU_API_KEY", ""),
        )

    def complete(self, messages: list[dict], **kwargs) -> str:
        extra = {}
        if self._config.ai_disable_thinking:
            extra["extra_body"] = {"thinking": {"type": "disabled"}}
        response = self._client.chat.completions.create(
            model=self._config.active_model,
            temperature=self._config.ai_temperature,
            max_tokens=self._config.ai_max_tokens,
            messages=messages,
            **extra,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("ZAI returned empty content")
        return content

    def verify_key(self) -> bool:
        try:
            self._client.models.list()
            return True
        except Exception:
            return False
```

```python
# providers/openrouter.py — key difference: system-role merging for free models
import os
from openai import OpenAI
from providers.base import LLMProvider
from config import Config

def _merge_system_into_user(messages: list[dict]) -> list[dict]:
    """Some free OpenRouter models reject 'system' role — merge into first user message."""
    result = []
    system_content = ""
    for msg in messages:
        if msg["role"] == "system":
            system_content = msg["content"]
        else:
            if system_content and msg["role"] == "user":
                result.append({"role": "user", "content": f"{system_content}\n\n{msg['content']}"})
                system_content = ""
            else:
                result.append(msg)
    return result

class OpenRouterProvider(LLMProvider):
    name = "openrouter"

    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = OpenAI(
            base_url=config.ai_fallback_base_url,
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        )

    def complete(self, messages: list[dict], **kwargs) -> str:
        merged = _merge_system_into_user(messages)
        response = self._client.chat.completions.create(
            model=self._config.model_fallback,
            temperature=self._config.ai_temperature,
            max_tokens=self._config.ai_max_tokens,
            messages=merged,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("OpenRouter returned empty content")
        return content

    def verify_key(self) -> bool:
        try:
            self._client.models.list()
            return True
        except Exception:
            return False
```

```python
# providers/ollama.py — stub for Веха 3; OpenAI-compatible endpoint
import os
from openai import OpenAI
from providers.base import LLMProvider
from config import Config

class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, config: Config) -> None:
        self._config = config
        # Ollama local endpoint; api_key required by SDK but ignored by Ollama
        self._client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        )

    def complete(self, messages: list[dict], **kwargs) -> str:
        response = self._client.chat.completions.create(
            model=getattr(self._config, "ollama_model", "qwen2.5:1.5b"),
            temperature=self._config.ai_temperature,
            max_tokens=self._config.ai_max_tokens,
            messages=messages,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Ollama returned empty content")
        return content

    def verify_key(self) -> bool:
        try:
            self._client.models.list()
            return True
        except Exception:
            return False
```

```python
# providers/__init__.py
from config import Config
from providers.base import LLMProvider
from providers.zai import ZAIProvider
from providers.openrouter import OpenRouterProvider
from providers.ollama import OllamaProvider

def get_provider(config: Config) -> LLMProvider:
    match config.active_provider:
        case "zai":        return ZAIProvider(config)
        case "openrouter": return OpenRouterProvider(config)
        case "ollama":     return OllamaProvider(config)
        case _:
            raise ValueError(f"Unknown active_provider: {config.active_provider!r}")

def get_fallback_provider(config: Config) -> LLMProvider | None:
    if not config.fallback_provider:
        return None
    match config.fallback_provider:
        case "openrouter": return OpenRouterProvider(config)
        case "ollama":     return OllamaProvider(config)
        case _:            return None
```

---

### Pattern 3: Fallback Orchestration Stays in ai_extractor.py (not in providers/)

**What:** Provider ABC handles single-provider API mechanics. Multi-provider fallback (try primary → retry with simpler prompt → try fallback provider → mark as failed) stays in `ai_extractor.py`. This is domain logic, not provider infrastructure.

```python
# modules/ai_extractor.py — refactored extract_metadata()
def extract_metadata(
    anonymized_text: str,
    config: Config,
    provider: LLMProvider,
    fallback_provider: LLMProvider | None = None,
) -> ContractMetadata:
    messages = _build_messages(anonymized_text, config)

    # Stage 1: primary provider, full prompt
    result = _try_provider(provider, messages, config)
    if isinstance(result, ContractMetadata):
        if _is_empty_result(result):
            # Retry with simplified prompt before declaring failure
            simple_msgs = _build_fallback_messages(anonymized_text)
            retry = _try_provider(provider, simple_msgs, config)
            if isinstance(retry, ContractMetadata) and not _is_empty_result(retry):
                return retry
        return result

    # Stage 2: fallback provider
    if fallback_provider:
        logger.info("Primary provider '%s' failed, trying fallback '%s'",
                    provider.name, fallback_provider.name)
        fb = _try_provider(fallback_provider, messages, config)
        if isinstance(fb, ContractMetadata):
            return fb

    raise RuntimeError(f"All providers failed. Last error: {result}")
```

---

### Pattern 4: Service Layer (FUND-02)

**What:** Module-level functions (not classes) in `services/`. Zero Streamlit imports. Pure facade over existing `controller.py` and `database.py`.

```python
# services/pipeline_service.py
# IMPORTANT: No `import streamlit` allowed in this file.
# This is intentional — service must be callable without UI.
from pathlib import Path
from typing import Callable
from config import Config
from controller import Controller

def process_archive(
    source_dir: Path,
    config: Config,
    grouping: str = "both",
    force_reprocess: bool = False,
    on_progress: Callable | None = None,
    on_file_done: Callable | None = None,
) -> dict:
    """Single entry point for archive processing.
    Called by Streamlit today. Called by CLI / API / tests without Streamlit.
    Returns: dict(total, done, errors, skipped, output_dir, report_path)
    """
    ctrl = Controller(config)
    return ctrl.process_archive(
        source_dir=source_dir,
        grouping=grouping,
        force_reprocess=force_reprocess,
        on_progress=on_progress,
        on_file_done=on_file_done,
    )
```

```python
# services/registry_service.py
from pathlib import Path
from modules.database import Database
from modules.reporter import Reporter
from config import Config

def get_all_contracts(db: Database) -> list[dict]:
    """All processed contracts from the database."""
    return db.get_all_results()

def generate_report(db: Database, output_dir: Path, config: Config) -> Path:
    """Generate Excel registry. Returns path to generated file."""
    reporter = Reporter(config)
    return reporter.generate(db, output_dir)
```

**main.py change:** Replace `ctrl = Controller(config); ctrl.process_archive(...)` with `pipeline_service.process_archive(source_dir, config, ...)`. All database queries similarly rerouted through `registry_service`.

---

### Pattern 5: Date Normalization in _json_to_metadata() (FUND-04)

**What:** After `_json_to_metadata()` builds `ContractMetadata` from the AI JSON response, all date fields pass through `_normalize_date()`. Returns ISO 8601 string or `None`. Logs the original raw value on normalization failure for debugging.

**Scope:** Normalization only (format unification). No logical validation — date sanity checks stay in `validator.py` L2.

```python
# modules/ai_extractor.py — add this function

from dateutil import parser as dateutil_parser
from dateutil.parser import ParserError

def _normalize_date(raw: str | None) -> str | None:
    """Normalize any date string to YYYY-MM-DD.
    Returns None if unparseable, if raw is ambiguous (year-only), or if raw is null.

    Handles:
    - "31 декабря 2025 г." -> "2025-12-31"
    - "31.12.2025" -> "2025-12-31"
    - "31.12.25" -> "2025-12-31"
    - "January 1, 2025" -> "2025-01-01"
    - "2025-12-31" -> "2025-12-31" (fast path)
    - "бессрочный" -> None
    - "2025" -> None (ambiguous year-only string)
    """
    if not raw:
        return None
    raw = raw.strip()
    if not raw or raw.lower() in ("null", "none", ""):
        return None

    # Fast path: already ISO 8601
    if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        return raw

    # Guard: year-only strings produce misleading dates (Jan 1 of that year)
    # A valid date string must contain at least a day and month indicator
    if len(raw) <= 4 and raw.isdigit():
        logger.warning("Ambiguous year-only date string rejected: %r", raw)
        return None

    try:
        dt = dateutil_parser.parse(raw, dayfirst=True)
        normalized = dt.strftime("%Y-%m-%d")
        # Sanity bounds: contracts from 1990 to 2099 only
        if not (1990 <= dt.year <= 2099):
            logger.warning("Date out of reasonable range: %r -> %s", raw, normalized)
            return None
        return normalized
    except (ParserError, ValueError, OverflowError):
        logger.warning("Could not normalize date: %r", raw)
        return None
```

**Applied in `_json_to_metadata()`:**
```python
def _json_to_metadata(data: dict) -> ContractMetadata:
    return ContractMetadata(
        ...
        date_signed=_normalize_date(data.get("date_signed")),
        date_start=_normalize_date(data.get("date_start")),
        date_end=_normalize_date(data.get("date_end")),
        ...
    )
```

---

### Anti-Patterns to Avoid

- **`ALTER TABLE` inside `executescript()` in a transaction:** SQLite issues an implicit COMMIT before `executescript()` runs. For DDL migrations, use individual `execute()` calls.
- **`extra_body` (ZAI thinking mode) in base class or in `ai_extractor.py`:** This is ZAI-specific and will break OpenRouter/Ollama calls. It belongs only in `ZAIProvider.complete()`.
- **`import streamlit` in `services/`:** Defeats FUND-02. Add a comment at the top of each service file as a guard; include a test that verifies the import is absent.
- **Storing computed document status in DB:** `status` (active/expiring/expired) is a function of `date_end` and `today()`. Storing it creates staleness. Compute with a SQL `CASE` expression at query time.
- **Running migrations without backup:** Any `ALTER TABLE` that fails mid-run can leave the DB inconsistent. Backup first, always.
- **Building new retry/routing infrastructure in `providers/`:** Retry logic (backoff, max attempts) is shared across providers and belongs as a single `_try_provider()` utility in `ai_extractor.py`. Providers are dumb HTTP wrappers.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parse "31 декабря 2025 г." to "2025-12-31" | Regex map of Russian month names | `dateutil.parser.parse(raw, dayfirst=True)` | dateutil handles genitive Russian month names ("декабря", "января"), abbreviated forms, mixed separators, two-digit years. Already installed. Custom regex always has untested edge cases |
| Multi-format date parsing | `strptime` with multiple format strings in a try-loop | Same `dateutil.parser.parse()` | A list of strptime formats misses combinations; dateutil handles >400 formats |
| Migration version tracking | Timestamps, filename-based versions, or md5 hashes | Integer version column in `schema_migrations` table | Integer versions are monotonic, ordered, human-readable, and trivially comparable in SQL |
| Provider-specific retry with backoff | Separate retry loop per provider class | Single `_try_provider(provider, messages, config)` in `ai_extractor.py` | Retry logic is identical for all providers; one function eliminates duplication and the current "three-tiered fallback hard to reason about" complaint from CONCERNS.md |
| Multi-provider routing | LiteLLM, LangChain | Thin ABC + openai SDK `base_url` | All three target providers speak OpenAI wire format. LiteLLM adds 50+ transitive deps and 200MB+ install size with no benefit for this use case |

**Key insight:** The entire "multi-provider AI" requirement is solved by ~30 lines of ABC + factory, using a library already installed. The date normalization requirement is solved by one function call on a library already installed. This phase is about removing complexity, not adding it.

---

## Common Pitfalls

### Pitfall 1: Migration Corrupts Existing v0.4 Databases
**What goes wrong:** Without `schema_migrations`, adding columns via `ALTER TABLE` provides no guarantee that migrations ran exactly once on upgrade. If a column was added by the old `try/except` code and then the new migration code also tries to add it, the silent suppression of `OperationalError` masks the inconsistency. Data backfill (e.g., setting `review_status='not_reviewed'` for existing rows) never runs.
**Why it happens:** The current pattern was designed for single-column additions, not upgrade paths.
**How to avoid:** Migration v1 covers the existing `review_status`/`lawyer_comment` columns. The `_is_migration_applied()` check prevents double-execution. Backup runs before any migration on a non-empty database.
**Warning signs:** Any `ALTER TABLE` in a `try/except` block after this phase is complete.

### Pitfall 2: ZAI `extra_body` Leaks to OpenRouter/Ollama
**What goes wrong:** `extra_body: {"thinking": {"type": "disabled"}}` is ZAI-specific. If it's passed to OpenRouter or Ollama's OpenAI-compatible endpoint, the call may fail with an "unexpected field" error.
**Why it happens:** In the current code, `extra_body` is conditional on `not use_fallback` inside `_try_model()`. When refactoring to providers, it's tempting to put all API kwargs in one place.
**How to avoid:** `extra_body` lives only in `ZAIProvider.complete()`. The `LLMProvider.complete()` base method takes only `messages: list[dict]`.
**Warning signs:** `extra_body` or `thinking` appear in `providers/base.py` or `ai_extractor.py`.

### Pitfall 3: Services Accidentally Import Streamlit
**What goes wrong:** A `st.session_state` read or `st.toast()` call is added to `pipeline_service.py` "just for this one thing." The service now cannot be called from tests or CLI without a running Streamlit server.
**Why it happens:** main.py is currently 1,400 lines with business logic mixed into UI handlers. The habit of reaching for `st.*` is deeply embedded.
**How to avoid:** Add `# NO import streamlit — this file must be UI-independent` as a comment at the top of each service file. Include a test: `assert "streamlit" not in importlib.import_module("services.pipeline_service").__dict__`.
**Warning signs:** `import streamlit` anywhere in `services/`.

### Pitfall 4: dateutil Parses Year-Only Strings
**What goes wrong:** `dateutil.parser.parse("2025")` returns `datetime(2025, current_month, current_day)` — today's date in 2025. This looks valid but is wrong for a contract's `date_end`.
**Why it happens:** dateutil is deliberately liberal. AI sometimes returns just a year when the exact date is unknown.
**How to avoid:** Guard: if `raw.isdigit()` and `len(raw) <= 4`, return `None` with a warning. The year-bounds check (1990–2099) also catches implausible dates from hallucination (year 1, year 9999).
**Warning signs:** Tests don't include a `"2025"` input case for `_normalize_date()`.

### Pitfall 5: Prompt Storage Deferred Becomes Blocker
**What goes wrong:** CONTEXT.md marks prompt format as Claude's Discretion for this phase. If prompts are moved to YAML as part of provider abstraction, and the YAML loading breaks, it blocks the entire phase.
**How to avoid:** Leave prompts as module-level constants in `ai_extractor.py` for Phase 1. Prompt externalization is explicitly deferred. The provider abstraction does not require moving prompts.

---

## Code Examples

### Current Pattern to Replace: Database Migration

```python
# CURRENT — database.py lines 67-73 (fragile, no history)
for col, default in (("review_status", "'not_reviewed'"), ("lawyer_comment", "''")):
    try:
        self.conn.execute(f"ALTER TABLE contracts ADD COLUMN {col} TEXT DEFAULT {default}")
        self.conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists — silent, no history, no backfill
```

### Current Pattern to Replace: Provider Creation

```python
# CURRENT — ai_extractor.py _create_client() (ZAI-specific params mixed with routing)
def _create_client(config: Config, use_fallback: bool = False) -> OpenAI:
    if use_fallback:
        key = os.environ.get("OPENROUTER_API_KEY", "")
        return OpenAI(base_url=config.ai_fallback_base_url, api_key=key)
    key = os.environ.get("ZAI_API_KEY") or os.environ.get("ZHIPU_API_KEY", "")
    return OpenAI(base_url=config.ai_base_url, api_key=key)
# Then in _try_model(): ZAI extra_body lives next to this routing logic
```

### Current Pattern to Replace: main.py → Controller Call

```python
# CURRENT — main.py calls Controller directly
ctrl = Controller(config)
results = ctrl.process_archive(source_dir=source_dir, grouping=grouping, ...)

# TARGET — main.py calls service
from services import pipeline_service
results = pipeline_service.process_archive(source_dir, config, grouping=grouping, ...)
```

---

## State of the Art

| Old Approach | Current Approach | Phase |
|--------------|------------------|-------|
| `try/except OperationalError` per column | `schema_migrations` table + numbered migration functions | FUND-01 |
| `use_fallback: bool` flag in a single `_create_client()` | `LLMProvider` ABC + `get_provider(config)` factory | FUND-03 |
| `strptime` / raw AI string stored directly | `dateutil.parser.parse(raw, dayfirst=True)` with bounds check | FUND-04 |
| Business logic in `main.py` event handlers | Service layer: `pipeline_service`, `registry_service` | FUND-02 |

**Not used in this phase:**
- Alembic — requires SQLAlchemy; plain sqlite3 + 60-line migration system is sufficient and more transparent
- LiteLLM — all target providers are OpenAI-compatible; adds 50+ transitive deps for no benefit
- FastAPI — service layer is called directly in-process; HTTP layer added only when external integrations require it (Phase 3+)

---

## Open Questions

1. **Prompt storage format (Claude's Discretion — deferred)**
   - What we know: `SYSTEM_PROMPT` and `USER_PROMPT_TEMPLATE` are module-level constants in `ai_extractor.py`
   - Recommendation: Keep as-is for Phase 1. Moving prompts to YAML is a Phase 2+ concern and is listed as Claude's Discretion. Phase 1 only extracts the client construction logic into providers/.

2. **ABC vs Protocol (Claude's Discretion)**
   - Recommendation: Use `abc.ABC`. For a non-developer team, `NotImplementedError` at class definition is more debuggable than structural subtyping failures at call time.

3. **Ollama stub completeness**
   - What we know: Ollama is Веха 3 (out of scope for Phase 1). But `providers/ollama.py` needs to exist as a stub so `get_provider("ollama")` does not raise `ImportError`.
   - Recommendation: Create stub with `raise NotImplementedError("Ollama support is scheduled for Веха 3")` in `complete()` and `verify_key()`.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.4.4 |
| Config file | `pytest.ini` (exists at project root, configured with `markers`) |
| Quick run command | `pytest tests/ -x -m "not slow"` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FUND-01 | Migration v1 runs on fresh DB without error | unit | `pytest tests/test_migrations.py::test_fresh_db -x` | Wave 0 |
| FUND-01 | Migration on v0.4 DB preserves existing rows | unit | `pytest tests/test_migrations.py::test_v04_upgrade_preserves_rows -x` | Wave 0 |
| FUND-01 | Backup file created before migration on non-empty DB | unit | `pytest tests/test_migrations.py::test_backup_created -x` | Wave 0 |
| FUND-01 | Running migrations twice is idempotent (no duplicate version rows) | unit | `pytest tests/test_migrations.py::test_idempotent -x` | Wave 0 |
| FUND-02 | `pipeline_service` module has no `streamlit` in its imports | unit | `pytest tests/test_service_layer.py::test_no_streamlit_import -x` | Wave 0 |
| FUND-02 | `process_archive()` is callable with mocked controller (no UI needed) | unit | `pytest tests/test_service_layer.py::test_process_archive_signature -x` | Wave 0 |
| FUND-02 | `registry_service.get_all_contracts()` returns list (mocked DB) | unit | `pytest tests/test_service_layer.py::test_registry_get_contracts -x` | Wave 0 |
| FUND-03 | `get_provider("zai")` returns `ZAIProvider` instance | unit | `pytest tests/test_providers.py::test_factory_zai -x` | Wave 0 |
| FUND-03 | `get_provider("openrouter")` returns `OpenRouterProvider` instance | unit | `pytest tests/test_providers.py::test_factory_openrouter -x` | Wave 0 |
| FUND-03 | `get_provider("unknown")` raises `ValueError` | unit | `pytest tests/test_providers.py::test_factory_unknown_raises -x` | Wave 0 |
| FUND-03 | `ZAIProvider.complete()` call includes `extra_body thinking disabled` | unit | `pytest tests/test_providers.py::test_zai_thinking_disabled -x` | Wave 0 |
| FUND-03 | `OpenRouterProvider.complete()` merges system message into user | unit | `pytest tests/test_providers.py::test_openrouter_system_merge -x` | Wave 0 |
| FUND-04 | `_normalize_date("31 декабря 2025 г.")` → `"2025-12-31"` | unit | `pytest tests/test_date_normalization.py::test_russian_full -x` | Wave 0 |
| FUND-04 | `_normalize_date("31.12.25")` → `"2025-12-31"` | unit | `pytest tests/test_date_normalization.py::test_short_year -x` | Wave 0 |
| FUND-04 | `_normalize_date("2025-12-31")` → `"2025-12-31"` (fast path) | unit | `pytest tests/test_date_normalization.py::test_iso_passthrough -x` | Wave 0 |
| FUND-04 | `_normalize_date("бессрочный")` → `None` | unit | `pytest tests/test_date_normalization.py::test_unparseable -x` | Wave 0 |
| FUND-04 | `_normalize_date("2025")` → `None` (year-only rejected) | unit | `pytest tests/test_date_normalization.py::test_year_only_returns_none -x` | Wave 0 |
| FUND-04 | `_normalize_date(None)` → `None` | unit | `pytest tests/test_date_normalization.py::test_none_input -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -m "not slow"` (all infrastructure tests are pure unit, run in < 5 seconds)
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
All four test files are new — none exist yet in `tests/`:
- [ ] `tests/test_migrations.py` — covers FUND-01 (fresh DB, v0.4 upgrade, backup, idempotency)
- [ ] `tests/test_service_layer.py` — covers FUND-02 (no-streamlit import, callable signatures)
- [ ] `tests/test_providers.py` — covers FUND-03 (factory, ZAI extra_body, OpenRouter merge, unknown provider)
- [ ] `tests/test_date_normalization.py` — covers FUND-04 (Russian dates, short year, ISO passthrough, unparseable, year-only, None)
- [ ] `tests/fixtures/v04_sample.sqlite` — v0.4 format database for migration upgrade test (created by fixture setup, not committed)

*(Existing `conftest.py` at `tests/conftest.py` correctly adds project root to sys.path — no changes needed)*

---

## Sources

### Primary (HIGH confidence)
- Direct codebase: `/yurteg/modules/database.py` lines 1–75 — migration pattern directly observed
- Direct codebase: `/yurteg/modules/ai_extractor.py` lines 1–320 — `_create_client()`, `_try_model()`, `_merge_system_into_user()`, prompts directly observed
- Direct codebase: `/yurteg/config.py` — full `Config` dataclass directly observed
- Direct codebase: `/yurteg/requirements.txt` — confirmed no new deps needed
- `.planning/codebase/CONCERNS.md` — tech debt catalogued 2026-03-19
- `.planning/codebase/ARCHITECTURE.md` — current layers documented 2026-03-19
- `.planning/research/ARCHITECTURE.md` — target architecture patterns (providers/, services/) verified against codebase
- `.planning/research/STACK.md` — stack recommendations verified (no new deps for Phase 1)
- `.planning/research/PITFALLS.md` — migration and provider pitfalls verified against codebase

### Secondary (MEDIUM confidence)
- `pip show python-dateutil` — confirmed version 2.9.0.post0 installed
- `pip show pytest` — confirmed version 7.4.4 installed

### Tertiary (LOW confidence — not needed; all required tools already in project)
- python-dateutil docs: https://dateutil.readthedocs.io/ — API cross-referenced with installed package

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified installed via `pip show`; zero new dependencies required
- Architecture patterns: HIGH — directly derived from existing source code; refactors are mechanical extractions
- Migration pattern: HIGH — derived from SQLite docs + direct code analysis of existing migration failure modes
- Date normalization: HIGH — dateutil installed and version confirmed; `dayfirst=True` parameter verified for Russian locale
- Pitfalls: HIGH — all derived from direct code analysis (CONCERNS.md + source files), not speculation

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stdlib + dateutil + pytest — stable, no rapid release cycle)
