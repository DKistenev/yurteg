# Feature Research — Visual Layer Overhaul

**Domain:** Bold, visually confident desktop document management application
**Researched:** 2026-03-22
**Confidence:** HIGH (direct codebase inspection + RunPod design analysis + SaaS design pattern research)

---

## Context: Current Visual State

The app runs on NiceGUI + Tailwind CSS + IBM Plex Sans + slate/indigo palette. The infrastructure is already correct:
- `app/styles.py` has design tokens
- `app/static/design-system.css` has micro-animations (row-in, dialog-in, badge-in, toast-in, button scale)
- AG Grid rows animate on load, dialogs have entrance transitions, buttons have press feedback

The skeleton is solid. But it reads as wireframe because:
- Everything is white, flat, and borderless
- Typography has no size spread — `text-xl` headers and `text-sm` body look nearly identical
- Header "ЮрТэг" is `text-base` — invisible as a brand anchor
- Zero visual depth: `shadow-none border` on all cards
- Status badges exist but are unstyled text
- Stats bar absent — registry top zone is blank
- Splash is a centered card on a white screen — no hero moment

Reference: RunPod.io — "from functional to expressive." Bold type, gradient accent on brand, dark chrome anchoring the layout, cards with shadow hierarchy, hero sections with visual confidence.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Missing any of these = still looks like a prototype, not a product.

| Feature | Why Expected | Complexity | NiceGUI Dependency |
|---------|--------------|------------|-------------------|
| **Type scale with genuine weight contrast** | Professional tools (Linear, Notion, Vercel) use 4–6 distinct type levels with clear size and weight spread. Currently all "headings" are `font-semibold` at nearly the same size — h1 and body label are visually indistinguishable | LOW | `app/styles.py` — extend TEXT_* constants (add 3xl, 4xl levels); update page headers in `registry.py`, `document.py`, `settings.py`, `templates.py` |
| **Dark or high-contrast header band** | Every confident desktop tool anchors the layout with a darkened navigation zone (dark chrome + light content is the dominant pattern: Linear, Vercel, VS Code, RunPod). Currently header is white-on-white with a 1px border — zero visual anchor | MEDIUM | `app/components/header.py` — change header classes; update text/button colors for dark background contrast |
| **Stats bar above registry table** | Document management tools show a summary row at a glance: total documents, expiring soon, requires attention. Users expect a density of information that confirms the app "knows" the state of their data. Currently the registry top zone is blank after the filter row | LOW | Pure NiceGUI row above grid; counts from `load_table_data()` return values already available |
| **Filled status badges with semantic color** | Status indicators (действует / истекает / истёк) must be instantly scannable. Filled pills with green/amber/red color semantic are the standard pattern (GitHub, Linear, Jira). Currently badges are styled as plain text in AG Grid cell renderer | LOW | `app/components/registry_table.py` — update JS cell renderer; add color constants to `styles.py` |
| **Card depth hierarchy** | Interactive surfaces (template cards, document card sections, dialogs) need a clear shadow layer signal: shadow-sm = content, shadow-md = interactive card, shadow-lg = modal. Currently `shadow-none border` everywhere — no depth cue, prototype feel | LOW | `styles.py` CARD_SECTION constant update; `templates.py` card restyle; `document.py` section blocks |
| **Header brand mark with visual weight** | "ЮрТэг" at `text-base font-semibold` is imperceptible as a brand anchor. Products with identity have a wordmark that reads clearly at small sizes. RunPod, Linear, Vercel all have a distinct brand mark that anchors the top-left | LOW | `app/components/header.py` — increase size to `text-lg` or `text-xl`, optionally apply gradient treatment |
| **Accent CTA in header** | The "+ Загрузить документы" button is currently `flat text-slate-700` — invisible. The primary action should be the most visually prominent element in the header. RunPod, Vercel, Linear all make their primary CTA a filled accent button | LOW | `app/components/header.py` — change upload button from `flat` to filled indigo; update label styling |
| **Consistent spacing scale** | The current layout mixes `gap-4`, `gap-6`, `gap-8`, `p-5`, `p-6`, `px-6 py-0` without a declared rhythm. A spacing scale (4/8/12/16/24/32/48px) applied consistently makes layouts feel intentional vs improvised | LOW | Audit all pages against a declared 8pt grid; update gap/padding classes in `registry.py`, `document.py`, `settings.py`, `templates.py` |
| **Rich empty state** | Current empty state has a `stroke="#cbd5e1"` outline SVG and plain body text. The empty state is seen by every new user — it is the first impression. It requires visual weight: a heavier icon, a bolder title at `text-2xl`, and descriptive hints | LOW | `app/components/ui_helpers.py` `empty_state()` — update SVG weight, title size, copy |
| **Footer / bottom anchor** | Without a footer the page content floats into nothing. A minimal 1-line footer (версия + статус модели) closes the visual space and gives the app a bounded, finished feeling | LOW | New `ui.footer()` component in `main.py` |

### Differentiators (Competitive Advantage)

These go beyond baseline polish and create a visual identity that makes the product memorable.

| Feature | Value Proposition | Complexity | NiceGUI Dependency |
|---------|-------------------|------------|-------------------|
| **Hero splash with full-screen visual moment** | First-run onboarding is currently a centered card on white — a form, not a product. A dark or gradient hero background, large headline ("Ваш архив договоров — под контролем"), the model download progress bar, and deliberate whitespace creates the "this is a real product" impression RunPod is the reference for. One screen, outsized effect | MEDIUM | `app/components/onboarding/splash.py` — full outer container rewrite; gradient background via `ui.html()` injection or CSS class; no layout architecture change |
| **Accent gradient on brand mark** | "ЮрТэг" wordmark with an indigo→violet gradient text effect makes the brand feel intentional vs typed. RunPod, Vercel, Stripe all use gradient text on their brand/headline. One CSS rule with outsized visual identity impact | LOW | `design-system.css` or inline style — CSS `background: linear-gradient(...); background-clip: text; -webkit-background-clip: text; color: transparent` on logo element |
| **Section dividers with uppercase labels** | Settings page and document card sections currently have no visual dividers. Adding a `text-xs uppercase tracking-wider text-slate-400` label above each section group (pattern from Stripe, Linear, Figma) creates scan-ability and visual structure without noise or extra chrome | LOW | `app/pages/settings.py`, `app/pages/document.py` — add label + 1px divider between logical groups |
| **Animated count-up on stats bar numbers** | Numbers that animate from 0 to their value on page load (requestAnimationFrame, ~400ms) turn a static label into a live dashboard. Standard pattern on RunPod, Vercel Analytics, Stripe Dashboard. Creates an impression of data being "computed in real time" even though it's a query result | MEDIUM | Inline JS via `ui.run_javascript()` after stats bar renders; or pure CSS counter animation |
| **Micro-copy with personality** | Every empty state, hint text, and error message currently uses generic placeholder copy. Rewriting to be direct and slightly dry ("Ничего не найдено. Попробуйте другой запрос — или загрузите ещё документы.") matches the RunPod voice: confident, not corporate | LOW | Copy-only pass over all pages — zero code complexity |
| **Visual active tab indicator** | The nav tabs in header have a `border-b-2 border-transparent hover:border-slate-900` pattern — subtle and invisible until hover. An active tab should have a visible filled underline or background indicator at all times, showing the current location | LOW | `app/components/header.py` — detect active route and apply filled indicator class; NiceGUI `ui.link` can receive dynamic classes based on `ui.page` context |
| **Template cards with icon + color accent** | Template cards on the Templates page are currently plain cards with title text. Adding a colored icon or left-border accent per template type (НДА = blue, Договор = indigo, Акт = green) creates visual scan-ability and a sense of product quality | LOW | `app/pages/templates.py` — add icon + left-border color per template type |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Full dark mode toggle** | RunPod uses dark; feels modern and developer-native | NiceGUI's dark mode is Quasar-level — affects component internals across the entire component library. AG Grid has its own separate theme system. Implementing full dark mode correctly requires auditing ~2 800 LOC of Tailwind classes and AG Grid theme overrides. That is a full milestone, not a visual polish pass. Partial dark mode creates jarring inconsistencies | Use a dark header/sidebar as a visual anchor. Keep light content area. This is the Linear/Notion/Vercel pattern: dark chrome, light workspace |
| **Glassmorphism** | Trendy; seen on RunPod background elements, Figma landing pages | Requires a non-white background to function — on white, frosted glass is invisible. On the content area it creates readability problems. Also signals the "AI slop aesthetic" the PROJECT.md brief explicitly rejects | Solid cards with shadow hierarchy: shadow-sm base, shadow-md on hover, shadow-lg on dialogs |
| **Custom font switch** | "A bespoke font signals design intent" | IBM Plex Sans already loads correctly from Google Fonts and is an excellent choice for a professional tool (designed by IBM for interfaces). A font switch at this stage adds CDN load complexity with near-zero visual ROI | Optimize the existing font load: ensure only `wght@400;500;600;700` is loaded — strip unused italic and 300-weight |
| **Sidebar navigation replacing header tabs** | Sidebars look more "app-like" than top tabs | NiceGUI's current architecture uses `ui.header()` + `ui.sub_pages()` for SPA navigation. A sidebar requires restructuring `main.py` and every page file — it is an architecture change, not a visual change. The 3-tab scope (Документы / Шаблоны / Настройки) does not justify a sidebar | Invest in the header's visual weight: dark band, logo size, active tab indicator, accent CTA |
| **More animations** | Animations signal polish | Core animations already exist: row-in, page-fade-in, dialog-in, badge-in, toast-in, button scale/press. Adding more animation without purpose creates jank and visual noise. The problem is visual weight, not animation quantity | Invest the animation budget purposefully: count-up numbers on stats bar and skeleton loaders — contextual, informative animations |
| **Decorative data visualization (charts)** | Dashboards have charts | No data exists in the current scope that needs charting vs tabular display. A chart added now is decorative, not functional — it's the definition of "AI slop." It also adds a charting library dependency | Stats bar with plain numbers is sufficient and honest. Charts become meaningful only post-launch when there is usage data across time |
| **Parallax / scroll animations on splash** | RunPod uses parallax on its homepage | RunPod.io is a marketing page designed to impress during a scroll. ЮрТэг splash is an onboarding screen shown once per install — the user's goal is to finish setup and start working. Animation that slows down that transition adds friction | One entrance animation on the splash hero content (fade + slide-up, 300ms) is the maximum |

---

## Feature Dependencies

```
Design Tokens (type scale + spacing scale)
    └──required by──> ALL visual features downstream

Dark Header Band
    └──requires──> Design Tokens (contrast check on dark bg)
    └──conflicts with──> Full Dark Mode Toggle

Status Badge Color System
    └──enhances──> Stats Bar (reuses same semantic colors)
    └──enhances──> Registry scan-ability

Stats Bar
    └──requires──> load_table_data() aggregate counts (already available)
    └──enhances──> Animated Count-up (depends on stats bar existing first)

Hero Splash Rework
    └──independent──> (self-contained, only touches splash.py)

Section Dividers with Labels
    └──requires──> Spacing Scale (applied first for consistent rhythm)

Template Cards with Icons
    └──requires──> Card Depth Hierarchy (icon sits inside card — card must be styled first)
```

### Dependency Notes

- **Design tokens first** — all other features inherit from `styles.py` TEXT_* and spacing constants. Update upstream before touching individual pages.
- **Badge color system before stats bar** — build semantic badge colors (green/amber/red/slate) first; the stats bar's "3 истекают" number then inherits the same amber color, ensuring visual coherence.
- **Dark header before accent CTA** — the upload button color needs to be designed against the final header background, not the current white.
- **Dark header conflicts with full dark mode** — architectural decision: dark chrome + light content, not full dark mode. This must be set explicitly so no one opens that scope during the milestone.

---

## MVP Definition (for v0.7 Visual Milestone)

### Must Ship in v0.7

These are the minimum changes that transform the app from wireframe to product. Without all of them, the milestone goal ("from wireframe to bold, confident product") is not met.

- [ ] **Design tokens extended** — type scale with 4+ distinct levels and weight spread, spacing scale declared in `styles.py` — foundation for everything else
- [ ] **Dark header band** — darkened navigation zone as visual anchor for the entire layout
- [ ] **Header: brand mark + accent CTA** — "ЮрТэг" at readable size with gradient treatment; upload button as filled indigo CTA
- [ ] **Active tab indicator** — visible current-page signal in header navigation
- [ ] **Stats bar on registry** — document count, expiring count, requires-attention count above the grid
- [ ] **Status badge color system** — filled green/amber/red/slate pills in AG Grid status column
- [ ] **Card depth hierarchy** — shadow-sm / shadow-md / shadow-lg applied consistently
- [ ] **Hero splash rework** — dark/gradient background, large headline, visual confidence on first impression
- [ ] **Section dividers with labels** — settings + document card sections structured with uppercase group labels
- [ ] **Rich empty state** — heavier icon, bolder title, more descriptive copy

### Add If Capacity Allows (v0.7 stretch)

- [ ] **Accent gradient on brand mark** — CSS one-liner, high identity value
- [ ] **Template cards with icon + color accent** — visual identity on Templates page
- [ ] **Micro-copy pass** — copy rewrite on all empty states and hints
- [ ] **Footer** — version + model status, closes the visual space

### Defer to v0.7.x or Later

- [ ] **Animated count-up on stats bar** — add when stats bar exists and feels static
- [ ] **Full dark mode** — after v0.8 packaging, own milestone
- [ ] **Sidebar navigation** — after v0.8, own milestone

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Design tokens (type scale + spacing) | HIGH | LOW | P1 |
| Dark header band | HIGH | MEDIUM | P1 |
| Header brand mark + accent CTA | HIGH | LOW | P1 |
| Hero splash rework | HIGH | MEDIUM | P1 |
| Stats bar on registry | HIGH | LOW | P1 |
| Status badge color system | HIGH | LOW | P1 |
| Card depth hierarchy | MEDIUM | LOW | P1 |
| Section dividers with labels | MEDIUM | LOW | P1 |
| Rich empty state | MEDIUM | LOW | P1 |
| Active tab indicator | MEDIUM | LOW | P1 |
| Accent gradient on brand mark | MEDIUM | LOW | P2 |
| Template cards with icon + color | MEDIUM | LOW | P2 |
| Micro-copy pass | MEDIUM | LOW | P2 |
| Footer | LOW | LOW | P2 |
| Animated count-up | LOW | MEDIUM | P3 |
| Full dark mode | HIGH | HIGH | Defer |

**Priority key:**
- P1: Must ship in v0.7 — milestone incomplete without
- P2: Ship in v0.7 if time allows — meaningful uplift
- P3: Defer to v0.7.x
- Defer: Own milestone

---

## Reference Design Analysis

| Visual Element | RunPod | Linear | Notion | Vercel | ЮрТэг v0.7 Approach |
|----------------|--------|--------|--------|--------|---------------------|
| Header style | Dark band, blur backdrop, gradient text logo | Light + filled active tab indicator | Light + bold logo | Dark band + light content | Dark band (no blur — desktop app, not browser) |
| Primary CTA | Filled accent button, prominent | Filled accent in top-right | "New page" inline | Filled button, prominent | Filled indigo in header, always visible |
| Brand mark | Gradient text, reads clearly at small size | Clean wordmark, semibold | Serif wordmark | Clean wordmark | "ЮрТэг" with indigo gradient or heavy weight |
| Type hierarchy | 3rem hero headline, 1.5rem section heads, 0.875rem body | 11–14px dense, bold section labels | 16px body, bold page titles | Large headline on landing, dense in app | 3xl+ for splash hero, 2xl for page title, xl for section, sm for body |
| Card depth | Semi-transparent bg + shadow | Flat + hover bg | Flat + hover bg | Subtle shadow + hover lift | shadow-sm base → shadow-md hover → shadow-lg modal |
| Status badges | Colored dots + labels | Filled color pills | Colored background labels | N/A | Filled pills, 4-color semantic system |
| Stats/metrics | Animated progress bars, bold numbers with accent color | Compact counters in sidebar | N/A | Large numbers in dashboard | Stats bar above grid, tabular-nums, semantic accent colors |
| Empty states | Illustrated, personality copy, clear CTA | Clean icon + CTA + explanation | Clean icon + CTA | Illustrated + CTA | Heavier icon + bold 2xl title + descriptive sub-copy + hint chips |

---

## Sources

- RunPod.io homepage direct inspection (2026-03-22) — design language, hero pattern, gradient text, card shadows
- RunPod blog "The New Runpod.io: Clearer, Faster, Built for What's Next" — design philosophy: "from functional to expressive"
- Current codebase direct inspection: `app/styles.py`, `app/static/design-system.css`, `app/components/header.py`, `app/components/onboarding/splash.py`, `app/pages/registry.py` — current visual state confirmed
- `.planning/PROJECT.md` — v0.7 milestone brief, target features list
- UI/UX 2025 trends (Lummi, Fontfabric, Pixelmatters) — bold typography patterns, dark mode best practices, SaaS dashboard visual density

---

*Feature research for: ЮрТэг v0.7 — full visual layer overhaul*
*Researched: 2026-03-22*
