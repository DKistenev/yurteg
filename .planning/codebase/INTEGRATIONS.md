# External Integrations

**Analysis Date:** 2026-03-19

## APIs & External Services

**LLM/AI Services:**
- **ZAI (主要) / GLM-4.7**
  - What it's used for: Primary AI model for extracting contract metadata (type, counterparty, amounts, dates, special conditions)
  - SDK/Client: openai Python SDK (openai>=1.30.0)
  - Base URL: `https://api.z.ai/api/coding/paas/v4`
  - Auth: Environment variable `ZHIPU_API_KEY` or `ZAI_API_KEY`
  - Location: `modules/ai_extractor.py`, `_create_client()` function
  - Request pattern: Standard OpenAI-compatible API via custom base_url
  - Max tokens: 2000 (configured in `config.py`)
  - Temperature: 0 (deterministic extraction)
  - Retry logic: 2 retries on APIError/APITimeoutError/RateLimitError

- **OpenRouter (Fallback)**
  - What it's used for: Fallback LLM when ZAI fails or is overloaded
  - SDK/Client: openai Python SDK
  - Base URL: `https://openrouter.ai/api/v1`
  - Auth: Environment variable `OPENROUTER_API_KEY`
  - Model: `arcee-ai/trinity-large-preview:free`
  - Activation: Auto-fallback if ZAI fails; also on explicit enable
  - Location: `modules/ai_extractor.py`, fallback logic in `extract_metadata()`

## Data Storage

**Databases:**
- **SQLite 3** (Local filesystem)
  - Connection: `yurteg.db` file (auto-created in working directory)
  - Client: sqlite3 (Python standard library)
  - Schema: `modules/database.py` - _SCHEMA constant
  - Tables:
    - `contracts` - Main table storing metadata, validation results, processing status
    - Indexes: `idx_file_hash`, `idx_status`, `idx_contract_type`
  - Thread safety: `check_same_thread=False` to allow ThreadPoolExecutor access
  - Resumability: File hash-based deduplication prevents re-processing same files

**File Storage:**
- **Local filesystem only**
  - Input: User-selected directory (PDF/DOCX files)
  - Output: Auto-created subdirectory structure via `modules/organizer.py`
  - Organization modes:
    - "type" - By document type (Договоры, Финансовые документы, etc.)
    - "counterparty" - By counterparty name
    - "both" - Combined hierarchy
  - Output folder name: `ЮрТэг_Результат` (configurable in `config.py`)

**Caching:**
- None configured
- Each file processed freshly unless already in database (by file hash)

## Authentication & Identity

**API Key Management:**
- **Environment Variables** (Primary approach)
  - `ZHIPU_API_KEY` - ZAI/GLM-4.7 access
  - `ZAI_API_KEY` - Alternative ZAI key name
  - `OPENROUTER_API_KEY` - OpenRouter fallback access
  - `YURTEG_CLOUD` - Flag for cloud deployment mode
  - `YURTEG_DESKTOP` - Flag for desktop mode (tkinter enabled)

- **Streamlit Secrets Bridge** (Cloud deployment)
  - Location: `.streamlit/secrets.toml`
  - Bridge code: `main.py` lines ~25-30, copies secrets to os.environ
  - No hardcoded keys anywhere in codebase

- **Manual Input** (UI fallback, `main.py`)
  - If env vars not found, user prompted via Streamlit sidebar to paste API keys
  - Keys validated via `verify_api_key()` before processing

**Auth Providers:**
- None (no user authentication)
- API key-based auth only
- No OAuth or identity federation

## Monitoring & Observability

**Error Tracking:**
- None integrated (Sentry, DataDog, etc. not used)
- Errors logged to Python logger

**Logs:**
- **Python logging module** (standard library)
  - Level: INFO for progress, WARNING for issues, ERROR for failures
  - Configuration: Via logging.basicConfig in controller
  - Output: stderr and Streamlit UI progress messages
  - Log format: [Module name] [Level] Message
  - No file logging configured (console/UI only)

**Progress Tracking:**
- Streamlit progress bar: `st.progress()` in `main.py`
- Callback pattern: `on_progress(file_index, total, filename)` passed to controller
- Real-time UI updates via Streamlit's reactive model

## CI/CD & Deployment

**Hosting:**
- **Streamlit Community Cloud** (primary target)
  - Deployment command: `streamlit run main.py`
  - Requirements file: `requirements.txt`
  - Config: `.streamlit/config.toml`

- **Desktop via Streamlit local server** (fallback)
  - Command: `streamlit run main.py` locally

**CI Pipeline:**
- None detected
- No GitHub Actions or other CI configured
- Manual testing via pytest (test files exist but CI not automated)

## Environment Configuration

**Required Environment Variables:**
- At least one of:
  - `ZHIPU_API_KEY` or `ZAI_API_KEY` (for primary ZAI model)
  - `OPENROUTER_API_KEY` (for fallback model)
- Optional: `YURTEG_CLOUD=1` (enables cloud mode, disables file dialogs)

**Secrets Location:**
- Development: `.env` file (git-ignored)
- Cloud deployment: `.streamlit/secrets.toml` (managed via Streamlit UI)
- Never hardcoded in source files

**Optional Configuration:**
- `YURTEG_DESKTOP=1` - Forces desktop mode, enables tkinter
- Model selection: `config.use_prod_model` flag (default: False, uses dev model)

## Webhooks & Callbacks

**Incoming:**
- None (desktop/web app, not API service)

**Outgoing:**
- None to external services
- Internal callbacks: `on_progress()`, `on_file_done()` for UI updates (passed to `Controller.process_archive()`)

## Data Flow Architecture

**Processing Pipeline:**
1. **Scanner** (`modules/scanner.py`)
   - Scans source directory for PDF/DOCX files
   - Calculates file hash (SHA-256) for deduplication

2. **Extractor** (`modules/extractor.py`)
   - Extracts raw text from PDF (pdfplumber) or DOCX (python-docx)
   - Detects scanned PDFs (is_scanned flag)

3. **Anonymizer** (`modules/anonymizer.py`)
   - Uses natasha NER to identify and mask personal data
   - Masks: names → [ФИО_N], phones → [ТЕЛЕФОН_N], etc.

4. **AI Extractor** (`modules/ai_extractor.py`)
   - Sends anonymized text + system prompt to LLM (ZAI or OpenRouter)
   - Receives JSON with: document_type, counterparty, subject, dates, amount, parties, confidence
   - Parallel execution: ThreadPoolExecutor with max_workers=5

5. **Validator** (`modules/validator.py`)
   - L1: Basic field presence validation
   - L2: Format validation (dates, amounts)
   - L3: Consistency checks (date_start <= date_end)
   - L4: Metadata conflict detection across batch
   - L5: Selective AI re-verification of low-confidence extracts

6. **Database** (`modules/database.py`)
   - Stores metadata in SQLite `contracts` table
   - Tracks processing status, validation results, organized file paths

7. **Organizer** (`modules/organizer.py`)
   - Copies files to output directory with hierarchical structure
   - No deletion or moving of original files

8. **Reporter** (`modules/reporter.py`)
   - Generates Excel workbook with:
     - Metadata sheet (all contracts with columns)
     - Statistics sheet (charts, counts by type/counterparty)
     - Issues sheet (validation warnings)

## Rate Limiting & Quotas

**ZAI/GLM-4.7:**
- No explicit rate limit configuration
- Retry logic: 2 retries on RateLimitError (429)
- Parallel requests: 5 concurrent (max_workers)
- Per-file processing time: ~4 seconds (bottleneck)

**OpenRouter:**
- Uses free tier model (may have stricter limits)
- Activated as fallback when ZAI rate-limited

---

*Integration audit: 2026-03-19*
