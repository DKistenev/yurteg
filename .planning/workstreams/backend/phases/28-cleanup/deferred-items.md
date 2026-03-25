# Deferred Items — Phase 28 Cleanup

## From Plan 28-01

### tests/stress_test.py — validator references

**Found during:** Task 2 final verification
**Issue:** `tests/stress_test.py` (2345 LOC) imports `validate_metadata`, `validate_batch`, `_validate_inn`, `_fuzzy_match` from the now-deleted `modules/validator.py`. Class `TestValidatorStress` (lines 569–1042) and parts of `TestHardEdgeCases` (lines 1574–1800) are fully dedicated to validator testing.
**Scope:** Out of scope for plan 28-01 — stress_test.py is a pre-existing file not listed in `files_modified`. Deleting the entire file would remove unrelated AnonymizationStress, OrganizerStress, LoadStress, IntegrationStress, and AI parsing tests.
**Recommended fix:** Delete `TestValidatorStress` class and validator-related sections from `TestHardEdgeCases`. Keep remaining test classes. Do in a dedicated cleanup task.
**Impact:** `pytest tests/stress_test.py` will fail with ImportError until fixed.
