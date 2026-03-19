# Coding Conventions

**Analysis Date:** 2026-03-19

## Naming Patterns

**Files:**
- Module files: `snake_case.py` — `extractor.py`, `ai_extractor.py`, `anonymizer.py`
- Main application: `main.py` (Streamlit entry point)
- Configuration: `config.py`
- Controller: `controller.py`

**Functions:**
- Regular functions: `snake_case` — `extract_text()`, `anonymize()`, `validate_metadata()`
- Private functions: leading underscore + snake_case — `_validate_l1()`, `_extract_from_pdf()`, `_sanitize_name()`
- Callback functions: `on_progress()`, `on_file_done()` (passed as parameters)

**Variables:**
- Local/instance variables: `snake_case` — `file_info`, `metadata`, `output_dir`
- Constants: `SCREAMING_SNAKE_CASE` — `SYSTEM_PROMPT`, `ENTITY_TYPES`, `PATTERNS`
- Private module variables: leading underscore + snake_case — `_segmenter`, `_morph_vocab`, `_emb`

**Classes & Types:**
- Dataclasses: `PascalCase` — `FileInfo`, `ExtractedText`, `ContractMetadata`, `ValidationResult`
- Type hints: always present — `def extract_text(file_info: FileInfo) -> ExtractedText`

## Code Style

**Formatting:**
- Line length: no explicit limit enforced (observed up to 100+ characters)
- String quotes: double quotes (`"text"`) preferred throughout
- Indentation: 4 spaces
- Trailing whitespace: avoided
- Blank lines: 2 between module-level functions/classes, 1 within class definitions

**Linting:**
- No `.eslintrc` or `.prettierrc` file present
- No automated formatting tool enforced
- Conventions followed through consistent patterns rather than tooling

**Docstrings:**
- Google/NumPy-style docstrings with triple quotes
- First line is summary sentence ending with period
- Followed by blank line, then multi-line sections like `Args:`, `Returns:`, `Raises:`
- Example: `modules/extractor.py` line 13-25

## Import Organization

**Order (observed pattern):**
1. Standard library imports (logging, re, json, pathlib, etc.)
2. Third-party imports (pdfplumber, python-docx, natasha, pandas, streamlit, etc.)
3. Blank line separator
4. Local imports from `config`, `modules.*`

**Path Aliases:**
- Absolute imports only — no relative imports (`from modules.models import...` not `from .models import...`)
- Project root added to sys.path via `conftest.py` for tests

**Examples:**
```python
# modules/ai_extractor.py
import json
import logging
import os
import re
import time
from typing import Optional

from openai import OpenAI, APIError, APITimeoutError, RateLimitError

from config import Config
from modules.models import ContractMetadata
```

## Error Handling

**Pattern: Silent Failure with Logging**
- Modules never raise exceptions to caller
- All exceptions caught with `except Exception as e:`
- Logged at appropriate level: ERROR, WARNING, or INFO
- Function returns sensible default (empty result, None, or "failed" status)
- Caller checks result status field to determine success

**Examples:**
- `modules/extractor.py` lines 25-37: If text extraction fails, returns `ExtractedText` with `extraction_method="failed"` rather than raising
- `modules/anonymizer.py`: If anonymization processing fails, returns original text unchanged
- `modules/ai_extractor.py`: API errors caught, fallback model attempted, partial metadata returned if needed

**Status Fields:**
- `ProcessingResult.status`: "pending" | "processing" | "done" | "error"
- `ExtractedText.extraction_method`: "pdfplumber" | "python-docx" | "ocr" | "failed"
- `ValidationResult.status`: "ok" | "warning" | "unreliable" | "error"

**Validation Levels:**
- L1: Structural — required fields, format validation
- L2: Logical — date ranges, anomaly detection
- L3: AI confidence — threshold checks
- L4: Batch — cross-file analysis, duplicate detection

## Logging

**Framework:** Python standard `logging` module

**Initialization Pattern:**
```python
import logging
logger = logging.getLogger(__name__)
```

**Log Levels Used:**
- `logger.debug()`: Low-level details (file hashes computed, etc.)
- `logger.info()`: Progress and success messages (file found, validation passed, etc.)
- `logger.warning()`: Skipped files, anomalies detected, fallback used
- `logger.error()`: Exceptions caught, extraction/API failures

**Common Patterns:**
```python
logger.info("Найдено %d файлов (%s)", len(files), ", ".join(parts))
logger.warning("Файл пропущен (размер %d МБ > %d МБ): %s", size_mb, max_mb, path.name)
logger.error("Ошибка извлечения текста из %s: %s", filename, e)
logger.debug("Сохранён: %s (статус=%s)", filename, status)
```

**Conventions:**
- Use `%s`, `%d`, `%f` format strings (not f-strings in logging calls)
- Include context (filename, size, count) in all log messages
- Russian language for all messages (logger output intended for Russian-speaking users)

## Comments

**When to Comment:**
- Algorithm explanations (why, not what) — see `modules/validator.py` for validation logic
- Non-obvious regex patterns — see `modules/anonymizer.py` patterns dictionary
- Complex prompts for AI — see `modules/ai_extractor.py` SYSTEM_PROMPT and USER_PROMPT_TEMPLATE
- Section separators for logical grouping (dashed lines like `# ── Extraction ───────────`)

**JSDoc/TSDoc:**
- Not used (Python project, not TypeScript/JavaScript)
- Docstrings follow Google style for modules, classes, and functions

**Module Docstrings:**
- Every module has docstring explaining purpose
- Example: `modules/validator.py` describes 4 levels of validation
- Example: `modules/organizer.py` explains 3 grouping modes

## Function Design

**Size:**
- Most functions 20-50 lines
- Longer functions (100+ lines) broken into internal helper functions with `_` prefix
- Example: `modules/ai_extractor.py` main `extract_metadata()` calls internal `_merge_system_into_user()`, `_prepare_fallback_request()`

**Parameters:**
- Type hints required for all parameters
- Dataclass objects preferred over multiple scalar parameters
- Example: `extract_text(file_info: FileInfo) -> ExtractedText` instead of separate filename/extension/size params
- Config passed as dependency when needed: `validate_metadata(metadata: ContractMetadata, config: Config)`

**Return Values:**
- Always use dataclass return types when multiple values needed
- Single responsibility: don't return success bool + multiple optional fields
- Example: return `ValidationResult` (single object with status, warnings, score) not tuple

**Callbacks:**
- Optional callbacks for UI progress: `on_progress(current: int, total: int, message: str)`
- Optional callbacks for file completion: `on_file_done(result: ProcessingResult)`
- Callbacks invoked via helper: `_notify(on_progress, 0, 0, "message")`

## Module Design

**Exports (Public Interface):**
- Main function(s) at module top (after docstring + imports)
- Helper functions prefixed with `_` for privacy
- All public functions typed with full type hints
- Example `modules/scanner.py`: exports `compute_file_hash()` and `scan_directory()`

**Barrel Files:**
- No barrel/index files used
- Each module imported directly: `from modules.scanner import scan_directory`
- `modules/__init__.py` exists but empty

**Data Flow via Dataclasses:**
- All inter-module communication through dataclass objects
- No loose dictionaries or tuples passed between modules
- Dataclasses defined in `modules/models.py` for shared use
- Each dataclass represents a clear domain concept: FileInfo, ExtractedText, ContractMetadata, etc.

**Layered Architecture:**
- Modules operate independently (no circular imports)
- `controller.py` orchestrates sequential module calls
- Each module can be tested in isolation
- Dependencies injected as parameters (Config, callbacks)

## Configuration

**Pattern: Single Centralized Config**
- All settings in `config.py` as fields in `Config` dataclass
- No scattered magic numbers or hardcoded values
- Config passed to functions that need it
- Example: `max_file_size_mb`, `ai_temperature`, `confidence_high` all in Config

**Environment Variables:**
- Loaded via `python-dotenv` (`.env` file)
- API keys: `ZHIPU_API_KEY`, `OPENROUTER_API_KEY`, `ZAI_API_KEY`
- Feature flags: `YURTEG_DESKTOP`, `YURTEG_CLOUD`
- Never hardcoded; always `os.environ.get("KEY")`

## Threading & Concurrency

**Pattern: ThreadPoolExecutor for AI Calls**
- Only AI extraction parallelized (bottleneck ~4 sec/file)
- Text extraction + anonymization sequential (fast, <0.1 sec combined)
- Database access protected with `threading.Lock`
- Example: `modules/database.py` uses `self._lock` for CRUD operations
- Example: `controller.py` uses `concurrent.futures.as_completed()` to track AI requests

## Unicode & Internationalization

**Encoding:**
- UTF-8 everywhere (specified in docstrings)
- Russian language in UI, logs, comments
- Cyrillic text in config (document type hints, field names)
- No ASCII-only assumptions

**File Paths:**
- Always use `pathlib.Path` (never `os.path`)
- `Path.rglob()` for recursive directory traversal
- `Path.suffix` for file extensions
- Handles Unicode filenames correctly on all platforms

---

*Convention analysis: 2026-03-19*
