# Phase 17: Полировка — templates, settings, анимации, сквозное - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning
**Mode:** Pre-discussed via milestone gray zone session

<domain>
## Phase Boundary

Final polish phase. Rework templates page (color-coded cards with type icons, rich empty state) and settings page (section dividers, sidebar structure). Add animations (page transitions, stagger, micro-interactions, skeleton loading). Add footer. Ensure consistent hover states. Run visual seam check across all screens. Performance budget: transitions < 200ms, no jank on macOS pywebview.

</domain>

<decisions>
## Implementation Decisions

### Templates Page
- Cards with color-coded left border (4px) by document type, type icon in accent color, shadow-md hover lift
- Cards visually distinct from each other at first glance — NOT identical generic cards
- Colored badges for document types (TMPL-02)
- Rich empty state: icon + title + description explaining what templates are and why they matter + CTA «Добавить первый шаблон»
- No backdrop-filter: blur() — CPU spikes on pywebview macOS

### Settings Page
- Sections with uppercase headers (text-xs uppercase tracking-wider) + 1px dividers — same pattern as document card (Phase 16)
- Sidebar: active item highlighted (bg-indigo-50 or similar), not just plain text
- Section descriptions under headers explaining what each section does

### Animations
- Page transitions: Claude's discretion (fade or slide, whichever looks better)
- Stagger effects on cards/rows appearance (ANIM-02) — use .hero-enter pattern from design-system.css
- Micro-interactions on buttons: subtle scale on hover (transform: scale(1.02)), not bounce/elastic
- Skeleton loading: gray pulse blocks while registry data loads — replaces blank white area
- Performance budget: all transitions < 200ms, no jank on macOS pywebview with 50+ elements

### Cross-cutting
- Footer: only version text «ЮрТэг v0.7» — minimal, just closes the page visually
- Consistent hover states on ALL interactive elements (buttons, links, cards, nav items)
- Visual seam check: navigate header→registry→card→templates→settings — all screens must feel like same product
- FullCalendar smoke-test after all CSS changes

### Claude's Discretion
- Page transition type (fade vs slide)
- Skeleton loader exact appearance (pulse rate, block shapes)
- Template card icon selection per document type
- Template card color mapping per type
- Footer positioning (fixed bottom vs content flow)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- app/pages/templates.py — current templates with card grid, CRUD
- app/pages/settings.py — current settings with sidebar, radio buttons
- app/styles.py — TEMPLATE_CARD, SECTION_HEADER, BTN_ACCENT_FILLED constants
- app/static/design-system.css — .hero-enter stagger, @layer components
- app/static/tokens.css — all --yt-* tokens

### Established Patterns
- Template cards use cards_ref list pattern for forward-reference
- Settings nav: ui.button + content.clear() pattern
- SECTION_DIVIDER_HEADER established in Phase 16 (document card)
- Stagger animation established in Phase 15 (splash)

### Integration Points
- app/pages/templates.py — card visual rework
- app/pages/settings.py — section/sidebar rework
- app/static/design-system.css — page transition CSS, skeleton CSS
- app/main.py — footer component, transition wiring
- All pages — hover state consistency audit

</code_context>

<specifics>
## Specific Ideas

- Template type colors: use a small palette of 4-5 distinct colors for different document types
- Skeleton loader: similar to GitHub's loading state — gray rounded blocks that pulse
- Footer should be subtle — small text, muted color, not competing with content

</specifics>

<deferred>
## Deferred Ideas

- Animated counter on stats bar — explicitly removed from requirements
- Full dark mode — separate milestone
- SVG illustrations for empty states — future enhancement

</deferred>
