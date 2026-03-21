---
phase: 9
slug: document-detail-card
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | tests/ (existing) |
| **Quick run command** | `python -m pytest tests/test_document_card.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_document_card.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Back button returns to registry | DOC-01 | Navigation in NiceGUI runtime | Click ← Назад, verify registry loads |
| Prev/next switches documents | DOC-03 | URL navigation | Click ◀/▶, verify doc_id changes in URL |
| AI review shows colored deviations | DOC-04 | Visual rendering | Click Проверить, verify colored list appears |
| Lawyer notes autosave on blur | DOC-06 | Focus event behavior | Type note, click away, reload page, verify note persists |
| Redline .docx downloads | DOC-05 | File download via FastAPI | Click Скачать redline, verify .docx opens in Word |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
