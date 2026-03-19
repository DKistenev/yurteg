# Architecture Research

**Domain:** Legal document processing pipeline — Python/Streamlit desktop app evolving toward multi-provider AI and on-premise B2B deployment
**Researched:** 2026-03-19
**Confidence:** HIGH (current codebase analyzed directly + verified patterns from official docs)

---

## Standard Architecture

### System Overview (Target State)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         UI Layer                                    │
│  main.py (Streamlit)                                                │
│  Calls services directly — no HTTP roundtrip needed locally        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ Python function calls
┌──────────────────────────────▼──────────────────────────────────────┐
│                      Service Layer                                  │
│  services/pipeline_service.py  — orchestrates processing            │
│  services/registry_service.py  — querying, filtering, reporting     │
│  services/deadline_service.py  — deadline checks, notifications     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ Python function calls
┌──────────────────────────────▼──────────────────────────────────────┐
│                    Processing Modules (unchanged)                   │
│  scanner → extractor → anonymizer → ai_extractor → validator        │
│                     → database → organizer → reporter               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
         ┌─────────────────────┴────────────────────┐
         │                                          │
┌────────▼──────────┐                   ┌───────────▼───────────┐
│   AI Provider     │                   │   Data Layer          │
│   Abstraction     │                   │   SQLite (yurteg.db)  │
│                   │                   │   File system         │
│  LLMProvider ABC  │                   └───────────────────────┘
│   ├─ ZAIProvider  │
│   ├─ OpenRouter   │
│   └─ OllamaLocal  │
└───────────────────┘
```

**Key insight:** The UI layer does NOT need an HTTP API layer to talk to services when everything runs in-process. The service layer is callable Python — this is sufficient for Streamlit and avoids unnecessary complexity. FastAPI is added only if and when external integrations demand it (веха 3+).

---

## Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `main.py` (Streamlit UI) | User interaction, progress display, results browsing | `services/pipeline_service.py`, `services/registry_service.py`, `Config` |
| `services/pipeline_service.py` | Single entry point for document processing; wraps `controller.py` logic | `controller.py`, all processing modules |
| `services/registry_service.py` | Query registry, filter, trigger report generation | `modules/database.py`, `modules/reporter.py` |
| `services/deadline_service.py` | Scan for approaching deadlines, format notifications | `modules/database.py` |
| `modules/ai_extractor.py` (refactored) | Delegates to `LLMProvider` ABC; owns prompts and JSON parsing | `providers/` |
| `providers/base.py` | Abstract `LLMProvider` interface — `complete(messages) -> str` | — |
| `providers/zai.py` | ZAI GLM via openai SDK | openai SDK |
| `providers/openrouter.py` | OpenRouter via openai SDK | openai SDK |
| `providers/ollama.py` | Local Ollama via openai SDK (OpenAI-compatible endpoint) | openai SDK |
| `controller.py` | Pipeline orchestration, parallelism, resumability | Processing modules, DB |
| `modules/database.py` | SQLite persistence, resumability queries | sqlite3 |
| `config.py` | All settings including `active_provider`, `providers` dict | All layers |

---

## Recommended Project Structure (Delta from Current)

```
yurteg/
├── main.py                       # Streamlit UI — unchanged entry point
├── controller.py                 # Pipeline orchestration — minor refactor
├── config.py                     # Add: active_provider, provider configs
├── modules/
│   ├── ai_extractor.py           # Refactor: delegate to LLMProvider, keep prompts
│   ├── models.py                 # Add: DocumentStatus, DeadlineAlert
│   └── ... (rest unchanged)
│
├── providers/                    # NEW: AI provider abstraction
│   ├── __init__.py
│   ├── base.py                   # Abstract LLMProvider
│   ├── zai.py                    # ZAI GLM (current primary)
│   ├── openrouter.py             # OpenRouter (current fallback)
│   └── ollama.py                 # Local Ollama (веха 3 target)
│
└── services/                     # NEW: service layer
    ├── __init__.py
    ├── pipeline_service.py       # process_archive() facade
    ├── registry_service.py       # get_contracts(), filter, export
    └── deadline_service.py       # get_approaching_deadlines(), notify
```

### Structure Rationale

- **`providers/`:** Isolates AI vendor specifics from processing logic. `ai_extractor.py` keeps all prompts and JSON parsing — those are domain logic, not provider concerns. Adding a new provider = one new file, no changes to `ai_extractor.py`.
- **`services/`:** Groups operations by business capability, not technical layer. `pipeline_service.py` becomes the stable public API that both Streamlit UI and any future FastAPI router call identically. No duplication.
- **Everything else stays put:** `modules/`, `controller.py`, `config.py` are working and tested. Surgical addition, not rewrite.

---

## Architectural Patterns

### Pattern 1: Provider Abstraction via ABC + openai SDK

**What:** Define `LLMProvider` as an abstract base class with a single method `complete(messages: list[dict], **kwargs) -> str`. Each concrete provider (`ZAIProvider`, `OpenRouterProvider`, `OllamaProvider`) instantiates an `openai.OpenAI` client with a different `base_url` and `api_key`. The factory function in `providers/__init__.py` reads `config.active_provider` and returns the right instance.

**When to use:** When you have 2+ LLM endpoints that share the openai-SDK wire format but differ in API key management, model names, and edge-case handling (e.g., some free OpenRouter models reject `system` role — already handled by `_merge_system_into_user` in current code).

**Trade-offs:** Lightweight — no new dependencies (LiteLLM is powerful but adds 40+ MB and its own config surface; overkill here). The openai SDK already handles all three target providers natively. If the provider count grows beyond 5, reconsider LiteLLM.

**Example:**
```python
# providers/base.py
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    def complete(self, messages: list[dict], **kwargs) -> str:
        """Returns raw text response from the model."""
        ...

    @abstractmethod
    def verify_key(self) -> bool:
        """Returns True if credentials are valid."""
        ...

# providers/zai.py
from openai import OpenAI
from providers.base import LLMProvider

class ZAIProvider(LLMProvider):
    def __init__(self, config: Config):
        self._client = OpenAI(
            base_url=config.ai_base_url,
            api_key=os.environ.get("ZHIPU_API_KEY", ""),
        )
        self._model = config.active_model
        self._config = config

    def complete(self, messages: list[dict], **kwargs) -> str:
        extra = {}
        if self._config.ai_disable_thinking:
            extra["extra_body"] = {"thinking": {"type": "disabled"}}
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=self._config.ai_temperature,
            max_tokens=self._config.ai_max_tokens,
            messages=messages,
            **extra,
        )
        return response.choices[0].message.content

# providers/__init__.py
def get_provider(config: Config) -> LLMProvider:
    match config.active_provider:
        case "zai":       return ZAIProvider(config)
        case "openrouter": return OpenRouterProvider(config)
        case "ollama":    return OllamaProvider(config)
        case _: raise ValueError(f"Unknown provider: {config.active_provider}")
```

---

### Pattern 2: Service Layer as Stable Façade

**What:** Thin Python classes/modules that wrap existing controller and module calls behind a stable interface. The service layer is what Streamlit calls today and what a FastAPI router would call tomorrow — the same code, no duplication.

**When to use:** When a UI currently calls controller internals directly and you anticipate adding an API or second UI (e.g., CLI tool for on-premise power users).

**Trade-offs:** Adds one indirection level. Worth it here because `main.py` currently has significant business logic mixed into Streamlit event handlers — the service layer extracts and stabilizes that.

**Example:**
```python
# services/pipeline_service.py
from controller import Controller
from config import Config
from typing import Callable

def process_archive(
    source_dir: Path,
    config: Config,
    grouping: str = "both",
    force_reprocess: bool = False,
    on_progress: Callable | None = None,
    on_file_done: Callable | None = None,
) -> dict:
    """Single entry point for document processing.
    Called by Streamlit UI today. Called by FastAPI endpoint tomorrow.
    """
    ctrl = Controller(config)
    return ctrl.process_archive(
        source_dir=source_dir,
        grouping=grouping,
        force_reprocess=force_reprocess,
        on_progress=on_progress,
        on_file_done=on_file_done,
    )
```

---

### Pattern 3: On-Premise Deployment via Docker Compose (No External Dependencies)

**What:** Package the entire Streamlit app as a single Docker Compose service. Client installs Docker Desktop, runs `docker compose up`, opens `localhost:8501`. No cloud, no internet dependency at runtime (except for LLM API calls, which go to local Ollama in the fully offline variant).

**When to use:** B2B clients with security requirements ("данные не покидают контур"), IT departments that distrust cloud SaaS, large inhouse legal teams.

**Trade-offs:** Client must have Docker Desktop installed (standard in enterprise IT). Image size ~600 MB with all Python deps. Update delivery via `docker compose pull && docker compose up`.

**Example `docker-compose.yml`:**
```yaml
services:
  yurteg:
    image: yurteg/app:latest
    ports:
      - "8501:8501"
    volumes:
      - ./documents:/data/input      # client mounts their docs here
      - ./output:/data/output        # results land here
      - ./yurteg.db:/data/yurteg.db  # persistent registry
    environment:
      - ZHIPU_API_KEY=${ZHIPU_API_KEY}
    restart: unless-stopped
```

For the fully offline variant (веха 3), add an `ollama` service to the same Compose file and set `active_provider=ollama`.

---

## Data Flow

### Document Processing Flow

```
User picks folder in Streamlit
        |
        v
services/pipeline_service.process_archive(source_dir, config)
        |
        v
controller.process_archive()
        |
        +---> [parallel, up to 5 workers]
        |     for each file:
        |       scanner -> FileInfo
        |       extractor -> ExtractedText
        |       anonymizer -> AnonymizedText (in-memory only)
        |       ai_extractor.extract_metadata(text, provider)
        |           |
        |           v
        |       providers/get_provider(config).complete(messages)
        |           |
        |           +--> ZAIProvider  (primary)
        |           +--> OpenRouterProvider (fallback if ZAI fails)
        |           +--> OllamaProvider (веха 3, fully local)
        |       validator -> ValidationResult
        |       organizer -> copies file to output dir
        |       database.save(ProcessingResult)
        |
        v
reporter.generate_excel(db) -> Реестр_договоров.xlsx
        |
        v
Streamlit UI displays results
```

### Config-Driven Provider Selection

```
config.active_provider = "zai" | "openrouter" | "ollama"
        |
        v
providers.get_provider(config) -> LLMProvider instance
        |
        v
ai_extractor.extract_metadata(text, provider=provider)
        |
        v
provider.complete(messages) -> raw_text
        |
        v
_parse_json_response(raw_text) -> ContractMetadata (unchanged)
```

### Deadline Notification Flow (new feature)

```
services/deadline_service.get_approaching_deadlines(days=30, db)
        |
        v
database.query("SELECT ... WHERE date_end BETWEEN today AND today+30d")
        |
        v
list[DeadlineAlert]
        |
        v
Streamlit: show banner in UI sidebar
(future: Telegram bot webhook — separate веха)
```

### State Management

- **In-memory during processing:** `ProcessingResult` objects in `controller.results` list — unchanged
- **Persistent:** `yurteg.db` (SQLite) in output directory — unchanged
- **Provider state:** `LLMProvider` instance created once per `process_archive()` call, not stored globally (allows config changes between runs)
- **Document status:** new `status` column in SQLite (`signed`, `negotiation`, `expiring`, `expired`) — computed from `date_end` at query time, not stored (avoids staleness)

---

## Build Order (Phase Dependencies)

This is the critical sequencing constraint for roadmap phases:

**Step 1 — Provider Abstraction** (prerequisite for everything else)
- Create `providers/base.py` (ABC)
- Extract `ZAIProvider` from current `ai_extractor._create_client()`
- Extract `OpenRouterProvider` similarly
- Update `ai_extractor.extract_metadata()` to accept `provider: LLMProvider`
- Update `Config` to add `active_provider: str`
- Zero behavior change — this is a mechanical refactor

**Step 2 — Service Layer** (can proceed in parallel with Step 1)
- Create `services/pipeline_service.py` wrapping `controller.process_archive()`
- Create `services/registry_service.py` wrapping database queries
- Update `main.py` to call services instead of controller directly
- Zero behavior change — mechanical extraction

**Step 3 — Document Status + Deadlines** (requires Step 2)
- Add `status` field to data model (`modules/models.py`)
- Create `services/deadline_service.py`
- Update Streamlit UI with status column and deadline banner
- Purely additive — no changes to processing pipeline

**Step 4 — On-Premise Docker Packaging** (can proceed after Step 1-2 complete)
- Write `Dockerfile` (multi-stage: build deps → runtime)
- Write `docker-compose.yml`
- Test volume mounts for documents and output
- No code changes — packaging only

**Step 5 — Ollama Local Provider** (веха 3, separate milestone)
- Create `providers/ollama.py` (OllamaProvider using openai SDK + local base_url)
- Add Ollama service to `docker-compose.yml`
- Test with QWEN model via Ollama
- Requires Step 1 complete — just adds one more provider file

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| ZAI GLM-4.7 | openai SDK, custom `base_url` | Current; keep as primary |
| OpenRouter | openai SDK, `base_url=https://openrouter.ai/api/v1` | Current fallback; some models need system-prompt merge |
| Ollama (local) | openai SDK, `base_url=http://localhost:11434/v1` | Веха 3; openai-compatible endpoint built into Ollama |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `main.py` ↔ `services/` | Direct Python calls | No HTTP — same process |
| `services/` ↔ `controller.py` | Direct Python calls | Controller stays unchanged |
| `ai_extractor` ↔ `providers/` | `provider.complete(messages)` call | Single method contract |
| `controller.py` ↔ `modules/` | Dataclass objects passed as args | Unchanged |
| Future `FastAPI router` ↔ `services/` | Direct Python imports | Same service layer, no duplication |

---

## Anti-Patterns

### Anti-Pattern 1: Adding FastAPI Before You Need It

**What people do:** Introduce a FastAPI HTTP server between Streamlit and business logic "to be ready for the future API."

**Why it's wrong:** For a desktop/on-premise app where Streamlit and services run in the same process, adding HTTP adds latency, complicates startup (two processes, two ports), breaks Streamlit's built-in progress callbacks (HTTP can't stream pipeline progress the way Python callbacks can), and adds deployment complexity for no current benefit.

**Do this instead:** Put business logic in `services/`. When an actual external API need emerges, add a thin FastAPI router that imports and calls those same service functions. Two files, done.

---

### Anti-Pattern 2: Vendor Lock in Prompt Logic

**What people do:** Hard-code ZAI-specific parameters (`extra_body`, `thinking: disabled`) inside `ai_extractor.py` alongside the prompts.

**Why it's wrong:** When switching providers, you have to edit the extraction logic to strip ZAI-specific fields. The current `_create_client()` already partially mixes provider routing with prompt construction — this is the thing to fix.

**Do this instead:** Keep all prompts and JSON parsing in `ai_extractor.py` (domain logic). Move all provider-specific API construction to `providers/`. The `complete()` method on each provider handles its own quirks (thinking mode, system-role merging, etc.) transparently.

---

### Anti-Pattern 3: Storing Computed Status in Database

**What people do:** Add a `status` column and update it via a background job ("expired", "expiring", etc.).

**Why it's wrong:** Status is a function of `date_end` and `today`. Storing it creates staleness bugs — a document stored as "active" in January is silently wrong in June. Stale status in the Excel export undermines user trust.

**Do this instead:** Compute status at query time: `CASE WHEN date_end < date('now') THEN 'expired' WHEN date_end < date('now', '+30 days') THEN 'expiring' ELSE 'active' END`. Add an indexed `date_end` column. Fast, always accurate.

---

## Scaling Considerations

This is a desktop/on-premise tool. Scaling means "handles larger document archives" not "handles more concurrent users."

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 100-500 docs (current) | Current ThreadPoolExecutor (5 workers) is sufficient |
| 1000-5000 docs | Increase `max_workers` in Config; consider batch-processing with progress checkpointing in DB |
| 10000+ docs | SQLite stays fine for reads; parallel write contention needs investigation; consider WAL mode (`PRAGMA journal_mode=WAL`) — single config line |

The AI bottleneck (GLM API rate limits) will hit before SQLite or CPU does. On-premise Ollama (веха 3) removes this bottleneck entirely.

---

## Sources

- Current codebase: `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/modules/ai_extractor.py` (direct analysis)
- Current codebase: `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/config.py` (direct analysis)
- LiteLLM documentation: [https://docs.litellm.ai/](https://docs.litellm.ai/) — provider abstraction patterns (MEDIUM confidence; LiteLLM itself not recommended here but its ABC pattern is)
- LiteLLM Ollama integration: [https://docs.litellm.ai/docs/providers/ollama](https://docs.litellm.ai/docs/providers/ollama) — confirms openai SDK compatibility
- FastAPI background tasks: [https://fastapi.tiangolo.com/tutorial/background-tasks/](https://fastapi.tiangolo.com/tutorial/background-tasks/) — verified why FastAPI premature here
- Streamlit service layer pattern: [https://discuss.streamlit.io/t/project-structure-for-medium-and-large-apps-full-example-ui-and-logic-splitted/59967](https://discuss.streamlit.io/t/project-structure-for-medium-and-large-apps-full-example-ui-and-logic-splitted/59967) — community-validated structure

---

*Architecture research for: ЮрТэг legal document processing pipeline*
*Researched: 2026-03-19*
