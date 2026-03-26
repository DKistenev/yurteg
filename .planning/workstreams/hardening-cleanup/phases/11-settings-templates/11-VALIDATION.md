---
phase: 11
slug: settings-templates
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 11 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Quick run command** | `python -m pytest tests/test_settings_templates.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Left nav switches sections | SETT-01 | Visual UI | Click AI/Обработка/Telegram, verify right panel changes |
| Provider radio buttons save on blur | SETT-02 | File persistence | Change provider, restart app, verify setting persisted |
| Template card preview shows text | TMPL-01 | Visual | Add template, verify 3-line preview on card |
| File picker opens for template | TMPL-02 | OS dialog | Click + Добавить, verify macOS file dialog |
| Telegram status indicator | SETT-04 | Network | Configure bot, click Проверить, verify green dot |

**Approval:** pending
