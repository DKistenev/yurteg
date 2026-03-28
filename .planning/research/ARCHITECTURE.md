# Architecture Research

**Domain:** Backend bug-fixing in Python document processing app (NiceGUI + SQLite + LLM pipeline)
**Researched:** 2026-03-28
**Confidence:** HIGH — all findings from direct code inspection, no external sources needed

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        UI Layer (app/)                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ registry │  │ document │  │ settings │  │    templates     │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘ │
└───────┼─────────────┼─────────────┼───────────────────┼──────────┘
        │             │             │                   │
┌───────▼─────────────▼─────────────▼───────────────────▼──────────┐
│                    Service Layer (services/)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────┐  │
│  │   lifecycle  │  │   version    │  │ payment  │  │  review  │  │
│  │   _service   │  │   _service   │  │ _service │  │ _service │  │
│  └──────┬───────┘  └──────┬───────┘  └────┬─────┘  └────┬─────┘  │
└─────────┼─────────────────┼───────────────┼──────────────┼────────┘
          │                 │               │              │
┌─────────▼─────────────────▼───────────────▼──────────────▼────────┐
│                 Orchestration (controller.py)                       │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  Pipeline: scan → extract → anonymize → AI → org → save   │    │
│  │  ThreadPoolExecutor (max_workers=5) for AI stage only      │    │
│  └────────────────────────────────────────────────────────────┘    │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────────────┐
│                   Module Layer (modules/)                            │
│  scanner → extractor → anonymizer → ai_extractor → postprocessor   │
│                           ↓                                          │
│                     database.py   ←→   organizer.py                 │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────────────┐
│               Provider Layer (providers/)                            │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐                  │
│  │  ollama  │    │   zai    │    │  openrouter  │                  │
│  │(primary) │    │(fallback)│    │  (fallback2) │                  │
│  └──────────┘    └──────────┘    └──────────────┘                  │
└────────────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────────────┐
│              Data Layer (SQLite, ~/.yurteg/)                         │
│  ┌──────────────────────┐   ┌─────────────────────────────────┐    │
│  │ yurteg.db (per-run)  │   │ settings.json (~/.yurteg/)      │    │
│  │ contracts            │   │ persistent user prefs           │    │
│  │ document_versions    │   └─────────────────────────────────┘    │
│  │ payments             │                                           │
│  │ templates            │                                           │
│  │ embeddings           │                                           │
│  │ template_embeddings  │                                           │
│  │ schema_migrations    │                                           │
│  └──────────────────────┘                                           │
└────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Current Bug State |
|-----------|----------------|-------------------|
| `config.py` | Config dataclass + settings.json persistence | Missing `__post_init__` validation; `active_model` property always returns "glm-4.7" regardless of `active_provider`; no `APP_VERSION`; `save_setting` has read-modify-write race |
| `modules/database.py` | SQLite CRUD, migrations, thread safety | `_lock` used on writes and some reads, but `get_all_results()`, `get_stats()`, `is_processed()` skip the lock; no `contract_number` column (needed by version_service) |
| `modules/models.py` | Shared dataclasses for all pipeline stages | `ContractMetadata` has no `contract_number` field — version_service queries it, controller passes it, but the field doesn't exist in the model |
| `controller.py` | Pipeline orchestration, ThreadPoolExecutor | Deanonymizes only 4 fields (counterparty, parties, subject, special_conditions); contract_type, amount, contract_number, payment_terms are skipped |
| `services/lifecycle_service.py` | Status computation, deadline alerts | `get_attention_required()` calls `db.conn.execute()` directly without acquiring `db._lock`; `STATUS_LABELS` lacks `css_class` key needed by UI |
| `services/version_service.py` | Embedding-based version matching | Queries `c.contract_number` column that doesn't exist yet (needs migration v10); this is the primary cause of version-linking failures |
| `providers/base.py` | LLMProvider ABC | No `get_logprobs()` in the abstract interface — only `OllamaProvider` has it; zai and openrouter silently lack the method |
| `providers/ollama.py` | llama-server via OpenAI SDK | No timeout on HTTP requests — a hung llama-server blocks the thread indefinitely in ThreadPoolExecutor |
| `providers/zai.py`, `providers/openrouter.py` | Cloud LLM providers | Same timeout issue; no `get_logprobs()` implementation |
| `services/payment_service.py` | Payment record saving | Unhandled edge cases: zero amount, invalid frequency values |

## Recommended Project Structure

Existing structure is correct and must not change. All fixes are in-place modifications within existing files. The only additive change is migration v10 in `database.py`.

```
yurteg/
├── config.py                    # ADD __post_init__ validation; FIX active_model; ADD APP_VERSION; FIX save_setting atomicity
├── modules/
│   ├── models.py                # ADD contract_number field to ContractMetadata
│   └── database.py              # ADD migration v10; ADD contract_number to save_result SQL; ADD _lock to 3 read methods
├── services/
│   ├── lifecycle_service.py     # ADD css_class to STATUS_LABELS; ADD db._lock in get_attention_required
│   ├── version_service.py       # No code change needed after migration v10 lands
│   └── payment_service.py       # FIX zero-amount and invalid-frequency edge cases
├── providers/
│   ├── base.py                  # ADD get_logprobs() abstract method (with default empty-dict impl)
│   ├── ollama.py                # ADD timeout= to OpenAI client constructor
│   ├── zai.py                   # ADD timeout= to OpenAI client constructor
│   └── openrouter.py            # ADD timeout= to OpenAI client constructor
└── controller.py                # FIX deanonymize: add contract_type, amount, contract_number, payment_terms
```

### Structure Rationale

No new files. No new directories. All changes are targeted edits inside existing functions. The migration v10 follows the existing numbered-migration pattern exactly — add a new `_migrate_v10_contract_number` function and register it at the bottom of `_run_migrations()`.

## Architectural Patterns

### Pattern 1: Numbered Migration Chain

**What:** Each migration is a standalone `_migrate_vN_*` function. `_run_migrations()` calls all of them in order. Each migration checks `_is_migration_applied()` first — making it idempotent.

**When to use:** Any schema change. This pattern is already established through v1–v9 and must be followed for v10.

**Trade-offs:** Simple and correct for SQLite. Linear scan at startup is negligible with fewer than 20 migrations.

**Example for v10:**
```python
def _migrate_v10_contract_number(conn: sqlite3.Connection) -> None:
    """v10: Добавить contract_number в contracts."""
    if _is_migration_applied(conn, 10):
        return
    try:
        conn.execute("ALTER TABLE contracts ADD COLUMN contract_number TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    _mark_migration_applied(conn, 10)
```

Then register: `_migrate_v10_contract_number(conn)` in `_run_migrations()`.

### Pattern 2: Explicit Lock Acquisition via `with db._lock`

**What:** All `db.conn.execute()` calls that read or write shared state must be wrapped with `with db._lock:`. This is already done correctly for all write paths and `get_contract_by_id`, `get_contract_id_by_hash`. Three read methods currently skip it.

**When to use:** Every database access path that could be called from multiple threads. The pipeline uses `ThreadPoolExecutor`, and the UI runs async callbacks that also call database methods.

**Trade-offs:** `_lock` is a `threading.Lock()` which is appropriate. It does not need upgrading to `RLock` unless a single thread re-enters the same lock — which does not happen in this codebase.

**Missing applications (three methods in database.py):**
```python
def is_processed(self, file_hash: str) -> bool:
    with self._lock:                                    # ADD THIS
        cursor = self.conn.execute(...)
        return cursor.fetchone() is not None

def get_all_results(self) -> list[dict]:
    with self._lock:                                    # ADD THIS
        cursor = self.conn.execute(...)
        rows = cursor.fetchall()
    results = []
    ...

def get_stats(self) -> dict:
    with self._lock:                                    # ADD THIS
        cursor = self.conn.execute(...)
        row = cursor.fetchone()
    ...
```

### Pattern 3: Stateless Services with `db` Injection

**What:** All service functions receive `db: Database` as a parameter. Services hold no state — they are pure functions over the database object.

**Implication for fixes:** `get_attention_required` in `lifecycle_service.py` calls `db.conn.execute()` directly. It must acquire `db._lock` explicitly, since it bypasses the `Database` method layer:

```python
def get_attention_required(db: Database, warning_days: int) -> list[DeadlineAlert]:
    sql = f"SELECT ... WHERE ..."
    with db._lock:                                      # ADD THIS
        rows = db.conn.execute(sql, {"warning_days": warning_days}).fetchall()
    ...
```

### Pattern 4: `__post_init__` for Config Validation

**What:** Python dataclasses support `__post_init__` which runs after `__init__`. This is the correct hook for field validation and derived-value fixups.

**When to use:** Any constraint on Config fields — valid providers, port range, and the `active_model` property fixup.

**Example:**
```python
def __post_init__(self) -> None:
    valid_providers = {"ollama", "zai", "openrouter"}
    if self.active_provider not in valid_providers:
        raise ValueError(
            f"active_provider must be one of {valid_providers}, got {self.active_provider!r}"
        )
    if not (1024 <= self.llama_server_port <= 65535):
        raise ValueError(f"llama_server_port out of range: {self.llama_server_port}")
```

And the `active_model` property fix:
```python
@property
def active_model(self) -> str:
    if self.active_provider == "ollama":
        return "qwen-1.5b"          # or self.llama_model_filename
    if self.active_provider == "zai":
        return "glm-4.7"
    return self.model_fallback
```

### Pattern 5: Provider Timeout via `OpenAI(timeout=...)`

**What:** The `openai.OpenAI` client accepts a `timeout` parameter at construction. Without it, HTTP requests have no deadline — a hung llama-server or slow cloud provider blocks the worker thread in `ThreadPoolExecutor` indefinitely.

**When to use:** All three providers.

**Example:**
```python
self._client = OpenAI(
    base_url=base_url,
    api_key="not-needed",
    timeout=30.0,   # seconds — prevents hung threads in ThreadPoolExecutor
)
```

## Data Flow

### Pipeline Processing Flow

```
Source directory
    ↓
scanner.scan_directory() → list[FileInfo]
    ↓
[Sequential, per-file]
extractor.extract_text(file_info) → ExtractedText
    ↓
anonymizer.anonymize(text) → AnonymizedText   [skipped for ollama provider]
    ↓
[Parallel: ThreadPoolExecutor(max_workers=5)]
ai_extractor.extract_metadata(anon_text, config, provider) → ContractMetadata
    ↓
[Back to sequential, per-result]
controller._deanonymize(metadata fields, replacements)
    ← BUG TODAY: only 4 fields (counterparty, parties, subject, special_conditions)
    ← FIX: add contract_type, amount, contract_number, payment_terms
    ↓
organizer.organize_file(result, output_dir) → organized_path
    ↓
database.save_result(result)   ← thread-safe (has _lock)
    ↓ (non-blocking, exception-swallowed)
version_service.find_version_match()  ← BUG TODAY: c.contract_number col missing
    → fixed by migration v10 + ContractMetadata.contract_number field
version_service.link_versions()
payment_service.save_payments()
```

### Settings Persistence Flow

```
UI settings change (e.g., toggle provider)
    ↓
config.save_setting(key, value)
    ↓ BUG: unsynchronized read-modify-write
load_settings() → mutate dict → write_text()
    ↓ FIX: wrap in threading.Lock() or use atomic Path.replace()
~/.yurteg/settings.json
```

### `active_model` Bug Flow

```
config.active_provider = "ollama"
config.active_model → returns "glm-4.7"    ← hardcoded, ignores active_provider
result.model_used = config.active_model    → stored as "glm-4.7" in DB for all ollama runs
```

## Integration Points

### Cross-Cutting Concerns (affects multiple files)

| Concern | Files Affected | Fix Approach |
|---------|----------------|--------------|
| `contract_number` column | `database.py` (migration + save_result SQL) + `models.py` (ContractMetadata field) + `controller.py` (pass to save) | Strictly sequential: models → migration → save_result SQL. version_service query fixes itself automatically after migration lands |
| `STATUS_LABELS` with `css_class` | `lifecycle_service.py` + all UI pages reading status badges | Add `css_class` key to STATUS_LABELS dict; UI reads it. No other files change |
| `APP_VERSION` constant | `config.py` + footer in UI | Add to config.py; UI imports it |
| `get_logprobs()` in provider ABC | `providers/base.py` + `providers/zai.py` + `providers/openrouter.py` | Add default `return {}` impl to base.py; zai/openrouter inherit the default; ollama keeps its full implementation |

### Fix Dependency Graph

```
Wave 1 — independent, no deps, safe to do in any order:
  config.py: __post_init__ + active_model fix + APP_VERSION + save_setting atomicity
  providers/base.py: get_logprobs() default impl
  providers/ollama.py + zai.py + openrouter.py: timeout parameter

Wave 2 — strictly sequential within this wave:
  models.py: add contract_number to ContractMetadata   ← must be first
      ↓
  database.py: migration v10 _migrate_v10_contract_number   ← must be second
      ↓
  database.py: save_result SQL includes contract_number   ← must be third
  database.py: _lock on 3 read methods   ← independent, batch here for locality

Wave 3 — depends on Wave 2:
  lifecycle_service.py: STATUS_LABELS css_class + get_attention_required lock
  payment_service.py: edge case fixes
  (version_service.py: no code change needed after migration v10)

Wave 4 — depends on Wave 2 + Wave 3:
  controller.py: deanonymize all string metadata fields

Wave 5 — test coverage:
  Tests for thread safety (concurrent save + read)
  Tests for migrations v2-v9 idempotency
  Tests for payment edges
  Tests for ai_extractor helpers
```

### New vs Modified Summary

| Change Type | Count | Files |
|-------------|-------|-------|
| New functions | 1 | `database.py` — `_migrate_v10_contract_number` |
| New fields on dataclass | 1 | `models.py` — `ContractMetadata.contract_number` |
| New constant | 1 | `config.py` — `APP_VERSION` |
| New method on ABC | 1 | `providers/base.py` — `get_logprobs()` with default impl |
| Modified methods | 12 | Various (see structure section above) |
| No change (auto-fixed by dependency) | 1 | `version_service.py` — works after migration v10 |

## Recommended Build Order

### Wave 1 — Foundation (zero dependencies, unblocks everything)

1. `config.py` — `__post_init__`, `active_model` fix, `APP_VERSION`, atomic `save_setting`
2. `providers/base.py` — `get_logprobs()` default impl
3. `providers/ollama.py`, `providers/zai.py`, `providers/openrouter.py` — add `timeout=30.0`

Write tests for config validation and provider construction immediately. These are fully independent.

### Wave 2 — Data layer (sequential)

4. `modules/models.py` — add `contract_number: Optional[str] = None` to `ContractMetadata`
5. `modules/database.py` (migration) — `_migrate_v10_contract_number` + register in `_run_migrations`
6. `modules/database.py` (save_result) — include `contract_number` in INSERT/UPDATE SQL
7. `modules/database.py` (thread safety) — `with self._lock:` in `get_all_results`, `get_stats`, `is_processed`

Step 4 before step 5 before step 6 is a hard ordering requirement. Step 7 is independent but batched here for locality.

### Wave 3 — Services (after Wave 2)

8. `services/lifecycle_service.py` — `STATUS_LABELS` `css_class` key + `get_attention_required` lock
9. `services/payment_service.py` — edge case fixes
10. `services/version_service.py` — verify query works (no code change expected)

### Wave 4 — Controller (after Wave 2 + Wave 3)

11. `controller.py` — add `contract_type`, `amount`, `contract_number`, `payment_terms` to deanonymize block

### Wave 5 — Test coverage

12. Thread safety: concurrent `save_result` + `get_all_results` test
13. Migration idempotency: v2-v9 re-run test
14. Payment edges: zero amount, unknown frequency
15. `ai_extractor` helper function unit tests

## Anti-Patterns

### Anti-Pattern 1: Direct `db.conn.execute()` Outside the Lock

**What people do:** Call `db.conn.execute(...)` directly in services or controller without `with db._lock:`, relying on `check_same_thread=False` to permit multi-thread access.

**Why it's wrong:** `check_same_thread=False` only removes the thread-ownership assertion. SQLite in WAL mode handles concurrent reads well, but the application-level `_lock` is still the correctness mechanism for the read-modify-write patterns used throughout (e.g., `is_processed` then `save_result` in the pipeline).

**Do this instead:** All `db.conn.execute()` calls must be inside `with db._lock:`. If calling from a service that receives `db` by injection, acquire `db._lock` explicitly before accessing `db.conn`.

### Anti-Pattern 2: Bare `except Exception: pass` on Schema Operations

**What people do:** Wrap the entire migration body in `except Exception: pass` to silence all errors.

**Why it's wrong:** A migration that fails silently leaves the schema in a partially applied state. `_is_migration_applied` records it as done, but the column is absent.

**Do this instead:** Catch only `sqlite3.OperationalError` (the specific exception for "column already exists"). Let all other exceptions propagate. The existing v1-v9 migrations already do this correctly.

### Anti-Pattern 3: Unsynchronized Read-Modify-Write on settings.json

**What people do:** `load_settings()` → mutate → `write_text()` without synchronization. Two rapid UI settings toggles can both read the same stale JSON and one write overwrites the other's change.

**Do this instead:** Add a module-level `_settings_lock = threading.Lock()` in `config.py` and wrap the entire `save_setting` body with `with _settings_lock:`. Alternatively, write to a temp file then use `Path.replace()` for atomic swap.

### Anti-Pattern 4: Hardcoded Return Value in a Property That Reads Config

**What people do:** `active_model` property always returns `"glm-4.7"` regardless of `active_provider`.

**Why it's wrong:** The stored `model_used` value in the database becomes wrong for ollama runs. Any debugging, auditing, or statistics based on this field is unreliable.

**Do this instead:** The property must branch on `self.active_provider`. Each provider maps to its canonical model name.

### Anti-Pattern 5: No Timeout on External HTTP Clients in a ThreadPoolExecutor

**What people do:** Create `OpenAI(base_url=..., api_key=...)` without a `timeout` parameter, then submit tasks to `ThreadPoolExecutor`.

**Why it's wrong:** If llama-server hangs or a cloud provider is slow, the worker thread blocks indefinitely. With `max_workers=5`, five simultaneous hangs exhaust the thread pool and the entire pipeline stalls with no error until the process is killed.

**Do this instead:** Always pass `timeout=30.0` (or a value appropriate for the provider) to the `OpenAI` client constructor.

## Sources

- Direct code inspection: `modules/database.py`, `config.py`, `controller.py`, `services/lifecycle_service.py`, `services/version_service.py`, `providers/base.py`, `providers/ollama.py`, `modules/models.py` — HIGH confidence
- Python `threading.Lock` semantics and `dataclasses.__post_init__` contract: Python standard library documentation — HIGH confidence
- SQLite `check_same_thread` behavior: Python sqlite3 documentation — HIGH confidence
- `openai.OpenAI(timeout=...)` parameter: openai Python SDK documentation — HIGH confidence

---
*Architecture research for: ЮрТэг v1.0 — backend bug-fixing milestone*
*Researched: 2026-03-28*
