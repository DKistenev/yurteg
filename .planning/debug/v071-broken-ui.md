---
status: awaiting_human_verify
trigger: "AG Grid shows '1 to 10 of 10' but ALL rows are invisible"
created: 2026-03-23T00:00:00
updated: 2026-03-23T12:30:00
---

## Current Focus

hypothesis: CSS row-in animation (animation-fill-mode:both, starts at opacity:0) conflicts with AG Grid 34's built-in .ag-opacity-zero{opacity:0!important} fade-in system. The !important flag blocks animation opacity:1. ALSO: .ag-theme-quartz CSS selector is dead in AG Grid 34 (JS theme API), so --ag-* variable overrides never apply.
test: Remove .ag-row animation block from design-system.css. Move --ag-* variables to :root or [data-ag-theme-mode] selector.
expecting: Rows become visible, theming variables take effect
next_action: Apply fix to design-system.css

## Symptoms

expected: AG Grid displays 10 rows of contract data
actual: Grid area is a white rectangle with no rows visible, but pagination says "1 to 10 of 10"
errors: No JS errors, only AG Grid deprecation warnings
reproduction: Load the app, navigate to registry page
started: After v0.7.1 UI redesign

## Eliminated

- hypothesis: domLayout:autoHeight + min-h-0 collapsing container height
  evidence: User confirmed removing domLayout, min-h-0, and adding height:520px did NOT fix the invisible rows
  timestamp: 2026-03-23T00:21:00

- hypothesis: Column field names don't match rowData keys
  evidence: SQL returns contract_type, counterparty, computed_status, amount — all match COLUMN_DEFS fields. row_factory=sqlite3.Row, dict(r) works.
  timestamp: 2026-03-23T12:10:00

- hypothesis: Grid container has insufficient height or is hidden
  evidence: Grid has explicit style("height: 520px;"), container set_visibility(True) before grid creation
  timestamp: 2026-03-23T12:12:00

- hypothesis: CSS hiding .ag-row via display:none or visibility:hidden
  evidence: No such rules in any CSS file
  timestamp: 2026-03-23T12:13:00

## Evidence

- timestamp: 2026-03-23T12:15:00
  checked: AG Grid 34 bundle (dist/index.js) for opacity-related code
  found: AG Grid 34 has ".ag-opacity-zero{opacity:0!important}" CSS built into its JS bundle. JS adds this class to rows on creation (fadeInAnimation[e]&&n.push("ag-opacity-zero")) then removes it to trigger CSS transition fade-in.
  implication: AG Grid has its OWN row animation system using opacity:0!important + transition.

- timestamp: 2026-03-23T12:18:00
  checked: design-system.css lines 10-26 — .ag-row animation
  found: ".ag-row { animation: row-in 200ms cubic-bezier(0.25,1,0.5,1) both; }" with staggered delays up to 640ms. @keyframes row-in goes from opacity:0 to opacity:1. animation-fill-mode:both means backwards fill sets opacity:0 before animation starts.
  implication: CONFLICT — our animation sets opacity:0 (backwards fill), AG Grid also sets opacity:0!important. When AG Grid removes its class to trigger fade-in via transition, our animation's fill-mode may interfere with the transition. The !important during animation playback prevents opacity:1 from taking effect.

- timestamp: 2026-03-23T12:22:00
  checked: AG Grid 34 row transition CSS in bundle
  found: ".ag-row-animation) .ag-row{transition:transform .4s,top .4s,opacity" — AG Grid applies opacity transition on rows for its own fade-in
  implication: AG Grid expects to control row opacity via transition. Our CSS animation overrides the transition behavior.

- timestamp: 2026-03-23T12:25:00
  checked: NiceGUI aggrid.js — theme handling
  found: AG Grid 34 uses JS theme API: theme = AgGrid.themeQuartz.withPart(AgGrid.colorSchemeVariable). Does NOT add CSS class .ag-theme-quartz to DOM. Uses data-ag-theme-mode attribute instead.
  implication: All --ag-* CSS variables in .ag-theme-quartz selector have ZERO effect — dead CSS.

## Resolution

root_cause: |
  PRIMARY: CSS animation ".ag-row { animation: row-in 200ms ... both }" in design-system.css conflicts with AG Grid 34's built-in row fade-in system (.ag-opacity-zero{opacity:0!important}). The animation-fill-mode:both sets backwards fill (opacity:0) which compounds with AG Grid's !important opacity:0. When AG Grid removes ag-opacity-zero to trigger its transition-based fade-in, the CSS animation's fill-mode interference prevents rows from becoming visible.

  SECONDARY: .ag-theme-quartz CSS selector is dead — AG Grid 34 uses JS theme API, not CSS class. All --ag-* variable overrides in design-system.css have no effect.

fix: |
  1. design-system.css: Remove .ag-row animation block and staggered delays (lines 8-26)
  2. design-system.css: Replace .ag-row transition with one that doesn't conflict with AG Grid's opacity transition
  3. design-system.css: Move --ag-* variables from .ag-theme-quartz to :root selector so they're globally available

verification:
files_changed:
  - app/static/design-system.css
