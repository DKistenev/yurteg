---
phase: 8
slug: registry-view
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | tests/ (existing) |
| **Quick run command** | `python -m pytest tests/test_registry.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_registry.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | REG-01 | unit | `python -c "from app.pages.registry import build"` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | REG-04 | grep | `grep 'STATUS_COLORS' app/components/table.py` | ❌ W0 | ⬜ pending |
| 08-02-01 | 02 | 2 | REG-03 | unit | `python -m pytest tests/test_registry.py::test_fuzzy_search -x` | ❌ W0 | ⬜ pending |
| 08-02-02 | 02 | 2 | REG-05 | grep | `grep 'segment' app/pages/registry.py` | ❌ W0 | ⬜ pending |
| 08-03-01 | 03 | 3 | REG-06 | grep | `grep 'cellClicked\|actions' app/components/table.py` | ❌ W0 | ⬜ pending |
| 08-03-02 | 03 | 3 | REG-07 | unit | `python -m pytest tests/test_registry.py::test_version_grouping -x` | ❌ W0 | ⬜ pending |
| 08-03-03 | 03 | 3 | REG-02 | manual | Click row → navigates to /document/{id} | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_registry.py` — stubs for REG-01..07
- [ ] `app/components/table.py` — created (currently missing)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Click row navigates to document | REG-02 | Requires NiceGUI runtime + browser | 1. Launch app 2. Click any row 3. URL shows /document/{id} |
| Hover-actions appear on mouse over | REG-06 | CSS hover state, visual | 1. Hover over row 2. ⋯ and status icon appear |
| Version rows expand/collapse | REG-07 | Interactive UI behavior | 1. Click ▶ on grouped doc 2. Child rows appear with indent |
| Client switch reloads table | SETT-05 | Requires multiple client DBs | 1. Switch client 2. Table shows different documents |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
