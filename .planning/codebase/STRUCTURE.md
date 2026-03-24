# Codebase Structure

**Analysis Date:** 2026-03-25

## Directory Layout

```
yurteg/
├── config.py                     # Centralized Config dataclass
├── controller.py                 # Pipeline orchestrator
├── main.py                       # Streamlit UI entrypoint (legacy, ~124KB)
├── desktop_app.py                # PyInstaller desktop app wrapper
│
├── app/                          # NiceGUI UI (SPA architecture)
│   ├── main.py                   # NiceGUI entrypoint, llama-server init
│   ├── state.py                  # AppState dataclass (per-connection state)
│   ├── styles.py                 # Design tokens, CSS classes
│   ├── demo_data.py              # Test fixtures for development
│   ├── components/               # Reusable UI components
│   │   ├── header.py             # Top navigation, client switcher
│   │   ├── registry_table.py     # AG Grid table with data loading, sorting, filtering
│   │   ├── split_panel.py        # Split-view container (document comparison)
│   │   ├── bulk_actions.py       # Bulk status change, export, delete
│   │   ├── process.py            # Processing UI (folder picker, progress bar)
│   │   ├── skeleton.py           # AG Grid loading skeleton
│   │   ├── ui_helpers.py         # Utility functions (empty state, formatting)
│   │   └── onboarding/           # First-time user experience
│   │       ├── splash.py         # Welcome screen
│   │       └── tour.py           # Guided tour (appears after first processing)
│   ├── pages/                    # SPA pages (sub_pages)
│   │   ├── registry.py           # Main document list view (~50KB, complex)
│   │   ├── document.py           # Document detail view (~30KB)
│   │   ├── settings.py           # API key config, provider selection
│   │   └── templates.py          # Template management (QA review standards)
│   └── static/                   # Global CSS and JS
│       ├── tokens.css            # Design system CSS custom properties
│       ├── animations.css        # Keyframe animations
│       └── [...other static]
│
├── modules/                      # Processing pipeline (modular, ~10 modules)
│   ├── models.py                 # Shared dataclasses (FileInfo, ExtractedText, ContractMetadata, ProcessingResult)
│   ├── scanner.py                # Directory scanning + SHA-256 hashing
│   ├── extractor.py              # Text extraction (PDF/DOCX)
│   ├── anonymizer.py             # NER-based personal data masking
│   ├── ai_extractor.py           # LLM prompting + JSON parsing
│   ├── postprocessor.py          # Metadata sanitization, date parsing, confidence scoring
│   ├── validator.py              # Multi-layer validation (L1-L5)
│   ├── database.py               # SQLite persistence + migrations
│   ├── organizer.py              # File copying to output structure
│   └── reporter.py               # Excel (.xlsx) generation
│
├── providers/                    # LLM provider abstraction
│   ├── __init__.py               # Factory: get_provider(), get_fallback_provider()
│   ├── base.py                   # Abstract LLMProvider interface
│   ├── zai.py                    # ZAI GLM-4.7 (primary, $0.018/doc)
│   ├── openrouter.py             # OpenRouter fallback (free models)
│   └── ollama.py                 # Local llama-server (privacy-first)
│
├── services/                     # Domain-specific business logic
│   ├── __init__.py               # Service imports
│   ├── pipeline_service.py       # Non-UI pipeline entry point (CLI, Telegram, tests)
│   ├── client_manager.py         # Multi-client/multi-registry tenant isolation
│   ├── lifecycle_service.py      # Document status (manual overrides, deadline tracking)
│   ├── payment_service.py        # Payment schedule extraction, calendar events
│   ├── version_service.py        # Document versioning, embedding-based diff, redline DOCX
│   ├── review_service.py         # Template-based contract review, QA matching
│   ├── llama_server.py           # Local LLM process management (download, start, stop)
│   ├── registry_service.py       # Client registry CRUD (minimal)
│   └── telegram_sync.py          # Telegram bot integration
│
├── tests/                        # Test suite
│   ├── test_extractor.py         # Text extraction tests
│   ├── test_anonymizer.py        # NER masking tests
│   ├── test_validator.py         # Validation logic tests
│   ├── test_database.py          # DB persistence tests
│   ├── [...other test files]
│   └── test_data/                # Test fixtures (sample PDFs, DOCX files)
│
├── dataset/                      # ML model training (separate from app)
│   ├── prepare_dataset.py        # Dataset preparation for SFT
│   ├── prepare_05b_dataset.py    # 0.5B model-specific prep
│   ├── prepare_05b_dpo.py        # DPO fine-tuning
│   ├── prepare_orpo_v3.py        # ORPO v3 training
│   ├── rejection_sampling.py     # Rejection sampling
│   ├── dpo_train_script.py       # DPO training runner
│   ├── demask_orpo.py            # Demask anonymization masks
│   ├── [...other training scripts]
│   └── training/                 # Training data files (.jsonl)
│
├── bot_server/                   # Telegram bot integration
│   ├── __init__.py
│   ├── handlers/                 # Telegram command handlers
│   ├── models/                   # Telegram message models
│   └── [...bot logic]
│
├── data/                         # Runtime data directory
│   └── [output/ structures]      # Processed archives get .db, Excel, organized files here
│
├── docs/                         # Documentation
│   └── [...technical specs, guides]
│
├── requirements.txt              # pip dependencies
├── README.md                     # Project overview
└── [.streamlit/, .pytest_cache/] # Tool configs and caches
```

## Directory Purposes

**config.py:**
- Purpose: Single source of configuration
- Contains: Config dataclass with all settings (models, API endpoints, paths, thresholds)
- Loaded by: Controller, UI, modules
- Not a directory; centralized config file

**app/ (NiceGUI Frontend):**
- Purpose: Desktop UI for document processing
- Contains: SPA pages, reusable components, state management, design system
- Key patterns: Sub_pages for SPA navigation, AppState per-connection, header persistence
- Styling: CSS tokens + class composition (no inline styles)

**modules/ (Processing Pipeline):**
- Purpose: Core document processing logic
- Contains: Scanner, Extractor, Anonymizer, AI Extractor, Validator, Database, Organizer, Reporter
- Pattern: Each module is a single .py file with 1-2 main functions + helpers
- Dataflow: Sequential for text extraction, parallel for AI calls (ThreadPoolExecutor)

**providers/ (LLM Abstraction):**
- Purpose: Plugin architecture for different LLM backends
- Contains: Abstract base class + concrete implementations (ZAI, OpenRouter, Ollama)
- Factory functions: get_provider(), get_fallback_provider()
- Usage: Controller uses provider.complete(prompt) → JSON response

**services/ (Domain Logic):**
- Purpose: Non-pipeline business logic (versioning, payments, lifecycle, review, etc.)
- Contains: Service classes for client mgmt, document versioning, payment scheduling, QA review
- Isolation: No import of main.py or Streamlit (work with Telegram, CLI, tests)

**tests/ (Test Suite):**
- Purpose: Unit and integration tests
- Contains: Test files mirroring module structure + test_data/ fixtures
- Pattern: pytest, no mocking framework (direct imports), real data files
- Run: pytest tests/ or pytest tests/test_extractor.py

**dataset/ (ML Training):**
- Purpose: Separate training pipeline for local LLM models (Qwen 1.5B, 0.5B)
- Contains: Data prep scripts, training configs, training data (.jsonl)
- Isolation: Not imported by main app; independent execution
- Related: models/ directory (downloaded/generated models) not committed

**bot_server/ (Telegram Integration):**
- Purpose: Telegram bot for async document processing and status updates
- Contains: Telegram command handlers, message models, webhook logic
- Isolation: Calls pipeline_service (non-UI entry point) to process archives

**data/ (Runtime Directory):**
- Purpose: Output directory for processed archives
- Contains: output_dir/{yurteg.db, report.xlsx, type/, counterparty/} structure
- Lifecycle: Created per process_archive() run; persists between runs for resumability

## Key File Locations

**Entry Points:**

- **NiceGUI Desktop:** `app/main.py` (primary desktop app, calls ui.run())
- **Streamlit Legacy:** `main.py` (old implementation, ~124KB, still active for cloud)
- **Desktop Packaging:** `desktop_app.py` (PyInstaller wrapper)
- **Non-UI Pipeline:** `services/pipeline_service.py` (Telegram, CLI, tests)

**Configuration:**

- **Runtime Config:** `config.py` (Config dataclass, all settings)
- **Persisted Settings:** `~/.yurteg/settings.json` (active_provider, thresholds) — not committed
- **Environment:** `.env` (development) or Streamlit secrets (cloud) — stores API keys
- **Design System:** `app/styles.py` (CSS classes) + `app/static/tokens.css` (CSS variables)

**Core Logic:**

- **Pipeline Orchestration:** `controller.py` (main entry: process_archive())
- **Config:** `config.py` (all settings)
- **Models:** `modules/models.py` (dataclasses: FileInfo, ExtractedText, ContractMetadata, ProcessingResult)
- **Scanner:** `modules/scanner.py` (scan_directory())
- **Extractor:** `modules/extractor.py` (extract_text())
- **Anonymizer:** `modules/anonymizer.py` (anonymize())
- **AI Extractor:** `modules/ai_extractor.py` (extract_metadata())
- **Validator:** `modules/validator.py` (validate_metadata(), validate_batch())
- **Database:** `modules/database.py` (Database class, CRUD)
- **Organizer:** `modules/organizer.py` (organize_file(), prepare_output_directory())
- **Reporter:** `modules/reporter.py` (generate_report())

**UI Layers:**

- **State:** `app/state.py` (AppState dataclass)
- **Pages:**
  - `app/pages/registry.py` (document list, ~50KB, most complex)
  - `app/pages/document.py` (detail view, ~30KB)
  - `app/pages/settings.py` (~18KB)
  - `app/pages/templates.py` (~20KB)
- **Components:**
  - `app/components/header.py` (navigation)
  - `app/components/registry_table.py` (AG Grid table, ~20KB)
  - `app/components/split_panel.py` (split view)
  - `app/components/bulk_actions.py` (bulk operations)
  - `app/components/process.py` (processing UI)
  - `app/components/onboarding/splash.py`, `onboarding/tour.py` (first-time UX)

**Services:**

- **Multi-Client Support:** `services/client_manager.py`
- **Status Management:** `services/lifecycle_service.py`
- **Payment Tracking:** `services/payment_service.py`
- **Document Versioning:** `services/version_service.py`
- **QA Review:** `services/review_service.py`
- **Local LLM:** `services/llama_server.py`

**Provider Abstraction:**

- **Factory:** `providers/__init__.py`
- **Abstract Base:** `providers/base.py`
- **Implementations:** `providers/zai.py`, `providers/openrouter.py`, `providers/ollama.py`

## Naming Conventions

**Files:**

- **Python modules:** snake_case.py (e.g., `ai_extractor.py`, `client_manager.py`)
- **Test files:** `test_*.py` (e.g., `test_extractor.py`, `test_validator.py`)
- **Config files:** lowercase (e.g., `config.py`, `.env`)
- **Static assets:** lowercase with hyphens (e.g., `tokens.css`, `animations.css`)
- **Database:** `yurteg.db` (SQLite, created in output_dir)
- **Backups:** `yurteg.db_backup_{timestamp}.sqlite`

**Directories:**

- **Packages (with __init__.py):** lowercase (e.g., `modules/`, `providers/`, `services/`, `app/`)
- **Sub-packages:** lowercase (e.g., `app/pages/`, `app/components/`, `bot_server/handlers/`)
- **Output directories:** Type-based or counterparty-based (user-controlled via config.grouping)

**Classes:**

- **Dataclasses (models):** PascalCase (e.g., `FileInfo`, `ContractMetadata`, `ProcessingResult`)
- **Service classes:** PascalCase ending in "Service" or "Manager" (e.g., `ClientManager`, `LlamaServerManager`)
- **Provider classes:** PascalCase ending in "Provider" (e.g., `ZAIProvider`, `OllamaProvider`)
- **UI components:** Functions (render_*) or plain PascalCase classes (e.g., `AppState`)

**Functions:**

- **Public functions:** snake_case (e.g., `scan_directory()`, `extract_text()`)
- **Private functions:** _leading_underscore (e.g., `_notify()`, `_apply_migration()`)
- **Callbacks:** on_* or _on_* (e.g., `on_progress()`, `_on_pick_folder()`)
- **Async functions:** async def with same naming (e.g., `async def _start_llama()`)

**Variables & Constants:**

- **Local variables:** snake_case (e.g., `source_dir`, `metadata_json`)
- **Constants:** UPPER_SNAKE_CASE (e.g., `MAX_FILE_SIZE`, `ENTITY_TYPES`)
- **State fields:** snake_case (e.g., `source_dir`, `selected_doc_id`, `bulk_mode`)

## Where to Add New Code

**New Feature (in existing module scope):**
- Primary code: Add function to existing `modules/*.py` file (e.g., new validator rule in `modules/validator.py`)
- Tests: Add test function to corresponding `tests/test_*.py` file (e.g., `tests/test_validator.py`)
- Example: Adding payment_frequency extraction → modify `modules/ai_extractor.py` prompt + ContractMetadata fields

**New Processing Stage (new module):**
- Implementation: Create new file in `modules/` (e.g., `modules/ocr_handler.py` for scanned PDFs)
- Integration: Import in `controller.py`, insert in _run_pipeline() sequence
- Tests: Create `tests/test_ocr_handler.py` with test fixtures
- Models: Add new dataclass to `modules/models.py` if needed

**New Service (domain logic beyond pipeline):**
- Implementation: Create new file in `services/` (e.g., `services/audit_log.py`)
- Factory: Add to `services/__init__.py` imports
- UI Integration: Import in page/component files that need it (e.g., `app/pages/registry.py`)
- Tests: Create `tests/test_audit_log.py`

**New LLM Provider:**
- Implementation: Create `providers/newprovider.py` inheriting from `providers.base.LLMProvider`
- Factory: Register in `providers/__init__.py` get_provider() and get_fallback_provider()
- Config: Add new env var to `config.py` (e.g., `newprovider_api_key`)
- Tests: Create `tests/test_newprovider.py`

**New UI Page:**
- Implementation: Create `app/pages/newpage.py` with page rendering function
- Integration: Register in `app/main.py` via ui.sub_page()
- Components: Create supporting components in `app/components/` as needed
- Styling: Use existing classes from `app/styles.py`, extend if needed

**New UI Component:**
- Implementation: Create `app/components/newcomponent.py` with render_* function
- Reusability: Keep logic pure (no hardcoded state)
- Styling: Import from `app/styles.py`
- Usage: Import and call in pages (`app/pages/*.py`)

## Special Directories

**data/:**
- Purpose: Runtime working directory for processed archives
- Generated: Yes (created during process_archive())
- Committed: No (.gitignore)
- Lifecycle: Persists across runs (yurteg.db enables resumability)
- Example structure:
  ```
  data/2025-03-15_contracts/
  ├── yurteg.db
  ├── report.xlsx
  ├── Договор поставки/
  │   ├── ООО Альфа/
  │   │   ├── contract_01.pdf
  │   │   └── contract_02.pdf
  │   └── ООО Бета/
  │       └── contract_03.pdf
  └── Договор аренды/
      └── ИП Гамма/
          └── contract_04.pdf
  ```

**.planning/codebase/:**
- Purpose: Architecture and structure documentation
- Generated: No (manually created by GSD mapper)
- Committed: Yes
- Contents: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md

**.streamlit/ & .pytest_cache/:**
- Purpose: Tool configuration and caches
- Generated: Yes
- Committed: No (.gitignore)
- Contents: Streamlit secrets, pytest cache

**dataset/:**
- Purpose: Model training pipeline (separate from main app)
- Generated: Yes (.jsonl training data files created by prep scripts)
- Committed: Partially (scripts committed, training data not)
- Lifecycle: Independent of main app; can be skipped in production

---

*Structure analysis: 2026-03-25*
