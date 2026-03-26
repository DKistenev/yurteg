---
phase: 3
slug: integrations-multitenancy
status: draft
nyquist_compliant: true
wave_0_complete: true
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
| 03-01-01 | 01 | 1 | INTG-04 | unit | `pytest tests/test_notifications.py` | Yes (W0) | ⬜ pending |
| 03-02-01 | 02 | 2 | INTG-01 | unit+integration | `pytest tests/test_telegram_bot.py` | Yes (W0) | ⬜ pending |
| 03-03-01 | 03 | 2 | INTG-01 | unit | `pytest tests/test_telegram_bot.py` | Yes (W0) | ⬜ pending |
| 03-04-01 | 04 | 3 | INTG-02 | unit | `pytest tests/test_telegram_bot.py` | Yes (W0) | ⬜ pending |
| 03-05-01 | 05 | 2 | PROF-01 | unit+integration | `pytest tests/test_client_manager.py` | Yes (W0) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_notifications.py` — stubs for INTG-04 (st.toast, attention check at startup)
- [x] `tests/test_telegram_bot.py` — stubs for INTG-01, INTG-02 (file queue, binding, processing, deadline digest)
- [x] `tests/test_client_manager.py` — stubs for PROF-01 (client isolation, DB switching, auto-binding)

Wave 0 test files are created by plan 03-00. File names match plan 03-00 output:
- `test_telegram_bot.py` covers INTG-01 and INTG-02 (bot server + deadline notifications share the same bot infrastructure)
- `test_client_manager.py` covers PROF-01 (client management, not generic "multitenancy")

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Telegram /start flow | INTG-01 | Requires real Telegram API interaction | Send /start to bot, verify code generation, enter code in app |
| st.toast visibility | INTG-04 | Streamlit visual component | Open app with expiring docs, verify toast appears |
| Selectbox switching | PROF-01 | Streamlit UI interaction | Create 2 clients, switch, verify registry changes |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
