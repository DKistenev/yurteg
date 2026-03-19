---
phase: 3
slug: integrations-multitenancy
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | tests/ directory (existing) |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | INTG-04 | unit | `pytest tests/test_notifications.py` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | INTG-01 | unit+integration | `pytest tests/test_telegram_bot.py` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 2 | INTG-02 | unit | `pytest tests/test_telegram_notifications.py` | ❌ W0 | ⬜ pending |
| 03-04-01 | 04 | 3 | PROF-01 | unit+integration | `pytest tests/test_multitenancy.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_notifications.py` — stubs for INTG-04 (st.toast, attention check at startup)
- [ ] `tests/test_telegram_bot.py` — stubs for INTG-01 (file queue, binding, processing)
- [ ] `tests/test_telegram_notifications.py` — stubs for INTG-02 (deadline check, digest send)
- [ ] `tests/test_multitenancy.py` — stubs for PROF-01 (client isolation, DB switching, auto-binding)
- [ ] `tests/conftest.py` — shared fixtures (mock telegram bot, temp DB paths)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Telegram /start flow | INTG-01 | Requires real Telegram API interaction | Send /start to bot, verify code generation, enter code in app |
| st.toast visibility | INTG-04 | Streamlit visual component | Open app with expiring docs, verify toast appears |
| Selectbox switching | PROF-01 | Streamlit UI interaction | Create 2 clients, switch, verify registry changes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
