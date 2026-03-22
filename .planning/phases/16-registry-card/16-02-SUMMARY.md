---
phase: 16-registry-card
plan: "02"
subsystem: registry-ui
tags: [empty-state, onboarding, CTA, capability-cards, REGI-04]
dependency_graph:
  requires: [16-01]
  provides: [rich-empty-state, registry-onboarding-CTA]
  affects: [app/pages/registry.py]
tech_stack:
  added: []
  patterns: [inline SVG capability cards, BTN_ACCENT_FILLED filled CTA, hero-zone pattern from Phase 15]
key_files:
  created: []
  modified:
    - app/pages/registry.py
decisions:
  - "Rich empty state inline (no empty_state() helper) — direct NiceGUI render for full layout control"
  - "BTN_ACCENT_FILLED reused from styles.py — consistent with header CTA pattern"
  - "Capability cards: 3-column flex-wrap, max-w-2xl, border/rounded-xl — matches design system card pattern"
metrics:
  duration: "~3 min"
  completed: "2026-03-22T19:45:57Z"
  tasks_completed: 1
  files_modified: 1
---

# Phase 16 Plan 02: Rich Empty State Summary

**One-liner:** Rich onboarding empty state for registry: hero icon + heading + filled indigo CTA + 3 inline capability cards (extract metadata / sort by folders / check deadlines).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Rich empty state — CTA + три карточки возможностей | fdca665 | app/pages/registry.py |

## What Was Built

**Task 1 — app/pages/registry.py:**
- Replaced `_render_empty_state` body: old version used `empty_state()` helper with hints list; new version renders inline NiceGUI layout for full visual control
- Hero zone: indigo-50 rounded icon anchor (64x64), h2 heading "Загрузите первые документы", p description
- CTA button "Выбрать папку" — uses `BTN_ACCENT_FILLED` from styles.py, sized `text-base px-8 py-3` for visual prominence
- 3 capability cards in `ui.row().classes("gap-4 w-full max-w-2xl justify-center flex-wrap")`:
  1. **Извлечём метаданные** — indigo document icon, "Тип, контрагент, суммы, сроки — автоматически из PDF и DOCX"
  2. **Разложим по папкам** — indigo folder icon, "Структура по типам документов и контрагентам создаётся автоматически"
  3. **Проверим сроки** — indigo clock icon, "Уведомления об истечении договоров — никаких пропущенных дедлайнов"
- Cards: `bg-white border border-slate-200 rounded-xl p-5`, flex-1 with min/max-w constraints for responsive wrap
- `_on_pick_folder` callback preserved identically — no regression in pipeline trigger
- Added `BTN_ACCENT_FILLED` to the styles import line

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. CTA wires to `_on_pick_folder` → `pick_folder()` → `state._on_upload()` — same functional path as before.

## Self-Check: PASSED

- `app/pages/registry.py` — contains `CAPABILITIES`, "Извлечём метаданные", "Разложим по папкам", "Проверим сроки", `BTN_ACCENT_FILLED`
- `python3 -c "import app.pages.registry"` — OK
- Commit fdca665 exists in git log
