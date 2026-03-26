---
phase: 10-pipeline-wiring
plan: 01
subsystem: ui
tags: [nicegui, pipeline, async, run.io_bound, call_soon_threadsafe, pywebview, folder-picker]

requires:
  - phase: 07-nicegui-scaffold
    provides: run.io_bound pattern, AppState, NiceGUI app scaffold
  - phase: 08-registry-view
    provides: header.py persistent header component

provides:
  - app/components/process.py with pick_folder() and start_pipeline() functions
  - Upload button in header.py wired to native folder picker
  - Async pipeline trigger via run.io_bound (non-blocking)
  - Thread-safe progress callbacks via loop.call_soon_threadsafe
  - Expandable error log rendered after pipeline completion
  - on_upload callback pattern in render_header signature

affects:
  - 10-02 (registry.py progress section wiring — receives ui_refs from process.py)
  - future phases using header.py (render_header signature now has on_upload param)

tech-stack:
  added: [pywebview 6.1 — for app.native.main_window.create_file_dialog]
  patterns:
    - "loop.call_soon_threadsafe for thread-safe UI updates from ThreadPoolExecutor callbacks"
    - "Debounce pattern via time.monotonic() in progress closure (500ms threshold)"
    - "ui_refs dict pattern: pass UI component references as dict to async runner"
    - "_header_refs module-level dict: export button ref from header for pipeline wiring"
    - "on_upload callback parameter on render_header — cleaner than storing in AppState"

key-files:
  created:
    - app/components/process.py
  modified:
    - app/components/header.py

key-decisions:
  - "on_upload passed as render_header() argument (not stored in AppState) — cleaner typing, no mutable callback in dataclass"
  - "Table refresh deferred to pipeline completion (not per-file) — avoids WebSocket flood at 20+ files"
  - "pywebview installed as explicit dependency (was transitive NiceGUI dep, not in requirements.txt)"
  - "Debounce 500ms on progress UI updates — balances responsiveness vs. WebSocket load"
  - "Error log hides after 10s timer (not immediately) — gives lawyer time to read errors"

patterns-established:
  - "Pattern: process.py as thin async glue — pick_folder + start_pipeline separate functions, no UI rendering"
  - "Pattern: ui_refs dict carries section/bar/count/file_label/error_col/upload_btn refs"
  - "Pattern: _header_refs module-level dict exposes upload_btn for pipeline wiring without props drilling"

requirements-completed: [PROC-01, PROC-02]

duration: 2min
completed: 2026-03-21
---

# Phase 10 Plan 01: Pipeline Trigger Summary

**Native macOS folder picker + async pipeline runner wired to persistent header upload button via run.io_bound and call_soon_threadsafe**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-21T23:23:59Z
- **Completed:** 2026-03-21T23:26:20Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `app/components/process.py` created — `pick_folder()` opens native OS folder dialog, `start_pipeline()` runs pipeline async via `run.io_bound`, `_render_error_log()` renders expandable error items
- `app/components/header.py` updated — `render_header(state, on_upload=None)` extended with upload button that calls `pick_folder()` on click and delegates to `on_upload` callback with selected Path
- Thread-safe progress callbacks via `loop.call_soon_threadsafe` with 500ms debounce; error entries collected in closure; toast notification on completion

## Task Commits

1. **Task 1: Create process.py — folder picker and async pipeline runner** - `0900c3b` (feat)
2. **Task 2: Add upload button to header** - `41f2fff` (feat)

## Files Created/Modified

- `app/components/process.py` — new component: pick_folder(), start_pipeline(), _render_error_log()
- `app/components/header.py` — extended with upload button, on_upload callback param, _header_refs export

## Decisions Made

- `on_upload` passed as `render_header()` argument (not stored in AppState) — cleaner typing, avoids mutable callback in dataclass
- Table refresh deferred to pipeline completion, not per-file — avoids WebSocket flood at 20+ files
- `pywebview` installed explicitly (was implicit transitive NiceGUI dependency)
- Debounce 500ms on progress callbacks — responsive but not flooding

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed pywebview package**
- **Found during:** Task 1 verification
- **Issue:** `import webview` failed — pywebview not installed (transitive NiceGUI dep not present in environment)
- **Fix:** `pip install pywebview` (6.1)
- **Files modified:** none (runtime environment only)
- **Verification:** `python -c "from app.components.process import pick_folder, start_pipeline; print('OK')"` passed
- **Committed in:** 0900c3b (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking — missing dependency)
**Impact on plan:** pywebview is required for native folder picker; install was necessary and unambiguous.

## Issues Encountered

None beyond the pywebview installation.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `process.py` ready with `pick_folder` and `start_pipeline` exports
- `header.py` ready with upload button and `on_upload` callback
- Phase 10-02 needs to: create progress section in `registry.py`, assemble `ui_refs` dict, and call `render_header(state, on_upload=lambda d: start_pipeline(d, state, ui_refs))`
- No blockers

---
*Phase: 10-pipeline-wiring*
*Completed: 2026-03-21*
