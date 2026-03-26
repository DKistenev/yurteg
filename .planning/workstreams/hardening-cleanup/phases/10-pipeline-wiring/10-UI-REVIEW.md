# Phase 10 — UI Review

**Audited:** 2026-03-22
**Baseline:** Abstract 6-pillar standards (no UI-SPEC for this phase)
**Screenshots:** Not captured (no NiceGUI dev server detected — code-only audit)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | All user-facing strings in Russian, specific and action-oriented |
| 2. Visuals | 3/4 | Progress section layout is sound; calendar toggle icons lack text labels |
| 3. Color | 3/4 | Consistent slate/indigo palette; 3 hardcoded hex values in data layer |
| 4. Typography | 3/4 | 5 font sizes in use — one size over the 4-size guideline |
| 5. Spacing | 4/4 | Standard Tailwind scale throughout, no arbitrary values |
| 6. Experience Design | 3/4 | Upload disable/enable and empty state are solid; delete action is a stub |

**Overall: 20/24**

---

## Top 3 Priority Fixes

1. **Delete action is a stub behind a confirmation dialog** — user can reach the "Удалить" menu item, confirm, then see a "Функция удаления доступна в следующей версии" toast. Lawyer loses trust when a destructive confirmation dialog leads to a no-op. Either implement it or hide the menu item entirely until ready — `registry.py:295-333`.

2. **Calendar toggle buttons use icon-only glyphs ("≡", "⊞") without visible labels** — the title prop adds a browser tooltip, but NiceGUI's native WebView does not reliably show native tooltips on hover. First-time users have no affordance for what the buttons do. Add a short visible label (e.g., "Список" / "Календарь") or a persistent tooltip via NiceGUI's `ui.tooltip()` — `registry.py:125-128`.

3. **Progress bar start state shows "0/0 файлов"** — when processing begins, the count label is initialised to `"0/0 файлов"` and only updates after the first 500ms debounce tick. A user who selects a small folder (1-3 files) may never see a meaningful count update before completion. Initialise the label to `""` or `"Подготовка..."` and update to the real count on the first `on_progress` call — `process.py:77`.

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)

No generic English labels found ("Submit", "OK", "Cancel", "Save" — clean). All CTAs are specific Russian phrases: "Загрузить", "Выбрать папку", "Добавить", "Отмена", "Удалить", "Переобработать". Empty state copy is purposeful: "Загрузите первые документы" with a concrete description of what will happen. Toast messages use real numbers: "Обработано N документов (M ошибок)". Error log prefix "✗ {filename}" is direct and unambiguous. The "Скачать оригинал" and "Переобработать" stub items in the action menu use plain informational toasts ("Функция доступна в следующей версии") — acceptable for pre-release, but see Priority Fix 1 for the delete case where a stub behind a confirmation dialog is problematic.

### Pillar 2: Visuals (3/4)

**Strengths:**
- Progress section structure is sound: bar + count on one row, filename below, error log below that. Hierarchy is clear.
- Empty state follows a classic icon/heading/body/CTA/hint pattern with appropriate size contrast (xl heading, sm body, sm hints).
- Upload button uses flat style in the header — appropriately secondary to navigation tabs.
- Error items use expandable `ui.expansion` with red color — correct visual signaling.

**Issues:**
- Calendar toggle buttons `≡` and `⊞` are icon-only glyphs (`registry.py:125-128`). The `title` prop sets an HTML `title` attribute which depends on browser tooltip rendering. In a NiceGUI native WebView (pywebview), hover tooltips are inconsistent. No visible text label exists.
- The `⚙` settings tab in the header (`header.py:41`) is also icon-only. Same concern — no visible label, no `ui.tooltip()` wrapper.
- Progress bar uses NiceGUI's default `ui.linear_progress` styling. There is no indication of animation state (indeterminate spinner for the start phase when total files is not yet known). For 1-3 file batches, the bar jumps from 0 to complete without meaningful intermediate states.

### Pillar 3: Color (3/4)

**Palette:** Predominantly slate (slate-400, slate-500, slate-600, slate-700, slate-900) for text and neutral backgrounds. Indigo-600 (`#4f46e5`) used as the single accent for: active segment pill, empty state CTA button, calendar event color, action icon hover. This is a correct 60/30/10-style application.

**Issues:**
- Three hardcoded hex values exist in `registry.py`:
  - `stroke="#cbd5e1"` (line 63) — SVG inline attribute, acceptable for SVG
  - `ev["color"] = "#94a3b8"` (line 175) — calendar event color set in data dict (FullCalendar API requirement, cannot use Tailwind class)
  - `"color": "#4f46e5"` (line 195) — same: FullCalendar API dict
- The FullCalendar and SVG hex values are technically forced by the APIs involved, not design inconsistency. They map correctly to `slate-300`, `slate-400`, and `indigo-600` in the established palette.
- `text-gray-700` on the upload button (`header.py:54`) — one instance of `gray` instead of `slate`. Minor inconsistency with the otherwise all-slate neutral palette. Should be `text-slate-700`.

### Pillar 4: Typography (3/4)

**Sizes in use across phase 10 files:**
| Size | Count | Usage |
|------|-------|-------|
| text-sm | 13 | Primary body, labels, buttons |
| text-xs | 2 | Secondary labels (filename, error detail) |
| text-lg | 2 | Dialog headings |
| text-xl | 1 | Empty state heading |
| text-base | 1 | Logo "ЮрТэг" |

5 distinct sizes — one over the recommended 4-size limit. `text-lg` is only used in dialogs (`_show_add_dialog`, `_confirm_delete`) and could be replaced with `text-base font-semibold` to reduce to 4 sizes while maintaining visual hierarchy through weight.

**Weights in use:** `font-semibold` (4), `font-normal` (4), `font-medium` (3). Three weights is within a healthy range. No `font-bold` or `font-light` extremes.

**Font family:** IBM Plex Sans loaded globally in `main.py` via Google Fonts CDN. Applied via `* { font-family: 'IBM Plex Sans', sans-serif; }`. Consistent across the entire app.

### Pillar 5: Spacing (4/4)

All spacing uses standard Tailwind scale (multiples of 4px base: 1=4px, 2=8px, 3=12px, 4=16px, 6=24px, 8=32px). Top spacing values in phase 10 files:

| Class | Count | px |
|-------|-------|----|
| px-6 | 5 | 24px |
| gap-1 | 5 | 4px |
| gap-2 | 3 | 8px |
| py-1 | 2 | 4px |
| px-4 | 2 | 16px |
| gap-4 | 2 | 16px |

No arbitrary `[Npx]` or `[Nrem]` values found. The `py-16` on the empty state container (64px vertical padding) is intentional — provides breathing room for the centered empty state. The `py-3` on the progress section gives it enough breathing room without being obtrusive above the table. Consistent with the vertical rhythm in the rest of the app.

### Pillar 6: Experience Design (3/4)

**Upload flow — excellent:**
- Button disabled via `set_enabled(False)` during processing, re-enabled after — `process.py:74,144`
- Guard in header `_on_upload_click` also checks `state.processing` — double protection against concurrent runs
- Progress section hidden by default, shown only during processing — `registry.py:131-132`
- Toast notification with file count and error count — `process.py:124-127`
- Error log stays visible for 10s before auto-hiding — `process.py:140`
- Table auto-refreshes after completion — `registry.py:376-377`
- Error items are expandable (click to reveal reason) — `process.py:161-162`

**Empty state — good:**
- Correctly detected: 0 rows AND no active filters AND segment "all" — `registry.py:390-393`
- Empty state CTA calls `pick_folder` and delegates to `state._on_upload` — same full pipeline flow as header button
- Calendar toggle buttons hidden in empty state (sensible — calendar with no data is meaningless) — `registry.py:396-398`

**Missing / stub states:**
- Delete action: confirmation dialog exists but delete itself is a stub (`registry.py:330-332`). This is a UX anti-pattern — a confirm dialog creates an expectation of action. Either grey out and add "(скоро)" or remove from menu until implemented.
- "Скачать оригинал" and "Переобработать" menu items are stubs with `ui.notify("Функция доступна в следующей версии")` — these are acceptable as no confirmation is implied, but all three stub items together make the context menu feel incomplete.
- No loading spinner during the initial `_init()` async call — between page load and `load_table_data` completion, the grid container is empty with no skeleton or spinner. This is a pre-existing issue from Phase 08, not introduced in Phase 10.
- `start_pipeline` does not handle the case where `process_archive` raises an unhandled exception — no try/except around `await run.io_bound(...)` at `process.py:113-119`. If pipeline_service throws, the upload button stays disabled and progress section stays visible.

---

## Files Audited

- `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/app/components/process.py` (new — Phase 10)
- `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/app/components/header.py` (modified — Phase 10)
- `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/app/pages/registry.py` (modified — Phase 10)
- `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/app/main.py` (modified — Phase 10)
- `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/.planning/phases/10-pipeline-wiring/10-CONTEXT.md`
- `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/.planning/phases/10-pipeline-wiring/10-01-SUMMARY.md`
- `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/.planning/phases/10-pipeline-wiring/10-02-SUMMARY.md`

Registry audit: shadcn not initialized — skipped.
