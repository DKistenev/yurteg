# Codebase Concerns

**Analysis Date:** 2026-03-19

## Tech Debt

**Monolithic main.py:**
- Issue: UI layer contains 1,402 lines with complex logic interleaved with Streamlit components. Contains filtering logic, dataframe manipulation, PDF operations, and subprocess calls mixed throughout.
- Files: `main.py`
- Impact: Difficult to test, modify, and maintain. High cognitive load. UI logic tightly coupled to presentation.
- Fix approach: Extract UI event handlers and data processing into separate controller classes. Separate concerns: state management, data filtering, presentation. Consider breaking into multiple pages using Streamlit's multi-page app feature.

**Hardcoded prompts in code:**
- Issue: SYSTEM_PROMPT and USER_PROMPT_TEMPLATE are defined inline in `modules/ai_extractor.py` (lines span entire file). Any prompt iteration requires code changes and testing.
- Files: `modules/ai_extractor.py`
- Impact: Prompt engineering workflow is coupled to code deployment. Changes to prompts require careful handling to avoid breaking existing parsing logic.
- Fix approach: Move prompts to a separate YAML/JSON configuration file. Implement prompt versioning and A/B testing framework.

**SQL schema embedded in module:**
- Issue: Database schema (_SCHEMA) is a raw SQL string in `modules/database.py`, migrations handled as ad-hoc try/except blocks.
- Files: `modules/database.py` (line 17–44)
- Impact: Schema changes are error-prone. No way to track migration history or rollback. Column migrations are silent (catch OperationalError).
- Fix approach: Implement proper migration system (e.g., Alembic). Version schema changes explicitly. Log all migrations.

**Magic numbers throughout codebase:**
- Issue: Confidence thresholds (0.8, 0.5), max file size (50 MB), max workers (5), token limits (2000) scattered across code.
- Files: `config.py`, `controller.py`, `modules/ai_extractor.py`, `modules/validator.py`
- Impact: Hard to tune system behavior. No single source of truth for tuning parameters.
- Fix approach: Centralize in `config.py` or create separate `tuning.yaml`. Already partially done in config.py but some values still hardcoded in modules.

---

## Known Bugs

**Scanned PDF detection unreliable:**
- Symptoms: PDFs with low average character count per page (< 50 chars) are marked as scanned, but some legitimate documents with sparse formatting may be incorrectly flagged.
- Files: `modules/extractor.py` (lines 46–55)
- Trigger: Process a text-based PDF with lots of whitespace or tables
- Workaround: Manually verify scanned PDFs. Consider visual inspection API.

**AI response parsing fragile:**
- Symptoms: If LLM returns malformed JSON with extra text, missing fields, or nested structures, parsing fails silently and falls back to error state. No structured error details on why parsing failed.
- Files: `modules/ai_extractor.py` (lines 445–467)
- Trigger: Model returns JSON with trailing text, comments, or extra whitespace
- Workaround: Pre-process response with regex to extract JSON block. Add debug logging of raw response.

**Database upsert race condition:**
- Symptoms: Threading.Lock in `Database` class protects save_result but `is_processed` check is not atomic. Two threads could both pass the check and both save same file.
- Files: `modules/database.py` (lines 79–95)
- Trigger: Process same source_dir with high max_workers and force_reprocess=False
- Workaround: Use database-level locking (PRAGMA busy_timeout) or implement file-level locks.

**Missing validation_score handling:**
- Symptoms: `validation_score` (ValidationResult.score) is calculated but never used for filtering/sorting in UI. Only validation_status is exposed.
- Files: `modules/validator.py` (line 40–44 sets score), `main.py` (never referenced)
- Trigger: User expects to filter by quality score, but only categorical status available
- Workaround: Add score column to Excel report; add score-based filtering UI.

**Anonymized text not stored, can't be recovered:**
- Symptoms: Anonymized text is calculated during processing but not persisted to database. If a user needs to see the anonymized version later, it's lost.
- Files: `controller.py` (line 128: result.anonymized set but never saved), `modules/database.py` (no anonymized_text column)
- Impact: Reproducibility breaks if user wants to verify what was sent to AI. Audit trail incomplete.
- Workaround: Store anonymized text hash or compressed text in database for audit purposes.

---

## Security Considerations

**Environment variable handling:**
- Risk: API keys (ZHIPU_API_KEY, OPENROUTER_API_KEY) loaded from .env file (not committed). If .env is leaked, all keys compromised. No key rotation mechanism.
- Files: `main.py` (lines 28–30), `config.py`
- Current mitigation: .env in .gitignore. Secrets loaded from st.secrets in cloud mode.
- Recommendations: (1) Implement key rotation API. (2) Use short-lived tokens. (3) Add audit logging of API key access. (4) Vault integration for production.

**SQL injection via user input:**
- Risk: Database queries use parameterized queries (good), but user-provided directory names and contract types are used in filesystem operations without validation.
- Files: `modules/organizer.py` (line 26: _sanitize_name is basic), `controller.py`
- Current mitigation: _sanitize_name removes dangerous characters, but max_length truncation could hide issues.
- Recommendations: (1) Validate all filesystem paths are within output_dir. (2) Use Path.resolve() to prevent path traversal. (3) Whitelist allowed characters in names.

**No input validation on file uploads:**
- Risk: Accepts any file with .pdf/.docx extension. No magic number checking. Could process malicious files.
- Files: `modules/scanner.py` (line 14–20 checks extension only), `modules/extractor.py`
- Current mitigation: Extension check. File size limit (50 MB).
- Recommendations: (1) Validate file magic numbers (PDF header, DOCX zip structure). (2) Use file type detection library (python-magic). (3) Implement sandboxing for untrusted PDFs.

**Anonymized data leakage risk:**
- Risk: Anonymized text sent to third-party LLMs (ZAI, OpenRouter). Even with masking, document structure and metadata may reveal PII.
- Files: `modules/ai_extractor.py` (sends text to external API)
- Current mitigation: Natasha NER + regex masking of direct PII. No PII in metadata prompts.
- Recommendations: (1) Add option to process locally (no external API). (2) Hash sensitive fields before sending. (3) Implement differential privacy. (4) Add legal banner about third-party processing.

**No authentication/authorization:**
- Risk: Desktop app and Streamlit Cloud app have no user authentication. Anyone with access can process all documents.
- Files: `main.py`, `desktop_app.py`
- Current mitigation: None.
- Recommendations: (1) Add user login for Streamlit Cloud. (2) Implement role-based access (viewer, processor, approver). (3) Audit log all operations.

---

## Performance Bottlenecks

**AI API call is serialized bottleneck (~4 sec/file):**
- Problem: ThreadPoolExecutor in `controller.py` parallelizes AI calls, but batch_size=1 and max_workers=5 limits throughput. Each file waits for full LLM round-trip.
- Files: `controller.py` (lines 176–187), `config.py` (line 28: max_workers=5)
- Cause: No request batching. No caching of similar documents. LLM latency dominates total time.
- Improvement path: (1) Implement batch API calls if provider supports. (2) Cache responses for identical inputs. (3) Use faster model for preprocessing (Haiku instead of GLM-4.7).

**Full-text extraction for large PDFs:**
- Problem: pdfplumber extracts ALL pages every time, even if document is short. No early stopping.
- Files: `modules/extractor.py` (lines 42–54)
- Cause: No page limit. No content-based early stopping.
- Improvement path: (1) Extract first N pages only for initial analysis. (2) Add progressive extraction callback. (3) Use streaming API if available.

**Natasha NER on full document text:**
- Problem: NER processes entire document (potentially 10K+ tokens). Expensive operation called sequentially for each file.
- Files: `modules/anonymizer.py` (lines 107–125)
- Cause: No text truncation or chunking. No caching of NER models.
- Improvement path: (1) Cache loaded models at module level (already done with _segmenter, _ner_tagger). (2) Process text in chunks. (3) Use lightweight NER for preprocessing.

**No query caching in database:**
- Problem: `db.get_all_results()` called every time UI is refreshed, reading entire contracts table.
- Files: `modules/database.py` (line 131–154)
- Cause: No caching. Streamlit reruns entire session on every interaction.
- Improvement path: Use Streamlit @st.cache_data on get_all_results. Invalidate cache only on save_result.

**DataFrame filtering in memory:**
- Problem: All filters applied to DataFrame in main.py (date range, amount, counterparty) after loading all records. No database-level filtering.
- Files: `main.py` (lines ~1200–1300)
- Cause: Data loaded then filtered in Python. No SQL WHERE clause.
- Improvement path: (1) Push filters to database queries. (2) Add database indexes on counterparty, contract_type, date_signed. (3) Implement pagination.

---

## Fragile Areas

**Anonymizer NER entity detection:**
- Files: `modules/anonymizer.py` (lines 100–175)
- Why fragile: Three-pass NER strategy (original text, normalized, OCR spaced) is complex and overlapping. Order of passes matters. If Natasha models are updated, behavior may change. Regex patterns for phone/email are locale-specific (Russian).
- Safe modification: (1) Add comprehensive tests for each entity type. (2) Document the three-pass strategy. (3) Consider alternative NER library. (4) Validate regex patterns against real documents.
- Test coverage: regex patterns tested informally, NER passes untested.

**Validator threshold logic:**
- Files: `modules/validator.py` (lines 26–70)
- Why fragile: Confidence thresholds hardcoded. Warnings accumulate in score calculation. Status depends on L1 > L2 > L3 order. If rules change, score calculation breaks. No way to disable specific rules.
- Safe modification: (1) Make thresholds configurable per rule. (2) Separate warning accumulation from status determination. (3) Implement rule registry with enable/disable flags.
- Test coverage: Some unit tests exist but threshold edge cases not fully covered.

**AI model fallback logic:**
- Files: `modules/ai_extractor.py` (lines 215–246)
- Why fragile: Three-tiered fallback (main model → fallback prompt → fallback model) with retries. If one API is down, switches to another. Order and retry counts intertwined. Hard to reason about which model will be used.
- Safe modification: (1) Add explicit model selection strategy (round-robin, least-recently-used). (2) Log which model was used. (3) Add metrics for fallback frequency. (4) Consider circuit breaker pattern.
- Test coverage: Happy path tested, failure scenarios not fully covered.

**Database schema migrations:**
- Files: `modules/database.py` (lines 65–73)
- Why fragile: Column additions caught with try/except, silently skipped if column exists. No way to track which migrations ran. Adding new required columns could cause data inconsistency.
- Safe modification: (1) Implement explicit migration tracking table. (2) Version schema. (3) Add migration validation (verify column exists and type is correct). (4) Log all migrations.
- Test coverage: No migration tests.

---

## Scaling Limits

**Concurrent file processing:**
- Current capacity: max_workers=5 threads. Total throughput ~1.25 files/sec (if 4 sec/file). For 1000 files, processing takes ~800 sec.
- Limit: ThreadPoolExecutor limited to OS-level thread pool. GIL limits true parallelism. API rate limits (ZAI, OpenRouter) unknown.
- Scaling path: (1) Switch to async/await with asyncio. (2) Use process pool for CPU-bound tasks (NER). (3) Implement queue-based architecture (Celery/RabbitMQ). (4) Add API request rate limiter.

**Database size:**
- Current capacity: SQLite with single contracts table. No indices on queries except file_hash and status. Each row ~500 bytes + JSON fields.
- Limit: SQLite degrades at ~100K records. Concurrent writes block. No replication.
- Scaling path: (1) Migrate to PostgreSQL for concurrent access. (2) Add indices on frequently queried columns. (3) Implement partitioning by date. (4) Archive old records.

**File system organization:**
- Current capacity: Nested directory structure (type/counterparty/file) can create deep paths that exceed OS limits.
- Limit: Windows path length limit 260 characters. Deeply nested structures break.
- Scaling path: (1) Cap directory depth or use hashing. (2) Use symbolic links for common paths. (3) Implement flat storage with metadata index.

**Memory usage:**
- Current capacity: Full anonymized text kept in memory for each file during processing. Large documents (100K characters) × 5 workers = 500K characters in RAM.
- Limit: Streaming large archives (1000+ files) could exhaust memory.
- Scaling path: (1) Stream text processing without keeping full content. (2) Implement memory-mapped file handling. (3) Process in batches with explicit cleanup.

---

## Dependencies at Risk

**pdfplumber >= 0.10.0:**
- Risk: Unmaintained or infrequent updates. Alternative: pypdf, pikepdf. pdfplumber relies on external pdfminer, version mismatches possible.
- Impact: Security vulnerabilities in PDF parsing. Incompatibility with newer Python versions.
- Migration plan: (1) Evaluate pymupdf (fitz) as faster alternative. (2) Implement plugin architecture to swap extractors. (3) Add tests for all major PDF formats.

**natasha >= 1.6.0 (Russian NER):**
- Risk: Natasha is heavily specialized for Russian. No active development in 2024. Models may drift from modern Russian text patterns.
- Impact: NER accuracy degrades for modern slang, legal jargon, English names in Russian text.
- Migration plan: (1) Consider RuBERT-based models. (2) Implement custom legal NER fine-tuned on contracts. (3) Add feedback loop to improve entity detection.

**setuptools < 81:**
- Risk: Pinned to specific version due to pymorphy2 dependency. Breaks compatibility with newer pip/setuptools. Security vulnerabilities in old setuptools unpatched.
- Impact: Installation fails on modern Python environments. pip resolver becomes fragile.
- Migration plan: (1) Upgrade pymorphy2 or replace with modern alternative. (2) Re-run dependency resolution. (3) Switch to modern package management (poetry, uv).

**openai >= 1.30.0:**
- Risk: OpenAI SDK breaking changes possible in major versions. Current code assumes specific API response structure.
- Impact: Upgrade to v2.x could require code refactoring. Rate limit handling may change.
- Migration plan: (1) Pin to major version (^1.30.0). (2) Implement version compatibility layer. (3) Add tests against multiple SDK versions.

**streamlit >= 1.30.0:**
- Risk: Streamlit evolves rapidly. Session state API changed multiple times. Cache decorators changed. CSS styling breaks with updates.
- Impact: UI may break with Streamlit updates. Custom CSS selectors may fail.
- Migration plan: (1) Use version pinning for stability. (2) Test against latest Streamlit on each update. (3) Consider migrating to Gradio or FastAPI for more stable API.

---

## Missing Critical Features

**No OCR support:**
- Problem: Scanned PDFs rejected entirely. ~5-10% of user documents likely require OCR.
- Blocks: Can't process document archives with scanned contracts. Limits business use case.
- Recommendations: (1) Integrate Tesseract OCR or cloud vision API. (2) Add async OCR queue. (3) Allow manual text input for unfathomable files.

**No document change tracking:**
- Problem: If user edits a document in Excel and re-uploads, no way to detect changes. Processed flag prevents reprocessing.
- Blocks: Workflow requires delete + reprocess, which is cumbersome.
- Recommendations: (1) Implement versioning (track all versions of each file). (2) Add change detection (diff original vs. new metadata). (3) Allow selective reprocessing.

**No batch API integration:**
- Problem: Processing sends one request per file. If AI provider has batch API (cheaper, slower), not utilized.
- Blocks: Can't optimize for cost on large archives.
- Recommendations: (1) Implement batch API client. (2) Add batch mode to config. (3) Queue batches for overnight processing.

**No model fine-tuning support:**
- Problem: Uses generic LLM prompts. Contract types and extraction logic not customized per customer.
- Blocks: Can't improve accuracy for specific contract styles. Cross-industry accuracy low.
- Recommendations: (1) Implement few-shot learning (examples in prompt). (2) Add fine-tuning pipeline for customer-specific models. (3) Create contract type-specific prompts.

---

## Test Coverage Gaps

**No integration tests for full pipeline:**
- What's not tested: End-to-end processing (file → extract → anonymize → AI → validate → organize → report). Only unit tests for individual modules.
- Files: `tests/` directory exists but lacks full-pipeline tests
- Risk: Breaking changes in module interfaces may not be caught. Interactions between modules untested.
- Priority: High

**Anonymizer regex patterns untested:**
- What's not tested: Actual phone numbers, emails, IPs, bank accounts against real-world variations. Test data minimal.
- Files: `modules/anonymizer.py` (PATTERNS dict, lines 42–71)
- Risk: Legitimate data masked, PII leaked due to pattern mismatches.
- Priority: High

**AI prompt edge cases:**
- What's not tested: Prompts tested with synthetic documents, not real legal contracts. Template detection, multilingual documents, corrupted text.
- Files: `modules/ai_extractor.py` (SYSTEM_PROMPT, USER_PROMPT_TEMPLATE)
- Risk: Prompt injection attacks, unexpected JSON formats, hallucinated data.
- Priority: High

**Database migrations:**
- What's not tested: Column additions, schema changes, data migration correctness. Only schema creation tested.
- Files: `modules/database.py`
- Risk: Schema mismatch after upgrade. Data loss.
- Priority: Medium

**Performance regressions:**
- What's not tested: Benchmark suite for processing time, memory usage. No baseline metrics.
- Files: `controller.py`, `modules/extractor.py`, `modules/anonymizer.py`
- Risk: Performance degradation undetected. User experience decays over time.
- Priority: Medium

**Error recovery:**
- What's not tested: Partial failure scenarios. API down mid-processing. Disk full. Permission denied. Recovery from interrupted runs.
- Files: `controller.py`, `modules/database.py`
- Risk: Processing state inconsistent after failures. Restart unclear.
- Priority: Medium

---

*Concerns audit: 2026-03-19*
