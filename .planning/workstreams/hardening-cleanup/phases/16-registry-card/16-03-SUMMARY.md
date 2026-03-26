---
phase: 16-registry-card
plan: "03"
subsystem: document-card
tags: [ui, document-card, breadcrumbs, section-dividers, ai-review, timeline]
dependency_graph:
  requires: []
  provides: [CARD-01, CARD-02, CARD-03]
  affects: [app/pages/document.py]
tech_stack:
  added: []
  patterns:
    - breadcrumb nav via ui.label on_click + ui.navigate.to('/')
    - section dividers: uppercase label + 1px border-bottom (SECTION_DIVIDER_HEADER)
    - AI-generated content accent: amber left-border via inline style (AI_REVIEW_BORDER_STYLE)
    - timeline pattern: VERSION_DOT + VERSION_LINE vertical connector
key_files:
  created: []
  modified:
    - app/pages/document.py
    - app/styles.py
decisions:
  - "amber-500 (#f59e0b) для AI-ревью accent — контрастирует с indigo, визуально маркирует AI-контент"
  - "Section dividers через plain ui.label с SECTION_DIVIDER_HEADER — не через ui.card wrapper"
  - "Timeline: VERSION_DOT + VERSION_LINE как отдельные div элементы в колонке"
metrics:
  duration: "~8 min"
  completed: "2026-03-22"
  tasks_completed: 2
  files_modified: 2
---

# Phase 16 Plan 03: Document Card Redesign Summary

**One-liner:** Breadcrumbs, uppercase section dividers, amber AI-review accent, and timeline versions replace flat expansion panels in the document card.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Новые стиль-константы в styles.py | 39bfd44 | app/styles.py |
| 2 | Рерайт document.py | c8787fc | app/pages/document.py |

## What Was Built

**Task 1 — styles.py constants:**
- `BREADCRUMB_LINK / BREADCRUMB_SEP / BREADCRUMB_CURRENT` — breadcrumb navigation tokens
- `SECTION_DIVIDER_HEADER` — text-xs uppercase + pb-2 border-b border-slate-200 section header
- `AI_REVIEW_BLOCK + AI_REVIEW_BORDER_STYLE` — amber left-border 4px accent wrapper
- `META_KEY / META_VAL` — compact key-value metadata tokens
- `VERSION_DOT / VERSION_LINE` — timeline dot and vertical connector line

**Task 2 — document.py rewrite:**
- Replaced old header + ui.expansion panels with inline section layout
- Breadcrumbs row: «Реестр» (clickable, navigates to '/') → {тип документа}, prev/next right-aligned
- 6 sections with SECTION_DIVIDER_HEADER: Сведения, Статус, Пометки юриста, Проверка по шаблону, История версий
- AI-review section wrapped in amber-500 left-border div (visually distinguishes AI content from factual data)
- Versions as timeline: indigo dots with vertical connectors between entries
- All async callbacks (_run_review, _do_review, _show_diff, _apply_status, _clear_status, _save_comment) preserved unchanged

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all sections wired to real data sources.

## Self-Check: PASSED

- app/styles.py — BREADCRUMB_LINK, SECTION_DIVIDER_HEADER, AI_REVIEW_BLOCK, META_KEY, VERSION_DOT all present
- app/pages/document.py — imports without errors, 6 SECTION_DIVIDER_HEADER usages, 0 ui.expansion, breadcrumb navigate.to('/') present, AI_REVIEW_BLOCK+AI_REVIEW_BORDER_STYLE present, VERSION_DOT present
- Commits 39bfd44 and c8787fc confirmed in git log
