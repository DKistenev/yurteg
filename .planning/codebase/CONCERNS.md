# Codebase Concerns

**Analysis Date:** 2026-03-25

## Tech Debt

**AG Grid column sizing:**
- Issue: AG Grid columns require manual sizing configuration. Column widths not optimal for all data sizes.
- Files: `app/components/registry_table.py`, `app/pages/registry.py`
- Impact: Columns may be too narrow for long text, causing text truncation or wrapping issues. Requires timer-based `sizeColumnsToFit()` workaround.
- Fix approach: Implement dynamic column sizing based on content width. Consider using `autoSizeColumns()` with proper min/max width constraints. Test with typical Russian legal document metadata.

**Confidence score handling:**
- Issue: Model currently tries to output `confidence` field, but it's unreliable. Workaround: calculate from `logprobs` via llama-server instead.
- Files: `modules/ai_extractor.py`, `services/llama_server.py`
- Impact: Confidence scores may be inaccurate or missing. UI shows placeholder values.
- Fix approach: Remove `confidence` from AI model output. Compute via logprobs post-processing in `modules/postprocessor.py`. Add field profile for confidence calculation.

**0.5B model reliability gap:**
- Issue: Qwen 0.5B distilled model produces crashes on ~30% of documents (19/60 in benchmarks). Code-switching and JSON malformation issues persist despite SFT+GKD training.
- Files: `services/llama_server.py`, `modules/ai_extractor.py`
- Impact: Fallback to 0.5B model on production would drop quality from 97% to 68%. Not production-ready.
- Fix approach: Keep 1.5B Q4_K_M as primary production model. 0.5B remains emergency fallback only. Further training would require larger dataset or different architecture.

**UI visual layer incomplete:**
- Issue: UI evaluated at 2.5/5. Large empty white spaces, insufficient visual structure, minimal color usage, no visual hierarchy.
- Files: `app/styles.py`, `app/pages/registry.py`, `app/pages/templates.py`, `app/components/header.py`
- Impact: Users find interface confusing and uninviting. Empty registry shows no guidance. Stats bar and footer minimal.
- Fix approach: Apply 12 point visual refresh plan: warm background (#faf8f5), visible card styling (shadow-sm, border, rounded corners), accent buttons, rich empty state with 3 capability cards, header polish, typographic scaling.

## Known Bugs

**Duplicate status CSS:**
- Symptoms: Status badge styling duplicated in Tailwind @apply and in main.py CSS. Inconsistent rendering.
- Files: `app/main.py` (CSS inline), `app/static/design-system.css`
- Trigger: Browser dev tools show status styles loaded twice
- Workaround: None currently. Delete Tailwind-based styles from main.py, consolidate in design-system.css (single source of truth).

**AG Grid null data rendering:**
- Symptoms: When data contains null values in text fields, AG Grid renders "null" as string instead of empty cell.
- Files: `app/components/registry_table.py` line ~130-160
- Trigger: Contracts with missing counterparty, subject, or amount fields
- Workaround: Post-process row data to replace null values with empty strings before grid render

**Tour component crash on HTML toggle:**
- Symptoms: Tour component crashes if HTML is loaded after JS event listeners attached.
- Files: `app/components/onboarding/tour.py`
- Trigger: First-time user viewing tour after HTML injection
- Workaround: HTML and JS now separated in main.py (lines 91-96 vs 108-111). Prevents event listener race condition.

**SPA calendar navigation returns 404:**
- Symptoms: Calendar date picker uses URL navigation which breaks sub_pages routing.
- Files: `app/components/registry_table.py`, `app/static/calendar.js`
- Trigger: Clicking date on calendar redirects to /calendar instead of staying on /
- Workaround: FullCalendar CDN lazy-loaded on demand (not eager). Calendar.js uses manual tooltip instead of full calendar library. See registry.py calendar implementation.

## Security Considerations

**API key exposure:**
- Risk: AI provider API keys (ZAI, OpenRouter) stored in config or environment. Could be leaked if app crashes or logs unfiltered.
- Files: `config.py`, `modules/ai_extractor.py`
- Current mitigation: Keys sourced from environment variables only. No hardcoded defaults. Llama-server (local model) used by default to avoid API exposure.
- Recommendations: Add request/response sanitization in ai_extractor.py to remove keys from error logs. Implement secret masking in logging.

**Local file path exposure:**
- Risk: File paths from users' local systems appear in logs and database records. Could leak user's directory structure.
- Files: `modules/scanner.py`, `modules/database.py`, `controller.py`
- Current mitigation: Paths stored as relative after initial scan. Anonymized text never persisted to disk.
- Recommendations: Sanitize file paths in user-facing error messages. Remove user's home directory from logs.

**Database access control:**
- Risk: SQLite database on user's machine is unencrypted. No authentication for local connections.
- Files: `modules/database.py`
- Current mitigation: App is desktop-only (native=True). Database only accessible from local process.
- Recommendations: Sufficient for MVP. Add encryption if cloud sync is implemented later.

## Performance Bottlenecks

**AI extraction latency:**
- Problem: Each document takes ~4 seconds for metadata extraction (via ollama or API). 500 documents = ~33 minutes.
- Files: `modules/ai_extractor.py`, `services/llama_server.py`
- Cause: Single-threaded sequential AI requests. ThreadPoolExecutor with max_workers=5 only parallelizes, doesn't optimize per-request latency.
- Improvement path: (1) Batch API requests (if provider supports). (2) Speculative decoding (tested but no gain). (3) Quantization (already at Q4_K_M optimal). (4) Accept 18-20s/doc as baseline for 1.5B model.

**Text extraction from scanned PDFs:**
- Problem: OCR-extracted documents use fallback extraction method (~0.5s per page, slow for 100+ page contracts).
- Files: `modules/extractor.py`
- Cause: pdfplumber cannot extract from image-only PDFs. Fallback uses placeholder extraction.
- Improvement path: Integrate lightweight OCR (pytesseract or easyocr). Trade-off: +5-15s per scanned document but improves accuracy. Not yet implemented.

**AG Grid re-rendering on data update:**
- Problem: Registry table flickers when filtering or sorting large datasets (500+ contracts).
- Files: `app/pages/registry.py`
- Cause: Full table redraw on state change instead of incremental updates.
- Improvement path: Implement ag-grid-vue or React wrapper with proper state management. Current Nicegui+ag-grid integration lacks delta updates.

**Search query latency:**
- Problem: Full-text search with rapidfuzz on 1000+ documents causes 200-300ms UI lag.
- Files: `app/pages/registry.py` (search debounce at 300ms)
- Cause: Fuzzy matching runs on main thread.
- Improvement path: Implement background worker thread for search. Pre-compute searchable index on document load.

## Fragile Areas

**LLM server lifecycle management:**
- Files: `app/main.py` (lines 31-68), `services/llama_server.py`
- Why fragile: Triple shutdown guard (on_shutdown, on_disconnect, atexit) required because NiceGUI on macOS native mode is unreliable. Server may hang or not stop cleanly.
- Safe modification: (1) Test all shutdown paths individually. (2) Add timeout to server.stop() call. (3) Monitor for zombie llama-server processes. (4) Log all shutdown events for debugging.
- Test coverage: Covered in test_lifecycle.py (151 lines). Gaps: macOS-specific crashes not fully reproduced.

**AI metadata extraction error recovery:**
- Files: `modules/ai_extractor.py` (lines 312-430), `controller.py` (lines 120-180)
- Why fragile: Multiple fallback providers (ollama → ZAI → OpenRouter) with different error handling. Timeout, rate limit, and connection errors each handled differently. Chain can fail at any link.
- Safe modification: (1) Test each provider independently. (2) Add circuit breaker pattern. (3) Log provider switch events. (4) Add user notification on provider downgrade.
- Test coverage: test_providers.py (83 lines) covers provider selection. Gaps: fallback chain not fully tested.

**Post-processing confidence and field validation:**
- Files: `modules/postprocessor.py` (189 lines), `modules/validator.py` (402 lines)
- Why fragile: Confidence calculation moved from AI model to logprobs post-processing. Field profiles for cyrillic_only, number, date handle type coercion. Bugs in post-processor can corrupt valid metadata.
- Safe modification: (1) Add roundtrip tests: raw AI output → post-processor → validator → verified output. (2) Catch ValueError/TypeError in post-processor, log and skip field. (3) Test with 100+ real document samples before deployment.
- Test coverage: test_postprocessing.py exists in dataset/, not in tests/. Gaps: No unit tests in main test suite for field profiles.

**Database schema consistency:**
- Files: `modules/database.py` (425 lines)
- Why fragile: Schema includes contract table with 30+ columns for dynamic metadata. No migrations framework. Manual schema updates risk data loss.
- Safe modification: (1) Never ALTER TABLE on production database. (2) Add migration framework (alembic or SQLAlchemy Migrate). (3) Version schema. (4) Backup before schema changes.
- Test coverage: test_migrations.py (103 lines) covers basic schema checks. Gaps: No rollback testing, no large dataset migration testing.

## Scaling Limits

**Parallel AI request workers:**
- Current capacity: max_workers=5 (config.py line 36). 500 documents = ~40 requests in flight at peak.
- Limit: ThreadPoolExecutor with 5 threads may exhaust system resources or hit API rate limits.
- Scaling path: (1) Profile CPU/memory with 10+ workers. (2) Implement adaptive worker scaling based on provider latency. (3) Add rate limiter per provider (ZAI: 100 req/s, OpenRouter: 50 req/s).

**Local SQLite database:**
- Current capacity: ~10,000 contracts before performance degrades (indexes on file_hash, status, contract_type).
- Limit: SQLite single-writer limitation. Concurrent writes from multiple workers cause locking.
- Scaling path: (1) For >10K documents, migrate to PostgreSQL. (2) Implement write batching in Database class. (3) Add database WAL mode for better concurrency.

**LLM server memory:**
- Current capacity: 1.5B model at Q4_K_M = ~1GB RAM. Single instance on typical laptop (8-16GB).
- Limit: 3 concurrent llama-server instances would require 3GB RAM.
- Scaling path: (1) Deploy to separate server if scaling beyond single machine. (2) Use model quantization (IQ3_M, IQ2_M) for lower-end hardware. (3) Batch requests to reduce server startup overhead.

**UI state synchronization:**
- Current capacity: AppState dataclass holds per-connection state. Works for single user.
- Limit: No distributed state management. Cannot sync across multiple windows or devices.
- Scaling path: Future consideration. MVP is single-user desktop app. If moving to web/multi-user, implement Redis cache or database-backed sessions.

## Dependencies at Risk

**Nicegui framework version pinning:**
- Risk: Nicegui evolving rapidly. Current codebase uses native=True (native window) which has known macOS issues (#2107 — unreliable on_shutdown).
- Impact: (1) Native window shutdown may hang. (2) Sub_pages SPA routing has quirks. (3) CSS custom property scoping incomplete.
- Migration plan: (1) Monitor Nicegui releases for macOS native fixes. (2) If issues persist, consider PyQt6 + web UI as alternative. (3) Document all known workarounds (triple shutdown guard, CSS scoping issues).

**Qwen model dependency:**
- Risk: 1.5B model from SuperPuperD/yurteg-1.5b-v3-gguf. If upstream repo deleted or weights change, cannot re-download.
- Impact: Binary dependency on HuggingFace model weights. No versioning/pinning.
- Migration plan: (1) Pin model hash in config. (2) Backup model to S3 or local mirror. (3) Consider training own model if upstream unreliable.

**pdfplumber text extraction limitations:**
- Risk: pdfplumber works for text PDFs but fails on image-only scanned PDFs. No built-in OCR.
- Impact: 30-40% of legal documents are scanned; these fall back to placeholder extraction.
- Migration plan: Add pytesseract (fast, lightweight) or easyocr (more accurate, slower) as optional fallback. Would add 5-15s per scanned page.

## Missing Critical Features

**OCR for scanned documents:**
- Problem: Scanned PDFs (image-only) cannot be processed. Extraction falls back to dummy method. Users with scanned contracts get no metadata extraction.
- Blocks: ~30-40% of legal documents are scans. Feature parity with non-scanned docs impossible without OCR.
- Priority: Medium. Workaround: users can request non-scanned versions or use online OCR tools. True fix requires integrating tesseract or Azure/Google Vision API.

**Document version comparison (redline):**
- Problem: Endpoint `/download/redline/{contract_id}/{other_id}` exists in app/main.py but not fully integrated into UI. Users cannot easily compare two document versions.
- Blocks: Contract version tracking implemented (versioning.py, version_service.py) but visual diff not shown.
- Priority: Medium. Endpoint works; just need UI button + modal to show before/after redline.

**Batch processing optimization:**
- Problem: Each document processes sequentially through AI extraction. No batching or request grouping even if provider supports it.
- Blocks: 500 documents still take 30+ minutes despite parallel threads.
- Priority: Low for MVP. Could be future optimization (estimate +20% throughput).

**Cloud sync / multi-device support:**
- Problem: App is single-machine desktop. No way to sync contracts between machines or access from web.
- Blocks: Enterprise customers want cloud backup and remote access.
- Priority: Post-MVP. Architecture supports it (Database class is abstraction) but would need migration to PostgreSQL and web UI.

**Telegram bot notifications:**
- Problem: services/telegram_sync.py exists with bot implementation (128 lines) but not integrated into main pipeline.
- Blocks: Users cannot receive contract deadline alerts on Telegram.
- Priority: Low for MVP. Implementation exists, just needs config and testing. Would add `telegram_bot_token` to config.

## Test Coverage Gaps

**E2E integration tests:**
- What's not tested: Full end-to-end pipeline from file upload → AI extraction → database save → Excel export. Current tests mock AI responses.
- Files: `tests/test_lifecycle.py` (151 lines), `tests/test_ai_extractor_wiring.py` (169 lines) cover parts but not full flow.
- Risk: Pipeline changes (ai_extractor ↔ validator ↔ database) could break interdependencies without detection.
- Priority: High. Add 50-100 line integration test with real llama-server or mocked but realistic responses.

**UI component interaction tests:**
- What's not tested: Registry table + split panel + bulk actions interactions. Current tests check rendering but not user workflows.
- Files: `tests/test_registry_view.py` (332 lines) tests grid rendering. Gaps: no tests for expand/collapse, row selection, context menu.
- Risk: UI refactors could break bulk operations or version expansion without notice.
- Priority: Medium. Add 20-30 test cases for common UI flows.

**Provider fallback chain:**
- What's not tested: Scenario where ollama unavailable → fallback to ZAI → fallback to OpenRouter. Each step's error handling.
- Files: `tests/test_providers.py` (83 lines) covers provider selection. Gaps: no network failure simulation.
- Risk: If primary provider breaks, fallback chain might fail silently or with confusing error.
- Priority: Medium. Add mock network failures to test each fallback step.

**Database schema migrations:**
- What's not tested: Schema changes in production database with real data. Current tests use fresh in-memory SQLite.
- Files: `tests/test_migrations.py` (103 lines) basic checks only. Gaps: no ALTER TABLE or data transformation tests.
- Risk: Schema change on 10K row production database could lose data or corrupt indexes.
- Priority: High for production. Add migration test with 1K+ row fixture database.

**Validator L4 cross-document checks:**
- What's not tested: Validator L4 detects duplicate contracts or version chains. Tests only cover L1-L3 (field-level).
- Files: `modules/validator.py` (402 lines) has L4 logic but tests incomplete.
- Risk: Duplicate contracts might be saved to database undetected.
- Priority: Medium. Add 30 line test with synthetic duplicate documents.

**Stress testing under load:**
- What's not tested: 500+ document pipeline stress. Tests run on 10-50 doc samples.
- Files: `tests/stress_test.py` (2345 lines\!) exists but appears to be synthetic. Real-world performance unknown.
- Risk: Production performance unknown. 500 document batch might crash or timeout.
- Priority: Low for MVP but high for production. Run on real dataset to baseline.

---

*Concerns audit: 2026-03-25*
