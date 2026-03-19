# Technology Stack

**Analysis Date:** 2026-03-19

## Languages

**Primary:**
- Python 3.10+ (3.12 recommended) - Main application language, all backend logic and CLI

**Supporting:**
- HTML/CSS/JavaScript - Streamlit auto-generates for UI styling

## Runtime

**Environment:**
- CPython 3.10+, tested with 3.12.2
- Conda-based deployment (see README.md: `conda create -n yurteg python=3.12`)

**Package Manager:**
- pip (managed through conda environment)
- Lockfile: not present (pinned minimum versions in `requirements.txt`)

## Frameworks

**Core:**
- Streamlit 1.30.0+ - Web UI framework for desktop/cloud deployment (`main.py`)

**Data Processing:**
- pandas 2.0.0+ - Tabular data handling, Excel generation (`modules/reporter.py`)
- openpyxl 3.1.0+ - Excel workbook creation with charts and styling (`modules/reporter.py`)

**Document Processing:**
- pdfplumber 0.10.0+ - PDF text extraction, page-by-page parsing (`modules/extractor.py`)
- python-docx 1.1.0+ - DOCX document reading, paragraph/table extraction (`modules/extractor.py`)

**NLP & Named Entity Recognition:**
- natasha 1.6.0 - Russian language NER for anonymization (`modules/anonymizer.py`)
- pymorphy2-dicts-ru - Russian morphology dictionaries (required by natasha)

**Testing:**
- pytest (via conftest.py and test files in `tests/`)

**Build/Dev:**
- setuptools <81 - Package utilities, compatibility fix for Streamlit Cloud deployment

## Key Dependencies

**Critical:**
- openai 1.30.0+ - OpenAI SDK for LLM API calls, supports custom base_url for ZAI/OpenRouter (`modules/ai_extractor.py`)
  - Used for both primary (ZAI/GLM-4.7) and fallback (OpenRouter) providers
  - Instantiated via OpenAI(api_key=..., base_url=...)

- pdfplumber 0.10.0+ - Stable PDF text extraction with high accuracy
  - Critical for handling legal documents in PDF format
  - Detects scanned PDFs (is_scanned flag based on text density)

**Infrastructure:**
- python-dotenv 1.0.0+ - Environment variable loading from `.env` files
  - Loads API keys: ZHIPU_API_KEY, ZAI_API_KEY, OPENROUTER_API_KEY
  - Fallback to Streamlit Secrets in cloud deployment

## Configuration

**Environment:**
- `.env` file (local development) - NOT tracked in git
  - Contains API keys: ZHIPU_API_KEY, ZAI_API_KEY, OPENROUTER_API_KEY
  - See `.gitignore` - .env is excluded

- Streamlit Secrets (cloud deployment) - `.streamlit/secrets.toml`
  - Bridged to `os.environ` in `main.py` lines ~30
  - Same keys: ZHIPU_API_KEY, OPENROUTER_API_KEY, ZAI_API_KEY, YURTEG_CLOUD

**Configuration Files:**
- `config.py` - Dataclass-based centralized configuration
  - `supported_extensions: tuple[str, ...]` - (".pdf", ".docx")
  - `ai_base_url: str` - "https://api.z.ai/api/coding/paas/v4" (ZAI)
  - `ai_fallback_base_url: str` - "https://openrouter.ai/api/v1"
  - `model_dev: str` - "glm-4.7"
  - `model_fallback: str` - "arcee-ai/trinity-large-preview:free"
  - `validation_mode: str` - "off" | "selective" | "full"
  - `max_workers: int` - 5 (parallel AI request threads)

- `.streamlit/config.toml` - Streamlit theming
  - Dark theme with cyan accent (#06B6D4)
  - `headless = true` for cloud deployment
  - Disables usage stats gathering

## Platform Requirements

**Development:**
- macOS, Linux, or Windows with Python 3.10+
- conda/pip for package installation
- 50+ MB disk space (for dependencies and processed data)
- pdfplumber requires: libpoppler (or pre-installed pdf parsing)

**Production:**
- Streamlit Community Cloud (primary target)
- Fallback: Desktop via `streamlit run main.py`
- Desktop app variant exists in `desktop_app.py` (legacy, uses tkinter)

## Deployment Modes

**Cloud (Streamlit Community Cloud):**
- Env var: `YURTEG_CLOUD=1`
- Secrets loaded from `.streamlit/secrets.toml` → `os.environ`
- No file dialogs (tkinter unavailable)
- Demo mode or API key input required

**Desktop:**
- Env var: `YURTEG_CLOUD` not set or `YURTEG_DESKTOP=1`
- File dialogs via tkinter.filedialog
- Loads `.env` via python-dotenv
- Full filesystem access for input/output folders

---

*Stack analysis: 2026-03-19*
