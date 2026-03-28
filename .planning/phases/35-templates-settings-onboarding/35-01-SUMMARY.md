---
phase: "35"
plan: "01"
subsystem: "ui-auxiliary-screens"
tags: [templates, settings, onboarding, visual-consistency, verification]
dependency_graph:
  requires: [Phase 33 (design tokens, scroll-to-section)]
  provides: [TMPL-01, SETT-01, ONBR-01]
  affects: [app/pages/templates.py]
tech_stack:
  patterns: [emoji-icons-direct, min-w-0-flex-overflow]
key_files:
  modified: [app/pages/templates.py]
decisions:
  - "Emoji icons rendered directly in div (not via material-icons span) — emojis are Unicode, not Material icon names"
  - "SETT-01 already complete from Phase 33 — no changes needed"
  - "ONBR-01 already functional end-to-end — no changes needed"
metrics:
  duration: "2m 15s"
  completed: "2026-03-28"
  tasks_total: 3
  tasks_completed: 3
---

# Phase 35 Plan 01: Templates, Settings & Onboarding Polish Summary

Template emoji icons rendered directly without material-icons wrapper; settings scroll-to-section and onboarding tour verified working end-to-end from prior phases.

## Tasks Completed

### Task 1: Templates Visual Consistency (TMPL-01) — 9b99914
- Fixed emoji icons: removed `<span class="material-icons">` wrapper from demo card, section headers, and actual card rendering — emojis now render in plain `<div>` with proper sizing
- Added `min-w-0` to flex-1 content columns in both demo and actual cards to prevent text overflow on narrow viewports
- Aligned demo card padding from `p-6` to `p-5` to match actual card layout
- Section header icons sized at 11px, card icons at 16px for visual hierarchy

### Task 2: Settings Scroll-to-Section (SETT-01) — VERIFIED, NO CHANGES
- `_section_header()` accepts `section_id` param, adds `id="settings-section-{id}"` to DOM
- Three section IDs confirmed: `ai`, `processing`, `notifications`
- `_SECTION_IDS` mapping connects Russian nav labels to DOM IDs
- `_switch()` uses `scrollIntoView({behavior:"smooth",block:"start"})`
- Summary cards pass section name to `_switch()` on click
- **Already implemented in Phase 33 (commit ee7058a)**

### Task 3: Onboarding Wizard + Tour E2E (ONBR-01) — VERIFIED, NO CHANGES
- **Splash wizard:** Renders on `first_run_completed == False` in main.py. 2-step flow: Welcome (5-slide carousel) -> Telegram. Both "Пропустить" and "Сохранить и начать" call `_finish()` which sets `first_run_completed=True`.
- **Guided tour:** 5 steps, all DOM targets verified present:
  - `[data-tour='upload']` — header.py line 68
  - `[data-tour='nav']` — header.py line 49
  - `[data-tour='filters']` — registry.py line 497
  - `[data-tour='calendar']` — registry.py line 490
  - `[data-tour='workspace']` — header.py line 87
- Tour triggers after first processing + trust prompt dismissal (registry.py:1340-1361)
- Completion saves `tour_completed=True` via hidden button click
- Header "?" button resets tour flag and navigates to `/`
- **All working, no fixes needed**

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED
