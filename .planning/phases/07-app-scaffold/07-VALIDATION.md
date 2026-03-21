---
phase: 7
slug: app-scaffold
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | tests/ (existing) |
| **Quick run command** | `python -m pytest tests/test_app_scaffold.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_app_scaffold.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | FUND-01 | unit | `python -c "from app.main import *"` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 1 | FUND-02 | unit | `python -c "from app.state import AppState; s=AppState(); assert s.current_client"` | ❌ W0 | ⬜ pending |
| 07-01-03 | 01 | 1 | FUND-05 | grep | `grep 'reload=False' app/main.py` | ❌ W0 | ⬜ pending |
| 07-02-01 | 02 | 2 | FUND-04 | manual | llama-server process check after close | N/A | ⬜ pending |
| 07-02-02 | 02 | 2 | FUND-03 | unit | `grep 'run.io_bound' app/main.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_app_scaffold.py` — stubs for FUND-01..05
- [ ] NiceGUI installed in requirements.txt

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| llama-server stops on window close | FUND-04 | Requires native window close event | 1. Launch app 2. Close window 3. `ps aux \| grep llama` → 0 results |
| Three tabs visible in native window | FUND-01 | Visual UI check | 1. Launch app 2. Verify Документы · Шаблоны · ⚙ tabs visible |
| Tab switching without page reload | FUND-01 | Visual UI check | 1. Click each tab 2. Verify header stays, content changes |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
