# Architecture Research

**Domain:** Visual design system overhaul — NiceGUI desktop app theming (v0.7)
**Researched:** 2026-03-22
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        THEME LAYER                                  │
│                                                                     │
│  app/static/tokens.css          app/static/design-system.css        │
│  (:root { --color-* ... })      (animations, AG Grid, FullCalendar) │
│           │                                  │                      │
│           └──────────────────┬───────────────┘                      │
│                              │ loaded via ui.add_head_html           │
├──────────────────────────────▼──────────────────────────────────────┤
│                        COMPONENT LAYER                               │
│                                                                     │
│  app/styles.py         app/components/header.py                     │
│  (Python token refs)   app/components/registry_table.py             │
│  TEXT_HEADING etc.     app/pages/registry.py                        │
│                        app/pages/settings.py                        │
│                        app/pages/templates.py                       │
│                        app/pages/document.py                        │
│                        app/components/onboarding/splash.py          │
├─────────────────────────────────────────────────────────────────────┤
│                        QUASAR LAYER                                  │
│                                                                     │
│  ui.colors(primary='#...') in root() → sets --q-primary on body     │
│  body.body--light class (Quasar managed, applied automatically)     │
│  Tailwind JIT (NiceGUI built-in) for utility classes                │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Current State |
|-----------|----------------|---------------|
| `app/static/tokens.css` | CSS custom properties — single source of truth for all colors, type scale, spacing, radii, shadows | Does not exist — values are hardcoded in Tailwind classes and HEX dict |
| `app/static/design-system.css` | Animations, AG Grid overrides, FullCalendar theme, Quasar component tweaks | Exists, animation-heavy, hardcoded hex values throughout |
| `app/styles.py` | Python-side token constants for Tailwind class strings used by pages and components | Exists — HEX dict + Tailwind class strings, all hardcoded |
| `app/main.py` | Loads CSS files into page head, calls ui.colors(), configures dark=False | Exists — inline font CSS, badge CSS, loads design-system.css |
| `app/pages/*.py` | Page layout and content rendering | Exist — Tailwind classes hardcoded inline throughout |
| `app/components/header.py` | Persistent top nav across all sub-pages | Exists — hardcoded slate/indigo Tailwind classes |
| `app/components/registry_table.py` | AG Grid registry table, column defs, JS cell renderers | Exists — inline hex in JS cell renderers |

## Recommended Project Structure

```
app/
├── static/
│   ├── tokens.css          # NEW — CSS custom properties (:root { --* })
│   ├── design-system.css   # MODIFY — replace hardcoded hex with var(--)
│   └── calendar.js         # unchanged
├── styles.py               # MODIFY — add semantic aliases, keep HEX for AG Grid JS
├── main.py                 # MODIFY — load tokens.css first, call ui.colors()
├── pages/
│   ├── registry.py         # MODIFY — hero stats bar, filter zone, visual density
│   ├── document.py         # MODIFY — breadcrumbs, structured blocks, visual hierarchy
│   ├── settings.py         # MODIFY — section headers, dividers, visual structure
│   └── templates.py        # MODIFY — card shadows, color badges, visual weight
└── components/
    ├── header.py           # MODIFY — visual weight, logo mark, accent CTA
    ├── registry_table.py   # MODIFY — table density, column visual treatment
    └── onboarding/
        └── splash.py       # MODIFY — hero section, full-screen, large typography
```

### Structure Rationale

- **tokens.css separate from design-system.css:** Tokens are the palette (values). design-system.css is the behavior layer (animations, transitions, hover states). Mixing them makes future palette updates require reading through behavior rules to find values to change.
- **tokens.css loaded first:** CSS custom properties must be defined before any element renders. Load order in `main.py` is: `tokens.css` first, then `design-system.css`, then Tailwind `@layer components` (status badges).
- **styles.py stays with HEX dict:** AG Grid cell renderers are JavaScript strings. They cannot read CSS custom properties at runtime. The HEX dict in `styles.py` remains the source for any hex values injected into JS strings.

## Architectural Patterns

### Pattern 1: Two-Layer Token System

**What:** Primitive tokens define the raw palette (`--color-indigo-600: #4f46e5`). Semantic tokens map intent to primitives (`--color-accent: var(--color-indigo-600)`). Components reference semantic tokens only, never primitives.

**When to use:** Every value that appears in more than one context. The semantic layer is the public API that pages and components consume. The primitive layer is the palette that can be swapped.

**Trade-offs:** One extra indirection in CSS. Worth it — changing the accent color in v0.8 from indigo to another color is a one-line change in tokens.css instead of a grep across 15 files.

**Example:**
```css
/* app/static/tokens.css */
:root {
  /* Primitives */
  --color-indigo-600: #4f46e5;
  --color-indigo-700: #4338ca;
  --color-indigo-50:  #eef2ff;
  --color-slate-900:  #0f172a;
  --color-slate-700:  #334155;
  --color-slate-600:  #475569;
  --color-slate-500:  #64748b;
  --color-slate-400:  #94a3b8;
  --color-slate-300:  #cbd5e1;
  --color-slate-200:  #e2e8f0;
  --color-slate-100:  #f1f5f9;
  --color-slate-50:   #f8fafc;

  /* Semantic colors */
  --color-accent:         var(--color-indigo-600);
  --color-accent-hover:   var(--color-indigo-700);
  --color-accent-subtle:  var(--color-indigo-50);
  --color-text-primary:   var(--color-slate-900);
  --color-text-secondary: var(--color-slate-600);
  --color-text-muted:     var(--color-slate-400);
  --color-surface:        #ffffff;
  --color-surface-raised: var(--color-slate-50);
  --color-border:         var(--color-slate-200);
  --color-border-strong:  var(--color-slate-300);

  /* Typography scale */
  --font-size-hero:   2.5rem;
  --font-size-h1:     1.75rem;
  --font-size-h2:     1.25rem;
  --font-weight-bold: 700;
  --font-weight-semi: 600;
  --line-height-tight: 1.2;

  /* Spatial scale */
  --space-hero:    64px;
  --space-section: 48px;
  --space-block:   24px;
  --space-item:    12px;

  /* Surfaces */
  --radius-card:   12px;
  --radius-badge:  6px;
  --shadow-card:   0 4px 16px -2px rgba(0,0,0,0.08), 0 1px 4px -1px rgba(0,0,0,0.05);
  --shadow-card-hover: 0 8px 24px -4px rgba(0,0,0,0.12), 0 2px 8px -2px rgba(0,0,0,0.06);
  --shadow-header: 0 1px 3px rgba(0,0,0,0.04);
}
```

### Pattern 2: Quasar Color Bridge

**What:** NiceGUI exposes `ui.colors()` which sets Quasar CSS variables (`--q-primary`, `--q-accent`, etc.) on `document.body`. All Quasar interactive components (buttons, chips, dialogs, menus) read these variables. Without calling `ui.colors()`, buttons remain default Quasar blue regardless of Tailwind overrides.

**When to use:** Mandatory. Called once in `root()` before `render_header()`. Uses the same hex value as `--color-accent` in tokens.css — keeps Quasar and the token system synchronized.

**Trade-offs:** `ui.colors()` is per-page (called in `root()`), not globally at module level. In this SPA with a single `@ui.page('/')`, that is fine. Do not call it inside page builders — it injects a `<style>` tag on every navigation, accumulating duplicates.

**Example:**
```python
# app/main.py — inside root(), before render_header()
ui.colors(primary='#4f46e5', secondary='#475569')
```

### Pattern 3: body--light Scoped Quasar Overrides

**What:** Quasar automatically applies `body.body--light` class when dark mode is off. Scoping overrides of Quasar defaults to this class prevents conflicts if dark mode is added later in v0.8.

**When to use:** Any rule that overrides Quasar component backgrounds, borders, or colors — headers, dialogs, menus, cards. Animation rules targeting `.q-btn`, `.q-card` stay unscoped since they apply in both modes.

**Trade-offs:** Adds CSS specificity. Necessary for future-proofing dark mode.

**Example:**
```css
/* design-system.css */
body.body--light .q-header {
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  box-shadow: var(--shadow-header);
}
```

### Pattern 4: Hero Section as Structural Zone

**What:** Full-width sections with an explicit background, vertical rhythm, large typographic anchors, and visual weight. Not padding inflation on an existing column — an intentional structural wrapper with its own CSS class.

**When to use:** Splash page (full-screen hero). Registry page top area (heading + stats bar + filters as a cohesive zone). Document card header zone.

**Trade-offs:** Requires replacing the existing `p-8 gap-6` patterns on page entry points with explicit zone containers. Cannot be bolted onto existing layout structure.

**Example:**
```python
# Registry page hero zone
with ui.element('div').classes('hero-zone w-full'):
    with ui.column().classes('gap-2'):
        ui.label('Реестр документов').style(
            'font-size: var(--font-size-h1);'
            'font-weight: var(--font-weight-bold);'
            'color: var(--color-text-primary);'
            'line-height: var(--line-height-tight);'
        )
```

```css
/* tokens.css */
.hero-zone {
  padding: var(--space-hero) var(--space-section);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}
```

## Data Flow

### Theme Load Order

```
ui.run() starts
    ↓
root() called
    ↓
ui.add_head_html(tokens.css)            CSS custom properties defined
    ↓
ui.add_head_html(design-system.css)     Animations + Quasar overrides using var(--)
    ↓
ui.add_head_html(status badge CSS)      Tailwind @layer components — literal class names
    ↓
ui.colors(primary='#4f46e5', ...)       Quasar --q-primary aligned to --color-accent value
    ↓
render_header()
    ↓
sub_pages routes to active page
    ↓
Page renders with Tailwind utility classes + style= attributes where vars needed
```

### Token Change Flow (future palette update)

```
Edit tokens.css primitive layer
    ↓
Browser recalculates all var(--*) references instantly (no recompile)
    ↓
Update ui.colors(primary=NEW_HEX) in main.py (one line)
    ↓
Update HEX dict in styles.py (for AG Grid JS renderers only)
```

### Key Data Flows

1. **Tailwind classes resolve at parse time** — they do not read CSS vars at runtime. `bg-indigo-600` is always indigo. For colors that must flex with the token system, use `style="background: var(--color-accent)"` or define a custom class in `@layer components`.

2. **AG Grid cell renderers are JavaScript strings** — they reference CSS class names (`.status-active` etc.) or hardcoded hex. They cannot access CSS custom properties. The HEX dict in `styles.py` stays alive for values injected into JS strings.

3. **FullCalendar overrides** — already in `design-system.css`. After tokens.css is live, replace hardcoded hex values (`#4f46e5`, `#4338ca`, etc.) with `var(--color-accent)` etc.

## Scaling Considerations

This is a desktop app — "scaling" here means maintainability as visual complexity grows across future milestones.

| Scale | Architecture Adjustments |
|-------|--------------------------|
| v0.7 (this milestone) | Single light theme, CSS vars in :root — no scoping needed |
| v0.8 (potential dark mode) | Add `body.body--dark { --color-surface: #0f172a; --color-text-primary: #f8fafc; }` block — semantic layer repoints automatically, components unchanged |
| v1+ (brand refresh) | Edit primitive layer in tokens.css only — all semantic tokens cascade through automatically |

### Scaling Priorities

1. **First issue:** Tailwind class strings in Python (`TEXT_HEADING`, `BTN_PRIMARY`, inline in pages) cannot read CSS vars — they are static strings resolved at Tailwind JIT parse time. Solution: use Tailwind for layout and spacing (flex, gap, padding, rounded), use `style=` attributes with `var(--)` for color, shadow, and type scale where Tailwind coverage ends.

2. **Second issue:** AG Grid column definitions produce JS strings. Any color in a cellRenderer must remain a literal hex or CSS class name. Keep HEX dict in `styles.py` as the single source for these values and update it in sync with tokens.css primitives.

## Anti-Patterns

### Anti-Pattern 1: Overloading design-system.css with token definitions

**What people do:** Add all new visual rules — hero sizes, card shadows, header weight — directly to the existing `design-system.css` alongside the animation rules.

**Why it's wrong:** design-system.css is the behavior layer. Mixing value definitions into it makes it impossible to understand what controls what, and a token change requires reading through animation code to find the value to edit.

**Do this instead:** `tokens.css` for values only, `design-system.css` for behaviors only. `style=` attribute for one-off per-element overrides.

### Anti-Pattern 2: Adding new hardcoded Tailwind color classes to styles.py

**What people do:** Continue adding `"text-indigo-600"` or `"bg-slate-900"` as new Tailwind class strings in `styles.py` for the v0.7 overhaul.

**Why it's wrong:** Tailwind color classes are hardcoded at parse time. If the accent shifts from indigo to another color in v0.8, every occurrence needs grep-and-replace across the entire codebase.

**Do this instead:** For hero text, large headings, and any color that should track the token system — use `style="color: var(--color-text-primary)"`. For stable utility colors (borders, subtle backgrounds) where Tailwind classes like `border-slate-200` are fine to stay, they can remain as Tailwind classes.

### Anti-Pattern 3: Hero sections via padding inflation

**What people do:** Add `pt-16 pb-12` to existing column containers to simulate a hero section.

**Why it's wrong:** A hero section is a structural zone with its own background, visual boundary, and typographic anchor. Padding inflation on an existing flex column produces a wireframe with extra whitespace, not a designed section with visual character.

**Do this instead:** Introduce explicit section wrapper elements (`ui.element('div')`) with semantic CSS classes defined in tokens.css (`.hero-zone`, `.registry-header`, etc.). These wrappers own their background, padding, and border.

### Anti-Pattern 4: Calling ui.colors() inside page builders

**What people do:** Call `ui.colors()` inside `registry.build()` or `settings.build()` to ensure colors are set on each navigation.

**Why it's wrong:** `ui.colors()` injects a `<style>` tag into the page head. Called per sub_page switch, it reinjects on every navigation, accumulating duplicate style tags over the lifetime of the session.

**Do this instead:** Call `ui.colors()` once in `root()` before the sub_pages block. It persists for the lifetime of the SPA session.

### Anti-Pattern 5: Mixing layout structure changes with visual changes

**What people do:** Rework Tailwind class strings while simultaneously restructuring the layout of a page.

**Why it's wrong:** Layout structure changes break functional behavior (filters stop firing, navigation breaks). Visual changes are safe if layout is stable. Mixing both in one edit makes it impossible to bisect what broke something.

**Do this instead:** Structural rework (new zone containers, hero wrappers) first. Visual token application (replacing hardcoded hex with vars, adding shadows, upgrading type scale) second, per component.

## Integration Points

### Where Theme Logic Lives

| Concern | File | Status | Notes |
|---------|------|--------|-------|
| CSS custom property values | `app/static/tokens.css` | NEW | Loaded first via main.py |
| Quasar color alignment | `app/main.py` root() | MODIFY | Add `ui.colors(primary='#4f46e5')` |
| Animation + behavior CSS | `app/static/design-system.css` | MODIFY | Replace hardcoded hex with var(--) |
| Python Tailwind constants | `app/styles.py` | MODIFY | Add semantic style helpers; keep HEX dict |
| AG Grid hex for JS renderers | `app/styles.py` HEX dict | KEEP | Cannot use CSS vars in JS strings |
| Per-page layout structure | `app/pages/*.py` | MODIFY | Structural zone wrappers added per page |
| Header visual weight | `app/components/header.py` | MODIFY | Logo mark, accent CTA, visual anchoring |
| Splash hero | `app/components/onboarding/splash.py` | MODIFY | Full-screen, large type, visual confidence |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| tokens.css → design-system.css | `var()` references | Load order critical: tokens must come first |
| tokens.css → Tailwind @layer | No direct connection | Tailwind resolves at parse time; use `style=` for dynamic values |
| styles.py → pages/components | Python string import | Tailwind class string constants; semantic additions welcome |
| ui.colors() → Quasar components | CSS `--q-primary` etc. on body | Called once in root() |
| AG Grid cellRenderers → CSS | Class name strings in JS | Must use literal `.status-*` class names; no CSS var access |
| FullCalendar → tokens | CSS class overrides in design-system.css | Replace hardcoded hex with var(--) after tokens.css is live |

### Build Order for This Milestone

Dependencies determine the order phases must ship in:

1. **tokens.css + main.py wiring** — foundation. No visual work is coherent before the token system is defined and loading correctly. Validate in browser devtools that `:root` custom properties are present.

2. **Header** — persistent across all pages. Reworked header must be stable before any page-level work, since it anchors the visual rhythm and the accent CTA sets expectations for interaction.

3. **Splash** — isolated component, no state dependencies, high visual impact. Full-screen hero. Good confidence check that large typography and hero zones work before tackling complex pages.

4. **Registry page** — highest complexity (stats bar, filter zone, AG Grid table, calendar toggle, empty state). Depends on tokens and header being stable. Most user-facing impact.

5. **Document card** — depends on registry navigation working correctly. Breadcrumbs, structured metadata blocks, visual section separators.

6. **Templates + Settings** — relatively isolated, lower visual complexity. Can ship as a pair.

7. **Sквозные микро-детали** — footer, transition polish, hover states, consistent spacing — final pass after all pages are structurally complete and stable.

## Sources

- [NiceGUI ui.colors documentation](https://nicegui.io/documentation/colors) — HIGH confidence
- [NiceGUI Styling and Theming (DeepWiki)](https://deepwiki.com/zauberzeug/nicegui/7.2-styling-and-theming) — HIGH confidence
- [Quasar Dark Mode — body--dark/body--light classes](https://quasar.dev/style/dark-mode/) — HIGH confidence
- [CSS Design Tokens and Custom Properties guide 2025](https://www.frontendtools.tech/blog/css-variables-guide-design-tokens-theming-2025) — MEDIUM confidence
- [Practical Guide to CSS Custom Properties for Theming](https://ronaldsvilcins.com/2025/03/30/a-practical-guide-to-css-custom-properties-for-theming/) — MEDIUM confidence
- Codebase direct analysis: `app/static/design-system.css`, `app/styles.py`, `app/main.py`, `app/components/header.py`, `app/pages/registry.py`, `app/pages/settings.py` — HIGH confidence

---
*Architecture research for: ЮрТэг v0.7 — visual design system overhaul*
*Researched: 2026-03-22*
