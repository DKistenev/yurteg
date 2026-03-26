---
phase: 17-polish
plan: 01
subsystem: templates-ui
tags: [visual, templates, color-coded, badges, empty-state]
dependency_graph:
  requires: []
  provides: [TMPL_TYPE_COLORS, color-coded-template-cards, rich-empty-state]
  affects: [app/pages/templates.py, app/styles.py]
tech_stack:
  added: []
  patterns: [color-coded-left-bar, inline-badge-html, on_add-callback-threading]
key_files:
  created: []
  modified:
    - app/styles.py
    - app/pages/templates.py
decisions:
  - "4px left bar via inline div with style background — not Tailwind border-l-4 (too thin)"
  - "on_add callback threaded through all CRUD paths so empty state CTA always works after edit/delete"
  - "build() uses closure _on_add with cards_ref list pattern to defer container reference"
metrics:
  duration: ~8min
  completed: "2026-03-22"
  tasks_completed: 2
  files_modified: 2
requirements: [TMPL-01, TMPL-02, TMPL-03]
---

# Phase 17 Plan 01: Templates Color-Coded Cards + Rich Empty State Summary

**One-liner:** Color-coded 4px left bar + type icon/badge per document type + rich empty state with CTA on templates page.

## What Was Built

Templates page was the last screen without visual character. This plan brings it in line with registry and card pages from Phase 16.

**Task 1 — TMPL_TYPE_COLORS in styles.py:**
Added `TMPL_TYPE_COLORS` dict with 8 document types, each mapping to `border` color, `badge_bg`, `badge_text`, and `icon` emoji. Added `TMPL_TYPE_DEFAULT` fallback and three empty state style constants (`TMPL_EMPTY_ICON`, `TMPL_EMPTY_TITLE`, `TMPL_EMPTY_BODY`).

**Task 2 — _render_card rewrite:**
- 4px filled left bar as `ui.element('div')` with inline `background` style — border-left would only be 1px
- Header row with emoji icon + bold name
- Colored pill badge (inline HTML span with `border-radius:9999px`) showing type
- Preview text truncated to 200 chars, `line-clamp-3`
- `cursor-default` class activates the design-system.css hover lift rule

**Task 2 — _render_cards empty state (TMPL-03):**
- `ui.icon("description")` 64px slate-300
- Title + description labels
- `ui.button("Добавить первый шаблон")` with `BTN_ACCENT_FILLED` class

**on_add callback threading:**
`_on_add` closure created in `build()`, threaded into `_render_cards`, `_render_card`, `_open_edit_dialog`, `_open_delete_dialog`, `_add_template_flow` — so empty state CTA always calls the same add flow regardless of how templates list empties.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | e5b4ee4 | feat(17-polish-01): add TMPL_TYPE_COLORS palette and empty state tokens to styles.py |
| 2 | 7ec57fc | feat(17-polish-01): color-coded cards, type badges, rich empty state in templates.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] Threaded on_add through all CRUD paths**
- **Found during:** Task 2
- **Issue:** `_open_edit_dialog` and `_open_delete_dialog` called `_render_cards(container)` without `on_add`, so empty state CTA would be missing after last template deleted via those flows
- **Fix:** Added `on_add: callable = None` parameter to both dialog functions and `_add_template_flow`; threaded through all `_render_cards` calls
- **Files modified:** app/pages/templates.py
- **Commit:** 7ec57fc

## Known Stubs

None — all data flows wired. Template cards render real data from DB. Empty state CTA triggers real add flow.

## Self-Check: PASSED

- [x] app/styles.py modified — TMPL_TYPE_COLORS present with 8 types
- [x] app/pages/templates.py modified — width:4px, badge_html, "Добавить первый шаблон" all present
- [x] Commit e5b4ee4 exists
- [x] Commit 7ec57fc exists
- [x] Import verification: `from app.pages.templates import build` — OK
- [x] `len(TMPL_TYPE_COLORS) >= 7` — OK (8 types)
