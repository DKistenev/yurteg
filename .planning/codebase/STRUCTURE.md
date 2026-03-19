# Codebase Structure

**Analysis Date:** 2026-03-19

## Directory Layout

```
yurteg/
├── .planning/                  # GSD planning documents
├── .streamlit/                 # Streamlit configuration
│   └── config.toml
├── .claude/                    # Claude context/notes
├── dataset/                    # Test/training data (not part of core pipeline)
│   ├── contracts_scraped/      # Sample contracts grouped by type
│   ├── training/               # Training data for fine-tuning
│   ├── prepare_dataset.py      # Dataset preparation utilities
│   ├── scrape_contracts.py     # Web scraper for sample contracts
│   └── ... (other dataset tools)
├── tests/                      # Test suite
│   ├── conftest.py             # pytest fixtures
│   ├── test_data/              # Sample PDF/DOCX files for testing
│   ├── test_extractor.py       # Tests for text extraction
│   ├── test_anonymizer.py      # Tests for anonymization
│   ├── test_validator.py       # Tests for validation
│   ├── generate_test_docs.py   # Utility to create test documents
│   ├── stress_test.py          # Large-scale processing tests
│   └── ЮрТэг_Результат/        # Sample output directory from test run
├── modules/                    # Core processing modules
│   ├── __init__.py
│   ├── models.py               # Shared dataclasses (FileInfo, ExtractedText, etc.)
│   ├── scanner.py              # Directory scanning, file discovery
│   ├── extractor.py            # Text extraction (PDF/DOCX)
│   ├── anonymizer.py           # PII masking with Natasha NER + regex
│   ├── ai_extractor.py         # LLM calls for metadata extraction
│   ├── validator.py            # 4-level validation (L1-L4)
│   ├── database.py             # SQLite persistence, resumability
│   ├── organizer.py            # File copying and folder organization
│   └── reporter.py             # Excel report generation
├── main.py                     # Streamlit UI entry point
├── controller.py               # Pipeline orchestration
├── config.py                   # Centralized configuration
├── desktop_app.py              # pywebview desktop wrapper (deprecated)
├── requirements.txt            # Python dependencies
├── README.md                   # Project description
└── CLAUDE.md                   # Project instructions & glossary
```

## Directory Purposes

**yurteg/ (root):**
- Purpose: Top-level project directory
- Contains: Entry points, config, modules
- Key files: `main.py`, `controller.py`, `config.py`

**modules/:**
- Purpose: Core processing pipeline, each module is independent
- Contains: 9 Python files, each responsible for one transformation stage
- Key files: See "Key File Locations" below

**tests/:**
- Purpose: Test suite and sample data
- Contains: pytest tests, fixtures, sample documents, test output
- Key files: `conftest.py` (fixtures), `test_*.py` (unit tests), `test_data/` (sample files)

**dataset/:**
- Purpose: Training/evaluation data, utilities for dataset management
- Contains: 30+ subdirectories of sample contracts (scraped from web)
- Key files: `scrape_contracts.py` (web scraper), `prepare_dataset.py` (data prep)
- Note: Used for fine-tuning AI models, NOT for production processing

**.streamlit/:**
- Purpose: Streamlit framework configuration
- Contains: `config.toml` (theme, logger settings)

**.planning/codebase/:**
- Purpose: GSD mapping documents
- Contains: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, STACK.md, INTEGRATIONS.md, CONCERNS.md

**.claude/:**
- Purpose: Claude context cache and notes
- Contains: .aider.conf, or similar

## Key File Locations

**Entry Points:**
- `main.py`: Streamlit UI, folder selection, progress display, results tabs
- `controller.py`: Pipeline orchestration, file processing loop, error handling

**Configuration:**
- `config.py`: All hardcoded settings (API endpoints, model names, validation thresholds, document type hints)
- `.streamlit/config.toml`: Streamlit theme/behavior settings
- `requirements.txt`: Python dependencies (see STACK.md)

**Core Logic (modules/):**
- `modules/models.py`: Shared dataclasses for inter-module communication
- `modules/scanner.py`: Recursive directory scan, file filtering, hash computation
- `modules/extractor.py`: PDF (pdfplumber) and DOCX (python-docx) text extraction
- `modules/anonymizer.py`: Natasha NER + regex for PII masking
- `modules/ai_extractor.py`: LLM calls to ZAI/OpenRouter, JSON parsing, fallback logic
- `modules/validator.py`: 4-level metadata validation (structural, logical, confidence, batch)
- `modules/database.py`: SQLite CRUD, resumability via is_processed()
- `modules/organizer.py`: File copying, path sanitization, grouping modes (type/counterparty/both)
- `modules/reporter.py`: Excel generation with multi-sheet layout, formatting, charts

**Testing:**
- `tests/conftest.py`: pytest fixtures (sample configs, mock data)
- `tests/test_extractor.py`: Tests for text extraction edge cases
- `tests/test_anonymizer.py`: Tests for NER and regex patterns
- `tests/test_validator.py`: Tests for validation rules
- `tests/test_data/`: Sample PDF/DOCX files
- `tests/stress_test.py`: Large-scale pipeline tests

**Training/Data:**
- `dataset/contracts_scraped/`: 30+ directories of sample contracts by type
- `dataset/training/`: Preprocessed data for AI model fine-tuning

## Naming Conventions

**Files:**
- Python modules: `lowercase_with_underscores.py` (e.g., `ai_extractor.py`, `test_anonymizer.py`)
- Output folder: `ЮрТэг_Результат` (hardcoded in config.output_folder_name)
- Excel report: `Реестр_договоров.xlsx`
- Database: `yurteg.db`

**Directories:**
- Package modules: `modules/`
- Tests: `tests/`, individual test files as `test_*.py`
- Data directories: descriptive, English or Russian (e.g., `contracts_scraped/`, `training/`)
- Output subdirectories (in result): `Документы/` (files organized by type/counterparty)

**Functions:**
- Private: leading underscore `_function_name()` (e.g., `_extract_from_pdf()`, `_validate_l1()`)
- Public: no prefix `function_name()`
- Callbacks: `on_progress`, `on_file_done` (passed to controller)

**Variables:**
- Constants: UPPERCASE (e.g., `SYSTEM_PROMPT`, `_SCHEMA`, `ENTITY_TYPES`)
- Local: snake_case (e.g., `file_hash`, `page_count`, `anonymized_text`)
- Class attributes: snake_case (e.g., `self.config`, `self.db_path`)

**Types:**
- Dataclasses: PascalCase (e.g., `FileInfo`, `ContractMetadata`, `ValidationResult`)
- Enums/aliases: mentioned in code but not explicitly defined; used as strings
- Type hints: full (e.g., `list[str]`, `dict[str, int]`, `Optional[Path]`)

## Where to Add New Code

**New Feature (e.g., parsing XLSX files):**
- Primary code: Create new module `modules/xlsx_extractor.py`
- Integration: Modify `modules/extractor.py` to dispatch to xlsx_extractor based on extension
- Modify config: Add `.xlsx` to `config.supported_extensions`
- Tests: Add `tests/test_xlsx_extractor.py`
- Update model: `modules/models.py` if new fields needed in `ExtractedText`

**New Validation Rule (e.g., detect fraudulent contracts):**
- Implementation: Add function `_validate_fraud()` in `modules/validator.py`
- Call site: Add to `validate_metadata()` alongside L1-L3 checks
- Return: Add warning string to warnings list (e.g., `"L4: Подозрение на мошеничество"`)
- Test: Add case to `tests/test_validator.py`

**New Data Transformation (e.g., entity normalization):**
- Implementation: Create new module `modules/normalizer.py`
- Call site: Insert in controller._run_pipeline() between anonymize and ai_extract
- Data flow: input `AnonymizedText`, output `AnonymizedText` (modified)
- Type hints: follow pattern in `modules/extractor.py`

**New Report Sheet (e.g., compliance summary):**
- Implementation: Add function `_create_compliance_sheet()` in `modules/reporter.py`
- Call site: Inside `generate_report()`, after existing sheets
- Naming: Use Russian labels in Excel (e.g., "Соответствие требованиям")
- Formatting: Follow color scheme in `STATUS_COLORS` and openpyxl styling

**Utility Function (e.g., date parser):**
- Location: `modules/models.py` or new `modules/utils.py` if substantial
- Naming: descriptive verb_noun (e.g., `parse_date()`, `sanitize_text()`)
- Pattern: pure function, no side effects, full type hints

## Special Directories

**modules/__pycache__/:**
- Purpose: Python bytecode cache
- Generated: Yes (by Python interpreter)
- Committed: No (in .gitignore)

**tests/ЮрТэг_Результат/:**
- Purpose: Sample output directory from test pipeline run
- Generated: Yes (created by stress_test.py)
- Committed: Yes (for reference/demo)

**dataset/contracts_scraped/:**
- Purpose: Sample contracts grouped by document type (for training/demos)
- Generated: No (manually created via scrape_contracts.py)
- Committed: Yes (part of repo)

**.streamlit/:**
- Purpose: Streamlit app configuration
- Files: `config.toml` (theme, logging, server settings)
- Committed: Yes

**.planning/codebase/:**
- Purpose: GSD mapping documents (architecture, structure, conventions, testing, stack, integrations, concerns)
- Generated: Yes (by gsd:map-codebase)
- Committed: Yes (for orchestrator/executor reference)

## Import Paths

**Absolute imports (used throughout codebase):**
```python
from config import Config
from controller import Controller
from modules.models import FileInfo, ContractMetadata
from modules.scanner import scan_directory
from modules.extractor import extract_text
from modules.anonymizer import anonymize
from modules.ai_extractor import extract_metadata
from modules.validator import validate_metadata, validate_batch
from modules.database import Database
from modules.organizer import organize_file, prepare_output_directory
from modules.reporter import generate_report
```

**Never used:**
- Relative imports (e.g., `from .models import...`)
- Aliasing with `as` (rare; only for external libraries like `pandas as pd`)

## Configuration Files

**config.py:**
- Type: Python dataclass
- Purpose: Single source of truth for all settings
- Key sections:
  - AI providers: endpoints, model names, fallback strategy
  - Validation: confidence thresholds, validation_mode
  - File handling: supported extensions, max size, anonymization types
  - Output: folder naming, document type hints

**.streamlit/config.toml:**
- Type: TOML
- Purpose: Streamlit framework settings
- Key settings: theme (light/dark), client logging level, server settings

**requirements.txt:**
- Type: Plain text
- Purpose: Python dependencies
- Format: one package per line (pinned or range versions)

**CLAUDE.md (project instructions):**
- Type: Markdown
- Purpose: Technical specification, team memory, preferences
- Contains: Architecture overview, module specs, development order, key rules

---

*Structure analysis: 2026-03-19*
