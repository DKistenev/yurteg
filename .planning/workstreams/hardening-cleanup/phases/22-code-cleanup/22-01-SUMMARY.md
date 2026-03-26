---
phase: 22-code-cleanup
plan: 01
subsystem: codebase
tags: [cleanup, dead-code, streamlit, refactor]
dependency_graph:
  requires: []
  provides: [CLEAN-01, CLEAN-02]
  affects: [modules/ai_extractor.py, config.py, app/state.py, app/styles.py, app/components/ui_helpers.py, app/pages/]
tech_stack:
  added: []
  patterns: [import-from-provider-module, single-source-of-truth]
key_files:
  created: []
  modified:
    - modules/ai_extractor.py
    - config.py
    - modules/reporter.py
    - app/styles.py
    - app/components/ui_helpers.py
    - app/state.py
    - app/pages/document.py
    - app/pages/templates.py
    - app/pages/settings.py
    - tests/test_service_layer.py
    - tests/test_app_scaffold.py
  deleted:
    - main.py
    - desktop_app.py
    - services/registry_service.py
    - app/components/skeleton.py
decisions:
  - "CLEAN-01: Deleted Streamlit main.py (2247 lines) and desktop_app.py — both replaced by NiceGUI app/main.py"
  - "CLEAN-02: _merge_system_into_user moved to providers/openrouter.py as single source of truth"
  - "CLEAN-02: active_model property simplified to return 'glm-4.7' directly (model_dev == model_prod anyway)"
  - "CLEAN-02: AppState reduced from 19 to 16 fields — removed Streamlit-legacy filter_type, filter_status, selected_doc_id"
  - "CLEAN-02: skeleton.py deleted entirely — skeleton_rows and skeleton_card had zero callers"
  - "Test deviation: test_app_scaffold.py updated to match new field count (19 → 16) and remove deleted field assertions"
metrics:
  duration: "~8 min"
  completed: "2026-03-24"
  tasks_completed: 2
  files_changed: 15
requirements:
  - CLEAN-01
  - CLEAN-02
---

# Phase 22 Plan 01: Dead Code Removal Summary

**One-liner:** Deleted 2247-line Streamlit UI + registry_service + skeleton.py; removed duplicate _merge_system_into_user, dead config model toggle, and 15+ unused imports/fields across app/.

## What Was Done

### Task 1: Delete Streamlit UI (CLEAN-01)

Deleted `main.py` (2247-line Streamlit UI) and `desktop_app.py` (pywebview launcher that referenced main.py). Both were dead code since the NiceGUI migration in v0.6. The active entry point `app/main.py` was untouched.

### Task 2: Remove Dead Code (CLEAN-02)

**modules/ai_extractor.py:** Removed the local `_merge_system_into_user()` definition (31 lines) and replaced it with `from providers.openrouter import _merge_system_into_user`. The function existed in both files — now single source of truth in openrouter.py.

**services/registry_service.py:** Deleted entire file. It was a thin wrapper around db.get_all_results() that no NiceGUI code imported. Updated tests/test_service_layer.py to remove the associated test.

**config.py:** Removed `model_dev`, `model_prod`, `use_prod_model` fields. Both model fields were identical ("glm-4.7"), and `use_prod_model` was always False. Simplified `active_model` property to return `"glm-4.7"` directly.

**modules/reporter.py:** Removed two unused inline imports (`DataPoint`, `PatternFillProperties`, `ColorChoice` from openpyxl) that were imported but never called within the same function scope.

**app/styles.py:** Removed 7 unused constants: `BTN_PRIMARY`, `BTN_FLAT`, `TEXT_HEADING_XL`, `TEXT_BODY`, `SECTION_LABEL`, `DIVIDER`, `TEMPLATE_CARD`.

**app/components/ui_helpers.py:** Removed `form_dialog()` and `section_card()` — both had zero callers in any NiceGUI page. Also cleaned up the now-unused `CARD_DIALOG` import.

**app/components/skeleton.py:** Deleted entirely. `skeleton_rows()` and `skeleton_card()` had no callers in the codebase.

**app/state.py:** Removed `filter_type`, `filter_status`, `selected_doc_id` — all three were Streamlit session_state legacy fields with no callers in the NiceGUI app. AppState now has 16 fields (was 19).

**app/pages/document.py:** Removed 7 unused imports: `CARD_SECTION`, `TEXT_SUBHEAD`, `HEX`, `META_KEY`, `META_VAL`, `ACTION_BTN_PRIMARY`, `generate_redline_docx`.

**app/pages/templates.py:** Removed 3 unused imports: `TEXT_MUTED`, `TMPL_EMPTY_ICON`, `APPLE_CARD_ICON`.

**app/pages/settings.py:** Removed 3 unused imports: `TEXT_LABEL_SECTION`, `APPLE_CARD_COMPACT_ICON`, `ENTITY_TYPES`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] Updated test_app_scaffold.py to match new AppState**
- **Found during:** Task 2 (AppState field removal)
- **Issue:** test_app_scaffold.py had hardcoded assertions for 19 fields, and checks for filter_type, filter_status, selected_doc_id defaults that we were removing
- **Fix:** Updated field count assertion (19 → 16), removed assertions for the three deleted fields
- **Files modified:** tests/test_app_scaffold.py
- **Commit:** b6f9068

**2. [Rule 2 - Missing] Removed CARD_DIALOG import from ui_helpers.py**
- **Found during:** Task 2 (form_dialog removal)
- **Issue:** CARD_DIALOG was only used by form_dialog(); after deleting form_dialog(), the import became unused
- **Fix:** Changed `from app.styles import CARD_DIALOG, CARD_DIALOG_SM` to `from app.styles import CARD_DIALOG_SM`
- **Files modified:** app/components/ui_helpers.py
- **Commit:** b6f9068

**3. [Rule 2 - Missing] Cleaned unused imports in test_service_layer.py**
- **Found during:** Task 2 (registry_service test removal)
- **Issue:** After removing test_registry_get_contracts, imports MagicMock, patch, importlib, Path became unused
- **Fix:** Removed those imports
- **Files modified:** tests/test_service_layer.py
- **Commit:** b6f9068

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | 5603dd1 | feat(22-01): delete Streamlit main.py and desktop_app.py (CLEAN-01) |
| Task 2 | b6f9068 | feat(22-01): remove dead code across backend and frontend (CLEAN-02) |

## Known Stubs

None — plan was cleanup only, no new stubs introduced.

## Self-Check: PASSED

- main.py: MISSING (expected) ✓
- desktop_app.py: MISSING (expected) ✓
- services/registry_service.py: MISSING (expected) ✓
- app/components/skeleton.py: MISSING (expected) ✓
- app/main.py: EXISTS ✓
- modules/ai_extractor.py: EXISTS ✓
- config.py: EXISTS ✓
- Commits 5603dd1, b6f9068: verified in git log ✓
- All modules import cleanly: ✓
