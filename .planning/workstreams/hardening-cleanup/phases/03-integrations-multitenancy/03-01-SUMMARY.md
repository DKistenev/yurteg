---
phase: 03-integrations-multitenancy
plan: "01"
subsystem: notifications
tags: [ui, toast, lifecycle, streamlit, session-state]
dependency_graph:
  requires: [services/lifecycle_service.py, modules/models.py]
  provides: [startup toast notification]
  affects: [main.py, tests/test_notifications.py]
tech_stack:
  added: []
  patterns: [session-state guard, context-manager db access]
key_files:
  created: []
  modified:
    - main.py
    - tests/test_notifications.py
decisions:
  - "Use computed_status field on DeadlineAlert (not alert_type) to count expiring vs expired"
  - "Toast block placed inside `if db_path.exists()` block — uses same context-manager pattern as rest of main.py"
  - "Database fixture in tests uses single db_path arg (no second argument)"
metrics:
  duration: "~5min"
  completed: "2026-03-20"
  tasks_completed: 2
  files_modified: 2
---

# Phase 03 Plan 01: Startup Toast Notification Summary

**One-liner:** st.toast startup alert using get_attention_required() guarded by session_state flag, shown once per session when expiring/expired documents exist.

## What Was Built

Added in-app startup toast to `main.py`: when the app loads with results, it calls `get_attention_required()` once and displays a `st.toast` with counts of expiring and expired documents. The guard flag `startup_toast_shown` in `st.session_state` prevents re-showing on every Streamlit rerun.

Updated `tests/test_notifications.py`: removed xfail markers from two tests that now have real assertions, added a third test (`test_startup_toast_with_alerts`), and kept xfail on the one test that requires actual Streamlit runtime.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add startup toast notification to main.py | 55820b9 | main.py |
| 2 | Update test_notifications.py — remove xfail from implemented tests | 0b68be6 | tests/test_notifications.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Used `computed_status` instead of `alert_type` on DeadlineAlert**
- **Found during:** Task 1
- **Issue:** Plan snippet referenced `a.alert_type` but `DeadlineAlert` dataclass has no such field — it uses `computed_status` ("expiring" | "expired")
- **Fix:** Changed both count lines to `a.computed_status == "expiring"` and `a.computed_status == "expired"`
- **Files modified:** main.py
- **Commit:** 55820b9

**2. [Rule 1 - Bug] Database fixture in tests used wrong constructor signature**
- **Found during:** Task 2
- **Issue:** `Database.__init__` takes one argument (db_path), but fixture called `Database(tmp_path / "test.db", tmp_path)` with two arguments — TypeError
- **Fix:** Removed second argument from Database instantiation in temp_db fixture
- **Files modified:** tests/test_notifications.py
- **Commit:** 0b68be6

## Test Results

```
tests/test_notifications.py::test_startup_toast_flag PASSED
tests/test_notifications.py::test_startup_toast_only_once XFAIL
tests/test_notifications.py::test_no_toast_when_no_alerts PASSED
tests/test_notifications.py::test_startup_toast_with_alerts PASSED
3 passed, 1 xfailed
```

## Self-Check: PASSED

- main.py: FOUND
- tests/test_notifications.py: FOUND
- SUMMARY.md: FOUND
- Commit 55820b9: FOUND
- Commit 0b68be6: FOUND
