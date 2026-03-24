# External Integrations

**Analysis Date:** 2026-03-25

## APIs & External Services

**LLM Providers (pluggable via provider pattern):**
- **ZAI (GLM-4.7)** - Primary AI provider for document metadata extraction
  - SDK/Client: `openai` 1.30+ (OpenAI-compatible)
  - Implementation: `providers/zai.py`
  - Base URL: `https://api.z.ai/api/coding/paas/v4`
  - Auth: `ZAI_API_KEY` or `ZHIPU_API_KEY` env var
  - Model: `glm-4.7`
  - Use case: Fast, accurate metadata extraction from legal documents

- **OpenRouter** - Fallback LLM provider (bespoke models)
  - SDK/Client: `openai` 1.30+ (OpenAI-compatible)
  - Implementation: `providers/openrouter.py`
  - Base URL: `https://openrouter.ai/api/v1`
  - Auth: `OPENROUTER_API_KEY` env var
  - Model: `arcee-ai/trinity-large-preview:free` (configurable fallback)
  - Use case: Free tier backup when ZAI unavailable
  - Note: Merges system messages into user content (some models don't support role=system)

- **Ollama (llama-server)** - Local inference engine for private processing
  - SDK/Client: `openai` 1.30+ (OpenAI-compatible to llama-server endpoint)
  - Implementation: `providers/ollama.py`
  - Base URL: `http://localhost:8080/v1` (configurable port in `config.py`)
  - Model: QWEN 1.5B v3 ORPO (`yurteg-v3-Q4_K_M.gguf`)
  - Model source: Hugging Face `SuperPuperD/yurteg-1.5b-v3-gguf`
  - Auth: None (local, API key not needed)
  - Process: Managed by `LlamaServerManager` (`services/llama_server.py`)
  - Use case: Private, offline document processing without external API calls

## Data Storage

**Databases:**
- **SQLite** (file-based)
  - Location: User-specified directory during setup (e.g., `~/.yurteg/contracts.db`)
  - Schema: `modules/database.py` - Contracts table with metadata, validation status, organized path
  - Client: Standard library `sqlite3`
  - Schema: Includes columns for contract metadata (type, counterparty, subject, dates, amount, parties, confidence scores)
  - Migrations: Applied via `_ensure_migrations_table()` and `_is_migration_applied()` pattern
  - Indexes: On `file_hash`, `status`, `contract_type` for query performance

**Model Storage:**
- **Hugging Face Hub** - Model distribution
  - Client: `huggingface_hub` 0.23+
  - Repo: `SuperPuperD/yurteg-1.5b-v3-gguf`
  - File: `yurteg-v3-Q4_K_M.gguf` (~940 MB)
  - Download location: `~/.yurteg/yurteg-v3-Q4_K_M.gguf`
  - Managed by: `LlamaServerManager.ensure_model()` (`services/llama_server.py`)

**File Storage:**
- **Local filesystem only** - No cloud storage integration
  - Source files: Unchanged in original directory (copy-only, never delete)
  - Organized output: User-defined output folder (default: `ЮрТэг_Результат`)
  - Database: SQLite file in same location as output

## Caching

**None** - Direct API calls to providers on each request (stateless extraction)

**Model Caching:**
- Local GGUF model cached in `~/.yurteg/` after first download
- llama-server instance cached as Streamlit resource (`@st.cache_resource`)

## Authentication & Identity

**Auth Providers:**
- **Custom** - Application-managed authentication
  - No OAuth/OIDC integration
  - Telegram binding via 6-digit code (`bot_server/bot.py`)
  - Binding code generation: Secrets module (`secrets` library)
  - Binding TTL: 30 minutes (configurable in `bot_server/config.py`)

**API Key Management:**
- Environment variables: `ZAI_API_KEY`, `OPENROUTER_API_KEY`, `TELEGRAM_BOT_TOKEN`
- Fallback: `ZHIPU_API_KEY` as alternative for ZAI
- Verification: Each provider implements `verify_key()` method (`providers/base.py`)
- Cloud mode: Keys loaded from Streamlit Secrets (`st.secrets`) during app init (`main.py` lines 26-32)

## Monitoring & Observability

**Error Tracking:**
- None configured - errors logged to Python `logging` module

**Logs:**
- Standard Python `logging` (stdout/stderr)
- Log levels: INFO (progress), WARNING (alerts), ERROR (failures)
- No structured logging or external aggregation

**Health Checks:**
- Bot server: `GET /api/health` endpoint (`bot_server/main.py`) - used for connection verification
- Telegram sync: `TelegramSync.check_connection()` pings health endpoint with 5s timeout (`services/telegram_sync.py`)

## CI/CD & Deployment

**Hosting:**
- **Streamlit Cloud** - Recommended for web UI (official deployment target)
- **Cloud Platforms** - Railway, Vercel, or similar for bot server
- **Local Desktop** - NiceGUI app bundle (`.dmg` for macOS)

**CI Pipeline:**
- None configured - Manual testing and deployment

**Bot Server Deployment:**
- FastAPI with uvicorn (`bot_server/main.py`)
- Requires public URL for Telegram webhook registration
- Lifespan management: FastAPI `@asynccontextmanager` for setup/shutdown

## Environment Configuration

**Required env vars:**
- `ZAI_API_KEY` - GLM-4.7 API authentication
- `TELEGRAM_BOT_TOKEN` - Telegram bot credentials (bot_server only)

**Optional env vars:**
- `OPENROUTER_API_KEY` - OpenRouter fallback provider
- `ZHIPU_API_KEY` - Alternative ZAI provider key
- `YURTEG_CLOUD` - Set "1" for cloud mode (enables Streamlit Secrets)
- `YURTEG_DESKTOP` - Set "1" for desktop mode (disables tkinter import)

**Secrets location:**
- Development: `.env` file (loaded via `python-dotenv`)
- Cloud (Streamlit): Streamlit Secrets dashboard
- Cloud (FastAPI): Environment variables on hosting platform
- Persisted user settings: `~/.yurteg/settings.json` (JSON file)

## Webhooks & Callbacks

**Incoming Webhooks:**
- **Telegram Webhook** - `POST /telegram/webhook` (`bot_server/main.py`)
  - Receives Telegram updates via long polling configured in webhook
  - Endpoint registered at startup via `app_bot.bot.set_webhook()`
  - Webhook URL: `{SERVER_URL}/telegram/webhook`

**Outgoing Webhooks:**
- None configured

**Bot Server REST API:**
- `POST /api/bind` - Exchange 6-digit code for chat_id (`bot_server/main.py`)
- `GET /api/queue/{chat_id}` - Fetch pending files for a user
- `GET /api/files/{file_id}` - Download a specific queued file
- `DELETE /api/queue/{file_id}` - Confirm file retrieval
- `POST /api/deadlines/{chat_id}` - Sync deadline alerts from local app
- `GET /api/health` - Liveness probe

**Local App ↔ Bot Server Communication:**
- Client: `TelegramSync` class (`services/telegram_sync.py`)
- Protocol: HTTP REST with `httpx` client (async-capable)
- Features: Timeout handling (5s for health, 30s for file ops), graceful error handling

## LLM Provider Routing

**Provider Selection Logic:**
- `config.active_provider` - Currently active provider ("ollama", "zai", "openrouter")
- `config.fallback_provider` - Fallback if active unavailable
- Persisted: `~/.yurteg/settings.json` stores user preference
- Initialization: `ai_extractor.py` instantiates provider via factory pattern
- Key verification: Each provider's `verify_key()` called before use
- Fallback trigger: If active provider `verify_key()` fails, system auto-switches to fallback

**Default Provider Order:**
1. ollama (local, no API key required)
2. zai (GLM-4.7, primary cloud provider)
3. openrouter (free tier backup)

---

*Integration audit: 2026-03-25*
