# Phase 16: Registry + Card - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning
**Mode:** Pre-discussed via milestone gray zone session

<domain>
## Phase Boundary

Visually rework the two main working screens: registry page (stats bar, filter bar, AG Grid theming, empty state, heading) and document card (breadcrumbs, section dividers, visually distinct metadata/review/versions blocks). Hero-zone pattern validated in Phase 15 — apply to registry header zone.

</domain>

<decisions>
## Implementation Decisions

### Registry Page
- Stats bar: on LIGHT background (slate-100), not dark strip — крупные цифры (STAT_NUMBER from styles.py), separators with «·»
- Filter bar (REGI-06): segment buttons with filled active state — визуально когерентен со stats bar
- Animation guard: row animation must NOT replay on filter segment switch (Pitfall 7)
- AG Grid theming: ONLY via --ag-* CSS variables scoped to .ag-theme-quartz — verify class name in DevTools first
- Heading «Реестр» (renamed from «Документы» in Phase 14) with visual weight (text-2xl font-semibold)
- Rich empty state: CTA «Выбрать папку» + 3 пункта что произойдёт (извлечём метаданные / разложим по папкам / проверим сроки)
- Filled semantic status badges: green (действует), amber (истекает), red (истёк) — filled pills, not text-only
- Functional CSS class names (actions-cell, status-*, expand-icon) — NEVER rename

### Document Card
- Breadcrumbs: «Реестр → {document name}» with ui.navigate.to('/') on click
- Section dividers: uppercase labels (text-xs uppercase tracking-wider) + 1px border-bottom
- Visually distinct blocks:
  - Метаданные: compact key-value pairs (no card wrapper, just structured rows)
  - AI-ревью: amber/orange accent left-border (4px), visually marks "AI-generated content"
  - Версии: timeline-style with vertical line + dots

### Pre-Phase Checks
- DevTools: confirm .ag-theme-quartz class on AG Grid container
- Check load_table_data() return shape for aggregate counts (stats bar needs total/expiring/attention)

### Claude's Discretion
- Exact AG Grid --ag-* variable values for row hover, header, borders
- Stats bar icon choice (if any)
- Empty state icon/illustration
- Breadcrumb separator character (» or / or →)
- AI-ревью accent: amber-500 or orange-500 — pick what looks better with indigo

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- app/pages/registry.py — current registry page with search, segments, AG Grid, empty state, calendar toggle
- app/components/registry_table.py — AG Grid setup, cellRenderer JS strings, functional classes
- app/pages/document.py — current document card with tabs
- app/styles.py — STAT_NUMBER, TEXT_HERO, BTN_ACCENT_FILLED, SECTION_HEADER constants
- app/static/tokens.css — --yt-* design tokens
- app/static/design-system.css — @layer components with card/link styles

### Established Patterns
- AG Grid cellRenderer uses JavaScript strings with CSS class references
- Segments filter via Python-side list comprehension after SQL fetch
- _on_cell_clicked dispatches on colId: actions → menu, has_children → toggle, else → navigate
- document card uses NiceGUI tabs (ui.tab/ui.tab_panels)

### Integration Points
- app/pages/registry.py build() — stats bar + heading above existing search/filter
- app/components/registry_table.py load_table_data() — may need to return counts
- app/pages/document.py build() — restructure from tabs to sections
- app/main.py — no changes needed (routing already works)

</code_context>

<specifics>
## Specific Ideas

- Stats bar on light bg like notion property bar — not a dark strip competing with header
- Empty state similar to current but with more visual weight and clear CTA
- Card sections should feel like reading a document, not navigating tabs

</specifics>

<deferred>
## Deferred Ideas

- Counter animation on stats bar numbers — deferred from requirements
- AG Grid row stagger animation — Phase 17 (ANIM-02)
- Skeleton loader for registry — Phase 17 (ANIM-04)

</deferred>
