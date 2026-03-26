# Phase 15: Splash - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning
**Mode:** Pre-discussed via milestone gray zone session

<domain>
## Phase Boundary

Visually rework the splash/onboarding screen into a hero-zone with dark accent surface and bold typography. Validate the hero-zone structural wrapper pattern (ui.element('div') with semantic CSS class) before applying it to the complex registry page in Phase 16. Keep the 2-step wizard flow (welcome → Telegram). Keep the GGUF model download progress bar on splash.

</domain>

<decisions>
## Implementation Decisions

### Splash Structure
- Keep wizard 2-step flow: Step 1 = welcome/приветствие, Step 2 = Telegram настройка
- Model download progress bar (940 MB GGUF) stays on splash — юрист видит что происходит
- Hero-zone pattern: explicit structural wrapper (ui.element('div').classes('hero-zone')), NOT padding inflation on existing containers
- Dark accent surface for hero area — bg-slate-900 or similar from --yt-hero-bg token

### Visual Treatment
- Hero headline: IBM Plex Sans 700, text-4xl+ (use TEXT_HERO from styles.py)
- Subtext: font-weight 300, muted color
- «Далее: Уведомления →» button: filled accent (BTN_ACCENT_FILLED from styles.py)
- «Пропустить» link: ghost/text style
- Full-screen layout — splash occupies entire viewport, centered vertically
- SPLS-03 (staggered entrance animation) is STRETCH — implement if time, cut first if phase slips. Use .hero-enter CSS class from design-system.css

### Functional Preservation
- All wizard callbacks must survive visual restructuring: model download trigger, wizard step routing, Telegram setup flow
- render_splash() stays as full-page component (not ui.dialog)
- load_settings() called inside root() per-connection — don't change this pattern

### Claude's Discretion
- Exact layout proportions (hero area vs wizard content)
- Step indicator style (dots, progress bar, numbered)
- Wizard transition animation between steps (if any)
- Icon/illustration choice for welcome step

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- app/components/onboarding/splash.py — current splash implementation
- app/static/design-system.css — .hero-zone and .hero-enter CSS classes (created in Phase 14)
- app/styles.py — TEXT_HERO, BTN_ACCENT_FILLED constants
- app/static/tokens.css — --yt-hero-bg, --yt-color-accent, --yt-font-hero tokens

### Established Patterns
- render_splash() is called from main.py root() as early return gate
- load_settings() determines if splash should show
- NiceGUI ui.element('div') for structural wrappers
- Tailwind classes via .classes() method

### Integration Points
- app/main.py root() — splash gate (early return if first run)
- app/components/onboarding/splash.py — full rewrite target
- No dependency on registry, settings, or other pages — fully isolated

</code_context>

<specifics>
## Specific Ideas

- Reference: RunPod.io hero sections — bold, confident, fills the screen
- Splash should feel like "welcome to a product" not "fill in a form"
- Progress bar for model download should be styled to match the hero-zone aesthetic

</specifics>

<deferred>
## Deferred Ideas

- Single-screen welcome (decided to keep 2-step wizard)
- Moving model download to settings
- Parallax / scroll animations — not appropriate for a setup screen

</deferred>
