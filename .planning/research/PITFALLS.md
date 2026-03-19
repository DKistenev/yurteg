# Pitfalls Research

**Domain:** Legal document management — deadline tracking, multi-provider AI, on-premise deployment
**Researched:** 2026-03-19
**Confidence:** MEDIUM (domain-specific + codebase analysis HIGH; some on-premise enterprise patterns LOW due to single WebSearch sources)

---

## Critical Pitfalls

### Pitfall 1: Deadline Dates Extracted by AI Are Not Validated Before Storing

**What goes wrong:**
AI extracts `date_end` from contract text and stores it raw. Dates come back in a variety of formats ("31 декабря 2025 г.", "31.12.25", "2025-12-31"), some ambiguous, some wrong (hallucinated). The reminder system then fires on invalid dates — or silently never fires because `date_end` is NULL or unparseable. The user sees the reminder feature as broken, and stops trusting the product entirely.

**Why it happens:**
The existing `ai_extractor.py` already has fragile JSON parsing (CONCERNS.md line 41–45). Adding date fields to the same parser compounds the fragility. There is no dedicated date normalization step — dates from AI response are cast to the database schema as-is.

**How to avoid:**
After AI extraction, add a dedicated date normalization pass: parse every candidate date field through `dateutil.parser.parse()` with a fallback to None, store normalized ISO 8601 strings only, log the original raw string for audit. Set `confidence_date_end` flag (LOW/HIGH) based on whether normalization succeeded cleanly. Surface LOW-confidence dates in the UI with a warning before reminders fire.

**Warning signs:**
- Regression test: process 20 real contracts and check that `date_end` is never stored as a non-ISO string
- Any reminder fires on year 1970 or year 2099 (classic epoch/hallucination artifacts)
- AI response parsing error rate above 5% in logs

**Phase to address:** Deadline tracking phase (Milestone 1, before any reminder logic is written)

---

### Pitfall 2: Reminder Logic Built Into Streamlit Session State

**What goes wrong:**
Streamlit is a request-response framework with no persistent background process. If someone adds reminders by polling `datetime.now()` inside a Streamlit callback or by spawning a thread from `main.py`, the reminder check only runs while the browser tab is open. Close the tab — no reminders fire. The feature looks complete in a demo, works in local testing, then silently fails for actual users.

**Why it happens:**
`main.py` is already 1,402 lines with logic interleaved in UI (CONCERNS.md line 7–9). The natural impulse is to add deadline checks directly in the render loop. Streamlit Community Cloud has no persistent process at all.

**How to avoid:**
Decouple reminder state from Streamlit entirely. Store `next_reminder_at` and `reminded_at` in SQLite. Use one of: (a) a separate `scheduler.py` invoked by the user's OS scheduler (cron/Task Scheduler) — zero-dependency, works on-premise, (b) APScheduler as a background thread initialized at app startup with an explicit guard against double-registration. For Telegram channel (if chosen), the scheduler writes to a `pending_notifications` table; a separate lightweight process or cron script polls and delivers. Document that reminders require the app to be running or the scheduler script to be registered.

**Warning signs:**
- Reminder logic lives in any function decorated with `@st.fragment` or called from a render function
- Unit test for reminders requires a running Streamlit server
- Reminder check passes in demo but no one tested overnight with tab closed

**Phase to address:** Deadline tracking phase — architecture decision must be made before first line of reminder code

---

### Pitfall 3: Multi-Provider Abstraction Drifts Into a Custom LLM Framework

**What goes wrong:**
"We need to switch between GLM, Claude, and local QWEN" sounds like it requires a complex abstraction layer. The team builds provider-specific adapters, retry logic per provider, routing rules, and a config system. Three months later the "abstraction" is bigger than the feature it serves, has its own bugs, and no one on the team (3 lawyers, no developer) can debug it. When a provider's API changes, the whole thing breaks.

**Why it happens:**
The codebase already uses `openai` SDK with a base_url override (the correct approach for GLM compatibility). The temptation is to wrap this further. CONCERNS.md line 149–153 flags the existing three-tiered fallback as already hard to reason about.

**How to avoid:**
Do not build a custom abstraction. The `openai` Python SDK with `base_url` + `api_key` parameters already works for GLM, OpenRouter, and any OpenAI-compatible endpoint. For local QWEN (when it arrives in Milestone 3), Ollama exposes an OpenAI-compatible API — same pattern. The entire "multi-provider" feature is: a config entry per provider (name, base_url, api_key env var, model string), a provider selector in `config.py`, and a single factory function `build_client(provider_name) -> openai.OpenAI`. Nothing else. If LiteLLM is considered, be aware it adds ~500µs latency per call and non-trivial deployment complexity with no benefit over the base_url pattern for this use case.

**Warning signs:**
- Any new file called `router.py`, `gateway.py`, or `llm_manager.py`
- Provider-specific classes that inherit from a base `LLMProvider`
- Retry logic duplicated per provider instead of a single `retry_with_backoff()` utility

**Phase to address:** Multi-provider phase (Milestone 1) — enforce the base_url pattern as the only approach before any code is written

---

### Pitfall 4: On-Premise "Readiness" Implemented as an Installer, Not an Architecture

**What goes wrong:**
The team interprets "on-premise readiness" as packaging the app into a .exe or Docker image. The enterprise client IT team installs it and immediately asks: "Where is the audit log? How do we disable external API calls? How do we integrate with AD? How does our security team verify what data leaves the machine?" None of these are answered. The sale fails not because the product is bad but because it lacks enterprise trust signals — the same reason DIRECTUM implementations failed at target accounts (PROJECT.md line 67–68).

**Why it happens:**
CustDev confirmed security is barrier #1 (PROJECT.md line 61). But security for enterprise means specific, auditable answers — not just "it runs locally." The MVP has no authentication, no audit log, and the anonymization pipeline sends text to external APIs (CONCERNS.md line 87–91).

**How to avoid:**
On-premise readiness is a checklist of trust signals, not a deployment format. The minimum viable list for the Крупный инхаус / юроотдел segment: (1) a `--local-only` mode flag that disables all external API calls and forces local LLM only, (2) an append-only `audit.log` recording every file processed, which model was called, and whether data left the machine, (3) a clear UI banner stating what goes to external APIs when local-only mode is off, (4) `config.py` allowing full API endpoint override (so IT can point to an internal proxy). Authentication (AD/LDAP) is Milestone 2+ and must not be bundled into Milestone 1 scope.

**Warning signs:**
- On-premise "done" is declared when Docker image builds successfully
- No `--local-only` flag exists
- Security team's first question ("what data leaves the machine?") takes more than 30 seconds to answer from the UI

**Phase to address:** Architecture/on-premise phase (Milestone 1) — `--local-only` flag and audit log must ship together, not as separate items

---

### Pitfall 5: SQLite Schema Migration Breaks Existing User Databases on Update

**What goes wrong:**
Milestone 1 adds new columns: `date_end`, `date_start`, `status` (active/expiring/expired), `next_reminder_at`, `reminded_at`. The existing silent `try/except OperationalError` migration (CONCERNS.md line 157–158) adds columns if they don't exist — but does not backfill them, does not handle renamed columns, and has no migration tracking. A user who upgrades from MVP loses their processed flag or gets NULL deadlines for all previously processed contracts, with no explanation.

**Why it happens:**
Tech debt already documented in CONCERNS.md. Adding more columns to an already fragile migration system compounds the risk rather than resolving it.

**How to avoid:**
Before adding any new columns, replace the `try/except` migration with a versioned migration table: `CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT)`. Each migration is a numbered function that checks whether it's been applied. This is 50 lines of code and eliminates the entire class of silent migration bugs. Backfill `status = 'active'` for all existing rows when the deadline columns are added (safe default).

**Warning signs:**
- Any `ALTER TABLE` statement inside a `try/except OperationalError` block
- No `schema_migrations` table in the database
- Test that installs MVP, processes files, upgrades to Milestone 1 code, and verifies existing records intact — this test does not exist

**Phase to address:** First thing in Milestone 1, before any feature code — migration infrastructure is a prerequisite for deadline columns

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Inline deadline check in Streamlit render loop | Fast to demo | Reminders only fire with tab open; silent failure in production | Never — reminders require persistent process |
| One `ai_extractor.py` function handles all providers with if/elif | No abstraction layer needed | Provider logic tangled with extraction logic; any API change breaks all providers | MVP only — must refactor before third provider is added |
| Store raw date strings from AI response directly | Skip normalization code | Dates in mixed formats break `ORDER BY date_end`; reminder arithmetic fails | Never — always normalize to ISO 8601 before persistence |
| `try/except OperationalError` for schema additions | Works for adding columns | Masks errors, no rollback, silent data inconsistency on upgrades | MVP only — must replace before Milestone 1 ships |
| Hardcode Telegram bot token in config | Quick notification channel | Token in version control; no rotation mechanism; bot becomes attack surface | Never — token must be in environment variable, not config file |
| Use `datetime.date.today()` without timezone | Simple | Reminder fires at wrong local time for users in non-Moscow timezones | Never if product is distributed; acceptable if strictly single-machine local use |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| GLM / ZAI API | Assume OpenAI error codes map 1:1 | GLM returns different HTTP status codes for rate limits and content policy violations; test error handling against GLM specifically, not just OpenAI |
| OpenRouter fallback | Treat OpenRouter as identical to GLM | OpenRouter adds its own rate limits and may silently route to a different model version; log `model` field from response, not just from request |
| Local QWEN (future) | Assume Ollama OpenAI-compat layer handles all edge cases | Ollama's streaming and function-calling responses have subtle differences; test the full extraction prompt against Ollama before declaring it "works" |
| Telegram notifications | Fire Telegram message synchronously in processing loop | Bot API calls block processing thread and can timeout; write to `pending_notifications` table, deliver asynchronously |
| APScheduler in Streamlit | Start scheduler in module-level code | Streamlit reloads modules on code change; scheduler spawns duplicate threads; must guard with `if 'scheduler_started' not in st.session_state` |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `get_all_results()` on every Streamlit rerender | UI becomes sluggish as contract count grows; database reads on every tab click | `@st.cache_data(ttl=30)` on the query function, invalidate on write | ~500 contracts in SQLite |
| Checking deadline status in Python loop over all contracts | "Expiring soon" filter takes seconds | Add `status` column maintained by DB trigger or update-on-write; use `WHERE status = 'expiring'` SQL query | ~200 contracts |
| NER (Natasha) model reload per file | Processing time grows linearly | Already partially addressed (CONCERNS.md); verify model cached at module level, not inside `process_file()` | From first batch — but noticeable only at ~50 files |
| Scanning full directory tree on every "Refresh" click | Re-hashing large archives is slow | Cache last scan result with modification time check; only re-scan changed files | ~1000 files in source directory |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| No `--local-only` mode | Enterprise client has no way to guarantee data stays on-premise; single security question kills the sale | Implement `LOCAL_ONLY=true` env var that raises an exception if any external HTTP call is attempted; log it |
| Audit trail is missing | On-premise client cannot answer "who processed what when" to their own security team | Append-only `audit.log` (file, not just database) with: timestamp, filename hash, provider used, whether data left machine |
| Telegram bot token stored in `config.py` or `.env` committed to git | Token compromise means attacker can send messages to all users | Token only from environment variable; add `TELEGRAM_BOT_TOKEN` to `.gitignore` check; rotate on any accidental exposure |
| Path traversal via counterparty names in organizer | Malicious filename like `../../etc/passwd` in extracted counterparty field could write outside output_dir | `Path.resolve()` check — verify output path starts with `output_dir.resolve()` before any write |
| External API called even when `local_only=True` | User believes data is local, but validator L5 or fallback model silently calls external provider | All HTTP calls must check `config.LOCAL_ONLY` at call site; write a test that patches `httpx.Client.send` and asserts it's never called in local-only mode |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Reminder shown only in app UI (banner/badge) | Lawyer closes laptop Friday, misses Monday deadline | Default reminder channel: OS notification via `plyer` or `win10toast`; Telegram opt-in for mobile coverage |
| "Истекает через 30 дней" shown without date | Lawyer cannot verify if the reminder is correct | Always show both relative ("через 14 дней") and absolute ("31 марта 2026") |
| Status "истёк" shown with no clear action | Lawyer sees a wall of expired contracts and doesn't know what to do | Group by status; for "истёк" show "требует внимания" with a filter to hide acknowledged items |
| Multi-provider selector exposed as raw API URL input | Non-technical lawyer types wrong URL, gets cryptic connection error | Provider selector is a dropdown (GLM / Claude / Локальная); advanced users get "Свой провайдер" option with URL field |
| "Обрабатывается..." spinner with no progress for 500-file archive | User thinks app crashed after 2 minutes | Show per-file progress (file N of M), ETA based on rolling average speed |

---

## "Looks Done But Isn't" Checklist

- [ ] **Deadline tracking:** AI extracts `date_end` and it displays in UI — but reminders actually fire with the app closed. Verify by closing the app, waiting past a test deadline, reopening, confirming reminder state.
- [ ] **Multi-provider switching:** Provider dropdown switches between GLM and OpenRouter — but error handling was only tested against GLM's response format. Verify by intentionally causing a rate limit error on each provider and confirming graceful fallback.
- [ ] **On-premise mode:** App runs without internet — but the initial startup still pings an external health check or OpenRouter availability check. Verify by starting app with `--local-only` behind a firewall and confirming zero outbound connections.
- [ ] **Schema migration:** Milestone 1 columns added — but existing MVP databases from pre-release testers fail silently on upgrade. Verify by running migration against a SQLite file created by v0.4 code.
- [ ] **Telegram reminders:** Notifications appear in Telegram — but only when the Streamlit session is active. Verify by sending a test reminder from a background process with Streamlit not running.
- [ ] **Status column:** `status` field shows "истекает" — but old contracts processed before the column existed show NULL, not "активен". Verify backfill ran correctly on upgrade.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Reminder fires on hallucinated dates | MEDIUM | Add `confidence_date_end` column; re-run AI extraction with validation prompt on all rows where `confidence_date_end IS NULL`; do not delete old data |
| Streamlit thread-based scheduler spawning duplicates | LOW | Add `scheduler_started` guard in session state; restart app; duplicate threads are harmless but waste RAM |
| SQLite migration corrupts existing data | HIGH | Keep automatic backup (`db_backup_{timestamp}.sqlite`) before any migration runs; restore from backup; fix migration script; re-run |
| LiteLLM (if adopted) causes latency regression | MEDIUM | Remove LiteLLM; revert to direct `openai.OpenAI(base_url=...)` factory; LiteLLM adds no value for this use case |
| API key leaked in committed config | HIGH | Immediately rotate all keys (GLM, OpenRouter, Telegram); audit git history with `git log --all -S "api_key_value"`; add pre-commit hook checking for key patterns |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| AI date extraction not validated | Milestone 1 — deadline feature design | Integration test: process 20 contracts, assert all `date_end` values are ISO 8601 or NULL |
| Reminders only fire with app open | Milestone 1 — deadline architecture decision | Close Streamlit, wait 60s past a test deadline, reopen — reminder state must be correct |
| Custom LLM framework drift | Milestone 1 — multi-provider design | Code review gate: no new file named `router/gateway/manager`; `build_client()` is the only factory |
| On-premise = installer only | Milestone 1 — architecture phase | Security checklist: `--local-only` flag exists, audit log writes, zero external calls in local-only mode |
| SQLite migration breaks existing DBs | Milestone 1 — first task | Migration test against v0.4 SQLite file passes before any feature code merges |
| Path traversal via counterparty names | Milestone 1 — on-premise hardening | Fuzz test: counterparty name `../../etc/passwd` must not write outside output_dir |
| Telegram token in config | Milestone 1 — notification channel | Pre-commit hook or CI check: no string matching `bot[0-9]+:[A-Za-z0-9_-]{35}` in tracked files |

---

## Sources

- CONCERNS.md codebase analysis (2026-03-19) — HIGH confidence, directly observed
- PROJECT.md — CustDev findings on security barriers and СЭД PTSD — HIGH confidence
- [5 Common Document Management Mistakes for Law Firms](https://lexworkplace.com/document-management-mistakes-law-firms/) — MEDIUM confidence
- [How Poor Document Management Leads to Missed Deadlines](https://www.legalsoft.com/blog/poor-document-management-to-missed-deadlines) — MEDIUM confidence
- [Six Common Pitfalls In Legal Tech Adoption](https://www.americanbar.org/groups/law_practice/resources/law-technology-today/2025/six-common-pitfalls-in-legal-tech-adoption/) — MEDIUM confidence
- [Multi-provider LLM orchestration in production: A 2026 Guide](https://dev.to/ash_dubai/multi-provider-llm-orchestration-in-production-a-2026-guide-1g10) — MEDIUM confidence
- [Why Multi-LLM Provider Support is Critical for Enterprises](https://portkey.ai/blog/multi-llm-support-for-enterprises/) — MEDIUM confidence
- [LiteLLM Alternatives: Advanced Solutions](https://mljourney.com/litellm-alternatives-advanced-solutions-for-multi-model-llm-integration/) — LOW confidence (single source)
- [Ten Python datetime pitfalls](https://dev.arie.bovenberg.net/blog/python-datetime-pitfalls/) — HIGH confidence
- [Securely Deploying Streamlit Apps in Your Company](https://medium.com/snowflake-engineering/practical-solutions-for-securely-deploying-streamlit-applications-within-your-company-68735cbe9db2) — MEDIUM confidence
- [Streamlit deployment and data security discussion](https://discuss.streamlit.io/t/streamlit-deployment-and-data-security/47013) — MEDIUM confidence

---
*Pitfalls research for: ЮрТэг — Milestone 1 (deadline tracking, multi-provider AI, on-premise readiness)*
*Researched: 2026-03-19*
