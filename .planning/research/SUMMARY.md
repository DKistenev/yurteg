# Project Research Summary

**Project:** ЮрТэг v0.7 — Визуальный продукт
**Domain:** Visual design system overhaul for NiceGUI 3.9.0 desktop application
**Researched:** 2026-03-22
**Confidence:** HIGH

## Executive Summary

ЮрТэг v0.7 is a purely visual milestone — no Python dependencies change, no business logic moves. The task is transforming a functional wireframe-grade UI (v0.6) into a product with genuine visual confidence, using the existing NiceGUI 3.9.0 + Tailwind 4 + IBM Plex Sans + indigo/slate palette stack. The recommended approach is a layered design system: CSS custom properties in a new `tokens.css` file establish the single source of truth, `design-system.css` handles behavior (animations, overrides), and `styles.py` keeps Python-side Tailwind constants for components. The visual reference is RunPod.io — dark accent surfaces for hero moments, heavy typography, stat bars with real numbers, filled semantic status badges. No new pip packages are required.

The recommended build sequence is dependency-driven: tokens first (everything inherits from them), then header (persistent across all pages), then splash (isolated, high-impact confidence check), then registry (highest complexity, most user-facing), then document card, then templates and settings together, then a final cross-cutting polish pass. This ordering prevents the most common failure mode — visual changes that break functional behavior because layout structure and visual styling were changed simultaneously.

The key risk is NiceGUI 3.x's CSS layer system. All custom CSS must be wrapped in the correct `@layer` block — rules outside any layer are silently overridden by Quasar's layered CSS with no error. AG Grid lives completely outside NiceGUI's layer system and requires `.ag-theme-quartz` selector scoping and `--ag-*` CSS custom properties for safe theming. Functional class names used by AG Grid cellRenderer JavaScript strings (`actions-cell`, `status-active`, etc.) must never be renamed. Follow these three rules and the visual overhaul is low-risk.

---

## Key Findings

### Recommended Stack

The entire v0.7 overhaul requires zero new Python packages. All tools are in place: NiceGUI 3.9.0 (confirmed installed via `pip show`), Tailwind 4 CDN (bundled by NiceGUI), IBM Plex Sans via Google Fonts (weights 100–700, Cyrillic subset available), Quasar bundled components, AG Grid, FullCalendar. The only "additions" are a new `app/static/tokens.css` file, expanded font weight range in the Google Fonts URL (add 300 and 700), and calling `app.colors()` once at module level in `main.py`.

**Core technologies:**
- **NiceGUI 3.9.0:** UI framework — `app.colors()` (available since v3.6.0) sets Quasar brand CSS variables; no new dependencies needed
- **Tailwind 4 (bundled by NiceGUI):** Layout and spacing via `@layer components` — `@theme` directive is unavailable without a build step; use `@layer components` in `<style type="text/tailwindcss">` blocks
- **CSS custom properties (`:root` in `tokens.css`):** Design token system — single source of truth accessible from CSS, JavaScript AG Grid renderers (via class name lookup), and inline `style=` attributes
- **IBM Plex Sans:** Expand request from 400/600 to 300/400/500/600/700 — one Google Fonts URL parameter change, free
- **AG Grid `--ag-*` CSS variables:** Official AG Grid theming API — avoids specificity fights entirely; use with `.ag-theme-quartz` scope prefix

### Expected Features

**Must have (P1 — milestone incomplete without all of these):**
- Design tokens extended — type scale with 4+ distinct levels and weight spread, spacing scale in `styles.py`
- Dark header band — darkened navigation zone as visual anchor for the entire layout
- Header brand mark + filled accent CTA — "ЮрТэг" at readable size with optional gradient; upload button as filled indigo
- Active tab indicator — visible current-page signal in header navigation
- Stats bar above registry grid — document count, expiring count, requires-attention count
- Status badge color system — filled green/amber/red/slate pills in AG Grid status column
- Card depth hierarchy — shadow-sm / shadow-md / shadow-lg applied consistently
- Hero splash rework — dark background, large headline, visual confidence on first impression
- Section dividers with uppercase labels — settings and document card sections
- Rich empty state — heavier icon, bolder title, descriptive copy

**Should have (P2 — ship in v0.7 if time allows):**
- Accent gradient on brand mark — CSS one-liner, high brand identity value
- Template cards with icon + color accent — visual scan-ability on Templates page
- Micro-copy pass — rewrite all empty states and hints with direct, dry voice
- Footer — version + model status, closes the visual space

**Defer to v0.7.x or later:**
- Animated count-up on stats bar numbers — add after stats bar exists and feels static
- Full dark mode — own dedicated milestone after v0.8 packaging
- Sidebar navigation — architectural change, own milestone

**Anti-features (explicitly rejected — do not add):**
- Full dark mode toggle — doubles CSS surface area; AG Grid has its own separate theme system; partial dark mode creates jarring inconsistencies; must be a dedicated milestone
- Glassmorphism — "AI slop aesthetic" explicitly rejected in project brief; requires non-white background to function at all
- Sidebar navigation — restructures `main.py` and all page files; not a visual change; 3-tab scope does not justify it
- Parallax / scroll animations on splash — RunPod pattern is a marketing page; splash is a setup screen shown once; animation adds friction

### Architecture Approach

Three layers define the design system architecture. `tokens.css` (NEW file) contains only CSS custom property values — primitive palette (`--color-indigo-600`) and semantic aliases (`--color-accent: var(--color-indigo-600)`). `design-system.css` (MODIFY) is the behavior layer — animations, transitions, hover states, Quasar overrides that reference tokens via `var(--)`. `styles.py` (MODIFY) provides Python-side Tailwind class string constants for components and keeps a separate HEX dict for AG Grid cellRenderer JavaScript strings, which cannot access CSS custom properties at runtime.

Load order in `main.py` is critical: `tokens.css` must load first, then `design-system.css`, then Tailwind `@layer components` status badge CSS, then `ui.colors()` to align Quasar's `--q-primary` with the token system value. Hero sections must be implemented as explicit structural zone wrappers (`ui.element('div').classes('hero-zone')`) — not padding inflation on existing column containers.

**Major components and their changes:**
1. `app/static/tokens.css` — NEW; primitive + semantic CSS custom property layers; two-level system enables one-line palette swaps in v0.8+
2. `app/static/design-system.css` — MODIFY; replace hardcoded hex with `var(--)` references; add hero-enter stagger animation, template-card hover lift, `@layer overrides` for Quasar internals
3. `app/styles.py` — MODIFY; add v0.7 semantic style constants (TEXT_HERO, STAT_NUMBER, SECTION_HEADER, etc.); keep HEX dict for AG Grid JS
4. `app/main.py` — MODIFY; load `tokens.css` first; expand font weights in Google Fonts URL; add `app.colors()`; extend `@layer components` block
5. `app/components/header.py` — MODIFY; dark band, logo mark, active tab indicator, filled accent CTA
6. `app/components/onboarding/splash.py` — FULL REWRITE; dark hero surface, large IBM Plex Sans 700 headline, visual confidence
7. `app/pages/registry.py` — MODIFY; add stats bar zone with hero-zone wrapper, update empty state
8. `app/pages/templates.py` — MODIFY; card shadows, color type badges, hover lift via `template-card` CSS class
9. `app/pages/settings.py` — MODIFY; `bg-slate-50` section containers, uppercase divider labels
10. `app/components/registry_table.py` — MODIFY; AG Grid theming via `--ag-*` CSS variables scoped to `.ag-theme-quartz`

### Critical Pitfalls

1. **CSS outside `@layer` is silently ignored by Quasar** — NiceGUI 3.x moved all framework CSS into CSS layers; unlayered custom CSS loses cascade priority silently. All custom CSS must be in `@layer components` or `@layer overrides`. Establish this convention in Phase 1 before writing any new CSS.

2. **AG Grid requires `.ag-theme-quartz` selector prefix and `--ag-*` variables** — AG Grid's CSS lives completely outside NiceGUI's `@layer` system; `@layer components { .ag-row { ... } }` has zero effect on AG Grid. Use `--ag-*` CSS custom properties scoped to `.ag-theme-quartz` for all AG Grid theming.

3. **Functional CSS class names are an API contract** — `actions-cell`, `action-icon`, `expand-icon`, and all `status-*` classes are referenced inside AG Grid cellRenderer JavaScript strings in `registry_table.py`. Rename any of them and AG Grid interactivity silently breaks with no error. Grep `app/` before any rename; add new classes for new treatments, never mutate existing functional names.

4. **Quasar color props emit `!important` and cannot be overridden cleanly** — `ui.button().props("color=primary")` makes the color `!important` from Quasar; fighting it requires `!important` chains. Use `.classes("bg-indigo-600 text-white hover:bg-indigo-700")` instead — Tailwind classes are overridable.

5. **NiceGUI default padding variables override Tailwind spacing** — `--nicegui-default-padding` is applied to `.nicegui-content`, `.nicegui-card`, etc. and can silently override `p-4` or `px-6` Tailwind classes depending on layer interaction. Set `--nicegui-default-padding: 0; --nicegui-default-gap: 0` in `:root` at the start of `design-system.css` at Phase 1.

6. **FullCalendar CSS bleeds — use `--yt-` prefix for all project CSS variables** — FullCalendar injects `--fc-*` CSS variables globally; naming your design tokens `--color-*` can accidentally shadow FullCalendar values. Use `--yt-` prefix on all project-level custom properties. Smoke-test calendar view after every `:root` variable addition.

7. **Hero sections require structural zone wrappers, not padding inflation** — adding `pt-16 pb-12` to an existing flex column produces a wireframe with extra whitespace, not a designed section with visual character. Introduce explicit `ui.element('div')` wrappers with semantic CSS classes (`.hero-zone`, `.registry-header`, etc.) that own their background, padding, and border.

---

## Implications for Roadmap

Architecture imposes a strict dependency order. All downstream visual features inherit from the token layer; header must be stable before page-level work; the pattern must be validated on a simple isolated component (splash) before applying to the complex registry page.

### Phase 1: Design System Foundation
**Rationale:** Every downstream visual feature inherits from tokens. Without this, all subsequent phases use hardcoded values that drift. Also establishes the CSS layer discipline and NiceGUI padding variable overrides — without them, subsequent phases will encounter silent CSS failures that are expensive to diagnose.
**Delivers:** `app/static/tokens.css` with full primitive + semantic token set; `main.py` updated with `app.colors()`, expanded font weights (300–700), correct load order (`tokens.css` first); `styles.py` extended with v0.7 constants; `--nicegui-default-padding: 0` set at root; `@layer` convention documented and enforced across the codebase
**Addresses:** Type scale (P1), spacing scale (P1), design token system foundation
**Avoids:** Pitfall 1 (CSS layer), Pitfall 4 (dark mode Tailwind race condition), Pitfall 8 (NiceGUI padding override)

### Phase 2: Header Visual Overhaul
**Rationale:** Header is persistent across all pages and anchors the visual rhythm. Reworking pages before header means pages are designed against the wrong visual frame. The accent CTA color and dark band tone set expectations that all pages must harmonize with.
**Delivers:** Dark header band, readable "ЮрТэг" brand mark (optionally with CSS gradient), filled indigo CTA button, visible active tab indicator showing current page
**Addresses:** Dark header band (P1), brand mark (P1), accent CTA (P1), active tab indicator (P1)
**Avoids:** Pitfall 2 (Quasar `!important` — use Tailwind classes for button color, not Quasar props)

### Phase 3: Splash Hero Rework
**Rationale:** Splash is isolated from all other pages — no data dependencies, no navigation state, no AG Grid. High visual impact relative to implementation cost. Validates that hero zone structural wrappers and large IBM Plex Sans typography work correctly in NiceGUI before applying the hero-zone pattern to the more complex registry page.
**Delivers:** Full-screen dark hero surface (`bg-slate-900`), IBM Plex Sans 700 headline at `clamp(2.5rem, 5vw, 3.5rem)`, subtext at font-weight 300, hero-enter CSS stagger animation, visual confidence on first impression
**Addresses:** Hero splash rework (P1 must-have)
**Avoids:** Pitfall — preserve all functional callbacks (wizard flow routing, model download trigger) intact during structural rebuild; functional logic and visual wrapper are separate concerns

### Phase 4: Registry Page Visual Rework
**Rationale:** Registry is the core of the app and highest complexity (stats bar, filter zone, AG Grid, calendar toggle, empty state). Depends on tokens (Phase 1) and header (Phase 2) being stable. Most user-facing impact. AG Grid theming is the highest-risk CSS work in the milestone and must be isolated in its own phase.
**Delivers:** Stats bar zone above grid with document/expiring/attention counts; filled semantic status badges in AG Grid (green/amber/red/slate pills); AG Grid theme via `--ag-*` CSS variables scoped to `.ag-theme-quartz`; hero-zone structural wrapper for registry page header; updated rich empty state
**Addresses:** Stats bar (P1), status badge color system (P1), rich empty state (P1), card depth hierarchy
**Avoids:** Pitfall 3 (AG Grid theming — `.ag-theme-quartz` prefix required), Pitfall 6 (functional class freeze on `status-*` and `actions-cell`), Pitfall 7 (animation double-fire on grid refresh — test filter segment switching)

### Phase 5: Document Card + Section Structure
**Rationale:** Document card depends on registry navigation working correctly. Section divider pattern (uppercase labels + 1px border) established here is the same pattern applied to settings in Phase 6 — build it once here, reference it there.
**Delivers:** Breadcrumb visual treatment, structured metadata blocks with visual hierarchy, uppercase section dividers between logical groups, consistent spacing rhythm throughout card
**Addresses:** Section dividers with labels (P1)
**Avoids:** Pitfall — breadcrumb `ui.navigate.to()` callbacks must survive typography and layout changes; `.classes()` changes and event handler `.on('click')` wiring are separate concerns

### Phase 6: Templates + Settings Pages
**Rationale:** Relatively isolated, lower visual complexity, can ship together. Template card shadow and hover lift pattern is independent of all other pages. Settings section containers apply the divider pattern from Phase 5. These are the safest pages to polish because they have the least functional complexity.
**Delivers:** Template cards with shadow hierarchy, hover lift (transform + box-shadow transition), color type badge accents per template type; settings page with `bg-slate-50` section containers, uppercase divider labels, visual grouping
**Addresses:** Card depth hierarchy (P1), template cards with icons (P2), section dividers (P1)
**Avoids:** Pitfall — settings `bind_value` targets must survive visual re-wrapping of inputs in new container elements; test that all radio buttons and toggles still save correctly after layout changes

### Phase 7: Cross-cutting Polish
**Rationale:** Final pass after all pages are structurally complete. Spacing inconsistencies and visual rhythm issues can only be assessed once all pages exist. This phase also handles the FullCalendar smoke-test after all CSS variables have been added — the most fragile integration in the codebase.
**Delivers:** Footer (version + model status anchor), micro-copy pass over all empty states and hints, spacing rhythm consistency audit, `prefers-reduced-motion` media query validation, FullCalendar smoke-test, pywebview native window visual check (WebKit rendering differences vs Chrome), optional animated count-up on stats bar if capacity allows
**Addresses:** Footer (P2), micro-copy (P2), animated count-up (P3 stretch)
**Avoids:** Pitfall 5 (FullCalendar CSS bleed — final CSS variable smoke-test), Pitfall 7 (animation polish pass — verify no double-fire on grid refresh after all changes)

### Phase Ordering Rationale

- **Tokens before everything** — all downstream features consume CSS custom properties; no coherent visual work possible without this foundation
- **Header before pages** — persistent component; every page is designed against the header's visual frame; wrong to style pages against an unstable anchor
- **Splash before registry** — isolated test of hero-zone pattern and large typography; easy rollback if pattern reveals issues; validates approach before committing to the most complex page
- **Registry before document card** — document card is accessed via registry row navigation; registry data model and routing must be stable first
- **Document card before templates/settings** — section divider pattern is defined here and referenced by settings; establishes the pattern once
- **Polish always last** — spacing rhythm and visual consistency can only be assessed when all pages are structurally complete

### Research Flags

Phases with standard, well-documented patterns (skip `/gsd:research-phase`):
- **Phase 1 (Tokens):** CSS custom properties + NiceGUI `app.colors()` are fully documented at nicegui.io; no unknowns; HIGH confidence
- **Phase 2 (Header):** Tailwind utility classes on NiceGUI components; established pattern already in codebase
- **Phase 3 (Splash):** Isolated component, no external integrations; no research needed
- **Phase 5 (Document Card):** Tailwind typography and layout additions; standard patterns
- **Phase 6 (Templates + Settings):** Pure Tailwind class changes and layout additions; no unknowns

Phases that benefit from targeted pre-phase verification (not full research):
- **Phase 4 (Registry):** Verify the exact AG Grid theme class name active in NiceGUI 3.9.0 (`ag-theme-quartz` vs `ag-theme-alpine`) with one DevTools check before writing any AG Grid CSS. Also confirm `load_table_data()` return shape includes aggregate counts.
- **Phase 7 (Polish):** Confirm `backdrop-filter: blur()` behavior in pywebview / macOS WebKit before committing to any blur effects — WebKit is not GPU-accelerated the same as Chrome and may cause CPU spikes.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | NiceGUI 3.9.0 installed and verified; all API references confirmed at nicegui.io; `app.colors()` availability confirmed since v3.6.0; zero new pip dependencies required |
| Features | HIGH | Direct codebase inspection + RunPod design analysis + SaaS design pattern research; must-have vs defer list is well-reasoned with explicit anti-feature rationale |
| Architecture | HIGH | Load order and CSS layer hierarchy confirmed via official NiceGUI docs and verified GitHub issues with issue numbers; two-layer token system is standard CSS design token practice |
| Pitfalls | HIGH | All 8 critical pitfalls sourced from official NiceGUI GitHub issues and release notes with issue numbers; recovery strategies confirmed; AG Grid pitfalls confirmed via AG Grid official CSS docs |

**Overall confidence: HIGH**

### Gaps to Address

- **AG Grid theme name (minor):** Research says `ag-theme-quartz` is the NiceGUI 3.x default but instructs to verify with DevTools. Confirm the exact theme class on the `.ag-grid-container` element before writing any AG Grid CSS in Phase 4. One DevTools inspection at phase start resolves this.
- **`load_table_data()` return shape for stats bar (minor):** Research confirms aggregate counts are available but does not verify the exact function signature returns them. Check `app/pages/registry.py` at Phase 4 start; add count queries if not already returned.
- **FullCalendar `--fc-*` variable enumeration (minor):** Research flags naming collision risk but does not enumerate which `--fc-*` variables the bundled FullCalendar version uses. Before Phase 7 CSS variable additions, inspect the FullCalendar bundle to confirm `--yt-` prefix avoids all conflicts.

---

## Sources

### Primary (HIGH confidence)
- [nicegui.io/documentation/colors](https://nicegui.io/documentation/colors) — `app.colors()` API, `ui.colors()` per-page usage
- [nicegui.io/documentation/add_style](https://nicegui.io/documentation/add_style) — `ui.add_css()`, CSS layer ordering
- [nicegui.io/documentation/section_styling_appearance](https://nicegui.io/documentation/section_styling_appearance) — Tailwind `@layer components`, CSS layer stack in NiceGUI v3
- [github.com/zauberzeug/nicegui/discussions/5331](https://github.com/zauberzeug/nicegui/discussions/5331) — NiceGUI v3 ships Tailwind 4; `.tailwind()` removed
- [github.com/zauberzeug/nicegui/discussions/5240](https://github.com/zauberzeug/nicegui/discussions/5240) — CSS layer ordering for overriding Quasar; `@layer overrides` pattern
- [github.com/zauberzeug/nicegui/issues/3753](https://github.com/zauberzeug/nicegui/issues/3753) — dark mode breaks Tailwind styling race condition
- [github.com/zauberzeug/nicegui/releases/tag/v3.0.0](https://github.com/zauberzeug/nicegui/releases/tag/v3.0.0) — CSS layers breaking change in v3
- [github.com/zauberzeug/nicegui/issues/4415](https://github.com/zauberzeug/nicegui/issues/4415) — Quasar `!important` pollution; closed as not planned
- [github.com/zauberzeug/nicegui/issues/5408](https://github.com/zauberzeug/nicegui/issues/5408) — NiceGUI default padding variable overrides
- [quasar.dev/style/color-palette](https://quasar.dev/style/color-palette/) — `--q-primary` and other CSS vars set by Quasar
- [quasar.dev/style/dark-mode](https://quasar.dev/style/dark-mode/) — `body--light` / `body--dark` class mechanism
- [fonts.google.com/specimen/IBM+Plex+Sans](https://fonts.google.com/specimen/IBM%2BPlex+Sans) — weight range 100–700, Cyrillic subset confirmed
- [tailwindcss.com/blog/tailwindcss-v4](https://tailwindcss.com/blog/tailwindcss-v4) — `@theme` vs `:root` distinction in Tailwind 4
- Current codebase direct inspection: `app/styles.py`, `app/static/design-system.css`, `app/components/header.py`, `app/components/onboarding/splash.py`, `app/pages/registry.py`, `app/pages/settings.py`
- `pip show nicegui` — version 3.9.0 confirmed (March 2026)

### Secondary (MEDIUM confidence)
- RunPod.io homepage direct inspection (2026-03-22) — design language, hero pattern, gradient text, stat bars, dark chrome
- RunPod blog "The New Runpod.io: Clearer, Faster, Built for What's Next" — design philosophy: "from functional to expressive"
- [deepwiki.com/zauberzeug/nicegui/7.2-styling-and-theming](https://deepwiki.com/zauberzeug/nicegui/7.2-styling-and-theming) — NiceGUI styling and theming overview
- [frontendtools.tech — CSS variables guide, design tokens, theming 2025](https://www.frontendtools.tech/blog/css-variables-guide-design-tokens-theming-2025) — two-layer primitive/semantic token pattern
- UI/UX 2025 trends (Lummi, Fontfabric, Pixelmatters) — bold typography patterns, dark mode best practices
- `.planning/PROJECT.md` — v0.7 milestone brief, target features list

---
*Research completed: 2026-03-22*
*Ready for roadmap: yes*
