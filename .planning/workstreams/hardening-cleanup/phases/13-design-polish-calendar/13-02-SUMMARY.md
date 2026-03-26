---
phase: 13
plan: 02
subsystem: ui-palette
tags: [design, palette, tailwind, gray-to-slate, indigo, migration]
dependency_graph:
  requires: [13-01]
  provides: [gray-free-ui-pages]
  affects: [registry, document, header, settings, templates, onboarding]
tech_stack:
  added: []
  patterns: [gray→slate neutral ramp migration, bg-gray-900→bg-indigo-600 CTA pattern, transition-colors hover effects]
key_files:
  created: []
  modified:
    - app/pages/registry.py
    - app/pages/document.py
    - app/pages/settings.py
    - app/pages/templates.py
    - app/components/header.py
    - app/components/onboarding/splash.py
    - app/components/onboarding/tour.py
decisions:
  - process.py not migrated — outside plan scope (files_modified list), deferred to separate task
  - progress bar color=grey-9 → color=indigo (Quasar prop), track-color=grey-3 kept (Quasar own grey scale)
  - spotlight outline #111827 → #4f46e5 (indigo-600) — spotlight ring = accent, not neutral
metrics:
  duration: "~6min"
  completed_date: "2026-03-22"
  tasks_completed: 2
  files_modified: 7
---

# Phase 13 Plan 02: Palette Migration (gray→slate + indigo) Summary

Bulk visual migration: replaced all `gray-*` Tailwind classes across 7 `app/pages/` and `app/components/` files with `slate-*` equivalents, and all `bg-gray-900` CTA backgrounds with `bg-indigo-600`. Tour inline JS hex codes also migrated to slate/indigo ramp.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Migrate registry.py, document.py, header.py | 18ab53f | app/pages/registry.py, app/pages/document.py, app/components/header.py |
| 2 | Migrate settings.py, templates.py, splash.py, tour.py | 79b57db | app/pages/settings.py, app/pages/templates.py, app/components/onboarding/splash.py, app/components/onboarding/tour.py |

## What Was Built

**registry.py:**
- `_SEG_ACTIVE`: `bg-gray-900` → `bg-indigo-600` + `transition-colors duration-150`
- `_SEG_INACTIVE`: `text-gray-600` → `text-slate-600`, `hover:bg-gray-100` → `hover:bg-slate-100` + transition
- Folder SVG stroke: `#d1d5db` → `#cbd5e1` (slate-300)
- Empty state: all text/bg gray → slate, CTA button `bg-gray-900` → `bg-indigo-600`
- Segment container: `bg-gray-100` → `bg-slate-100`
- Progress labels: `text-gray-500` → `text-slate-500`, `text-gray-400` → `text-slate-400`
- Delete confirm dialog: `text-gray-500` → `text-slate-500`

**document.py:**
- Metadata grid field labels: `text-gray-400` → `text-slate-400`
- Field values: `text-gray-900` → `text-slate-900`
- Special conditions text: `text-gray-700` → `text-slate-700`
- Deviations inline hex: `#9ca3af` → `#94a3b8`, `#6b7280` → `#64748b`, `#111827` → `#0f172a`
- Nav buttons (back, prev, next): `text-gray-600` → `text-slate-600`, `text-gray-500` → `text-slate-500`
- Section headings (Метаданные, Статус, Пометки юриста): `text-gray-700` → `text-slate-700`
- Page heading (contract_type): `text-gray-900` → `text-slate-900`
- Status reset button: `text-gray-500` → `text-slate-500`
- Versions labels: `text-gray-900` → `text-slate-900`, `text-gray-400` → `text-slate-400`
- No-template notice: `text-gray-500` → `text-slate-500`

**header.py:**
- Header border: `border-gray-200` → `border-slate-200`
- Logo: `text-gray-900` → `text-slate-900`
- Upload button: `text-gray-700` → `text-slate-700`
- Profile button: `text-gray-600` → `text-slate-600`
- Nav links: `text-gray-600` → `text-slate-600`, `hover:text-gray-900` → `hover:text-slate-900`, `hover:border-gray-900` → `hover:border-slate-900` + `transition-colors duration-150`

**settings.py:**
- Left nav: `border-gray-200` → `border-slate-200`, `bg-gray-50` → `bg-slate-50`
- Nav section label: `text-gray-400` → `text-slate-400`
- Nav buttons: `text-gray-600` → `text-slate-600` + `transition-colors duration-150 hover:bg-slate-50`
- Active nav class swap: `text-gray-600` ↔ `text-gray-900` → `text-slate-600` ↔ `text-slate-900`
- Section headings (AI-провайдер, Анонимизация, Предупреждения, Telegram-бот): `text-gray-900` → `text-slate-900`
- Section descriptions: `text-gray-500` → `text-slate-500`
- Checkbox labels: `text-gray-700` → `text-slate-700`
- Connection check button: `text-gray-600` → `text-slate-600`

**templates.py:**
- Empty state labels: `text-gray-400` → `text-slate-400`, `text-gray-300` → `text-slate-300`
- Card: added `transition-colors duration-150 hover:bg-slate-100`
- Card name: `text-gray-900` → `text-slate-900`
- Card type: `text-gray-500` → `text-slate-500`
- Card preview: `text-gray-400` → `text-slate-400`
- Card date: `text-gray-300` → `text-slate-300`
- Dialog headings (edit, delete, add): `text-gray-900` → `text-slate-900`
- Delete dialog subtitle: `text-gray-600` → `text-slate-600`
- Page heading "Шаблоны": `text-gray-900` → `text-slate-900`
- Page subtitle: `text-gray-400` → `text-slate-400`
- Status label (add flow): `text-gray-400` → `text-slate-400`

**splash.py:**
- Logo, headings: `text-gray-900` → `text-slate-900`
- Capability section bg: `bg-gray-50` → `bg-slate-50`
- Bullet dots: `text-gray-400` → `text-slate-400`
- Bullet text: `text-gray-600` → `text-slate-600`
- Progress label: `text-gray-500` → `text-slate-500`
- Progress bar: `color=grey-9` → `color=indigo`
- Step 2 body: `text-gray-500` → `text-slate-500`
- Skip buttons: `text-gray-400 hover:text-gray-600` → `text-slate-400 hover:text-slate-600`
- CTA "Далее: Telegram →": `bg-gray-900` → `bg-indigo-600`
- CTA "Сохранить и начать": `bg-gray-900` → `bg-indigo-600`

**tour.py:**
- Tooltip border: `#e5e7eb` → `#e2e8f0` (slate-200)
- Step counter color: `#9ca3af` → `#94a3b8` (slate-400)
- Title color: `#111827` → `#0f172a` (slate-900)
- Body color: `#6b7280` → `#64748b` (slate-500)
- Skip button color: `#9ca3af` → `#94a3b8` (slate-400)
- Next button background: `#111827` → `#4f46e5` (indigo-600)
- Spotlight outline: `#111827` → `#4f46e5` (indigo-600)

## Success Criteria Verification

1. Zero `bg-gray-900` in app/pages/ and app/components/ — PASS (0 found in .py files)
2. Zero `gray-*` Tailwind classes in plan-scoped files — PASS (0 in all 7 files)
3. All `text-gray-900` headings → `text-slate-900` — PASS
4. Semantic status colors (green, yellow, red) untouched — PASS
5. Hover transitions added to template cards, settings nav, header nav links — PASS

## Deviations from Plan

### Out of Scope (not fixed)

**process.py line 162 — `text-gray-500`:** This file is outside the plan scope (not in `files_modified` list). Logged as deferred item.

## Known Stubs

None — this is a pure palette migration. No data sources, no UI stubs.

## Self-Check: PASSED

- app/pages/registry.py — exists, modified
- app/pages/document.py — exists, modified
- app/components/header.py — exists, modified
- app/pages/settings.py — exists, modified
- app/pages/templates.py — exists, modified
- app/components/onboarding/splash.py — exists, modified
- app/components/onboarding/tour.py — exists, modified
- Commit 18ab53f — Task 1
- Commit 79b57db — Task 2
