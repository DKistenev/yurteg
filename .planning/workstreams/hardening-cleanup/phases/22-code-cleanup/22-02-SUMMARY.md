---
phase: 22-code-cleanup
plan: 02
subsystem: testing
tags: [pytest, conftest, proxy, xfail, lifecycle, payments, versioning, design-system]

requires:
  - phase: 22-code-cleanup plan 01
    provides: Deleted Streamlit/desktop_app.py, simplified providers, cleaned AppState

provides:
  - 275 tests passing green with zero failures, zero xfail, zero xpassed
  - Session-scoped proxy env cleanup fixture in conftest.py
  - testpaths=tests in pytest.ini (prevents dataset/ from being collected)
  - All xfail markers removed from lifecycle/payment/versioning tests
  - test_design_polish updated to match NiceGUI+design-system.css reality

affects:
  - phase-23-coverage-expansion
  - any future test additions

tech-stack:
  added: []
  patterns:
    - "Proxy env cleanup: session-scoped autouse fixture in conftest.py clears ALL_PROXY/HTTPS_PROXY/HTTP_PROXY"
    - "pytest.ini testpaths: restricts collection to tests/ only, dataset/ scripts excluded"
    - "Design system tests check design-system.css hex values, not Tailwind classes"

key-files:
  created: []
  modified:
    - tests/conftest.py
    - pytest.ini
    - tests/test_lifecycle.py
    - tests/test_payments.py
    - tests/test_versioning.py
    - tests/test_notifications.py
    - tests/test_design_polish.py

key-decisions:
  - "CLEAN-03: proxy env cleanup is session-scoped (not function-scoped) — httpx client creation happens at import time"
  - "test_design_polish: status CSS assertions moved from app/main.py Tailwind to design-system.css hex values (#f1f5f9 = slate-100)"
  - "test_animation_keyframes: @keyframes row-in removed from CSS (AG Grid 34 conflict), assertions updated to check page-fade-in + stagger delays"
  - "test_payments: rewrote to use actual unroll_payments() API (dict list, not Payment objects)"
  - "test_versioning: rewrote to use actual link_versions(db, cid, group_id) API"

requirements-completed:
  - CLEAN-03

duration: 25min
completed: 2026-03-25
---

# Phase 22 Plan 02: Code Cleanup — Test Suite Summary

**275 tests passing green (zero failures, zero xfail) after fixing proxy env, removing 9 xfail markers, updating 3 test files to match actual service APIs**

## Performance

- **Duration:** 25 min
- **Started:** 2026-03-25T~09:45Z
- **Completed:** 2026-03-25
- **Tasks:** 1
- **Files modified:** 7

## Accomplishments

- Proxy env cleanup fixture added — 10 tests that were failing with `ValueError: Unknown scheme for proxy URL socks5h://` now pass
- All xfail markers removed from test_lifecycle.py (4), test_payments.py (2), test_versioning.py (2), test_notifications.py (1 deleted)
- test_design_polish.py updated to match NiceGUI+design-system.css architecture (no Tailwind in main.py)
- pytest.ini restricted to `testpaths = tests` to stop dataset/ stress test from being collected
- Test count: 275 passing (was 251 passed + 16 failed + 8 xfailed before this plan)

## Task Commits

1. **Task 1: Fix proxy failures and remove xfail markers** - `9f4618c` (fix)

## Files Created/Modified

- `tests/conftest.py` — added `_clear_proxy_env` autouse session-scoped fixture
- `pytest.ini` — added `testpaths = tests`
- `tests/test_lifecycle.py` — removed 4 xfail markers; fixed Database() args; fixed db._conn → db.conn; removed duplicate 3-arg execute() call
- `tests/test_payments.py` — removed 2 xfail markers; rewrote to use `unroll_payments()` + `ContractMetadata.contract_type`
- `tests/test_versioning.py` — removed 2 xfail markers; rewrote to use `link_versions()` instead of nonexistent `link_versions_for_contract()`
- `tests/test_notifications.py` — deleted `test_startup_toast_only_once` (Streamlit placeholder, always-False)
- `tests/test_design_polish.py` — `test_status_css_slate` checks design-system.css hex values; `test_animation_keyframes` updated to current CSS

## Decisions Made

- `_clear_proxy_env` is session-scoped not function-scoped — httpx validates proxy scheme at client construction, which happens once per session
- `test_design_polish.py` test assertions updated to check the actual source of truth (design-system.css hex colors, not Tailwind classes that don't exist in NiceGUI app)
- `@keyframes row-in` was deliberately removed from design-system.css (comment: AG Grid 34 conflict with animation-fill-mode:both) — test updated accordingly

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Database() 2-arg calls in 3 test fixtures**
- **Found during:** Task 1 (removing xfail from lifecycle/payments/versioning)
- **Issue:** All three temp_db fixtures used `Database(tmp_path / "test.db", tmp_path)` but `Database.__init__` only accepts 1 arg (db_path)
- **Fix:** Removed the second argument from all three fixtures
- **Files modified:** tests/test_lifecycle.py, tests/test_payments.py, tests/test_versioning.py
- **Verification:** `TypeError: Database.__init__() takes 2 positional arguments` resolved
- **Committed in:** 9f4618c

**2. [Rule 1 - Bug] Fixed db._conn → db.conn in test files**
- **Found during:** Task 1 (lifecycle + versioning tests)
- **Issue:** Tests used `db._conn` but the Database class exposes `db.conn` (public attribute)
- **Fix:** Replaced all `db._conn` references with `db.conn`
- **Files modified:** tests/test_lifecycle.py, tests/test_versioning.py
- **Committed in:** 9f4618c

**3. [Rule 1 - Bug] Removed duplicate 3-arg execute() call in test_manual_status_override**
- **Found during:** Task 1
- **Issue:** `conn.execute(sql, {"warning_days": 30}, (cid,))` — sqlite3 only takes 2 args. A correct version followed 3 lines later (with the comment "Правильный вызов:"). Removed the bad call.
- **Fix:** Deleted the broken call (lines 83-84 in original), kept the correct named-param version
- **Files modified:** tests/test_lifecycle.py
- **Committed in:** 9f4618c

**4. [Rule 1 - Bug] Rewrote test_payment_unroll to use actual unroll_payments() API**
- **Found during:** Task 1
- **Issue:** Test called `unroll_periodic_payment(contract_id=..., start_date=..., ...)` which doesn't exist. Actual function is `unroll_payments(start, end, amount, frequency, direction)` returning `list[dict]` not `list[Payment]`
- **Fix:** Rewrote test to use correct function name, signature, and return type assertions
- **Files modified:** tests/test_payments.py
- **Committed in:** 9f4618c

**5. [Rule 1 - Bug] Rewrote test_payment_save_and_load to use actual save_payments() API**
- **Found during:** Task 1
- **Issue:** Test called `save_payments(db, payments)` with a list of Payment objects and `get_payments_for_contract` — neither matches the actual API. `save_payments(db, contract_id, meta: ContractMetadata)` and no `get_payments_for_contract` exists.
- **Fix:** Rewrote to create a ContractMetadata and call the correct API; verify via `get_calendar_events()`
- **Files modified:** tests/test_payments.py
- **Committed in:** 9f4618c

**6. [Rule 1 - Bug] Rewrote test_auto_version_linking to use actual link_versions() API**
- **Found during:** Task 1
- **Issue:** Test called `link_versions_for_contract(db, cid2)` which doesn't exist. Actual function is `link_versions(db, contract_id, group_id)`
- **Fix:** Rewrote test to manually call `link_versions(db, cid1, group_id=None)` then `link_versions(db, cid2, group_id=group_id)`, testing that both appear in the version group
- **Files modified:** tests/test_versioning.py
- **Committed in:** 9f4618c

**7. [Rule 1 - Bug] Updated test_design_polish.py assertions to match NiceGUI architecture**
- **Found during:** Task 1
- **Issue:** `test_status_css_slate` asserted Tailwind classes (`bg-slate-100`, `bg-green-50`) in `app/main.py` — but NiceGUI app uses design-system.css with hex values. `test_animation_keyframes` asserted `@keyframes row-in` and `animation-delay: 560ms` — both removed from CSS.
- **Fix:** Updated both tests to check design-system.css hex values and actual keyframe names
- **Files modified:** tests/test_design_polish.py
- **Committed in:** 9f4618c

---

**Total deviations:** 7 auto-fixed (all Rule 1 — bugs in test code)
**Impact on plan:** All fixes were test code corrections to match the actual production API. No production code changed. No scope creep.

## Issues Encountered

- `dataset/v2_stress_test.py` was being picked up by pytest collection and immediately erroring (fixture not found). Fixed by adding `testpaths = tests` to pytest.ini.

## Known Stubs

None.

## Next Phase Readiness

- All 275 tests green — Phase 23 (coverage expansion) can begin against a clean baseline
- No xfail suppressions hiding real problems
- Proxy env isolation in place for all future tests that create OpenAI/httpx clients

---
*Phase: 22-code-cleanup*
*Completed: 2026-03-25*
