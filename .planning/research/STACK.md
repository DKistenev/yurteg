# Stack Research

**Domain:** Python document processing app — deadline tracking, notifications, multi-provider LLM, API layer
**Researched:** 2026-03-19
**Confidence:** MEDIUM-HIGH (core libraries verified via PyPI/official docs; Streamlit threading patterns from official docs)

---

## Context

This is a brownfield addition to an existing Python 3.12 / Streamlit / SQLite / openai-SDK app. The goal is to add four capabilities without replacing the existing stack:

1. Deadline tracking and document status management
2. In-app + Telegram notifications
3. Multi-provider LLM abstraction (GLM / Claude / local QWEN)
4. API layer separating business logic from Streamlit UI

---

## Recommended Stack

### 1. Deadline Tracking & Background Scheduling

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| APScheduler | 3.11.2 | Background job runner for deadline checks | Proven in production, BackgroundScheduler runs in a separate daemon thread without blocking Streamlit's main thread. v3.x (not v4 alpha) is the stable branch. SQLite job store available for persistence. |

**Why APScheduler 3.x, not 4.x alpha:**
Version 4.0.0a6 (released April 2025) is still in alpha. The 3.x branch (latest: 3.11.2, Dec 2025) is stable. For a small team with no dedicated developer, alpha software is not acceptable risk.

**Streamlit threading caveat:**
APScheduler's `BackgroundScheduler` runs outside Streamlit's `ScriptRunContext`. It **cannot** call `st.*` functions directly. The correct pattern: the scheduler writes deadline alerts to the SQLite database; on each Streamlit rerender (triggered by user interaction or `st.rerun()`), the UI reads the alert table and renders `st.toast()`. This decouples the scheduler from the UI thread.

**Document status in SQLite:**
No new library needed. Add a `status` column (`draft` / `active` / `expiring` / `expired`) and a `deadline_date` column to the existing documents table. APScheduler runs a daily job that updates statuses via direct SQLite writes.

---

### 2. In-App Notifications

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Streamlit built-in `st.toast` | ≥1.25.0 (already installed) | Show deadline alerts in the UI | Zero dependencies. Already available. Duration configurable. Stacks multiple toasts. 2025 fixes: respects theme colors, works inside dialogs. |

**Pattern:**
```python
# On app startup / rerun, check for pending alerts
alerts = db.get_unread_alerts()
for alert in alerts:
    st.toast(f"Срок истекает: {alert.doc_name} — {alert.deadline}", icon="⚠️")
    db.mark_alert_read(alert.id)
```

No extra library needed for in-app notifications. `st.toast` is sufficient.

---

### 3. Telegram Notifications

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| python-telegram-bot | 22.7 | Send deadline alerts to Telegram | Standard library. Bot.send_message() works standalone — no full bot framework needed, just instantiate `Bot(token)` and call `await bot.send_message(chat_id=..., text=...)`. Async-native since v20. |

**Why python-telegram-bot, not raw requests to Telegram HTTP API:**
The HTTP API approach requires manual error handling, retry logic, and parse_mode encoding. python-telegram-bot provides all of this. For a one-way notification sender (not a bot that receives commands), only `telegram.Bot` is used — the full `Application` framework is not needed.

**Minimal usage pattern (one-way push):**
```python
import asyncio
from telegram import Bot

async def send_deadline_alert(token: str, chat_id: str, text: str) -> None:
    async with Bot(token) as bot:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")

# Call from APScheduler job (which runs in a thread, not async context):
asyncio.run(send_deadline_alert(token, chat_id, text))
```

**Why not aiogram:**
aiogram is a full async bot framework optimized for bots that receive user commands. For outbound-only notifications, it is overkill and has a steeper learning curve.

**User setup requirement:**
User must create a Telegram bot via @BotFather, obtain a token, and start a conversation with the bot to get their `chat_id`. This is a one-time setup. Store token + chat_id in `.env` / Streamlit Secrets.

---

### 4. Multi-Provider LLM Abstraction

**Decision: Thin wrapper over existing openai SDK — do NOT add LiteLLM.**

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| openai SDK (already installed) | 1.30.0+ | Unified interface to all providers | All target providers (ZAI/GLM, OpenRouter, Ollama, vLLM) expose OpenAI-compatible `/v1/chat/completions` endpoints. The SDK's `base_url` parameter already supports this. No new dependency needed. |

**Why not LiteLLM:**
LiteLLM 1.82.x is a 50+ transitive dependency tree. It adds significant install size to a Streamlit Cloud deployment (which has memory limits). The project's three current providers (GLM via ZAI, Claude via OpenRouter, future local QWEN via Ollama/vLLM) all speak OpenAI-compatible JSON. LiteLLM solves a problem this project doesn't have: abstracting fundamentally incompatible APIs (e.g., Anthropic's native format). Since even Anthropic models are accessed through OpenRouter here, the openai SDK with a configurable `base_url` is sufficient.

**Why not LangChain:**
LangChain adds even heavier dependencies and is designed for agent pipelines and RAG chains. ЮрТэг's AI usage is a single structured extraction call per document — there is no chain to build.

**Recommended implementation — `ProviderRouter` in `modules/ai_provider.py`:**

```python
from dataclasses import dataclass
from openai import OpenAI

@dataclass
class ProviderConfig:
    name: str          # "glm" | "openrouter" | "local"
    base_url: str
    api_key: str
    model: str

def build_client(cfg: ProviderConfig) -> OpenAI:
    return OpenAI(api_key=cfg.api_key, base_url=cfg.base_url)
```

`config.py` holds a list of `ProviderConfig` objects; `ai_extractor.py` iterates them on failure. This is the entire abstraction needed — ~30 lines, zero new dependencies.

**For future local QWEN (Веха 3):**
Run Ollama locally; it exposes `http://localhost:11434/v1` with OpenAI-compatible API. Same `build_client()` call, `api_key="ollama"`.

---

### 5. API Layer (Business Logic Separation)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| FastAPI | 0.135.1 | HTTP API layer separating pipeline logic from Streamlit UI | Standard Python async API framework. Auto-generates OpenAPI docs. Pydantic validation built in. Enables future B2B on-premise API deployment without Streamlit dependency. |
| uvicorn | 0.34.0+ | ASGI server to run FastAPI | Minimal, production-ready. Ships with FastAPI standard install. |

**Architecture pattern:**
```
Streamlit UI  →  HTTP (localhost)  →  FastAPI app  →  pipeline modules
                                                    →  SQLite DB
```

In desktop mode: FastAPI runs as a subprocess on `localhost:8000`; Streamlit calls it via `httpx` or `requests`. In on-premise B2B mode: FastAPI is deployed independently (Docker container); Streamlit becomes optional.

**Why FastAPI over Flask:**
FastAPI is async-native (matters for concurrent document processing), has built-in Pydantic validation (already used in the project's dataclasses), and auto-generates OpenAPI docs — useful for the "Tech-savvy юристы" segment that wants an API.

**Immediate scope for Веха 1:**
The API layer does not need to be fully deployed in this milestone. The correct approach is to extract business logic from `controller.py` into service classes that have no Streamlit imports. These service classes are then called both from a thin FastAPI router AND from the existing Streamlit `main.py`. This is the refactoring work; running FastAPI as a separate process is a subsequent step.

---

## Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | 0.27.0+ | Async HTTP client for Streamlit → FastAPI calls | When FastAPI runs as a separate process. Not needed if service classes are called directly in the same process. |
| pydantic | 2.x (already via FastAPI) | Request/response schema validation in FastAPI | Required by FastAPI; already used implicitly via openai SDK. |

---

## Installation

```bash
# Deadline tracking + scheduling
pip install APScheduler==3.11.2

# Telegram notifications
pip install python-telegram-bot==22.7

# API layer
pip install "fastapi[standard]==0.135.1"
# uvicorn is included in fastapi[standard]

# httpx (only needed if FastAPI runs as separate process)
pip install httpx==0.27.0
```

**No new dependency for multi-provider LLM** — openai SDK already installed.

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| APScheduler 3.11.2 | schedule library | `schedule` runs in the main thread; blocks Streamlit renders. No persistence. Not suitable for long-running apps. |
| APScheduler 3.11.2 | APScheduler 4.0 alpha | Still in alpha (a6 as of 2025). No stable release. Too risky for a team with no dedicated developer. |
| APScheduler 3.11.2 | Celery + Redis | Massive overkill. Requires a Redis server. Not deployable as a single desktop .dmg. |
| python-telegram-bot 22.7 | aiogram | Designed for interactive bots receiving commands. For outbound-only push, adds unnecessary complexity. |
| python-telegram-bot 22.7 | raw Telegram HTTP API (requests) | No retry logic, no error handling, manual encoding. Not worth reinventing. |
| Thin openai SDK wrapper | LiteLLM | 50+ transitive deps. Solves incompatible-API problems this project doesn't have (all providers speak OpenAI JSON). Adds Streamlit Cloud memory pressure. |
| Thin openai SDK wrapper | LangChain | Designed for chains/agents/RAG. ЮрТэг makes single extraction calls — no chain needed. Even heavier than LiteLLM. |
| FastAPI | Flask | Synchronous by default. No built-in Pydantic validation. FastAPI is the current standard for new Python API projects. |
| FastAPI | Django REST Framework | Server-side rendered framework assumptions. Way too heavy for an internal API layer in a desktop app. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| LiteLLM | 50+ deps, >200MB install with all extras; overkill when all providers are already OpenAI-compatible | Thin `ProviderRouter` wrapper over existing openai SDK |
| LangChain | Adds complexity and weight for what is a single structured prompt call | Direct openai SDK call with configurable `base_url` |
| APScheduler 4.x alpha | Alpha software, breaking API changes expected, no stable docs | APScheduler 3.11.2 (stable branch) |
| Celery | Requires external broker (Redis/RabbitMQ); not compatible with single-process desktop deployment | APScheduler BackgroundScheduler |
| Direct `st.*` calls from APScheduler threads | Raises `NoSessionContext` — scheduler thread has no Streamlit session | Write to SQLite; UI reads on rerender |
| `streamlit-server-state` | Adds a cross-session shared state abstraction — increases complexity; unnecessary when scheduler writes to SQLite | APScheduler + SQLite alert table pattern |

---

## Stack Patterns by Variant

**If deploying on-premise (B2B крупный инхаус):**
- Run FastAPI as a standalone Docker container
- Remove Streamlit dependency from production image
- Mount SQLite file as a Docker volume
- Expose FastAPI on internal network; optionally add an nginx reverse proxy

**If staying desktop-only:**
- Call service classes directly from Streamlit without running FastAPI as a separate process
- FastAPI router stays as dead code ready to activate — zero runtime cost
- APScheduler BackgroundScheduler starts in `main.py` at app launch, runs daemon thread

**If adding local QWEN (Веха 3):**
- Add `ProviderConfig(name="local", base_url="http://localhost:11434/v1", api_key="ollama", model="qwen2.5:1.5b")` to config
- Zero code changes in `ai_extractor.py`

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| APScheduler 3.11.2 | Python 3.8–3.12 | Requires `pytz` for timezone-aware triggers; `tzlocal` recommended |
| python-telegram-bot 22.7 | Python 3.8–3.13 | Requires `httpx` internally; async-only since v20 |
| FastAPI 0.135.1 | Python 3.8–3.13 | Requires `pydantic >=2.0`; fastapi[standard] pins compatible uvicorn |
| openai 1.30.0+ (existing) | All above | No conflicts; openai SDK is the abstraction layer for all LLM calls |

---

## Sources

- [APScheduler PyPI — version 3.11.2 confirmed](https://pypi.org/project/APScheduler/) — MEDIUM confidence
- [APScheduler 3.x User Guide — BackgroundScheduler docs](https://apscheduler.readthedocs.io/en/3.x/userguide.html) — HIGH confidence
- [Streamlit Threading — official docs on ScriptRunContext and background threads](https://docs.streamlit.io/develop/concepts/design/multithreading) — HIGH confidence
- [st.toast — official Streamlit docs, 2025 release notes confirming duration + theme fixes](https://docs.streamlit.io/develop/api-reference/status/st.toast) — HIGH confidence
- [python-telegram-bot PyPI — v22.7 confirmed Mar 16, 2026](https://pypi.org/project/python-telegram-bot/) — HIGH confidence
- [LiteLLM GitHub — 100+ provider support, OpenAI-compatible routing](https://github.com/BerriAI/litellm) — HIGH confidence
- [LiteLLM OpenAI-compatible endpoints docs](https://docs.litellm.ai/docs/providers/openai_compatible) — HIGH confidence
- [FastAPI PyPI — v0.135.1 confirmed](https://pypi.org/project/fastapi/) — HIGH confidence
- [FastAPI + Streamlit two-tier architecture pattern](https://pybit.es/articles/from-backend-to-frontend-connecting-fastapi-and-streamlit/) — MEDIUM confidence
- [python-telegram-bot Bot.send_message docs v22.7](https://docs.python-telegram-bot.org/telegram.bot.html) — HIGH confidence

---

*Stack research for: ЮрТэг Веха 1 — deadline tracking, notifications, multi-provider LLM, API layer*
*Researched: 2026-03-19*
