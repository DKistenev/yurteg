---
phase: 21-ui-fixes
plan: "02"
subsystem: ui
tags: [download, reprocess, fastapi, document-card]
dependency_graph:
  requires: []
  provides: [UIFIX-02, UIFIX-03]
  affects: [app/main.py, app/pages/document.py]
tech_stack:
  added: []
  patterns: [FastAPI route for file download, async reprocess via run.io_bound]
key_files:
  created: []
  modified:
    - app/main.py
    - app/pages/document.py
decisions:
  - "Download route placed after redline route — FastAPI specificity rules ensure /download/redline/{a}/{b} matches before /download/{doc_id}"
  - "Reprocess uses temp dir + os.symlink with shutil.copy2 fallback for Windows compatibility"
  - "force_reprocess=True passed to process_archive to bypass hash-based deduplication"
metrics:
  duration: "5 min"
  completed: "2026-03-25"
  tasks_completed: 1
  files_modified: 2
---

# Phase 21 Plan 02: Download & Reprocess Actions Summary

**One-liner:** FastAPI `/download/{doc_id}` route serving original file bytes, and async `_reprocess()` handler running `process_archive` for a single document via temp-dir symlink.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add /download/{doc_id} route and reprocess handler | 36f8a83 | app/main.py, app/pages/document.py |

## What Was Built

### UIFIX-02: Download PDF route

Added `GET /download/{doc_id}` FastAPI route in `app/main.py` (after the existing redline route at ~line 207). The route:
- Looks up the document by ID via `db.get_contract_by_id`
- Reads bytes from `original_path` on disk
- Returns a `FastAPIResponse` with correct `Content-Type` for PDF/DOCX/DOC
- Sets `Content-Disposition: attachment` so the browser/system downloads the file
- Returns 404 with a clear message if doc or file is missing

The existing `ui.button("Скачать PDF", on_click=lambda: ui.download(f"/download/{doc_id}"))` was already correct — it just had no matching route. Now it does.

### UIFIX-03: Reprocess button handler

Replaced the no-op `ui.navigate.to(f"/document/{doc_id}")` on_click with an `async def _reprocess()` closure defined inside `build()` where `contract`, `doc_id`, `state`, and `run` are in scope.

The handler:
1. Checks `original_path` exists — shows negative notify if not
2. Creates a `tempfile.TemporaryDirectory`
3. Creates a symlink to the original file inside the temp dir (with `shutil.copy2` fallback for Windows/permission errors)
4. Instantiates `Controller(Config())` and calls `process_archive` via `run.io_bound` with `force_reprocess=True`
5. Shows progress/result via `ui.notify`
6. Navigates back to `/document/{doc_id}` to reload updated data

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — both features are fully wired with real data sources.

## Self-Check: PASSED

- `grep "download/{doc_id}" app/main.py` → line 208: `@app.get('/download/{doc_id}')`
- `grep "_reprocess" app/pages/document.py` → lines 231, 270
- `grep "process_archive" app/pages/document.py` → line 255
- `python -c "import ast; ast.parse(open('app/main.py').read())"` → OK
- `python -c "import ast; ast.parse(open('app/pages/document.py').read())"` → OK
- Commit `36f8a83` exists in git log
