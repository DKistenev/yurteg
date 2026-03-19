# Feature Research

**Domain:** Legal document processing / contract lifecycle management (desktop, local-first, Russian SMB market)
**Researched:** 2026-03-19
**Confidence:** MEDIUM-HIGH — CLM/legal DMS patterns verified across multiple authoritative sources; Russian market specifics inferred from general patterns + CustDev data

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that are standard across legal document management products. Missing them makes the product feel unfinished relative to alternatives users have seen.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Document status display | Every CLM shows where a contract is in its lifecycle. Users can't work with a "black box" registry | LOW | Status enum: черновик / на согласовании / подписан / действует / истекает / истёк / расторгнут |
| Expiry date tracking | Core metadata field in every contract registry. Without it, the registry is just a file list | LOW | Already extracted by AI pipeline; needs surfacing in UI and filtering |
| Visual expiry warnings in registry | Color-coded rows (red = expired, yellow = expiring soon) are standard in every CLM tool | LOW | Purely UI — flag rows based on date diff from today |
| Configurable reminder threshold | Users expect to set "notify me 30/60/90 days before expiry" — industry standard is 30–90 days | LOW | Simple integer config field per user or per document type |
| In-app reminder panel | A "что требует внимания" section on the main screen listing approaching deadlines | MEDIUM | Requires scheduler check on app launch or periodic poll |
| Manual status override | Users need to mark a document "расторгнут" or "приостановлен" regardless of dates | LOW | Simple dropdown edit in registry row |
| Filter/sort registry by status | Status is useless if you can't filter by it | LOW | Already have filters; extend to status field |

### Differentiators (Competitive Advantage)

Features that go beyond what SMB-oriented legal tools in Russia typically offer. These align with ЮрТэг's core value prop: zero-onboarding, local processing, AI-powered.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Telegram-канал для уведомлений | Russian legal professionals live in Telegram. Push notifications via bot reach them even when app is closed — no email check needed | MEDIUM | python-telegram-bot + APScheduler; requires user to set up bot token once. Works as async companion to in-app panel |
| AI-confidence score per field | Show which extracted metadata is uncertain — users trust AI more when it's honest about gaps. 75–90% accuracy on clauses, 90–95% on dates/parties | LOW | Already partly implemented in validator (L1–L5); expose confidence visually in UI |
| Мульти-провайдер AI с автоматическим fallback | Resilience: if GLM is down, switch to OpenRouter or local model without user action. Also enables on-premise deployment (local LLM only) | MEDIUM | LiteLLM covers 100+ providers with OpenAI-compatible interface; drop-in for current openai SDK calls. Key for B2B enterprise segment |
| Статус "истекает" с настраиваемым окном | Smart status: document automatically moves to "истекает" N days before expiry, giving legal team lead time. Competitors require manual reminders | LOW | Derived from expiry date + config threshold; no new data needed |
| Batch status update | Update 20 documents' status at once after a signing session — saves time vs row-by-row | MEDIUM | Multi-select in registry + bulk action |
| Deadline history log | Record of when reminders were sent and acknowledged — useful for compliance ("мы уведомляли") | MEDIUM | Append-only log table in SQLite; simple to add but rarely found in SMB tools |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Email-уведомления | Familiar channel, "professional" | Requires SMTP config, email server, adds dependency. Users in Russian SMB don't check work email reliably. Infrastructure complexity for zero-onboarding product | Use Telegram bot (mobile push, zero server infra) + in-app panel |
| Автоматическое продление статуса через внешние API | "Smart" — pulls updated contract state from counterparty systems | Requires integration agreements, counterparty API access, legal liability for sync errors. Scope explosion | Manual status override with reminder to review |
| Workflow-based approval routing | CLM platforms like Agiloft/Ironclad offer this | Full approval routing requires user accounts, permissions, notifications to multiple parties — this is a 6-month project, not a feature | Focus on single-user + small team use case. Multi-user is веха 2+ |
| Версионирование документов | "What changed between v1 and v2?" | Requires storing multiple file versions, diff UI, storage costs. Already explicitly out of scope per PROJECT.md | Show AI extraction confidence; flag when document is re-processed |
| Real-time sync / collaborative registry | "Like Google Sheets" | Requires backend server, auth, conflict resolution — breaks local-first architecture | Export to Excel remains the sharing mechanism for v1 |
| Push-уведомления ОС (Windows/macOS) | Native desktop alerts | Streamlit apps run in browser — OS-level push requires a background service (tray app), separate install, different tech stack | In-app panel on launch + Telegram bot is sufficient and simpler |
| Облачный бэкап / синхронизация | "Don't lose my registry" | Security barrier (data leaves device) — identified as #1 adoption blocker in CustDev. Contradicts local-first positioning | Document local backup instructions; offer export to Excel as portable format |

---

## Feature Dependencies

```
[Статус документа]
    └──requires──> [Expiry date extraction] (already in AI pipeline)
    └──requires──> [Manual status override UI]

[In-app reminder panel]
    └──requires──> [Статус документа]
    └──requires──> [Configurable reminder threshold]
    └──requires──> [Scheduler (APScheduler or launch-time check)]

[Telegram-уведомления]
    └──requires──> [In-app reminder panel] (same logic, different delivery)
    └──requires──> [Scheduler running when app is open]
    └──enhances──> [Configurable reminder threshold]

[Мульти-провайдер AI]
    └──requires──> [Provider config in config.py]
    └──requires──> [LiteLLM or equivalent abstraction]
    └──enhances──> [On-premise deployment readiness]

[Batch status update]
    └──requires──> [Manual status override UI]
    └──requires──> [Multi-select in registry]

[Deadline history log]
    └──requires──> [In-app reminder panel] (events to log)
    └──requires──> [New SQLite table: reminder_log]
```

### Dependency Notes

- **Статус документа requires expiry date extraction:** The entire status lifecycle (истекает / истёк) is computed from `expiry_date` already extracted by AI. No new extraction needed — only UI and DB column for manual override.
- **Telegram requires scheduler:** Notifications only fire if something is checking deadlines periodically. APScheduler's BackgroundScheduler works inside Streamlit but has known caveats (ReportContext warnings in logs, multiple instances if page reloads). Safer approach: check on app launch + offer Telegram as push channel that fires from the scheduler.
- **Мульти-провайдер requires LiteLLM:** Current code uses openai SDK directly against GLM endpoint. LiteLLM wraps openai SDK — drop-in replacement with `litellm.completion()` instead of `client.chat.completions.create()`. One import change unlocks 100+ providers + Ollama local models.
- **Telegram conflicts with OS push notifications:** Building both in v1 is over-engineering. Telegram is the right choice for Russian market — higher Telegram penetration than email engagement among legal professionals.

---

## MVP Definition

### Launch With (v1 — текущая веха)

Minimum set that makes deadline tracking feel complete and usable.

- [ ] Статус документа — 7 статусов + цветовая индикация в реестре — *without this, the registry is a static list*
- [ ] Configurable reminder threshold (30/60/90 days) — *simplest config field, high user value*
- [ ] In-app "требует внимания" panel on app launch — *passive reminder, zero setup required from user*
- [ ] Manual status override — *users need to correct AI or reflect real-world changes*
- [ ] Filter registry by status — *status is useless without filterability*
- [ ] Мульти-провайдер AI через LiteLLM — *architectural requirement for on-premise B2B, GLM fallback, future local LLM*

### Add After Validation (v1.x)

Add when core is stable and first users are active.

- [ ] Telegram-уведомления — *trigger: users ask "can I get notified when I'm not in the app?"*
- [ ] AI-confidence score visible in UI — *trigger: users report errors they couldn't anticipate*
- [ ] Deadline history log — *trigger: compliance-oriented user segment grows*

### Future Consideration (v2+)

- [ ] Batch status update — *trigger: users with 500+ documents, currently out of scale*
- [ ] Multi-user registry access — *requires auth, backend, breaks local-first; defer to веха 2*
- [ ] Email-уведомления — *only if Telegram adoption is too low among target users*

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Статус документа (7 states + color) | HIGH — 6/9 named status | LOW | P1 |
| Configurable reminder threshold | HIGH — 5/9 unprompted | LOW | P1 |
| In-app reminder panel | HIGH — solves "пропустили срок" | MEDIUM | P1 |
| Manual status override | HIGH — AI isn't always right | LOW | P1 |
| Filter by status | HIGH — unusable without it | LOW | P1 |
| Мульти-провайдер AI (LiteLLM) | HIGH for B2B segment | MEDIUM | P1 |
| Telegram-уведомления | MEDIUM — high value, optional setup | MEDIUM | P2 |
| AI-confidence score in UI | MEDIUM — addresses trust barrier | LOW | P2 |
| Deadline history log | LOW for SMB, HIGH for enterprise | MEDIUM | P2 |
| Batch status update | LOW for current scale | MEDIUM | P3 |

**Priority key:**
- P1: Must have for this milestone
- P2: Should have, add when stable
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | Juro / Ironclad (global CLM) | КонсультантПлюс / СЭД (RU enterprise) | ЮрТэг Approach |
|---------|------------------------------|----------------------------------------|----------------|
| Document status | Full workflow states + approval routing | Document card with status field | 7 statuses, manual override, AI-computed expiry state |
| Deadline reminders | Email + in-app + calendar integration | Email + internal notifications | In-app panel + Telegram (no email infra required) |
| Reminder threshold | Configurable per contract | Fixed or per system config | Configurable globally + per document type (v1: global) |
| AI metadata extraction | Proprietary NLP, cloud only | Rule-based, no AI | Local-first, LLM-powered, anonymized before API call |
| Multi-provider AI | Single vendor | N/A | LiteLLM abstraction: GLM + OpenRouter + Ollama |
| On-premise | Enterprise tier, complex | Standard deployment | Designed-in from architecture layer |
| Pricing | $500–2000+/mo | License + integration project | 2 990–19 990 ₽/мес B2B, 490 ₽ B2C |

**Key insight:** Global CLMs (Juro, Ironclad) over-engineer for Russian SMB — complex onboarding, cloud-only, dollar pricing. Russian enterprise СЭД (DIRECTUM, Docsvision) are over-engineered in opposite direction — heavy IT projects, no AI. ЮрТэг's differentiation space is: AI-powered + zero-onboarding + local-first + affordable. Status tracking and deadline reminders are the features that make that value tangible day-to-day.

---

## Sources

- [Best Contract Lifecycle Management Software Features 2026 — ContractSafe](https://www.contractsafe.com/blog/best-contract-lifecycle-management-software-features-2026) (MEDIUM confidence — secondary source)
- [10 Must-Have CLM Features — Agiloft](https://www.agiloft.com/blog/the-10-clm-features-you-absolutely-need-and-why-they-matter/) (MEDIUM confidence)
- [Contract Expiration Best Practices — Juro](https://juro.com/learn/contract-expiration) (MEDIUM confidence)
- [Contract Status Tracking — MyDock365](https://www.mydock365.com/contract-status) (MEDIUM confidence)
- [LiteLLM Documentation — BerriAI](https://docs.litellm.ai/) (HIGH confidence — official docs)
- [LiteLLM GitHub — 33k+ stars, production adoption](https://github.com/BerriAI/litellm) (HIGH confidence)
- [APScheduler + Streamlit — Community discussion](https://discuss.streamlit.io/t/is-it-possible-to-include-a-kind-of-scheduler-within-streamlit/31279) (MEDIUM confidence — community forum, known caveats)
- [Notification UX Best Practices — Smashing Magazine](https://www.smashingmagazine.com/2025/07/design-guidelines-better-notifications-ux/) (MEDIUM confidence)
- [Adding Telegram Bot Notifications for Task Deadlines — Medium](https://medium.com/@ewho.ruth2014/adding-telegram-bot-notifications-for-task-deadlines-41981bb0957c) (LOW confidence — blog post, verify implementation details)
- CustDev findings (9 interviews, 3 real + 6 synthetic) — HIGH confidence for validated patterns, LOW confidence for specific numbers

---

*Feature research for: ЮрТэг — legal document processing, deadline tracking milestone*
*Researched: 2026-03-19*
