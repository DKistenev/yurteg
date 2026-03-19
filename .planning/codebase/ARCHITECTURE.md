# Architecture

**Analysis Date:** 2026-03-19

## Pattern Overview

**Overall:** Sequential pipeline with parallel AI bottleneck

**Key Characteristics:**
- Modular architecture: each module is independent, communicates via dataclasses
- Three-stage processing: fast sequential (extract+anonymize) → parallel AI (bottleneck) → fast sequential (validate+organize)
- Resumable: SQLite tracks processed files by hash; can re-run archive and skip already-done files
- Defensive error handling: single-file failure does not stop pipeline
- No frameworks: core logic uses only standard library + minimal dependencies (pdfplumber, python-docx, natasha)

## Layers

**UI Layer (Streamlit):**
- Purpose: User interface, folder selection, progress tracking, parameter configuration, results browsing
- Location: `main.py`
- Contains: Streamlit components, state management, visualization (charts via Altair)
- Depends on: Controller, Config, Models
- Used by: End user

**Controller Layer:**
- Purpose: Orchestrates the entire pipeline; manages state, parallelization, resumability
- Location: `controller.py`
- Contains: `Controller` class with `process_archive()` and `_run_pipeline()` methods
- Depends on: All modules, Config, Models
- Used by: main.py

**Processing Modules (core logic):**
- Purpose: Individual transformation steps in the pipeline
- Location: `modules/` directory
- Contains: scanner, extractor, anonymizer, ai_extractor, validator, database, organizer, reporter
- Each module: single responsibility, pure functions (except database)
- Depends on: Models, Config, external libraries

**Data Models:**
- Purpose: Shared data structures for inter-module communication
- Location: `modules/models.py`
- Contains: dataclasses for FileInfo, ExtractedText, AnonymizedText, ContractMetadata, ValidationResult, ProcessingResult
- Used by: All modules

**Configuration:**
- Purpose: Centralized settings (AI endpoints, validation thresholds, output naming)
- Location: `config.py`
- Contains: `Config` dataclass with all hardcoded defaults
- Used by: main.py, controller, all modules

## Data Flow

**Complete Processing Pipeline:**

1. **Scanning** (`modules/scanner.py`)
   - Input: source directory path
   - Processing: rglob for PDF/DOCX files, compute SHA-256 hash per file, filter by size/extension
   - Output: List of `FileInfo` objects (sorted alphabetically)

2. **Text Extraction** (`modules/extractor.py`)
   - Input: `FileInfo`
   - Processing:
     - PDF: pdfplumber → page-by-page extraction → joined with `\n\n`
     - DOCX: python-docx → paragraphs + table cells
     - .doc: tries .docx sibling, fallback to HTML parsing (common for web-sourced files)
   - Output: `ExtractedText` (text, page_count, is_scanned flag, extraction_method)
   - Error handling: returns `ExtractedText` with extraction_method="failed", no exception

3. **Anonymization** (`modules/anonymizer.py`)
   - Input: `ExtractedText`
   - Processing:
     - Natasha NER for entity extraction (ФИО, ТЕЛЕФОН, EMAIL, etc.)
     - Regex patterns for structured data (ИНН, СНИЛС, СЧЁТ, паспорт)
     - Replace entities with typed masks ([ФИО_1], [ТЕЛЕФОН_2], etc.)
   - Output: `AnonymizedText` (masked text, replacements dict, entity counts)
   - Note: anonymized text is NOT persisted to disk; masks aid AI context

4. **AI Metadata Extraction** (`modules/ai_extractor.py`)
   - Input: `AnonymizedText`
   - Processing (parallel via ThreadPoolExecutor, up to 5 concurrent):
     - Send anonymized text to LLM (ZAI GLM-4.7 primary, OpenRouter fallback)
     - Parse JSON response for contract metadata
     - On parse error or confidence < low_threshold: fallback prompt with basic extraction
   - Output: `ContractMetadata` (contract_type, counterparty, subject, dates, amount, parties, confidence, is_template)
   - Timeout & retry: max 2 retries, rate limit handling via APIError/RateLimitError

5. **Metadata Validation** (`modules/validator.py`)
   - Input: `ContractMetadata`
   - Processing: 4 levels
     - L1: structural (required fields, date format YYYY-MM-DD)
     - L2: logical (date sanity, amount anomalies, start > end)
     - L3: AI confidence thresholds (based on config.confidence_high/low)
     - L4 (batch-level): duplicate detection (counterparty + date + amount), outliers
   - Output: `ValidationResult` (status="ok"|"warning"|"unreliable"|"error", warnings[], score)

6. **File Organization** (`modules/organizer.py`)
   - Input: `ProcessingResult` (with metadata)
   - Processing:
     - Determine output path based on grouping mode:
       - "type": `Документы/{contract_type}/{filename}`
       - "counterparty": `Документы/{counterparty}/{filename}`
       - "both": `Документы/{contract_type}/{counterparty}/{filename}`
     - Sanitize folder/file names (remove invalid chars, max length 80)
     - Copy file (shutil.copy2, preserves metadata)
     - Handle conflicts (add _1, _2 suffix)
   - Output: `organized_path` (Path to copied file)
   - Important: files are COPIED, never moved/deleted from source

7. **Database Persistence** (`modules/database.py`)
   - Input: `ProcessingResult` (after all transformations)
   - Processing:
     - SQLite INSERT OR REPLACE (upsert by file_hash)
     - Serialize lists (special_conditions, parties) to JSON
     - Track processed_at timestamp
   - Output: yurteg.db in output directory
   - Enables: resumability (query `is_processed(file_hash)`)

8. **Report Generation** (`modules/reporter.py`)
   - Input: all results from database
   - Processing:
     - Create DataFrame from contracts table
     - Pivot special_conditions & parties lists → comma-separated strings
     - Generate Excel with sheets: "Реестр договоров" (all), "Требуют проверки" (warnings), "Сводка" (charts)
     - Add auto-filters, conditional formatting (color by validation status), validation comments
   - Output: Реестр_договоров.xlsx

**State Management:**

- **In-memory during processing:** `ProcessingResult` objects accumulate in controller.results list
- **Persistent:** SQLite database (yurteg.db) in output directory
- **Resumability:** on next run, controller queries `db.is_processed(file_hash)` and skips already-done files
- **Force reprocess:** `db.clear_all()` if `force_reprocess=True`

## Key Abstractions

**ProcessingResult:**
- Purpose: Complete record of one file's transformation through the entire pipeline
- Fields: file_info, text, anonymized, metadata, validation, organized_path, status, error_message, model_used, processed_at
- Pattern: passed between modules, accumulated in controller.results, saved to DB

**ContractMetadata:**
- Purpose: Extracted structured information from document
- Fields: contract_type, counterparty, subject, date_signed, date_start, date_end, amount, special_conditions[], parties[], confidence, is_template
- Pattern: AI-generated, validated, used for file organization

**ValidationResult:**
- Purpose: Quality assessment of extracted metadata
- Fields: status, warnings[], score
- Pattern: populated by L1-L3 validation, extended by L4 batch validation

**Config:**
- Purpose: Single source of truth for all settings
- Fields: AI endpoints/models/retries, validation thresholds, supported extensions, anonymization types, document type hints, output folder naming
- Pattern: passed to constructor, read-only throughout processing

## Entry Points

**Main Entry:** `main.py`
- Location: `main.py`
- Triggers: `streamlit run main.py`
- Responsibilities:
  - Streamlit UI setup (page config, custom CSS, sidebar)
  - Environment variable loading (local .env and cloud secrets)
  - Folder selection dialog (tkinter fallback for desktop)
  - Parameter configuration (grouping, API key, anonymization types)
  - Progress tracking (callbacks to UI)
  - Results browsing (tabs for validation issues, filtered tables, charts)

**Controller Entry:** `controller.process_archive()`
- Called by: main.py event handler
- Parameters: source_dir, grouping, force_reprocess, callbacks (on_progress, on_file_done)
- Returns: dict with stats (total, done, errors, skipped, output_dir, report_path)

## Error Handling

**Strategy:** Defensive — single-file failure does not cascade

**Patterns:**

1. **Text Extraction Errors:**
   - All exceptions caught, logged as WARNING/ERROR
   - Returns `ExtractedText` with extraction_method="failed", empty text
   - File marked as "error" status, continues to next file

2. **AI Request Errors:**
   - APIError, RateLimitError, APITimeoutError caught
   - Retried up to ai_max_retries times
   - On failure: fallback prompt with basic extraction
   - If fallback also fails: empty metadata, status="error"

3. **Validation Failures:**
   - Warnings collected, never exceptions
   - File continues to organization/DB even with low confidence

4. **File Organization Errors:**
   - PermissionError on write → raises to UI with message
   - Disk space check before starting (required_size = 2x source size)
   - Filename conflicts resolved with auto-incrementing suffix

5. **Database Errors:**
   - Thread-safe via `_lock` (threading.Lock)
   - Upsert pattern prevents duplicate key violations

**Logging:**
- Standard logging module, level INFO (progress), WARNING (skipped files), ERROR (failures)
- Logged to console (Streamlit captures to UI)

## Cross-Cutting Concerns

**Logging:**
- Standard `import logging` in each module
- Logger name: `__name__` (module-specific)
- Levels: INFO for milestones, WARNING for skipped/malformed, ERROR for failures
- No structured logging framework; plain messages

**Validation:**
- Metadata validated in `modules/validator.py`, not pushed into earlier stages
- L1-L3 validation per-file, L4 batch validation on full results list
- Validation is non-blocking; all files processed regardless of score

**Authentication:**
- API keys: environment variables (os.environ) or Streamlit secrets
- ZAI_API_KEY, OPENROUTER_API_KEY, ZHIPU_API_KEY
- Verified via `verify_api_key()` before processing starts
- No token refresh; single call per session

**Anonymization:**
- Selective: controlled by config.anonymize_types (None = all types)
- UI allows user to toggle types (ENTITY_TYPES enum)
- Not persisted to disk; used only to improve AI context
- Replacements kept in memory within AnonymizedText object only

---

*Architecture analysis: 2026-03-19*
