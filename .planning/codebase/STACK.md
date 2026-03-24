# Technology Stack

**Analysis Date:** 2026-03-25

## Languages

**Primary:**
- Python 3.10+ - Application core, AI extraction pipelines, desktop/web UI

## Runtime

**Environment:**
- Python 3.10+ (via virtual environment)

**Package Manager:**
- pip
- Lockfile: `requirements.txt`

## Frameworks

**Core UI:**
- Streamlit 1.x - Main web interface for document processing (`main.py`)
- NiceGUI 3.9.0 - Alternative desktop/native UI framework (`desktop_app.py`)
- CustomTkinter - Native desktop alternative with tkinter bindings

**Data Processing:**
- pandas 2.0+ - Data manipulation and Excel report generation
- pdfplumber 0.10+ - PDF text extraction (`modules/extractor.py`)
- python-docx 1.1+ - DOCX text extraction (`modules/extractor.py`)

**NLP & Anonymization:**
- natasha 1.6+ - Named entity recognition (Russian NER) (`modules/anonymizer.py`)
- pymorphy2-dicts-ru - Russian morphological analysis dictionary

**AI/LLM Framework:**
- openai 1.30+ - OpenAI-compatible SDK for all LLM providers (ZAI, OpenRouter, Ollama) (`modules/ai_extractor.py`, `providers/`)

**LLM Execution:**
- llama.cpp (b5606) - Local inference engine for GGUF models (`services/llama_server.py`)

**Async/Scheduling:**
- APScheduler 3.10+ - Scheduled task execution for deadline digests (`bot_server/scheduler.py`)

**Desktop/Web:**
- Telegram (python-telegram-bot 22.7+) - Telegram bot integration (`bot_server/bot.py`, `bot_server/main.py`)
- FastAPI 0.135+ - REST API server for bot backend (`bot_server/main.py`)
- uvicorn 0.42+ - ASGI server for FastAPI

**Utilities:**
- python-dotenv 1.0+ - Environment variable management
- python-dateutil 2.8+ - Date parsing and normalization
- rapidfuzz 3.14+ - Fuzzy string matching
- openpyxl 3.1+ - Excel file generation (paired with pandas)
- huggingface_hub 0.23+ - Model downloading from Hugging Face (`services/llama_server.py`)

## Key Dependencies

**Critical for Core Functionality:**
- `openai` - Unified API client for ZAI (GLM-4.7), OpenRouter, and Ollama providers
- `natasha` - Russian NLP for PII anonymization (`modules/anonymizer.py`)
- `pdfplumber` + `python-docx` - Document text extraction, supports PDF and DOCX

**Infrastructure:**
- `pandas` + `openpyxl` - Excel report generation (`modules/reporter.py`)
- `APScheduler` - Scheduled deadline alerts via Telegram
- `huggingface_hub` - Model distribution and caching

**Client/Server Communication:**
- `httpx` - HTTP client for Telegram sync (`services/telegram_sync.py`)
- `python-telegram-bot` - Telegram bot handlers (`bot_server/bot.py`)
- `FastAPI` + `uvicorn` - Bot server API endpoints

## Configuration

**Environment:**
- Loaded from `.env` file via `python-dotenv` (development)
- Streamlit Secrets integration for cloud deployments (via `st.secrets`)
- Persisted settings in `~/.yurteg/settings.json` (user preferences, active provider)
- Config class: `config.py` - Centralized configuration with sensible defaults

**Required Environment Variables:**
- `ZAI_API_KEY` or `ZHIPU_API_KEY` - ZAI/GLM API key (main provider)
- `OPENROUTER_API_KEY` - OpenRouter fallback provider
- `TELEGRAM_BOT_TOKEN` - Telegram bot server token
- `YURTEG_CLOUD` - Set to "1" for cloud deployments (triggers Streamlit Secrets)

**Build/Runtime:**
- `.streamlit/config.toml` - Streamlit theme and server settings (headless mode, no stats)
- `bot_server/requirements.txt` - Separate dependency list for bot server (smaller footprint)

## Platform Requirements

**Development:**
- macOS, Linux, or Windows
- Python 3.10+ with pip
- 2GB+ RAM minimum (local LLM mode requires ~1.5GB)
- Internet connection for cloud provider API calls

**Production:**
- Cloud deployment: Streamlit Cloud, Railway, Vercel, or similar
- Bot server: Dedicated server/VPS for FastAPI (`bot_server/main.py`)
- Database: SQLite (file-based, no external DB required)
- Telegram webhook: Public URL for receiving bot updates

**Local LLM Mode (Optional):**
- ~1.5GB disk space for GGUF model (`~/.yurteg/yurteg-v3-Q4_K_M.gguf`)
- ~1.5GB RAM during inference
- CPU: x86_64 or ARM64 (Apple Silicon)

---

*Stack analysis: 2026-03-25*
