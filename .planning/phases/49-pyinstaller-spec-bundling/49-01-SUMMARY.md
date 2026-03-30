---
phase: 49-pyinstaller-spec-bundling
plan: 01
subsystem: infra
tags: [pyinstaller, onedir, bundle, macos, llama-server, nicegui, torch]

requires:
  - phase: 47-runtime-safety
    provides: hidden imports, freeze_support patterns
provides:
  - "onedir yurteg.spec with COLLECT+BUNDLE, NiceGUI data, torch excludes, llama-server"
  - "Verified .app bundle (1.8 GB) with all required contents"
affects: [50-torch-exclude-validation, 51-github-actions-ci]

tech-stack:
  added: [pyinstaller-6.19.0]
  patterns: [onedir-collect-bundle, binary-copy-at-build-time]

key-files:
  modified: [yurteg.spec, .gitignore]

key-decisions:
  - "onedir mode via COLLECT+BUNDLE for fast startup (no temp extraction)"
  - "Only torch.cuda and torch.distributed excluded (safe); _inductor/_dynamo deferred to Phase 50"
  - "llama-server copied from ~/.yurteg/ at build time with graceful fallback"
  - "PyInstaller 6.x places binaries in Contents/Frameworks/, not Contents/MacOS/"

patterns-established:
  - "Binary bundling: copy to project root at spec execution time, add to binaries list with '.' destination"
  - "NiceGUI packaging: collect_data_files + collect_submodules for both nicegui and webview"

requirements-completed: [BUILD-01, BUILD-02, BUILD-03, BUILD-04]

duration: 13min
completed: 2026-03-31
---

# Phase 49 Plan 01: PyInstaller Spec + Bundling Summary

**Onedir yurteg.spec with COLLECT+BUNDLE, NiceGUI/webview data collection, torch.cuda/distributed excludes, and llama-server binary bundling -- verified 1.8 GB .app bundle**

## Performance

- **Duration:** 13 min
- **Started:** 2026-03-30T22:44:02Z
- **Completed:** 2026-03-30T22:57:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Rewrote yurteg.spec from onefile to onedir mode (COLLECT+BUNDLE pattern) for fast app startup
- Added NiceGUI static files (70 MB) and webview submodules collection -- prevents blank window in frozen app
- Excluded torch.cuda and torch.distributed from bundle (confirmed absent from output)
- Bundled llama-server binary (4.7 MB Mach-O arm64) -- present and executable in .app
- Successfully built .app bundle (1.8 GB) with 464 framework entries confirming onedir mode

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite yurteg.spec** - `f8daeb0` (feat)
2. **Task 2: Build .app and verify bundle + .gitignore** - `097a5c9` (chore)

## Files Created/Modified
- `yurteg.spec` - Rewritten to onedir mode with COLLECT+BUNDLE, NiceGUI/webview data, torch excludes, llama-server binary
- `.gitignore` - Added build/, dist/, llama-server (PyInstaller build outputs)

## Decisions Made
- **PyInstaller 6.x .app structure:** Binaries go to Contents/Frameworks/, data to Contents/Resources/ (not Contents/MacOS/ as older docs suggest). Adjusted verification accordingly.
- **torch excludes scope:** Only torch.cuda and torch.distributed excluded per plan. torch.backends.cuda, numba.cuda, torch._inductor directories remain (pulled via other dependencies) -- safe, deferred to Phase 50 for runtime validation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added build artifacts to .gitignore**
- **Found during:** Task 2 (after build)
- **Issue:** build/, dist/, and llama-server copy appeared as untracked files
- **Fix:** Added to .gitignore
- **Files modified:** .gitignore
- **Committed in:** 097a5c9

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary cleanup, no scope creep.

## Issues Encountered
- PyInstaller 6.x BUNDLE places binaries in Contents/Frameworks/ instead of Contents/MacOS/. The plan's verification script expected Contents/MacOS/llama-server. Adjusted verification to check Frameworks/ path. This is correct behavior for modern PyInstaller -- the main executable is in MacOS/, everything else is distributed across Frameworks/ and Resources/.
- `find -name "cuda" -type d` catches torch.backends.cuda and numba.cuda directories (unrelated to torch.cuda package). The actual torch/cuda/ directory is confirmed absent, meaning the excludes work correctly.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- .app bundle builds successfully, ready for torch exclude runtime validation (Phase 50)
- llama-server bundled and executable, ready for CI download logic (Phase 51)
- Bundle size is 1.8 GB -- torch _inductor/_dynamo excludes in Phase 50 could reduce by ~25 MB

---
*Phase: 49-pyinstaller-spec-bundling*
*Completed: 2026-03-31*
