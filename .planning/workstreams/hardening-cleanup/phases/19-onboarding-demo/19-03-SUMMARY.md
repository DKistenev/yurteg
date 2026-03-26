---
phase: 19-onboarding-demo
plan: 03
subsystem: ui
tags: [nicegui, pywebview, web-mode, fallback]

requires:
  - phase: 12-onboarding
    provides: pick_folder() and _pick_file() native dialog implementations

provides:
  - pick_folder() with try/except (ImportError, AttributeError) — RBST-01 compliant
  - _pick_file() with try/except (ImportError, AttributeError) — RBST-01 compliant
  - ui.notify fallback messages for web mode

affects:
  - app/components/process.py
  - app/pages/templates.py

tech-stack:
  added: []
  patterns:
    - "Local import guard pattern: `import webview` inside try/except (ImportError, AttributeError) for web mode compatibility"

key-files:
  created: []
  modified:
    - app/components/process.py
    - app/pages/templates.py

key-decisions:
  - "Local import guard (not top-level) for webview — allows module import in web environments without pywebview installed"
  - "Catch both ImportError (no pywebview installed) and AttributeError (app.native not initialized) for full web mode coverage"

patterns-established:
  - "RBST-01 pattern: wrap any webview/native dialog call in try/except (ImportError, AttributeError) with ui.notify fallback"

requirements-completed: [RBST-01]

duration: 5min
completed: 2026-03-22
---

# Phase 19 Plan 03: Web Mode Fallback Summary

**pick_folder() and _pick_file() protected with try/except (ImportError, AttributeError) — app no longer crashes in web mode without pywebview**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-22T21:00:00Z
- **Completed:** 2026-03-22T21:05:00Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Removed top-level `import webview` from both `process.py` and `templates.py`
- Wrapped webview dialog calls in try/except (ImportError, AttributeError) with graceful fallback
- Both functions show informative ui.notify messages in web mode and return None safely
- Native mode behaviour unchanged — no regression

## Task Commits

1. **Task 1: Web mode fallback in pick_folder() and _pick_file()** - `167c8c0` (fix)

**Plan metadata:** (see final commit below)

## Files Created/Modified

- `app/components/process.py` - top-level `import webview` removed; pick_folder() wrapped in try/except with ui.notify fallback
- `app/pages/templates.py` - top-level `import webview` removed; _pick_file() wrapped in try/except with ui.notify fallback

## Decisions Made

- Local import guard pattern chosen over conditional import at module level — cleaner, explicit, and prevents ImportError at module load time in web environments

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Both file-picker functions are now web-mode safe
- App can be launched in web mode (streamlit/nicegui without --native) without crashing on folder/file picker calls
- Ready for onboarding demo flow (Phase 19 plans 01, 02) to exercise these paths

---
*Phase: 19-onboarding-demo*
*Completed: 2026-03-22*
