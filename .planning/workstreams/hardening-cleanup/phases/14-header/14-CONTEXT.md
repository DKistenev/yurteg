# Phase 14: Фундамент — дизайн-система + header - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning
**Mode:** Pre-discussed via milestone gray zone session

<domain>
## Phase Boundary

Establish the design token system (tokens.css with --yt-* variables), integrate with NiceGUI Quasar via app.colors(), set up IBM Plex Sans full weight range with role mapping, enforce @layer discipline, set content background to slate-100, reset NiceGUI default padding, and build the dark chrome header with logo mark, filled CTA, and active tab indicator. This phase is the foundation — every subsequent phase inherits from it.

</domain>

<decisions>
## Implementation Decisions

### Design Tokens & Background
- Background for content zones: slate-100 (#f1f5f9) — white cards "float" above it
- All CSS variables use --yt-* prefix to avoid --fc-* FullCalendar collision
- --nicegui-default-padding: 0 and --nicegui-default-gap: 0 set in :root at start of design-system.css
- Token architecture: tokens.css (values) → design-system.css (behaviors) → styles.py (Python constants)
- Load order in main.py: tokens.css first, then design-system.css, then @layer components
- Enumerate --fc-* FullCalendar variables in DevTools during smoke-test, document in tokens.css comment

### Typography Role Mapping
- Hero: text-4xl font-bold (IBM Plex Sans 700)
- Page title: text-2xl font-semibold (600)
- Section label: text-xs uppercase tracking-wider font-medium text-slate-400
- Body: text-sm font-normal (400)
- Display subtext: font-light (300)
- Expand Google Fonts URL to include weights 300/400/500/600/700

### Header
- Dark chrome band as visual anchor (bg-slate-900 or similar dark)
- Logo mark: indigo rounded-lg square with white «Ю» inside, then «рТэг» in white — like Slack/Notion app icon pattern
- Rename nav: «Документы» → «Реестр»; keep «Шаблоны» and «⚙» as-is
- CTA button «Загрузить документы»: filled indigo (bg-indigo-600 text-white), NOT flat/outline — use Tailwind classes not Quasar color prop (avoids !important)
- Active tab: visible indicator (underline or background highlight), distinct from inactive tabs
- Hover states on all nav items

### @layer Discipline
- All custom CSS in @layer components or @layer overrides
- AG Grid theming via --ag-* CSS variables with .ag-theme-quartz scope only (not in @layer)
- Functional class names (actions-cell, status-*, expand-icon) — NEVER rename, they're JS API contracts

### Claude's Discretion
- Exact dark shade for header (slate-900 vs slate-800 vs custom)
- Exact spacing scale values in tokens
- Shadow scale (sm/md/lg) exact values
- Border radius scale

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- app/styles.py — existing design token constants, HEX dict for AG Grid JS renderers
- app/static/design-system.css — existing CSS with @layer components
- app/main.py — entrypoint with ui.add_head_html for fonts, CSS; app scaffold with ui.sub_pages

### Established Patterns
- IBM Plex Sans loaded via Google Fonts CDN in add_head_html (currently 400/600 only)
- Tailwind classes applied via .classes() on NiceGUI elements
- AG Grid cellRenderer uses JavaScript strings with CSS class references
- app.colors() not yet called — will be new addition
- FullCalendar loaded via CDN, lazy on calendar toggle

### Integration Points
- app/main.py root() — add tokens.css load, app.colors() call, font weight expansion
- app/components/header.py render_header() — full visual rework
- app/static/design-system.css — add @layer overrides section
- app/styles.py — extend with v0.7 semantic constants

</code_context>

<specifics>
## Specific Ideas

- Reference: RunPod.io — "dark chrome + light content" pattern
- Logo mark inspired by Slack/Notion/Figma icon+name pattern
- Stats bar (Phase 16) will be on light background, not dark — header is the ONLY dark element at page level
- AG Grid functional classes freeze: grep app/ before any CSS class rename

</specifics>

<deferred>
## Deferred Ideas

- Full dark mode toggle — separate milestone (requires 2800 LOC audit)
- Gradient on logo mark — decided against, AI-slop risk
- backdrop-filter: blur() — CPU spikes in pywebview macOS

</deferred>
