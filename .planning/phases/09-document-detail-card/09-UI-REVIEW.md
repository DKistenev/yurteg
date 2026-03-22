# Phase 09 — UI Review

**Audited:** 2026-03-22
**Baseline:** Abstract 6-pillar standards (no UI-SPEC for this phase)
**Screenshots:** Not captured — Playwright could not connect to port 8080 despite HTTP 200 response (NiceGUI app likely requires browser session init before screenshot tool can render)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Russian microcopy is precise; icon-only nav buttons lack visible labels |
| 2. Visuals | 3/4 | Clean Notion-style card layout; icon-only ◀▶ buttons have no tooltip or aria-label |
| 3. Color | 4/4 | Blue accent used only on interactive elements; no arbitrary hardcoded hex outside of justified inline diff renderer |
| 4. Typography | 4/4 | Tight 4-level scale (xs/sm/xl + uppercase labels); consistent slate palette throughout |
| 5. Spacing | 3/4 | Coherent Tailwind scale with no arbitrary values; minor gap-0.5 is a non-standard micro-step |
| 6. Experience Design | 3/4 | Loading spinners on AI review, edge-disabled nav buttons, 4 empty states; no error handling for failed DB or AI calls |

**Overall: 20/24**

---

## Top 3 Priority Fixes

1. **Icon-only prev/next buttons have no tooltip or aria-label** — a lawyer using the app for the first time will not know what ◀ and ▶ do — add `.props('tooltip="Предыдущий документ"')` and `.props('tooltip="Следующий документ"')` to both buttons in `app/pages/document.py` lines 166-175.

2. **No error handling when DB or AI calls fail** — if `get_contract_by_id`, `set_manual_status`, `review_against_template`, or `get_version_group` raises an exception, the UI silently breaks with no user feedback — wrap the awaited calls in `try/except` blocks and surface a `ui.notify(..., type='negative')` message in each failure path.

3. **"Изменить" status button always visible regardless of manual_status state** — the "Сбросить" button correctly appears only when `manual_status` is set, but "Изменить" is always visible even after the manual status is already set, which creates a confusing double-action state — hide "Изменить" when `contract.get('manual_status')` is already set (mirror the same conditional as "Сбросить").

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

The Russian microcopy is a strong point overall. All labels are specific and domain-appropriate:

- "← Назад к реестру" — directional and explicit, not generic "Назад"
- "Проверить по шаблону" — action-specific CTA
- "Добавьте заметку..." — clear placeholder in textarea (document.py:265)
- "Нет шаблонов. Добавьте в разделе Шаблоны" — actionable empty state with link (line 289-290)
- "Версии не найдены" / "Отступлений не найдено" / "Изменений не найдено" — each empty state is unique per context

Issues found:

- `"◀"` and `"▶"` (lines 167, 173) are icon-only button labels with no tooltip, aria-label, or screen-reader text. A first-time user cannot discern these as document navigation without context.
- Section header "Ревью" (line 269) is an abbreviation. "Проверка по шаблону" or "AI-ревью" would be more self-explanatory.
- No error-state microcopy exists anywhere in the file — if an async call raises, the UI produces no message.

### Pillar 2: Visuals (3/4)

The overall layout follows the Notion-style card design specified in context (D-01, 09-CONTEXT.md). Three `ui.card().classes("w-full shadow-none border rounded-lg p-5")` blocks create consistent section framing for metadata, status, and notes. The two collapsible `ui.expansion` sections correctly use Quasar icons (`rate_review`, `history`) for visual differentiation.

The `_render_metadata` helper uses the uppercase tracking-wide label pattern (`text-xs font-medium text-slate-400 uppercase tracking-wide`) consistently across all 7 metadata fields and special conditions — a clean typographic hierarchy.

Issues found:

- `◀`/`▶` buttons have no accessible label. They appear as small flat buttons at the top-right with no tooltip — a UI ambiguity risk for new users.
- The `_render_deviations` inline HTML block (lines 82-92) uses raw `font-size: 11px` and `font-size: 12px` which are outside the Tailwind scale and inconsistent with the rest of the file. This creates a visual scale discrepancy inside the deviation cards vs. all other content.
- The `_render_diff_table` section (lines 95-110) injects a full NiceGUI table inside a column that already has its own padding — no bottom spacing is applied after the table renders, which may cause it to visually collide with subsequent content.

### Pillar 3: Color (4/4)

Color usage is disciplined:

- Accent (blue) is used only on interactive elements: "Изменить", "Применить", "Проверить по шаблону", "Проверить", "Сравнить", template link — 7 occurrences total, all on actionable elements.
- Slate is used for all content hierarchy: `text-slate-900` (primary), `text-slate-700` (secondary), `text-slate-500/400` (labels/disabled).
- Green is reserved for positive empty states ("Отступлений не найдено", "Изменений не найдено") — semantically correct.
- Red appears only in the diff table slot (`text-red-600 line-through`) — semantically correct for deleted content.

The 4 hardcoded hex values in the deviation renderer (`#94a3b8`, `#64748b`, `#0f172a`, `#9ca3af`) are justified by the documented decision to use inline styles for dynamically-colored diff rendering (Pitfall 4, 09-CONTEXT.md). These hex values correspond exactly to Tailwind `slate-400`, `slate-500`, `slate-900`, and `gray-400` — consistent with the overall palette.

### Pillar 4: Typography (4/4)

Font size distribution (4 distinct sizes):
- `text-xs` — 10 uses (metadata labels, version meta, button labels)
- `text-sm` — 11 uses (metadata values, body content, table)
- `text-xl` — 2 uses (document title in header, not-found heading)
- Inline `font-size: 11px` / `12px` / `14px` — 3 uses inside deviation renderer only (justified by dynamic inline style requirement)

Font weight distribution (2 distinct weights):
- `font-medium` — 3 uses (version number, metadata label pattern)
- `font-semibold` — 4 uses (section headings: "Метаданные", "Статус", "Пометки юриста", document title)

This is within the 4-size / 2-weight threshold. The uppercase + tracking-wide label pattern is applied consistently for all secondary labels, providing clear visual hierarchy without introducing additional font sizes.

### Pillar 5: Spacing (3/4)

Tailwind spacing class distribution (top 10):
- `gap-` — 16 uses (primary layout tool)
- `p-` — 6 uses (card padding)
- `py-` — 2 uses (header, version row padding)
- `px-` — 1 use (content column)
- `mx-` — 1 use (auto centering)

No arbitrary `[Xpx]` or `[Xrem]` values found — the file uses only Tailwind scale values.

Issues found:

- `gap-0.5` (line 42, 51) is a non-standard micro-step (`2px`) used for tight label-value stacking inside metadata cells. While functional, `gap-1` (`4px`) is more consistent with the rest of the spacing system. This is a minor inconsistency, not a visual defect.
- The inline `padding: 8px 12px` and `margin-bottom: 8px` in the deviation renderer (lines 83-84) are outside the Tailwind scale — justified by the inline style requirement but worth noting as a spacing inconsistency within the renderer.

### Pillar 6: Experience Design (3/4)

States covered:

- Loading: `ui.spinner('dots')` shown during AI review calls — implemented in two places (`_run_review` line 275, `_do_review` line 318). Spinner is cleared when results render.
- Empty states: 4 distinct, contextually appropriate messages for each content area (document not found, no deviations, no changes, no versions).
- Disabled states: prev/next buttons use `set_enabled(prev_id is not None)` and `set_enabled(next_id is not None)` — correct edge handling.
- Destructive actions: "Сбросить" resets manual status without confirmation. This is the only potentially destructive action and it lacks a confirmation step.

Missing states:

- No error handling anywhere in the async call chain. If `db.get_contract_by_id` raises (DB locked, schema mismatch), or if `review_against_template` raises (AI timeout, network error), the page silently breaks with no user-visible feedback.
- No loading indicator while the page initially loads contract data (`await run.io_bound(db.get_contract_by_id, ...)` at line 128) — the user sees a blank page during initial DB fetch.
- "Изменить" button always renders visible regardless of current manual_status, creating a redundant action when a manual status is already active.

Registry audit: no shadcn — skipped.

---

## Files Audited

- `app/pages/document.py` (364 lines — primary audit target)
- `.planning/phases/09-document-detail-card/09-CONTEXT.md`
- `.planning/phases/09-document-detail-card/09-01-SUMMARY.md`
- `.planning/phases/09-document-detail-card/09-02-SUMMARY.md`
- `.planning/phases/09-document-detail-card/09-01-PLAN.md`
- `.planning/phases/09-document-detail-card/09-02-PLAN.md`
