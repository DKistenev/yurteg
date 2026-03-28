---
phase: "33"
plan: "01"
subsystem: "frontend-quality"
tags: [a11y, DRY, error-handling, design-tokens, code-quality]
dependency_graph:
  requires: []
  provides: [app/utils.py, format_date_ru]
  affects: [app/pages/settings.py, app/pages/registry.py, app/pages/document.py, app/components/split_panel.py, app/components/bulk_actions.py, app/components/process.py]
tech_stack:
  added: []
  patterns: [CSS custom properties for colors, shared utils module, pre-flight health checks]
key_files:
  created: [app/utils.py]
  modified: [app/pages/settings.py, app/pages/registry.py, app/pages/document.py, app/components/split_panel.py, app/components/bulk_actions.py, app/components/process.py]
decisions:
  - "format_date_ru supports short=True for abbreviated months (split_panel uses short)"
  - "Pre-flight llama-server check warns but does not block pipeline (fallback chain handles)"
  - "Only replaced hex colors with matching --yt-* tokens; left AG Grid JS, SVG, status badges as-is"
metrics:
  duration: "~15 min"
  completed: "2026-03-28"
---

# Phase 33 Plan 01: Code Quality & Error Resilience Summary

**Extracted shared date utils, replaced hardcoded hex with CSS vars, added keyboard a11y to bulk actions, wired settings scroll-to-section, and added error resilience for pipeline failures and llama-server unavailability.**

## Tasks Completed

| # | Task | Commit | Requirement |
|---|------|--------|-------------|
| 1 | Extract _MONTHS_RU + format_date_ru into app/utils.py | 7cba3fd | AUDIT-07 |
| 2 | Replace inline hex with CSS custom properties | 9008b61 | AUDIT-05 |
| 3 | Bulk actions: ui.button with aria-label for a11y | d8fe779 | AUDIT-06 |
| 4 | Settings summary cards scroll to section | ee7058a | AUDIT-04 |
| 5 | Error toast on pipeline failure | 16be4ec | ERRES-01 |
| 6 | Graceful toast when llama-server unavailable | 52bdbd0 | ERRES-02 |

## Decisions Made

1. **format_date_ru API**: Single function with `short=True` parameter replaces two different implementations (full months in document.py, abbreviated in split_panel.py).
2. **AUDIT-05 scope**: Only replaced hex values in settings.py and split_panel.py where matching `--yt-*` tokens exist. Left AG Grid JS preview card (250+ lines of inline JS), SVG strokes, status badge colors, and TMPL_TYPE_COLORS untouched -- they're systematic and scoped.
3. **ERRES-02 behavior**: Pre-flight health check warns user but doesn't block pipeline. The existing provider fallback chain handles actual switching. This avoids false negatives if llama-server starts between check and use.

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None -- all functionality is wired and operational.
