# Stack Research

**Domain:** Visual overhaul of existing NiceGUI 3.9.0 desktop app — design system, theming, typography weight, animation
**Researched:** 2026-03-22
**Confidence:** HIGH (NiceGUI 3.9.0 installed and verified; Quasar color API confirmed via nicegui.io; Tailwind 4 layer system confirmed via v3 discussion thread)

---

## Context

This is a **purely visual milestone**. The existing Python stack (NiceGUI 3.9.0, AG Grid, SQLite, IBM Plex Sans, Tailwind 4, Quasar, llama-server) is not changing. No new Python dependencies are required. The question is: what CSS architecture, theming patterns, and animation techniques are needed to transform the current wireframe-grade UI into a bold, confident product?

**Current state (v0.6):** Functional, clean, but visually thin. Flat white backgrounds everywhere. Typography at two weights (400/600) only. Header has no visual weight. Splash is a centered card that looks like a form. Segments have shape but no presence. Empty states exist but feel generic.

**Target (v0.7):** RunPod-grade visual confidence. Heavy typography (300–700 range used intentionally). Dark accent surfaces for hero moments. Stats bar with numbers. Rich empty states. Hover states that feel intentional. A design system that lives in CSS custom properties (not just Python string constants).

---

## What NOT to Add (New Dependencies)

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Any new Python UI library | No new pip dependencies — visual work is CSS/JS only | Inline `<style>` and `<script>` via `ui.add_head_html` |
| GSAP / Framer Motion / anime.js | Overkill for micro-interactions in a desktop productivity app; adds CDN dependency | Pure CSS `@keyframes` + `transition` — already proven in design-system.css |
| Tailwind CSS v4 `@theme` directive | NiceGUI bundles its own Tailwind 4 CDN build. Custom `@theme` blocks require a Tailwind build step, which NiceGUI doesn't expose. `@layer components` is the correct integration point. | `<style type="text/tailwindcss">` with `@layer components` blocks (already used in main.py for status badges) |
| CSS-in-JS or styled-components | Not applicable in Python/NiceGUI | CSS custom properties in `:root` |
| Icon font CDN (Font Awesome, etc.) | Adds latency on first load; Material Icons already bundled by Quasar | `ui.icon()` with Quasar material icons, or inline SVG for hero moments |
| Dark mode toggle | v0.7 goal is confident light-with-dark-accent, not a full dark mode system. Adding a toggle doubles the CSS surface area. | `ui.dark_mode(value=False)` stays fixed; dark surfaces implemented as bg-slate-900 regions, not system dark mode |

---

## Core Theming Architecture

### Layer 1 — Quasar Brand Colors (app-wide, set at startup)

NiceGUI 3.9.0 exposes `app.colors()` (v3.6.0+) and `ui.colors()` (per-page). These set Quasar's `--q-primary`, `--q-secondary`, etc. as CSS custom properties on `:root`.

**Integration point:** Call `app.colors()` once at module level in `main.py` before `ui.run()`. This eliminates the need to repeat `ui.colors()` on every page.

```python
from nicegui import app

app.colors(
    primary='#4f46e5',    # indigo-600 — already the brand color in v0.6
    secondary='#64748b',  # slate-500
    accent='#4f46e5',
    positive='#059669',   # green-600
    negative='#dc2626',   # red-600
    warning='#d97706',    # amber-600
    info='#3b82f6',       # blue-500
    dark='#0f172a',       # slate-900
    dark_page='#0f172a',
)
```

This is HIGH confidence — verified at nicegui.io/documentation/colors. `app.colors()` added in NiceGUI v3.6.0; current installed version is 3.9.0.

### Layer 2 — CSS Custom Properties Design Tokens (in design-system.css)

Extend `app/static/design-system.css` with a `:root` block defining the full design token set. These are plain CSS variables — no build step, no framework, available everywhere including AG Grid `cellRenderer` JavaScript strings.

```css
:root {
  /* Palette */
  --color-brand:       #4f46e5;  /* indigo-600 */
  --color-brand-dark:  #4338ca;  /* indigo-700 */
  --color-brand-light: #eef2ff;  /* indigo-50 */
  --color-surface:     #ffffff;
  --color-surface-2:   #f8fafc;  /* slate-50 */
  --color-surface-3:   #f1f5f9;  /* slate-100 */
  --color-border:      #e2e8f0;  /* slate-200 */
  --color-text-strong: #0f172a;  /* slate-900 */
  --color-text-body:   #475569;  /* slate-600 */
  --color-text-muted:  #94a3b8;  /* slate-400 */
  --color-hero-bg:     #0f172a;  /* slate-900 — for hero/splash dark surface */

  /* Typography scale */
  --font-family:     'IBM Plex Sans', system-ui, sans-serif;
  --text-hero:       clamp(2.5rem, 5vw, 3.5rem);  /* splash headline */
  --text-display:    2rem;     /* 32px — page section titles */
  --text-title:      1.25rem;  /* 20px — card headings */
  --text-body:       0.875rem; /* 14px — default body */
  --text-small:      0.75rem;  /* 12px — labels, badges */
  --weight-light:    300;
  --weight-regular:  400;
  --weight-medium:   500;      /* IBM Plex Sans supports 500 */
  --weight-semibold: 600;
  --weight-bold:     700;

  /* Spacing scale */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  --space-12: 3rem;
  --space-16: 4rem;

  /* Shadow scale */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.07), 0 2px 4px -2px rgb(0 0 0 / 0.05);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.08), 0 4px 6px -4px rgb(0 0 0 / 0.05);
  --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.06);

  /* Radius scale */
  --radius-sm: 0.375rem;  /* 6px */
  --radius-md: 0.5rem;    /* 8px */
  --radius-lg: 0.75rem;   /* 12px */
  --radius-xl: 1rem;      /* 16px */

  /* Transition */
  --ease-out: cubic-bezier(0.25, 1, 0.5, 1);
  --duration-fast: 150ms;
  --duration-base: 200ms;
  --duration-slow: 300ms;
}
```

**Why CSS custom properties instead of Python constants in styles.py:** The Python constants in `styles.py` are Tailwind class strings — they work for `.classes()` calls but cannot be used in AG Grid `cellRenderer` JavaScript, inline `<style>` blocks, or `calc()` expressions. CSS custom properties are the single source of truth accessible from all three layers (Python/NiceGUI, CSS, JavaScript).

**Migrate styles.py:** Keep the Tailwind class constants in `styles.py` for Python-side usage, but have them reference the same visual values defined in `:root`. This keeps the dual access pattern without duplication.

### Layer 3 — Tailwind Component Classes (@layer components)

The existing `<style type="text/tailwindcss">` block in `main.py` already defines status badge classes. Extend this pattern for new reusable components that need Tailwind utility composition:

```python
ui.add_head_html("""
<style type="text/tailwindcss">
  @layer components {
    /* Hero surface */
    .hero-surface {
      @apply bg-slate-900 text-white;
    }
    /* Stats bar item */
    .stat-item {
      @apply flex flex-col gap-0.5 px-6 py-4 border-r border-slate-800 last:border-r-0;
    }
    .stat-number {
      @apply text-2xl font-bold text-white tabular-nums;
    }
    .stat-label {
      @apply text-xs text-slate-400 uppercase tracking-wide;
    }
    /* Section header pattern */
    .section-header {
      @apply flex items-center justify-between px-6 py-4 border-b border-slate-200;
    }
    /* Rich empty state */
    .empty-state {
      @apply flex flex-col items-center justify-center gap-4 py-24 text-center;
    }
    /* Accent CTA button */
    .btn-hero {
      @apply px-8 py-3 bg-indigo-600 text-white font-semibold text-base rounded-lg
             hover:bg-indigo-700 transition-colors duration-150 shadow-md;
    }
  }
</style>
""", shared=True)
```

**Layer ordering confirmed (NiceGUI v3):** `theme, base, quasar, nicegui, components, utilities, overrides, quasar_importants`. The `components` layer sits above `quasar` — classes defined there override Quasar defaults without needing `!important`.

### Layer 4 — Quasar `!important` Overrides (for Quasar internals)

When overriding Quasar component internals (e.g., `.q-header` background, `.q-btn` padding), use `@layer overrides` in `design-system.css`:

```css
@layer overrides {
  /* Header: give it visual weight instead of flat white */
  .q-header {
    border-bottom: 1px solid var(--color-border);
    background: var(--color-surface) !important;
  }
  /* Remove Quasar's default button text-transform: uppercase */
  .q-btn .block {
    text-transform: none !important;
  }
}
```

---

## Typography Upgrade

IBM Plex Sans already loaded from Google Fonts. Currently only weights 400 and 600 are requested. The v0.7 hero splash needs 300 (light for display contrast) and 700 (bold for hero text). Update the font `<link>` in `main.py`:

```python
ui.add_head_html("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap&subset=cyrillic" rel="stylesheet">
<style>
  body {
    font-family: 'IBM Plex Sans', system-ui, sans-serif;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
    color: var(--color-text-strong);
  }
</style>
""", shared=True)
```

**IBM Plex Sans weight support (verified):** The typeface supports 100, 200, 300, 400, 500, 600, 700 — all available via Google Fonts with Cyrillic subset. Currently the app requests only 400 and 600. Adding 300 (for hero subtext at size) and 700 (for hero headline) is a no-cost one-line change to the Google Fonts URL.

**Typography rules for v0.7:**
- Hero headline: `font-size: var(--text-hero); font-weight: 700; letter-spacing: -0.02em`
- Page section title: `font-size: var(--text-display); font-weight: 700`
- Card heading: `font-size: var(--text-title); font-weight: 600`
- Stats number: `font-size: 1.75rem; font-weight: 700; font-variant-numeric: tabular-nums`
- Body: `font-size: var(--text-body); font-weight: 400`
- Labels/uppercase: `font-size: var(--text-small); font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase`

---

## Animation Additions

The existing `design-system.css` already has a solid animation foundation: `row-in`, `page-fade-in`, `dialog-in`, `badge-in`, `toast-in`, `link-underline-grow`. These are correct and stay. V0.7 needs three additional patterns:

### 1. Hero text entrance (stagger children)

```css
/* Staggered entrance for hero content blocks */
@keyframes hero-slide-up {
  from { opacity: 0; transform: translateY(24px); }
  to   { opacity: 1; transform: translateY(0); }
}

.hero-enter {
  animation: hero-slide-up var(--duration-slow) var(--ease-out) both;
}
.hero-enter:nth-child(1) { animation-delay: 0ms; }
.hero-enter:nth-child(2) { animation-delay: 100ms; }
.hero-enter:nth-child(3) { animation-delay: 200ms; }
.hero-enter:nth-child(4) { animation-delay: 300ms; }
```

Apply `.hero-enter` to each child block of the splash hero section. Pure CSS, no JavaScript, respects `prefers-reduced-motion` (already covered by the existing `@media` block in design-system.css).

### 2. Number counter (stats bar)

For the stats bar showing document count / expiring count / processed today, numbers should animate from 0 to their value on load. This requires 5 lines of vanilla JS injected once:

```javascript
// Animate data-count elements from 0 to target
document.querySelectorAll('[data-count]').forEach(el => {
  const target = parseInt(el.dataset.count);
  const dur = 800;
  const start = performance.now();
  const step = (now) => {
    const p = Math.min((now - start) / dur, 1);
    el.textContent = Math.round(p * target);
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
});
```

Called via `ui.run_javascript(COUNTER_SCRIPT)` after stats are rendered. No library needed.

### 3. Card hover lift (templates page)

Already partially implemented for `.q-card.cursor-default`. Extend to all template cards explicitly:

```css
@layer components {
  .template-card {
    transition: box-shadow var(--duration-base) var(--ease-out),
                transform var(--duration-base) var(--ease-out);
  }
  .template-card:hover {
    box-shadow: var(--shadow-xl);
    transform: translateY(-3px);
  }
}
```

---

## Surfaces and Dark Accent Approach

The v0.7 goal is "дерзкий" (bold, daring) — not minimalist white. The pattern from RunPod: use a dark surface for high-impact moments (hero, splash, maybe header), light surfaces everywhere else. This avoids full dark mode complexity while achieving visual weight.

**Implementation pattern:**

```python
# Splash hero — full dark surface
with ui.column().classes("min-h-screen bg-slate-900 text-white"):
    with ui.column().classes("max-w-2xl mx-auto py-24 px-8 gap-8"):
        ui.label("ЮрТэг").classes(
            "text-base font-semibold text-slate-400 uppercase tracking-widest"
        )
        ui.html("<h1 style='font-size: var(--text-hero); font-weight: 700; "
                "letter-spacing: -0.02em; line-height: 1.15; margin: 0;'>"
                "Реестр договоров<br>за 20 минут</h1>")
        ui.label("Загрузите папку — получите структурированный реестр с "
                 "метаданными, сроками и автосортировкой.").classes(
            "text-lg font-light text-slate-300 max-w-lg"
        )
```

**Key surfaces by section:**

| Section | Surface | Rationale |
|---------|---------|-----------|
| Splash/hero | `bg-slate-900` dark | Maximum visual impact, RunPod-like confidence |
| Header | `bg-white` with stronger border and logo weight | Professional, recedes behind content |
| Stats bar (registry top) | `bg-slate-900` strip or `bg-indigo-600` | Numbers pop visually |
| Registry table | `bg-white` | Content-first, readable |
| Template cards | `bg-white` with `shadow-md` | Cards need lift to feel interactive |
| Settings sections | `bg-slate-50` section containers | Gentle grouping |
| Empty state | `bg-white` with centered SVG illustration | Inviting, not clinical |

---

## styles.py Upgrade

Keep `styles.py` for Python-side Tailwind class constants. Extend with new v0.7 tokens:

```python
# ── New v0.7 constants ────────────────────────────────────────────────────────

# Hero / dark surface typography
TEXT_HERO = "font-bold text-white tracking-tight leading-tight"
TEXT_HERO_SUB = "text-lg font-light text-slate-300"
TEXT_EYEBROW = "text-xs font-semibold text-slate-400 uppercase tracking-widest"

# Stats bar
STAT_NUMBER = "text-2xl font-bold text-white tabular-nums"
STAT_LABEL = "text-xs text-slate-400 uppercase tracking-wide"

# Section structural
SECTION_HEADER = "flex items-center justify-between px-6 py-4 border-b border-slate-200"
DIVIDER = "border-t border-slate-100 my-6"

# Template card
TEMPLATE_CARD = "template-card bg-white border border-slate-200 rounded-xl p-5 cursor-pointer"

# Accent CTA
BTN_HERO = "btn-hero"

# Header logo mark
LOGO_MARK = "text-base font-bold text-slate-900 tracking-tight"
```

---

## No New pip Dependencies

The entire v0.7 visual overhaul requires zero new Python packages. All tools are already in the stack:

| Need | Tool | Already Available |
|------|------|-------------------|
| CSS custom properties | Plain CSS in design-system.css | Yes |
| Tailwind utility composition | `@layer components` in existing `<style type="text/tailwindcss">` block | Yes |
| Quasar brand color tokens | `app.colors()` from NiceGUI | Yes |
| Font weight expansion | Google Fonts URL parameter | Yes (free) |
| Hero animations | CSS `@keyframes` in design-system.css | Yes |
| Stats counter animation | 10-line vanilla JS via `ui.run_javascript()` | Yes |
| Dark surface sections | `bg-slate-900` Tailwind class | Yes |
| Card shadows and lift | Tailwind `shadow-*` + CSS transition | Yes |

---

## Integration Points with Existing Stack

| Existing System | v0.7 Touch Point | Change |
|-----------------|-----------------|--------|
| `app/static/design-system.css` | Add `:root` token block, hero-enter animation, template-card hover, @layer overrides | Extend only — existing rules stay |
| `app/main.py` | Add `app.colors()` call, update font weights in Google Fonts URL, extend `@layer components` block | Targeted edits |
| `app/styles.py` | Add new Python constants for v0.7 surfaces | Additive only |
| `app/components/onboarding/splash.py` | Full rework — dark hero surface, heavy typography, centered CTA | Full rewrite of layout |
| `app/components/header.py` | Logo weight/mark, stronger visual presence, accent CTA button style | Targeted edits |
| `app/pages/registry.py` | Add stats bar above table, update empty state visuals | New stats bar component |
| `app/pages/templates.py` | Card shadow/lift, colored type badges | CSS class changes |
| `app/pages/settings.py` | Section containers with `bg-slate-50`, visual dividers | Layout additions |
| `app/components/registry_table.py` | AG Grid theme tweaks for header row weight | CSS in design-system.css |

---

## Version Compatibility

| Package | Version | Notes |
|---------|---------|-------|
| nicegui | 3.9.0 (installed) | `app.colors()` available since 3.6.0 — confirmed |
| Tailwind CSS | 4.x (bundled by NiceGUI) | `@layer components` works; `@theme` directive not available without build step |
| Quasar | bundled | `--q-primary` etc. set via `app.colors()` |
| IBM Plex Sans | variable 100–700 | Cyrillic subset, Google Fonts CDN |
| CSS custom properties | native browser | Fully supported in WKWebView (macOS) and EdgeChromium (Windows) |

---

## Sources

- [nicegui.io/documentation/colors](https://nicegui.io/documentation/colors) — `app.colors()` API, `ui.colors()` per-page — HIGH confidence
- [nicegui.io/documentation/add_style](https://nicegui.io/documentation/add_style) — `ui.add_css()`, CSS layer ordering — HIGH confidence
- [nicegui.io/documentation/section_styling_appearance](https://nicegui.io/documentation/section_styling_appearance) — Tailwind @layer components, CSS layer stack — HIGH confidence
- [github.com/zauberzeug/nicegui/discussions/5331](https://github.com/zauberzeug/nicegui/discussions/5331) — NiceGUI v3 ships Tailwind 4; `.tailwind()` removed — HIGH confidence
- [github.com/zauberzeug/nicegui/discussions/5240](https://github.com/zauberzeug/nicegui/discussions/5240) — CSS layer ordering for overriding Quasar; `@layer overrides` pattern — HIGH confidence
- [quasar.dev/style/color-palette](https://quasar.dev/style/color-palette/) — `--q-primary` and other CSS vars exposed by Quasar — HIGH confidence
- [quasar.dev/style/dark-mode](https://quasar.dev/style/dark-mode/) — `body--light` / `body--dark` class mechanism — HIGH confidence
- [fonts.google.com/specimen/IBM+Plex+Sans](https://fonts.google.com/specimen/IBM%2BPlex+Sans) — Weight range 100–700, Cyrillic subset available — HIGH confidence
- [tailwindcss.com/blog/tailwindcss-v4](https://tailwindcss.com/blog/tailwindcss-v4) — @theme vs :root distinction, CSS-native token system — HIGH confidence
- Verified installed version: `pip show nicegui` → 3.9.0 (confirmed March 2026)

---

*Stack research for: ЮрТэг v0.7 — Визуальный продукт*
*Researched: 2026-03-22*
