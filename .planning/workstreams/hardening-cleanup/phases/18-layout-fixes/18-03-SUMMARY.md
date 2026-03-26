---
phase: 18-layout-fixes
plan: "03"
subsystem: ui
tags: [layout, css, polish, footer, segments, calendar]
dependency_graph:
  requires: []
  provides: [footer-centered, seg-inactive-styled, calendar-text-labels, hero-enter-5, css-clean]
  affects: [app/main.py, app/styles.py, app/static/design-system.css, app/pages/registry.py]
tech_stack:
  added: []
  patterns: [tailwind-utilities, css-layer-components]
key_files:
  created: []
  modified:
    - app/main.py
    - app/styles.py
    - app/static/design-system.css
    - app/pages/registry.py
decisions:
  - "SEG_INACTIVE hover softened to slate-50 (not slate-100) for cleaner appearance on white background"
  - "Calendar toggle wrapped in pill container bg-slate-100 matching segment bar pattern"
  - "Dead CSS block comment removed entirely — breadcrumb-link kept in its own @layer block"
metrics:
  duration: "~5 min"
  completed: "2026-03-22"
  tasks: 2
  files_modified: 4
---

# Phase 18 Plan 03: Footer + Segments + Calendar + CSS Cleanup Summary

**One-liner:** Footer centered with v0.7.1, inactive segments styled with white bg + border, calendar toggle shows "Список"/"Календарь" text labels, hero-enter extended to 5 children, dead CSS rules removed.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Footer center + v0.7.1, SEG_INACTIVE border, calendar text labels | ed022fb | app/main.py, app/styles.py, app/pages/registry.py |
| 2 | hero-enter:nth-child(5) + delete dead CSS | 4c13afb | app/static/design-system.css |

## What Was Built

**Footer (LAY-05):** Changed `justify-end` → `justify-center` and bumped label to "ЮрТэг v0.7.1".

**SEG_INACTIVE (BRND-02):** Added `bg-white border border-slate-200` so inactive segment buttons are visually distinct from plain text. Hover softened from `slate-100` → `slate-50` for a lighter feel on white.

**Calendar toggle (BRND-03):** Icon-only buttons replaced with pill container `bg-slate-100 p-1 rounded-lg` holding "≡ Список" / "⊞ Календарь" text buttons. Pattern matches the segment bar pill design.

**hero-enter nth-child(5) (PLSH-03):** Added `animation-delay: 400ms` for the 5th hero element — onboarding splash now has 5 staggered children covered.

**Dead CSS removal (PLSH-04):** Removed `.settings-nav-item:not(.settings-nav-active):hover` and `.stats-item-clickable:hover` — neither class is assigned anywhere in the Python codebase. Kept `.breadcrumb-link:hover` in its own `@layer components` block.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- app/main.py contains `justify-center` in footer line: FOUND
- app/main.py contains `v0.7.1`: FOUND
- app/styles.py SEG_INACTIVE has `border border-slate-200`: FOUND
- app/pages/registry.py has `≡ Список` and `⊞ Календарь`: FOUND
- design-system.css has `nth-child(5)`: FOUND
- design-system.css has no `settings-nav-item`: CONFIRMED
- design-system.css has no `stats-item-clickable`: CONFIRMED
- design-system.css keeps `breadcrumb-link`: FOUND
- Commits ed022fb and 4c13afb: exist on branch dev/phase-2-lifecycle
