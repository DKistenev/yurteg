# Phase 18: Layout + Visual Fixes - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning
**Mode:** Pre-discussed via user feedback + audit + critique

<domain>
## Phase Boundary

Fix all layout and visual issues identified in v0.7 audit: stats bar broken layout, page centering, footer alignment, logo rework, inactive segments, calendar toggle visibility, CSS cleanup, ARIA labels, dialog restyle.

</domain>

<decisions>
## Implementation Decisions

### Stats Bar Fix (LAY-01, LAY-07)
- Root cause: ui.label() for numbers created BEFORE `with stats_row:` — NiceGUI builds DOM in creation order, labels render outside the flex container
- Fix: Create ALL labels INSIDE `with stats_row:` / `with ui.column().classes(STATS_ITEM):`
- Stats bar bg: remove bg-white, use transparent or match slate-100 page bg — should not look like a separate element
- Horizontal layout: `flex items-center gap-6` with three columns, each containing number (large) + label (small) vertically

### Page Centering (LAY-02, LAY-03, LAY-04)
- Registry: add `max-w-6xl mx-auto` on root column
- Templates: add `max-w-5xl mx-auto` on root column
- Settings: remove `min-h-screen`, use `flex-1` for content height, ensure sidebar doesn't stretch to full viewport

### Footer (LAY-05)
- Change `justify-end` → `justify-center` in main.py:171

### Logo (BRND-01)
- Change: «Ю» → «Юр» in indigo square, «рТэг» → «Тэг» as wordmark
- Square slightly wider to fit 2 characters

### Visual Polish
- Inactive segments (BRND-02): add `bg-white border border-slate-200` to SEG_INACTIVE
- Calendar toggle (BRND-03): add aria-labels, consider text labels «Список» / «Календарь»
- Search input (LAY-06): change max-w-md → max-w-lg
- Dialog «Новое пространство» (PLSH-01): add proper styling, not generic Quasar card
- Templates empty state (PLSH-02): reduce py-20 to py-10, move closer to heading
- hero-enter:nth-child(5) (PLSH-03): add `animation-delay: 400ms` to design-system.css
- Dead CSS (PLSH-04): remove settings-nav-item, stats-item-clickable rules
- ARIA labels (RBST-02): add to stats bar, template cards, empty state CTA
- AG Grid warnings (RBST-03): suppress or fix deprecated API

### Claude's Discretion
- Exact centering breakpoints (6xl vs 7xl)
- Stats bar separator style (· or |)
- Dialog styling details

</decisions>

<code_context>
## Existing Code Insights

### Files to Modify
- app/pages/registry.py — stats bar fix (LAY-01), centering (LAY-02), search (LAY-06)
- app/main.py — footer (LAY-05)
- app/components/header.py — logo (BRND-01), dialog (PLSH-01)
- app/pages/templates.py — centering (LAY-03), empty state spacing (PLSH-02)
- app/pages/settings.py — centering (LAY-04)
- app/styles.py — SEG_INACTIVE (BRND-02)
- app/static/design-system.css — hero-enter fix (PLSH-03), dead CSS (PLSH-04)

### Key Patterns
- NiceGUI elements build DOM in creation order — labels must be created inside their parent container
- Tailwind classes via .classes() method
- styles.py constants for reusable class strings

</code_context>

<specifics>
## Specific Ideas

- User said: "всё прибито влево, как будто пол экрана обрезали"
- User said: "footer почему-то справа, не по центру"
- User said: "нули сверху экрана прибиты, скомкало"
- User said: "уродливая кнопка новое рабочее пространство"

</specifics>

<deferred>
## Deferred Ideas

- Full responsive design for mobile — out of scope for desktop app
- Animated transitions between settings sections

</deferred>
