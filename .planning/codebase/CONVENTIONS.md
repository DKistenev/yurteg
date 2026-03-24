# Coding Conventions

**Analysis Date:** 2026-03-25

## Naming Patterns

**Files:**
- snake_case for all Python files: `ai_extractor.py`, `client_manager.py`, `registry_service.py`
- Component files in `app/components/` follow pattern: `{feature}.py` (e.g., `split_panel.py`, `bulk_actions.py`)
- Page files in `app/pages/` named by page: `registry.py`, `document.py`, `templates.py`, `settings.py`
- Test files: `test_{feature}.py` (e.g., `test_lifecycle.py`, `test_registry_view.py`)

**Functions:**
- snake_case for all functions: `compute_file_hash()`, `save_payments()`, `get_state()`
- Private functions with leading underscore: `_notify()`, `_on_upload_click()`, `_start_llama()`
- Async functions are async def with same naming: `async def _on_upload_click()`
- Callback helpers with `_on_` prefix for UI event handlers: `_on_pick_folder()`, `_on_upload_click()`

**Variables:**
- snake_case for all variables: `source_dir`, `file_hash`, `temp_db`, `validation_warnings`
- Constants in UPPER_SNAKE_CASE: `MAX_FILE_SIZE_MB`, `MANUAL_STATUSES`, `STATUS_LABELS`
- Type hints always present on function parameters and returns
- Module-level singletons prefixed with underscore: `_llama_manager`, `_cm` (ClientManager), `_header_refs`

**Types and Classes:**
- PascalCase for all classes: `FileInfo`, `ExtractedText`, `ContractMetadata`, `ProcessingResult`, `AppState`, `Controller`, `Database`
- Dataclasses use `@dataclass` decorator from `dataclasses` module
- Type hints on all fields: `path: Path`, `text: str`, `confidence: float = 0.0`

## Code Style

**Formatting:**
- No explicit formatter configured (black/prettier not in requirements.txt)
- Consistent use of double quotes for strings (not enforced, but used)
- Docstrings: triple double-quotes with doctest/NumPy style (see examples below)
- Line breaks after imports section (blank line between stdlib/third-party/local)
- Indentation: 4 spaces (Python standard)

**Linting:**
- pytest configured in `pytest.ini` with markers for slow tests
- No flake8, mypy, or ruff config detected
- Test markers: `@pytest.mark.slow` for tests >5 sec, `@pytest.mark.xfail` for tests not yet implemented

**Docstring Pattern:**

```python
def scan_directory(directory: Path, config: Config) -> list[FileInfo]:
    """
    Рекурсивно сканирует директорию.

    Аргументы:
        directory: путь к папке с договорами
        config: конфигурация (расширения, макс. размер)

    Возвращает:
        Список FileInfo для всех найденных файлов поддерживаемых форматов.
        Файлы, превышающие max_file_size_mb, пропускаются (логируются как WARNING).

    Raises:
        FileNotFoundError: если directory не существует или не является директорией
    """
```

Docstrings always in Russian. Include Args, Returns, Raises sections. Describe constraints and behavior.

## Import Organization

**Order:**
1. Standard library imports: `import logging`, `from dataclasses import dataclass`, `from pathlib import Path`
2. Third-party imports: `from nicegui import app, ui`, `from openai import OpenAI`, `import pytest`
3. Local imports: `from config import Config`, `from modules.models import FileInfo`, `from app.state import AppState`

**Path Aliases:**
- No path aliases configured (`src/` mapping, etc.)
- Relative imports not used — all imports from package root
- Example: `from modules.ai_extractor import extract_metadata` (not relative from siblings)

**Pattern - Standard Module Structure:**

```python
"""Module docstring — brief description in Russian."""
import logging
from pathlib import Path
from typing import Optional

from nicegui import ui  # third-party
from config import Config  # local

logger = logging.getLogger(__name__)
```

All modules initialize `logger = logging.getLogger(__name__)` for logging.

## Error Handling

**Patterns:**

1. **Exceptions propagate by default** — catch only when you need to handle or log:
   ```python
   try:
       text = extract_text(file_info)
   except Exception as e:
       logger.error("Ошибка при извлечении текста: %s", e)
       result.error_message = "Не удалось извлечь текст"
       result.status = "error"
   ```

2. **Custom status codes** instead of exceptions:
   ```python
   result = ProcessingResult(file_info=file_info, status="processing")
   # ...
   if extraction_failed:
       result.status = "error"
       result.error_message = "..."
       db.save_result(result)
   ```

3. **Log levels:**
   - `logger.info()` — normal operations, progress, counts (e.g., "Найдено 42 файлов (5 PDF, 37 DOCX)")
   - `logger.warning()` — recoverable issues (e.g., file too large, missing field)
   - `logger.error()` — recoverable errors during processing (e.g., extraction failed, API timeout)
   - `logger.exception()` — use in except blocks to include traceback

4. **No try/finally for cleanup** — use context managers:
   ```python
   with Database(db_path) as db:
       # db auto-closes
   ```

5. **Function failures return status, not exceptions:**
   - See `ProcessingResult` — stores `status` ("done"/"error") and `error_message`
   - Errors don't break the pipeline — logged and continued

## Logging

**Framework:** Standard Python `logging` module

**Initialization:** Every module starts with:
```python
logger = logging.getLogger(__name__)
```

**Patterns:**
- Progress updates use `logger.info()` with context
- File operations log counts: `logger.info("Найдено %d файлов (%s)", len(files), parts)`
- Skipped files log as warnings: `logger.warning("Файл пропущен (размер %d МБ): %s", size_mb, path.name)`
- API failures log as error/warning depending on retry strategy
- No log-in-debug; focus on meaningful info/warning/error levels

**Examples:**
```python
logger.info("Найдено %d файлов (5 PDF, 37 DOCX)", 42)
logger.warning("Файл пропущен (размер 100 МБ > 50 МБ): contract.pdf")
logger.error("Ошибка при сохранении результата: %s", str(e))
logger.info("llama-server запущен")
logger.info("llama-server остановлен")
```

## Comments

**When to Comment:**
- Explain WHY, not WHAT — code is self-documenting
- Complex algorithms (e.g., SQL CASE expression for status computation)
- Workarounds for bugs or platform quirks (e.g., "NiceGUI bug #2107 — on_shutdown unreliable in native=True on macOS")
- Non-obvious architectural decisions

**Pattern:**
```python
# Тройная защита shutdown (D-10, FUND-04):
# on_shutdown ненадёжен в native=True на macOS (NiceGUI bug #2107)
app.on_startup(_start_llama)
app.on_shutdown(_stop_llama)
app.on_disconnect(_stop_llama)
atexit.register(_stop_llama)
```

Per-file docstrings referencing design phases (e.g., `Per D-12: ...`) are common.

## Function Design

**Size:**
- Small and focused — typically 5-30 lines
- Long functions (>50 lines) indicate need to extract helpers
- Examples: `_notify()` is 3 lines, `_run_pipeline()` is ~150 lines but clearly sectioned with comments

**Parameters:**
- Type-hinted always: `def compute_file_hash(file_path: Path) -> str:`
- Optional parameters with defaults: `on_progress: Optional[Callable[[int, int, str], None]] = None`
- Dataclass instances preferred over many individual params: `ProcessingResult` instead of 10 booleans/strings
- Callback functions as parameters: `on_progress(current, total, message)` pattern

**Return Values:**
- Explicit types: `-> list[FileInfo]`, `-> dict`, `-> Optional[Path]`
- Dataclass instances for complex returns: `ProcessingResult`, `ContractMetadata`
- None for side-effect-only functions (e.g., `_notify()`)
- Tuple unpacking discouraged; use dataclasses instead

**Idempotency:**
- Functions safe to call multiple times: `manager.stop()` is idempotent, `atexit.register()` called 3 times is safe
- SQL migrations idempotent (checked with version)
- File operations create directories with `mkdir(parents=True, exist_ok=True)`

## Module Design

**Exports:**
- No `__all__` defined — import what you need
- Public functions/classes have no leading underscore
- Internal helpers have `_prefix`

**Barrel Files:**
- `app/components/__init__.py` and `app/pages/__init__.py` mostly empty
- Import directly from modules: `from app.components.header import render_header`
- No re-exports

**Organization:**
- Each module has one main responsibility: `scanner.py` = find files, `anonymizer.py` = mask PII
- Services layer (`services/*.py`) isolates business logic from Streamlit/NiceGUI
- UI components in `app/components/` or `app/pages/`
- Data layer (`modules/database.py`, models in `modules/models.py`)

## Type Hints

**Always required:**
- Function parameters: `def process(name: str, count: int) -> bool:`
- Variable declarations when not obvious: `files: list[FileInfo] = []`
- Dataclass fields: `name: str`, `items: list[str] = field(default_factory=list)`

**Patterns:**
- Use `Path` from pathlib, not str for file paths
- Use `Optional[T]` instead of `T | None` (Python 3.9 compatibility)
- `dict[str, str]` not `Dict[str, str]` (Python 3.9+)
- `list[FileInfo]` not `List[FileInfo]`

## Async/Await

**Pattern for blocking operations in UI:**
```python
async def _on_upload_click() -> None:
    if state.processing:
        return
    source_dir = await pick_folder()
    if source_dir and on_upload:
        await on_upload(source_dir)
```

**Pattern for running sync code from async context:**
```python
await run.io_bound(manager.ensure_model)
await run.io_bound(manager.start, get_grammar_path())
```

Use `run.io_bound()` for ALL blocking calls from NiceGUI event loop — never block directly.

---

*Convention analysis: 2026-03-25*
