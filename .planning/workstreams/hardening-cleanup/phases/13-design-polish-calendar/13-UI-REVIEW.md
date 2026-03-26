# Phase 13 — UI Review

**Audited:** 2026-03-22
**Baseline:** 13-UI-SPEC.md (approved design contract)
**Screenshots:** Not captured (Playwright CLI not installed; dev server running at port 8080)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Calendar and action strings match spec; two action menu stubs use developer-facing "следующей версии" copy |
| 2. Visuals | 3/4 | Clear hierarchy, indigo CTA focal points, toggle icons accessible via title attribute; text-base and text-2xl are off-spec sizes |
| 3. Color | 3/4 | Palette migration complete and clean; document.py uses text-blue-600/bg-blue-600 outside the accent contract |
| 4. Typography | 2/4 | font-medium (500 weight) appears 18 times across app/; spec declares only font-normal and font-semibold |
| 5. Spacing | 4/4 | Standard scale throughout; three min-w-[] arbitrary values in dialog modals are acceptable exceptions |
| 6. Experience Design | 3/4 | Loading, empty, error states all handled; two feature-stub notifies expose developer copy; upload button correctly disabled during processing |

**Overall: 18/24**

---

## Top 3 Priority Fixes

1. **font-medium used 18 times across all pages** — violates the 2-weight contract (400/600 only); blurs the typographic hierarchy between body and headings — replace all `font-medium` with either `font-normal` (body, captions) or `font-semibold` (headings, CTAs) per the spec rule
2. **text-blue-600 / bg-blue-600 used 7 times in document.py** — introduces a fourth color (blue) into the accent slot; lawyers will interpret blue links/buttons differently from indigo primary actions — replace with `text-indigo-600` / `bg-indigo-600` to maintain the 60/30/10 contract
3. **Action menu stubs say "Функция доступна в следующей версии"** (Скачать оригинал, Переобработать) — lawyer-facing message sounds like a bug report, not a product decision — either remove the stub menu items entirely or change to "Готовится" or hide with `set_visibility(False)` until implemented

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Matches spec:**
- Calendar toggle title attributes: `title="Список"` and `title="Календарь"` — matches copywriting contract exactly (icon-only, label via title attribute)
- Tooltip type labels: `'Дата окончания'` / `'Платёж'` — matches spec (app/main.py:162)
- Tooltip CTA: `'Открыть →'` — matches spec (app/main.py:170)
- Calendar nav: `buttonText: { today: 'Сегодня' }` — matches spec (app/main.py:151)
- Calendar error state: `'Не удалось загрузить события календаря. Попробуйте переключить вид.'` — matches spec exactly (app/pages/registry.py:207-210)
- Empty state heading: `"Загрузите первые документы"` — contextual and professional (app/pages/registry.py:68)
- Delete confirm dialog: proper Russian copy, confirmation pattern present (app/pages/registry.py:322-333)

**Issues:**
- `app/pages/registry.py:274`: `ui.notify("Функция доступна в следующей версии", type="info")` for "Скачать оригинал" — surfaces to users, developer-facing phrasing
- `app/pages/registry.py:276`: Same stub copy for "Переобработать"
- `app/pages/registry.py:331`: Delete stub uses `type="warning"` for same stub message — three visible placeholders using identical generic text

No generic English labels (Submit, OK, Cancel, Save) found. All visible copy is in Russian.

---

### Pillar 2: Visuals (3/4)

**Strengths:**
- Clear primary focal point on registry: indigo CTA "Выбрать папку" in empty state (app/pages/registry.py:77-79)
- Active segment control uses `bg-indigo-600` — visually distinct from inactive slate
- Icon-only toggle buttons (≡ / ⊞) have `title` attributes for accessibility — matches spec
- Staggered row animation and page fade-in applied via global CSS — motion is present without being mechanical
- Header is minimal (logo + text nav tabs) — no visual noise
- Document card header has clear 3-zone layout: back button left, title center, prev/next right

**Issues:**
- `app/components/header.py:35`: Logo "ЮрТэг" uses `text-base` (16px). The spec scale has `text-sm` (body, 14px) and `text-xl` (heading, 20px); `text-base` is an intermediate step not declared in typography. At 16px and `font-semibold`, the logo could be stronger at `text-xl`
- `app/pages/templates.py:230`: Page heading "Шаблоны" uses `text-2xl` — not in the spec scale (which has `text-xl` for headings, `text-3xl` only for the brand mark on splash)
- `app/pages/settings.py:157`: "Предупреждения" section label uses `text-base font-medium` — neither the correct size nor the correct weight
- The "+ Загрузить" header button is `flat` style with `text-slate-700` — visually indistinguishable from nav tabs; no visual affordance that it triggers an action vs navigation

---

### Pillar 3: Color (3/4)

**Slate migration: COMPLETE**
- Zero `gray-*` Tailwind classes in `app/` — confirmed by grep returning no matches
- `_STATUS_CSS` migrated correctly: `status-unknown` and `status-terminated` use `bg-slate-100 text-slate-500`; semantic colors (green/yellow/red/blue/purple/orange) unchanged
- `_ACTIONS_CSS`: all hex codes migrated to slate/indigo ramp — `#64748b`, `#4f46e5`, `#94a3b8`, `#475569` confirmed
- Indigo accent usage: 4 Tailwind class instances (splash CTAs x2, segment active, empty state CTA) — restrained and correct
- Inline hex colors in `_CALENDAR_JS` and `tour.py` are all slate/indigo ramp values — consistent with the palette

**Issues:**
- `app/pages/document.py:202`: `text-blue-600` on "Изменить" button — outside accent contract. Spec reserves indigo only; blue introduces a fifth semantic tone that conflicts with the status badge system (blue = "extended" contract status)
- `app/pages/document.py:241`: `bg-blue-600 text-white` on "Применить" button — this is a primary action button rendered in blue, not indigo
- `app/pages/document.py:290,309,325,358,364`: `text-blue-600` on 5 link/button elements in AI Review and version diff sections — 7 blue accent instances in document.py alone

The 60/30/10 contract: white/slate-50/indigo-600 is met on all other pages. The document detail page breaks it with unsanctioned blue.

---

### Pillar 4: Typography (2/4)

**Spec contract:** Two weights only — `font-normal` (400) for body/captions, `font-semibold` (600) for headings and CTAs. No `font-medium` (500) anywhere.

**Reality:**
```
font-semibold: 19 instances — correct
font-normal:    7 instances — correct
font-medium:   18 instances — VIOLATION
```

**font-medium violations by file:**
- `app/components/header.py:96`: `font-medium` on "Новый клиент" dialog heading
- `app/main.py:194-201`: All 8 status badge classes use `font-medium` — these are rendered in every registry row
- `app/pages/registry.py:38-39`: Segment control uses `font-medium` for both active and inactive states
- `app/pages/document.py:43,50`: Metadata field labels use `font-medium` (should be `font-normal` for captions)
- `app/pages/document.py:342`: Version number uses `font-medium`
- `app/pages/settings.py:88,136,157,175`: Section headings use `font-medium` (should be `font-semibold`)

**Size violations:**
- `text-base` (16px): `app/components/header.py:35` (logo), `app/pages/settings.py:157` ("Предупреждения") — not in declared scale
- `text-2xl` (24px): `app/pages/templates.py:230` — not in declared scale (spec has `text-xl` for page headings)
- `text-lg` (18px): 9 instances — not in the 4-step scale (12/14/20/28). Scale declares `text-xl` for headings; `text-lg` falls between body and heading, weakening visual contrast

The status badge `font-medium` is significant since it appears in every table row on the main registry screen.

---

### Pillar 5: Spacing (4/4)

**Scale compliance:**
- Primary spacing values in use: `gap-1/2/4/6/8`, `p-2/3/4/5/6/8`, `px-2/3/4/6/8`, `py-0.5/1/2/3/6`, `my-4` — all are Tailwind standard multiples of 4px
- Layout zones: registry uses `px-6 pt-4 pb-2` for search row, `px-6` for calendar container — consistent with the `lg` (24px) spacing token declared in spec
- Document page: `max-w-4xl mx-auto px-6 py-6 gap-6` — well-structured, matches spec intent
- Settings: `p-8 gap-6` for content panel, `p-3 gap-1` for nav — appropriate density contrast

**Arbitrary values (acceptable):**
- `app/pages/templates.py:90,127,162`: `min-w-[400px]`, `min-w-[360px]` on dialogs — these are minimum width constraints on modal dialogs, not spacing overrides. Acceptable per the spec's stated exceptions for dialog sizing.

No non-standard pixel or rem values in spacing roles. Spec-declared spacing exceptions for calendar (mt-4, p-0) and toggle (p-2) are implemented correctly.

---

### Pillar 6: Experience Design (3/4)

**State coverage:**
- Loading: `ui.spinner('dots')` shown during AI review and template matching operations (app/pages/document.py:275,318) — present
- Upload progress: progress section with bar + count label + file label + error column — full fidelity (app/pages/registry.py:130-139)
- Empty state: registry has dedicated `_render_empty_state()` with illustration, heading, description, CTA — matches spec (app/pages/registry.py:46-90)
- Error state: calendar load failure shows `ui.notify(..., type='warning')` — matches spec copy exactly
- Disabled state: upload button disabled during processing, prev/next navigation buttons disabled at boundaries — correct
- Destructive confirm: delete action shows confirmation dialog with "Удалить" / "Отмена" — implemented
- Calendar toggle: state machine properly handled via `state.calendar_visible`, container visibility toggling is clean

**Issues:**
- Two stub menu items ("Скачать оригинал", "Переобработать") emit `type="info"` notify rather than being removed or hidden. From a UX standpoint, presenting menu items that don't function trains users to distrust the interface. These items are inside the context menu (hover-actions) that appears on every row — high exposure surface.
- `app/pages/document.py:289-291`: When no templates exist, the copy "Нет шаблонов." followed by a link is structurally correct but the period after "шаблонов" before the linked sentence creates awkward punctuation ("Нет шаблонов. Добавьте...") — minor UX polish issue.
- No keyboard navigation or focus management for the calendar tooltip (can only be dismissed via click outside) — acceptable for desktop MVP per CONTEXT.md out-of-scope rules.

---

## Registry Safety

Shadcn not initialized (`components.json` not found). No third-party component registry audit required.

---

## Files Audited

- `/app/main.py` — Global CSS injection: `_FONT_CSS`, `_FULLCALENDAR_CSS`, `_ANIMATION_CSS`, `_CALENDAR_JS`, `_STATUS_CSS`, `_ACTIONS_CSS`
- `/app/state.py` — `AppState` dataclass, `calendar_visible` field
- `/app/pages/registry.py` — Segment control, calendar toggle, `_show_calendar()`, `_switch_view()`, empty state
- `/app/pages/document.py` — Metadata grid, status section, AI review, version history
- `/app/pages/settings.py` — Left nav, AI/processing/Telegram sections
- `/app/pages/templates.py` — Template cards, dialogs
- `/app/components/header.py` — Navigation header, client dropdown
- `/app/components/onboarding/splash.py` — Onboarding splash screen
- `/app/components/onboarding/tour.py` — Guided tour overlay
- `/app/components/process.py` — Upload pipeline, progress rendering
- `.planning/phases/13-design-polish-calendar/13-UI-SPEC.md` — Audit baseline
- `.planning/phases/13-design-polish-calendar/13-CONTEXT.md` — Decision context
- `.planning/phases/13-design-polish-calendar/13-01-SUMMARY.md` through `13-04-SUMMARY.md`
