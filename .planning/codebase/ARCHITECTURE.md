# Architecture

**Analysis Date:** 2026-03-25

## Pattern Overview

**Overall:** Modular pipeline + layered UI architecture

**Key Characteristics:**
- **Backend:** Sequential + parallel pipeline orchestration (scan → extract → anonymize → AI → validate → organize → report)
- **Frontend:** NiceGUI SPA with per-connection state management and persistent AppState
- **Processing:** ThreadPoolExecutor parallelism for AI calls (~4 sec/file), sequential for text extraction/anonymization (<0.1 sec/file)
- **Resumability:** File hashes + SQLite caching enable safe re-runs without reprocessing already-handled files
- **Provider abstraction:** Pluggable LLM providers (ZAI, OpenRouter, Ollama) with automatic fallback

## Layers

**Configuration Layer:**
- Purpose: Centralized runtime settings (model names, API endpoints, paths, thresholds)
- Location: `config.py`
- Contains: Config dataclass with all app settings (supported formats, AI models, validation thresholds, etc.)
- Depends on: None (pure data)
- Used by: Controller, UI, modules

**Processing Pipeline (modules/ directory):**

- **Scanner:** `modules/scanner.py`
  - Purpose: Recursively scan source directory for PDF/DOCX files
  - Computes SHA-256 hashes for file deduplication
  - Returns sorted FileInfo objects with size, hash, path

- **Extractor:** `modules/extractor.py`
  - Purpose: Text extraction from PDF/DOCX files
  - Handles multiple methods (pdfplumber for PDF, python-docx for DOCX, OCR fallback)
  - Returns ExtractedText with page count and scan detection

- **Anonymizer:** `modules/anonymizer.py`
  - Purpose: Mask personal data (names, phones, emails, IPs, etc.) using natasha NER
  - Produces replacement map for later unmasking
  - Skipped for ollama provider (local processing, no privacy risk)

- **AI Extractor:** `modules/ai_extractor.py`
  - Purpose: Send anonymized text to LLM (ZAI GLM-4.7 or OpenRouter) for structured metadata extraction
  - Returns ContractMetadata (type, counterparty, dates, amount, special_conditions, etc.)
  - Handles retries, timeout fallback, and provider switching

- **Postprocessor:** `modules/postprocessor.py`
  - Purpose: Clean and validate AI-extracted metadata (date parsing, confidence scoring via logprobs, GBNF grammar validation)
  - Returns sanitized ContractMetadata

- **Validator:** `modules/validator.py`
  - Purpose: Multi-level validation (L1-L5) of extracted metadata
  - Checks for required fields, date consistency, amount formatting, pattern matching
  - Returns ValidationResult with warnings and confidence score

- **Database:** `modules/database.py`
  - Purpose: SQLite persistence of processing results and metadata
  - Tracks file_hash for deduplication, saves ContractMetadata, validation status
  - Supports schema migrations with backup
  - Enables resumability: `db.is_processed(file_hash)` skips previously handled files

- **Organizer:** `modules/organizer.py`
  - Purpose: Copy processed files into output directory structure (grouped by type and/or counterparty)
  - Creates directory hierarchy: `output/[type]/[counterparty]/document.pdf`
  - Never moves/deletes original files, only copies

- **Reporter:** `modules/reporter.py`
  - Purpose: Generate Excel (.xlsx) report with all extracted metadata
  - Uses openpyxl for formatting, pandas for tabular organization
  - Single entry point: `generate_report(output_dir)`

**Controller (Orchestration):**
- Location: `controller.py`
- Purpose: Orchestrates entire pipeline — calls modules in sequence for each file
- Pattern: Sequential extraction+anonymization, then parallel AI extraction via ThreadPoolExecutor (max_workers=5)
- Handles retries, progress callbacks (on_progress, on_file_done), error logging
- Returns dict with stats (total, done, errors, skipped, output_dir, report_path)

**Provider Abstraction Layer:**
- Location: `providers/` directory
- Purpose: Abstract LLM provider switching (ZAI, OpenRouter, Ollama)
- Contains:
  - `providers/base.py`: LLMProvider abstract interface
  - `providers/zai.py`: ZAI GLM-4.7 (primary, paid)
  - `providers/openrouter.py`: OpenRouter fallback (free models)
  - `providers/ollama.py`: Local llama-server (privacy-first)
- Factory functions: `get_provider(config)`, `get_fallback_provider(config)`

**Services Layer (services/ directory):**
- Location: `services/` directory
- Purpose: Domain-specific business logic beyond the pipeline
- Key services:
  - `client_manager.py`: Multi-client (multi-registry) tenant isolation
  - `lifecycle_service.py`: Document status management (manual overrides, deadline tracking)
  - `payment_service.py`: Payment schedule extraction and calendar events
  - `version_service.py`: Document versioning, diff generation, redline DOCX
  - `review_service.py`: Template-based contract review, QA matching
  - `llama_server.py`: Local LLM server process management (download, start, stop)
  - `telegram_sync.py`: Telegram bot integration for async status updates
  - `registry_service.py`: Client registry CRUD

**UI Layer (app/ directory):**
- Location: `app/` directory using NiceGUI
- Architecture: Single Page Application (SPA) with per-connection AppState

- **State Management:** `app/state.py`
  - AppState dataclass: Single source of truth for UI state
  - Stored in app.storage.client['state'] (per-connection, in-memory)
  - Fields: current_client, selected_doc_id, filter_type, filter_status, split_panel_doc_id, bulk_mode, etc.

- **Pages:** `app/pages/` directory
  - Each page is a NiceGUI sub_page() route
  - `registry.py` (~50KB): Main document registry with AG Grid table, filtering, sorting, bulk actions
  - `document.py` (~30KB): Document detail view with side panel, split view for versioning
  - `settings.py` (~18KB): Provider/API key configuration, threshold settings
  - `templates.py` (~20KB): Template management (QA standards, contract types)

- **Components:** `app/components/` directory
  - Reusable UI building blocks:
    - `header.py`: Persistent top navigation (client switcher, breadcrumbs, buttons)
    - `registry_table.py`: AG Grid data table with lazy loading, context menu, row actions
    - `split_panel.py`: Split-view container for document comparison (v0.7.1 overhaul)
    - `bulk_actions.py`: Bulk status change, delete, export to Excel
    - `process.py`: Processing component (folder picker, progress bar, real-time file updates)
    - `skeleton.py`: Loading skeleton for AG Grid
    - `onboarding/`: First-time user onboarding (splash, guided tour)

- **Styling:** `app/styles.py`
  - Centralized CSS classes and design tokens
  - Color palette (Indigo-600, Slate-500, etc.)
  - Button, segment, toggle styles

- **Main Entry:** `app/main.py`
  - NiceGUI entrypoint (D-08, D-09, D-10)
  - Initializes llama-server singleton via app.on_startup
  - Loads design system (font, CSS tokens, HTML)
  - Registers pages as sub_pages() for SPA navigation
  - Runs with native=True (desktop), dark=False, reload=False

**Desktop Integration:**
- Location: `desktop_app.py`
- Purpose: Wrapper for packaged .dmg (macOS) or .exe (Windows)
- Uses PyInstaller or native packaging for distribution

## Data Flow

**Processing Pipeline Flow:**

1. **User Input:** Folder selection (UI or Telegram) → Source directory path
2. **Scanning:** scan_directory() → list of FileInfo objects
3. **Deduplication:** Check file_hash against db.contracts.file_hash
4. **Sequential Processing (fast):**
   - extract_text(file_info) → ExtractedText
   - anonymize(text) → AnonymizedText (if not ollama)
5. **Parallel AI Processing (bottleneck):**
   - ThreadPoolExecutor.submit(extract_metadata, anonymized_text, provider)
   - Provider.complete(prompt) → JSON response
   - sanitize_metadata() → ContractMetadata
6. **Validation & Organization:**
   - validate_metadata(metadata) → ValidationResult
   - organize_file(file_info, output_dir, grouping) → copies to structure
   - db.save_result(ProcessingResult) → SQLite insert
7. **Reporting:**
   - generate_report(output_dir) → .xlsx with all metadata
8. **Callbacks:** on_progress(done, total, msg), on_file_done(result)

**UI Data Flow:**

1. User navigates to /registry → page loads AppState
2. UI queries db for all contracts → AgGrid.load_table_data()
3. User filters (type, status, search) → state.filter_* updated
4. User clicks row → navigate to /document/{doc_id}
5. Document page loads selected_doc_id from state
6. Split panel loads version children (expand/collapse versions)
7. User bulk-selects rows → state.selected_doc_ids updated
8. Bulk actions (status, export, delete) → write to db, refresh grid

**State Management:**

- **Persistent Settings:** ~/.yurteg/settings.json (active_provider, warning_days_threshold)
- **Per-Connection State:** app.storage.client['state'] (AppState dataclass)
- **Database:** yurteg.db (contracts, templates, versions, payments, schema_migrations)

## Key Abstractions

**FileInfo:**
- Purpose: Represent found file with metadata (path, filename, hash, size)
- Examples: `modules/models.py` line 9-15
- Pattern: Immutable dataclass passed through pipeline stages

**ProcessingResult:**
- Purpose: Envelope containing file → final output (text, metadata, validation, organized_path)
- Examples: `modules/models.py` line 116-128
- Pattern: Status machine (pending → processing → done/error) with optional error_message

**ContractMetadata:**
- Purpose: Structured extraction from document (type, counterparty, dates, amount, parties, special_conditions)
- Examples: `modules/models.py` line 36-55
- Pattern: Optional fields (null values), confidence scoring, is_template flag

**AppState:**
- Purpose: Single typed state container for entire UI
- Examples: `app/state.py` line 12-46
- Pattern: Dataclass with default_factory fields, per-connection isolation

**LLMProvider:**
- Purpose: Abstract interface for different LLM backends
- Examples: `providers/base.py` (abstract), `providers/zai.py`, `providers/openrouter.py`, `providers/ollama.py`
- Pattern: Pluggable implementations for ZAI, OpenRouter (cloud) and Ollama (local)

## Entry Points

**Desktop/Streamlit (main.py):**
- Location: `main.py`
- Triggers: User runs `streamlit run main.py` (Streamlit) or `python app/main.py` (NiceGUI)
- Responsibilities:
  - Loads config from .env and secrets
  - Initializes llama-server singleton if active_provider == "ollama"
  - Renders Streamlit/NiceGUI pages
  - Bridges UI callbacks to Controller.process_archive()

**Desktop App (desktop_app.py):**
- Location: `desktop_app.py`
- Triggers: User launches packaged .dmg or .exe
- Responsibilities: Python entrypoint for pyinstaller, calls main.py

**Services Entry (pipeline_service.py):**
- Location: `services/pipeline_service.py`
- Triggers: Telegram bot, CLI, tests (non-UI callers)
- Responsibilities: Unit entry point for processing — calls Controller without UI dependencies
- No streamlit import (intentional isolation)

## Error Handling

**Strategy:** Per-file error resilience — one file's failure doesn't stop processing others

**Patterns:**

1. **Text Extraction Failure:**
   - Result.status = "error"
   - Result.error_message = "Не удалось извлечь текст"
   - db.save_result(result) → persists error
   - Processing continues to next file

2. **AI Extraction Failure:**
   - Try primary provider → catch APIError/timeout
   - Fallback to secondary provider (if configured)
   - If both fail: return Metadata with all fields null, confidence=0.0

3. **Validation Failure:**
   - ValidationResult.status = "warning" (non-fatal) or "error" (critical)
   - Warnings logged but don't block organizing
   - Errors trigger db.save_result() with validation_status set

4. **Organization Failure:**
   - Rare (mostly FS permission errors)
   - organized_path = None, error logged
   - File still saved to db (result is complete)

5. **Database Errors:**
   - Thread-safe via sqlite3 built-in locking
   - Connection pool not needed (single-threaded writes in Controller._run_pipeline)
   - Backups created on schema migrations

## Cross-Cutting Concerns

**Logging:** Standard Python logging module
- Level INFO: Progress messages, file counts, provider selection
- Level WARNING: Oversized files, extraction failures, model download progress
- Level ERROR: API timeouts, DB corruption, unhandled exceptions
- Log format includes timestamps and module names

**Validation:** Multi-layer approach
- L1 (Basic): Required fields, data types
- L2 (Format): Date parsing (YYYY-MM-DD), amount currency, ФИО nominative case
- L3 (Pattern): Regex for phone, email, INN, KPP
- L4 (Semantic): Counterparty consistency, date_start ≤ date_end
- L5 (AI confidence): logprobs-based scoring, threshold = 0.8 (high) / 0.5 (low)

**Authentication:**
- API keys from environment (ZHIPU_API_KEY, OPENROUTER_API_KEY, etc.)
- Stored in .env (development) or Streamlit secrets (cloud)
- Never hardcoded, never logged

**Privacy:**
- Personal data masked via natasha NER before sending to cloud LLM
- Anonymized text only (~0.5KB) sent to API, original file never leaves machine
- Local Ollama mode: no API calls, all processing on-device

**Performance:**
- File scanning: O(n log n) sort by filename
- Text extraction: Sequential, parallelizable in future (GIL limitations)
- AI extraction: Parallel via ThreadPoolExecutor (main bottleneck, ~4 sec/file)
- DB queries: Indexed by file_hash, status, contract_type
- UI grid: Lazy loading (AG Grid virtual rows), search debounced 300ms

---

*Architecture analysis: 2026-03-25*
