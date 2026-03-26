---
phase: 10
slug: pipeline-wiring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 10 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Quick run command** | `python -m pytest tests/test_pipeline_wiring.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Native folder picker opens | PROC-01 | OS dialog | Click + Загрузить, verify macOS folder dialog |
| Progress bar updates in real-time | PROC-03 | Visual UI | Process 5+ files, verify bar moves smoothly |
| Table auto-refreshes after processing | PROC-04 | Full NiceGUI runtime | Process files, verify new rows appear |
| Error files shown in log | PROC-04 | Visual | Include invalid file, verify ✗ in log |

**Approval:** pending
