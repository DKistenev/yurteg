# Pitfalls Research

**Domain:** Visual overhaul of existing NiceGUI 3.x desktop app (NiceGUI 3.9.0, Tailwind 4, AG Grid, FullCalendar)
**Researched:** 2026-03-22
**Confidence:** HIGH — all critical pitfalls confirmed via official NiceGUI GitHub issues, release notes, and v3.0 migration docs

> This file focuses on v0.7 "Визуальный продукт" — adding a full design-system overhaul on top of the working v0.6 codebase.
> Previous migration pitfalls (Pitfall 1–8 from v0.6 PITFALLS.md) remain valid for the business logic layer.

---

## Critical Pitfalls

### Pitfall 1: Custom CSS Without @layer — Silently Ignored by Quasar

**What goes wrong:**
Custom CSS added via `ui.add_css()` or `ui.add_head_html('<style>...')` doesn't override Quasar/NiceGUI component styles. Buttons, cards, inputs look unchanged despite correct CSS being in the DOM. Symptoms: no visual error, but the style simply doesn't apply.

**Why it happens:**
NiceGUI 3.x (including 3.9.0) moved all Tailwind and Quasar CSS into CSS `@layer` blocks. Layer hierarchy (highest to lowest priority): `overrides → utilities → components → nicegui → quasar → base → theme`. CSS written outside any `@layer` declaration loses cascade priority to layered framework styles. Previously (v2.x), unlayered CSS would win by default — this changed in v3.0.0 and broke existing style overrides silently.

**How to avoid:**
All custom CSS overrides must be wrapped in the appropriate `@layer`:

```css
/* RIGHT — survives cascade */
@layer components {
  .my-card { background: #f8fafc; border-radius: 12px; }
}

@layer overrides {
  /* For overriding Quasar !important declarations */
  .q-btn.accent-cta { background: #4f46e5; }
}

/* WRONG — silently overridden by Quasar's layered CSS */
.my-card { background: #f8fafc; }
```

For `app/static/design-system.css`, wrap section by section in `@layer components` unless targeting AG Grid (which lives outside NiceGUI's layer system — see Pitfall 3).

**Warning signs:**
- Style added to CSS file, visible in DevTools DOM, but element looks wrong
- Works with `!important` but fails without it
- Only affects Quasar components (`.q-btn`, `.q-card`, `.q-header`), not plain HTML divs

**Phase to address:** Phase 1 (Design system foundation) — establish layer convention before writing any new CSS.

---

### Pitfall 2: Quasar Color Palette !important Pollution

**What goes wrong:**
All Quasar semantic color classes (`.text-primary`, `.bg-primary`, `.text-negative`, `.text-dark`, etc.) are generated with `!important` on every property. Trying to override them with custom CSS creates a specificity war — your CSS needs `!important` too, which then bleeds into other elements and creates cascading !important pollution across the stylesheet.

**Why it happens:**
NiceGUI maintainers intentionally do not modify `quasar.prod.css`. Issue #4415 was closed as "not planned." The `@layer` system partially neuters this by wrapping Quasar's `!important` in a lower-priority layer, but Quasar-prop-based colors (set via `.props('color=primary')`) still emit `!important` inline-style equivalents in v3.

**How to avoid:**
Do not use Quasar semantic color props for elements that need custom overrides. Instead use Tailwind utility classes directly (`bg-indigo-600`, `text-white`) via `.classes()`:

```python
# WRONG — bg-primary is !important, hard to override
ui.button("CTA").props("color=primary")

# RIGHT — Tailwind class, overridable, in design system
ui.button("CTA").classes("bg-indigo-600 text-white hover:bg-indigo-700")
```

In `app/styles.py`, make sure `BTN_PRIMARY` and similar tokens only use Tailwind, not Quasar props.

**Warning signs:**
- Attempting to override button colors by adding CSS class that Quasar's color prop also touches
- DevTools shows `!important` on color/background rules you didn't write
- Only happens on Quasar-prop-colored components, not plain-styled elements

**Phase to address:** Phase 1 (Design system) — audit `styles.py` tokens. Phase 2 (Header/CTA) — header uses Quasar button props.

---

### Pitfall 3: AG Grid CSS Needs Theme Scope Prefix, Not Tailwind Layer

**What goes wrong:**
Attempts to restyle AG Grid (row height, header background, cell padding, border colors) either do nothing or require `!important` on every rule. The AG Grid table looks like the default alpine theme regardless of what CSS is written.

**Why it happens:**
AG Grid's CSS specificity system requires selectors scoped to the theme class. Without the prefix, AG Grid's bundled CSS wins. For example:

```css
/* WRONG — too low specificity */
.ag-header-cell { background: #f8fafc; }

/* RIGHT — theme-scoped */
.ag-theme-alpine .ag-header-cell { background: #f8fafc; }
/* or if using Quartz theme: */
.ag-theme-quartz .ag-header-cell { background: #f8fafc; }
```

Additionally, AG Grid styles live completely outside NiceGUI's `@layer` system — they're injected by AG Grid's own JS bundle. So `@layer components { .ag-row { ... } }` has no effect on AG Grid's internal cascade.

**How to avoid:**
- Write all AG Grid CSS outside any `@layer` (in `design-system.css`) with `.ag-theme-alpine` prefix
- Use `!important` only where AG Grid's bundled CSS uses `!important` internally (row hover backgrounds, focus rings)
- Check which theme is active: `ui.aggrid` in NiceGUI 3.x defaults to `ag-theme-quartz` — verify with DevTools
- CSS custom properties (`--ag-*`) are the official way to restyle AG Grid without specificity fights:

```css
.ag-theme-quartz {
  --ag-header-background-color: #f8fafc;
  --ag-odd-row-background-color: transparent;
  --ag-row-hover-color: #f1f5f9;
  --ag-border-color: #e2e8f0;
  --ag-font-family: 'IBM Plex Sans', sans-serif;
  --ag-font-size: 13px;
}
```

**Warning signs:**
- AG Grid CSS changes seemingly random — sometimes works, sometimes doesn't
- Styles apply in browser DevTools when typed manually but don't apply from stylesheet
- Row hover color different from rest of grid theme

**Phase to address:** Phase 3 (Registry visual rework) — AG Grid is the core component here.

---

### Pitfall 4: Dark Mode Tailwind Classes Break in Specific Component Trees

**What goes wrong:**
This project uses `dark=False` (light mode only), but Quasar's `body--dark` class can be toggled accidentally or bleed from OS-level dark mode detection. When this happens, Tailwind `dark:` variant classes activate while your custom Tailwind light-mode classes remain — producing a half-dark, half-light visual state with broken colors.

More specifically: since NiceGUI 2.0, there is a verified race condition (Issue #3753) where Tailwind dynamic styles don't populate into the `<style>` tag before elements render. Classes are present in the DOM but their CSS rules are missing from the stylesheet. The symptom is that `w-1/2` or `bg-slate-50` classes appear on elements but have no visual effect.

**Why it happens:**
NiceGUI renders the initial DOM before Tailwind's JIT engine has finished scanning for class names and emitting CSS rules. With `dark=False` set at `ui.run()` level, the risk is lower but not zero — especially when Quasar's storage-persisted dark mode setting conflicts with the hardcoded `dark=False`.

**How to avoid:**
1. Keep `dark=False` at `ui.run()` AND also call `ui.dark_mode(value=False)` inside the `@ui.page('/')` function (belt-and-suspenders). Already done in v0.6, keep it.
2. For new design-system CSS: prefer inline `style=` attributes or `.classes()` with Tailwind for layout-critical properties (width, height, flex). These are applied synchronously.
3. Avoid `dark:` Tailwind variant classes entirely — this is a light-mode-only product.
4. If a Tailwind class seems to have no effect: add a one-off `style="background: red"` inline to confirm the element is being targeted, then diagnose why the class isn't emitting.

**Warning signs:**
- Colors correct in one run, wrong in another (non-deterministic)
- `asyncio.sleep()` workarounds making CSS "work"
- DevTools shows class name on element but no matching CSS rule in Styles panel

**Phase to address:** Phase 1 (Design system) — establish the "no dark: variants" rule upfront.

---

### Pitfall 5: FullCalendar Styles Bleed Into the Rest of the App

**What goes wrong:**
FullCalendar's CDN bundle injects its own CSS globally. Generic selectors like `.fc button`, `.fc table`, `.fc td` can conflict with Tailwind's base reset or your custom CSS if class names overlap. More critically: FullCalendar's theme relies on CSS custom properties (`--fc-*`) which can be overridden by `body` or `:root` level CSS variables you add to the design system.

**Why it happens:**
FullCalendar is loaded via `<script>` tag injected by NiceGUI (lazy-loaded in the current codebase on first calendar toggle). Its CSS is not scoped — it targets generic element selectors with `.fc` parent scope. Any CSS custom property you define on `:root` that shares a name pattern with `--fc-*` variables can accidentally override calendar behavior.

**How to avoid:**
- Always scope FullCalendar overrides to `.fc { ... }` — already done in `design-system.css`
- When adding CSS variables for the design system, use a project-specific prefix: `--yt-*` (юртэг) instead of bare `--color-*` or `--spacing-*`
- After any CSS variable addition, visually check the calendar view in the app — it's the most fragile integration
- Keep FullCalendar CSS overrides in a dedicated `/* FullCalendar theme overrides */` block at the bottom of `design-system.css` — already done, maintain this discipline

**Warning signs:**
- Calendar toolbar buttons lose styling after design-system changes
- Calendar day cells get unexpected backgrounds
- `.fc-button-primary` color reverts to FullCalendar blue after you change indigo palette

**Phase to address:** Phase 5 (Cross-cutting polish) — CSS variable additions happen here and need calendar smoke-test.

---

### Pitfall 6: Breaking Functional Code by Changing Classes That Drive JS Logic

**What goes wrong:**
Renaming or removing Tailwind/custom CSS classes from Python components breaks JavaScript cell renderers and event handlers in AG Grid that target those class names. In this codebase: `actions-cell`, `action-icon`, `expand-icon`, and `status-*` classes are referenced directly in the `STATUS_CELL_RENDERER`, `_ACTIONS_CELL_RENDERER`, and `_EXPAND_CELL_RENDERER` JS strings in `registry_table.py`. Remove or rename any of these and the AG Grid interactivity silently breaks.

**Why it happens:**
In NiceGUI, Python generates both HTML structure and the JS string literals injected into AG Grid cellRenderers. These JS strings use `className` assignments that reference CSS class names. There is no type-checking or IDE warning if a class name drifts between the Python/CSS and the JS string.

**How to avoid:**
- Before renaming any CSS class in `design-system.css` or `styles.py`: grep the entire `app/` directory for that class name string
- Classes that must be treated as a stable API (do not rename without finding all usages):
  - `actions-cell` — `.ag-row:hover .actions-cell` in CSS + JS cellRenderer
  - `action-icon` — JS cellRenderer + CSS
  - `expand-icon` — JS cellRenderer + CSS
  - `status-active`, `status-expiring`, `status-expired`, `status-unknown`, `status-terminated`, `status-extended`, `status-negotiation`, `status-suspended` — used in AG Grid JS AND defined via `@layer components` Tailwind block in `main.py`
- During visual overhaul: add new classes for new visual treatments, never mutate existing functional class names

**Warning signs:**
- AG Grid action column (⋯) disappears or stops responding to hover
- Status badges revert to plain text after CSS changes
- Expand/collapse arrows (▶/▼) in version rows stop working

**Phase to address:** Phase 3 (Registry) — highest risk. Establish "functional class freeze" rule before editing anything in `registry_table.py`.

---

### Pitfall 7: Staggered Row Animation Doubles on Grid Refresh

**What goes wrong:**
The `.ag-row:nth-child()` stagger animation defined in `design-system.css` triggers on every AG Grid `grid.update()` call. In a heavy visual overhaul where design tokens change spacing, fonts, or colors, the grid may refresh multiple times (initial load, data update, column resize). Each refresh re-fires the animation, causing a distracting flash-and-stagger loop visible to the user.

**Why it happens:**
CSS `animation` on `.ag-row` is re-triggered whenever AG Grid re-renders the row DOM (which happens on any `grid.options["rowData"] = ...; grid.update()` call). The animation has no `animation-fill-mode: none` guard and is applied unconditionally via a tag selector.

**How to avoid:**
- Cap total animation duration: current implementation has `animation-delay` up to 640ms for rows 9+. With large datasets, this means the last row animates 640ms after load — acceptable for first load but jarring for rapid refreshes
- Consider adding a CSS class guard: only apply the animation when a special `.animate-initial` class is present on the grid wrapper, and remove it after first load
- After design-system changes: test grid with 50+ rows and trigger a filter change to verify animation doesn't double-fire
- If animateRows causes performance issues on macOS native (pywebview/WebKit): set `animateRows: false` in AG Grid options as a fallback

**Warning signs:**
- Rows flash/blink when switching filter segments (Все / Истекают / Внимание)
- Animation plays during search input typing
- Performance degradation with 200+ rows on macOS (pywebview uses WebKit which is less GPU-optimized than Chrome)

**Phase to address:** Phase 3 (Registry) — animation is part of registry. Phase 5 (Polish) — performance pass.

---

### Pitfall 8: NiceGUI Default Padding Variables Override Tailwind Spacing Classes

**What goes wrong:**
NiceGUI defines `--nicegui-default-padding` and `--nicegui-default-gap` CSS variables applied to `.nicegui-content`, `.nicegui-card`, `.nicegui-row`, `.nicegui-column`. These override Tailwind padding classes (`p-4`, `px-6`, etc.) when the Tailwind class loads into a lower-priority `@layer`. The result: you set `p-6` on a card, it visually shows the NiceGUI default padding instead.

**Why it happens:**
NiceGUI's CSS variable rules are inside a specific layer. Tailwind utility classes are in the `utilities` layer. The interaction between these two layers can produce unexpected results depending on exactly how NiceGUI's framework CSS is ordered relative to your additions. Confirmed in Issue #5408 where Quasar's `q-pa-xs` was silently overridden by `.nicegui-header { padding: var(--nicegui-default-padding) }`.

**How to avoid:**
- Override NiceGUI spacing variables at the `:root` level when needed:
  ```css
  :root {
    --nicegui-default-padding: 0;
    --nicegui-default-gap: 0;
  }
  ```
- Or use `.classes('nicegui-card-tight')` to zero out padding before adding custom spacing
- When adding spacing to design system cards/containers, test visually with DevTools rather than assuming the Tailwind class wins
- Prefer inline `.style('padding: 20px')` on critical layout elements if Tailwind class is unreliable

**Warning signs:**
- Padding looks wrong even though correct Tailwind class is in DevTools DOM
- Spacing inconsistency between different card components using the same Tailwind class
- DevTools shows correct class but `Computed` tab shows a different padding value (from CSS variable)

**Phase to address:** Phase 1 (Design system foundation) — set variable overrides at root level from the start.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcode hex colors inline instead of design tokens | Fast iteration | Colors drift, impossible to theme consistently | Never — defeats the point of a design system |
| Use `!important` to "fix" a CSS specificity issue | Solves the immediate problem | Creates !important chains, makes future overrides impossible | Only as last resort for AG Grid internal overrides |
| Rename functional CSS classes (actions-cell etc.) without grep | Cleaner naming | Silently breaks AG Grid JS renderers | Never |
| Add CSS outside `@layer` | Simpler code | Silently loses to Quasar/NiceGUI layered CSS | Never in NiceGUI 3.x |
| Use Quasar color props (`color=primary`) instead of Tailwind classes | Less verbose | Cannot be overridden without !important war | Only for elements you'll never need to restyle |
| Inline all styles instead of CSS file | Always works, no layer confusion | 2800 LOC of app code gets polluted with style strings | Only for truly one-off critical elements |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| AG Grid | Writing CSS without `.ag-theme-quartz` prefix | Always scope: `.ag-theme-quartz .ag-row { ... }` |
| AG Grid | Using Tailwind classes in cellRenderer JS strings | Use plain CSS classes defined outside @layer, or inline `style=""` in the JS string |
| AG Grid | Setting `domLayout: autoHeight` for variable-height grid | Use `domLayout: normal` + `paginationAutoPageSize` — already fixed in v0.6, don't revert |
| FullCalendar | Modifying `:root` CSS variables with names conflicting with `--fc-*` | Use `--yt-` prefix for all project-level CSS variables |
| FullCalendar | Eager loading CDN script | Already lazy-loaded on calendar toggle — do not change to eager without measuring startup time |
| Quasar buttons | Using `.props('color=indigo-600')` | Use `.classes('bg-indigo-600 text-white')` — Tailwind class is overridable, Quasar prop is not |
| NiceGUI header | Adding custom `ui.header()` styles | Styles must be in `@layer components` or NiceGUI's default header padding overrides them |
| pywebview / native | Testing only in browser, not native window | Always do final visual check in native mode — fonts, shadows, backdrop-filter may render differently in WebKit vs. Chrome |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| CSS `animation` on `.ag-row` firing on every grid.update() | Row flash on filter/search change | Add class guard or use `animation-play-state` | Any grid refresh — low threshold |
| `box-shadow` + `transform` on every card on hover | Jank on hover in grids with 50+ cards | Use `will-change: transform` on template cards, not globally | 20+ animated elements simultaneously |
| Google Fonts CDN load on startup | 200-400ms delay before IBM Plex Sans renders (FOUT) | Already preconnect-loaded in main.py — don't move or reorder the link tag | Every startup if link tag order changes |
| `backdrop-filter: blur()` in native pywebview/WebKit | Significant CPU spike on macOS | Avoid backdrop-filter entirely — WebKit on macOS is not GPU-accelerated the same as Chrome | Immediately on any blur usage |
| Heavy `@keyframes` animation on page-level containers | Stuttering on slow machines | Test on lowest-spec target machine; keep `page-fade-in` under 200ms | Low-end hardware |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Removing padding from AG Grid rows during visual overhaul | Rows become too dense, content truncates | Increase `--ag-row-height` via CSS variable instead of removing padding |
| Making header visually heavier (taller, more elements) | Reduces vertical space for the registry table — core of the app | Keep header at 48px (h-12) — any increase must be deliberate and tested with full registry visible |
| Adding decorative animations to functional status badges | Distracts from status reading during rapid scanning | Status badge `badge-in` animation already exists; don't add persistent pulse/glow to status badges |
| Hiding AG Grid floating filters during redesign | Users lose column-level filter capability they may rely on | Keep `floatingFilter: True` on contract_type and counterparty columns |
| Using low-contrast accent colors to look "subtle" | Юрист пропустит срочный статус (expired/expiring) | Status color contrast must meet WCAG AA minimum even if overall palette is muted |

---

## "Looks Done But Isn't" Checklist

- [ ] **Splash hero section:** Check that the CTA button routes correctly to wizard flow — visual change may accidentally remove the `on_click` handler if the button is rebuilt from scratch
- [ ] **AG Grid after theme rework:** Test all 8 status badges render correctly (active/expiring/expired/unknown/terminated/extended/negotiation/suspended) — `status-*` classes must remain in `@layer components` block in `main.py`
- [ ] **Header CTA button:** Confirm `+ Загрузить документы` still triggers `pick_folder()` after header is rebuilt — structural changes to `render_header()` can lose the callback binding
- [ ] **Settings page:** Verify provider radio buttons still save to config correctly after visual sectioning — visual refactors often re-wrap inputs in new containers that break `bind_value` targets
- [ ] **FullCalendar after palette change:** Open calendar view and verify events still render with correct colors — `--fc-button-bg-color` and `--fc-event-bg-color` may need manual sync with new palette
- [ ] **Document card breadcrumbs:** After typography overhaul, confirm breadcrumb nav links still fire `ui.navigate.to()` correctly — don't confuse `.classes()` changes with `.props()` or event handler changes
- [ ] **Animations under reduced-motion:** macOS Accessibility setting "Reduce Motion" must suppress all animations — `@media (prefers-reduced-motion: reduce)` block already exists in `design-system.css`, keep it intact after adding new animations
- [ ] **Template card CRUD:** After visual card rebuild, confirm Delete/Edit dialogs still open correctly — `.on('click')` handlers on card children can be swallowed by parent click events if event propagation changes

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| CSS silently not applying (layer issue) | LOW | Wrap offending CSS in `@layer components { }`, clear browser cache in pywebview |
| Quasar !important war | MEDIUM | Switch component from Quasar prop-based color to Tailwind class; remove !important from both sides |
| Functional class renamed, AG Grid JS broken | MEDIUM | Restore old class name in CSS + JS cellRenderer string simultaneously; grep for all usages first |
| FullCalendar broken after CSS variable addition | LOW | Rename CSS variable to use `--yt-` prefix; smoke-test calendar after every `:root` variable change |
| Animation double-fire on grid refresh | LOW | Add `animation: none` override scoped to a `.loaded` class; apply class after first data load |
| NiceGUI default padding overriding Tailwind | LOW | Add `--nicegui-default-padding: 0` to `:root` at top of design-system.css |
| Breaking splash/onboarding flow during visual rebuild | HIGH | Keep functional logic separate: rebuild visual wrapper, preserve all event handlers and callbacks; test first-run flow end-to-end after each phase |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| CSS @layer ignored (Pitfall 1) | Phase 1: Design system foundation | Every CSS rule in new design system must be in `@layer components` or `@layer overrides` |
| Quasar !important pollution (Pitfall 2) | Phase 1: Design system / Phase 2: Header | Audit `styles.py` tokens; replace any Quasar props with Tailwind classes before building new components |
| AG Grid theme scoping (Pitfall 3) | Phase 3: Registry visual rework | AG Grid DevTools inspection — confirm `.ag-theme-quartz` prefix on all AG Grid CSS |
| Dark mode race condition (Pitfall 4) | Phase 1: Design system | Establish "no dark: variants" rule; confirm `ui.dark_mode(value=False)` persists |
| FullCalendar CSS bleed (Pitfall 5) | Phase 5: Cross-cutting polish | Visual smoke-test of calendar view after every `:root` CSS variable addition |
| Functional class breakage (Pitfall 6) | Phase 3: Registry | Grep `app/` for class name before any rename; test AG Grid actions and status badges after every change |
| Animation double-fire (Pitfall 7) | Phase 3: Registry / Phase 5: Polish | Trigger filter segment switch and search while watching for animation replay |
| NiceGUI padding variable override (Pitfall 8) | Phase 1: Design system | Set `--nicegui-default-padding: 0` at `:root` at the start of design-system.css |

---

## Sources

- [Dark mode breaks Tailwind styling since NiceGUI 2.0 — Issue #3753](https://github.com/zauberzeug/nicegui/issues/3753)
- [NiceGUI v3 CSS customization broken — Discussion #5240](https://github.com/zauberzeug/nicegui/discussions/5240)
- [NiceGUI v3.0.0 Release Notes — CSS layers breaking change](https://github.com/zauberzeug/nicegui/releases/tag/v3.0.0)
- [Quasar color palette !important pollution — Issue #4415](https://github.com/zauberzeug/nicegui/issues/4415)
- [Quasar padding classes ignored — Issue #5408](https://github.com/zauberzeug/nicegui/issues/5408)
- [AG Grid styling with CSS properties — Issue #4743](https://github.com/zauberzeug/nicegui/issues/4743)
- [AG Grid dark theme in NiceGUI — Discussion #3611](https://github.com/zauberzeug/nicegui/discussions/3611)
- [AG Grid performance in Electron/desktop — Medium](https://medium.com/swlh/ag-grid-performance-optimization-memory-usage-and-speed-slowness-considerations-for-enterprise-72b4b5e9e64d)
- [NiceGUI styling methods overview — Discussion #1806](https://github.com/zauberzeug/nicegui/discussions/1806)
- [NiceGUI Styling and Theming — DeepWiki](https://deepwiki.com/zauberzeug/nicegui/7.2-styling-and-theming)
- [NiceGUI warning on classes being lost — Discussion #3204](https://github.com/zauberzeug/nicegui/discussions/3204)

---
*Pitfalls research for: NiceGUI 3.x visual overhaul — ЮрТэг v0.7*
*Researched: 2026-03-22*
