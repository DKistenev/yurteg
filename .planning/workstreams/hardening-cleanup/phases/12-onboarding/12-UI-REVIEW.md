# Phase 12 — UI Review

**Audited:** 2026-03-22
**Baseline:** 12-UI-SPEC.md (approved design contract)
**Screenshots:** Not captured (no NiceGUI dev server detected on ports 3000, 5173, 8080)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | All declared CTAs present; model failure error state from spec is missing |
| 2. Visuals | 3/4 | Layout and hierarchy match spec; no visual hierarchy issue on splash |
| 3. Color | 2/4 | Accent changed from spec `bg-gray-900` (#111827) to `bg-indigo-600` (#4f46e5) across all CTAs and tour buttons |
| 4. Typography | 3/4 | `font-medium` appears in segment controls — spec allows only `font-normal` and `font-semibold` |
| 5. Spacing | 4/4 | All scale values from spec, no arbitrary units, consistent pattern |
| 6. Experience Design | 3/4 | Loading and empty states present; model load failure silently logged, no user-facing message |

**Overall: 18/24**

---

## Top 3 Priority Fixes

1. **Color contract violation: accent is `bg-indigo-600` everywhere, spec declares `bg-gray-900`** — Users get indigo (#4f46e5) buttons instead of the near-black (#111827) tone the design contract specifies. Also breaks internal color consistency: splash uses `bg-indigo-600`, tour spotlight uses `#4f46e5` outline and button background, while the spec says `ring-gray-900` and `bg-gray-900` for all accent surfaces. Fix: replace `bg-indigo-600` with `bg-gray-900` in `splash.py` lines 103 and 113; replace `bg-indigo-600` with `bg-gray-900` in `registry.py` line 79; replace `#4f46e5` with `#111827` in `tour.py` lines 114 and 183; change `color=indigo` to `color=grey-9` in `splash.py` line 63.

2. **Missing model load failure error state** — UI-SPEC Copywriting Contract declares the copy «Не удалось загрузить модель. Проверьте интернет-соединение или выберите облачный провайдер в настройках.» but the implementation silently calls `logger.warning()` with no user-visible message. A lawyer on a slow connection has no feedback that the download failed. Fix: in `splash.py` `_run_model_download()` catch block (line 138), update `progress_label.set_text` to the spec error string and visually distinguish (e.g. `text-red-600`) via `loop.call_soon_threadsafe`.

3. **`font-medium` used in segment controls — not in the 2-weight spec** — `registry.py` lines 38–39 use `font-medium` for all segment buttons (`_SEG_ACTIVE`, `_SEG_INACTIVE`). The UI-SPEC Typography section explicitly forbids `font-medium` (500) in this phase, allowing only `font-normal` (400) and `font-semibold` (600). Although the segment controls are Phase 08 code, they are rendered on the same page as onboarding components. Fix: change `font-medium` to `font-semibold` on the active segment and `font-normal` on inactive, consistent with the CTA weight pattern.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

All Copywriting Contract entries verified present in code:

| Element | Expected | Found | File |
|---------|----------|-------|------|
| Splash heading | «Добро пожаловать!» | PASS | splash.py:42 |
| Capability bullet 1 | «Загрузите папку → получите реестр» | PASS | splash.py:47 |
| Capability bullet 2 | «Автосортировка по папкам» | PASS | splash.py:48 |
| Capability bullet 3 | «Контроль сроков и предупреждения» | PASS | splash.py:49 |
| Wizard step 1 CTA | «Далее: Telegram →» | PASS | splash.py:112 |
| Wizard step 2 CTA | «Сохранить и начать» | PASS | splash.py:102 |
| Wizard skip | «Пропустить» | PASS | splash.py:99, 109 |
| Wizard step 2 heading | «Подключите Telegram-бот» | PASS | splash.py:86 |
| Wizard step 2 body | «Получайте уведомления…» | PASS | splash.py:91 |
| Input placeholder | «110201543:AAHdqTcvCH1vGWJxfSeofSs0K» | PASS | splash.py:95 |
| Empty state heading | «Загрузите первые документы» | PASS | registry.py:68 |
| Empty state body | «Выберите папку с PDF или DOCX…» | PASS | registry.py:73 |
| Empty state CTA | «Выбрать папку» | PASS | registry.py:77 |
| Hint bullet 1 | «Извлечёт метаданные» | PASS | registry.py:82 |
| Hint bullet 2 | «Разложит по папкам» | PASS | registry.py:85 |
| Hint bullet 3 | «Проверит сроки» | PASS | registry.py:88 |
| Tour step 1 title | «Реестр документов» | PASS | tour.py:19 |
| Tour step 1 body | «Это ваш реестр…» | PASS | tour.py:20 |
| Tour step 2 title | «Фильтры и поиск» | PASS | tour.py:23 |
| Tour step 2 body | «Используйте сегменты…» | PASS | tour.py:24 |
| Tour step 3 title | «Загрузка документов» | PASS | tour.py:28 |
| Tour step 3 body | «Нажмите здесь…» | PASS | tour.py:29 |
| Tour step counter | «Шаг {N} / 3» | PASS | tour.py:164 |
| Tour skip | «Пропустить тур» | PASS | tour.py:180 |
| Tour last step CTA | «Завершить тур» | PASS | tour.py:160 |

**Missing:** The error state copy «Не удалось загрузить модель. Проверьте интернет-соединение или выберите облачный провайдер в настройках.» (declared in Copywriting Contract) is not rendered anywhere. Errors are silently logged at `logger.warning` — `splash.py:139, 153`. No generic English strings found.

Score rationale: 22/25 declared strings present, one error string entirely absent, one state silently swallowed.

---

### Pillar 2: Visuals (3/4)

Confirmed from code review:

- Focal point on splash: logo → heading → bullets → progress → wizard, vertical flow is correct per D-02 layout spec.
- SVG folder icon in empty state uses correct inline SVG (48x48, outline stroke), not emoji. Code: `registry.py:62–66`.
- Bullet markers use `·` Unicode point with `text-gray-400` / `text-slate-400` — visually secondary to content text. Correct.
- Wizard navigation row uses `justify-between items-center` — «Пропустить» left, CTA right. Correct visual balance.
- Tour tooltip structure: step counter (muted) → title (prominent) → body (secondary) → buttons. Correct hierarchy.
- Icon-only buttons: calendar toggle uses `≡` and `⊞` glyphs (`registry.py:125–128`) with `title=` prop for tooltip, no `aria-label`. Acceptable in native desktop context but marginal.
- Progress bar height: `h-1.5` (6px) — thin and visually secondary as specified. Correct.

Minor issue: the hidden `done_btn` in `tour.py:47` has `.classes("hidden").style("display: none !important")` — double-hiding is defensive but the `!important` inline style could cause specificity issues if tour overlay CSS stacks. Low severity.

---

### Pillar 3: Color (2/4)

**Critical deviation from spec:** The UI-SPEC Color section declares accent as `#111827` / `bg-gray-900`. The implementation uses `#4f46e5` / `bg-indigo-600` throughout.

| Surface | Spec | Actual | File |
|---------|------|--------|------|
| Wizard step 1 CTA | `bg-gray-900` | `bg-indigo-600` | splash.py:113 |
| Wizard step 2 CTA | `bg-gray-900` | `bg-indigo-600` | splash.py:103 |
| Empty state CTA | `bg-gray-900` | `bg-indigo-600` | registry.py:79 |
| Progress bar fill | `color=grey-9` | `color=indigo` | splash.py:63 |
| Tour CTA button | `bg: #111827` | `bg: #4f46e5` | tour.py:183 |
| Tour spotlight outline | `ring-gray-900` (#111827) | `#4f46e5` | tour.py:114 |

The color itself is internally consistent (all indigo, no mixed accent) and is visually a reasonable branding choice. However, it diverges from the explicit design contract. The spec rationale was that `bg-gray-900` is the established segment control accent in Phases 7–11.

Additional findings:
- `bg-white` background on splash: PASS (spec: dominant 60%).
- `bg-slate-50` for capability bullets: equivalent to spec `bg-gray-50` (slate and gray scales are visually identical at the 50 step). Acceptable.
- Tour tooltip border: `#e2e8f0` (slate-200) vs spec `border-gray-200` (#e5e7eb). Values are one step apart in the scale, visually imperceptible.
- Tour tooltip shadow: `box-shadow: 0 1px 3px rgba(0,0,0,0.1)` vs spec `shadow-sm`. Equivalent.
- No hardcoded colors in the Python Tailwind classes — hardcoded hex values are only in the inline JS HTML string in `tour.py`, which is the only way to express them in that context. Correct approach.

---

### Pillar 4: Typography (3/4)

Font size distribution across onboarding files:

| Size | Count | Spec Allowed |
|------|-------|--------------|
| `text-sm` | 17 | Yes |
| `text-xl` | 3 | Yes |
| `text-3xl` | 1 | Yes (ЮрТэг logo only) |
| `text-lg` | 1 | No — not declared |
| `text-xs` | 1 | No — not declared |

`text-lg` appears once — checking source: this is in `registry.py:325` delete confirmation dialog label (`"Удалить документ?"`) which is Phase 08 code rendered contextually, not Phase 12 onboarding. Not a new violation.

`text-xs` appears once — at `registry.py:138` for `file_label` in the processing progress section (Phase 08). Not Phase 12 code.

Font weight findings:

| Weight | Count | Spec Allowed |
|--------|-------|--------------|
| `font-semibold` | 8 | Yes |
| `font-normal` | 7 | Yes |
| `font-medium` | 2 | **No** |

`font-medium` at `registry.py:38–39` in `_SEG_ACTIVE` / `_SEG_INACTIVE` constants. These are Phase 08 segment controls rendered on the registry page alongside Phase 12 components. The spec says no `font-medium` anywhere in this phase. Weight 500 vs the declared two-weight system (400/600).

IBM Plex Sans loaded globally via `main.py:75–79` — applied to all elements via `* { font-family: 'IBM Plex Sans', sans-serif; }`. Correct.

In-JS tooltip typography (tour.py): uses `font-size: 14px` and `font-weight: 600` directly — consistent with spec `text-sm` / `font-semibold` equivalents.

---

### Pillar 5: Spacing (4/4)

Spacing classes used across all Phase 12 files map cleanly to the declared scale:

| Class | Scale Token | Spec Value | Status |
|-------|-------------|-----------|--------|
| `py-16` | 3xl | 64px | PASS |
| `px-8`, `p-8` | xl | 32px | PASS |
| `mt-8`, `gap-8` | xl | 32px | PASS |
| `mt-6`, `gap-6`, `p-6`, `px-6` | lg | 24px | PASS |
| `gap-4`, `p-4`, `mt-4` | md | 16px | PASS |
| `gap-2`, `p-2`, `mt-2` | sm | 8px | PASS |
| `gap-1`, `p-1` | xs | 4px | PASS |
| `py-2`, `px-4`, `py-1` | sm/md | 8px/16px | PASS |

No arbitrary values (`[Npx]`, `[Nrem]`) found in any Phase 12 file. All spacing stays within the declared 4px-base scale.

Minor: `gap-0` at `splash.py:36` (inner column) suppresses the default gap — intentional per the stepped margin pattern (`mt-6`, `mt-8` used explicitly). Not a violation.

---

### Pillar 6: Experience Design (3/4)

**Loading states:**
- Splash progress bar: `ui.linear_progress(value=0)` with thread-safe updates via `loop.call_soon_threadsafe`. Label updates in real-time: «Загрузка модели (X/940 МБ)». Pitfall 1 guard sets `set_value(1.0)` after `ensure_model` returns regardless of progress callback invocation. Well-implemented.
- Registry processing progress: hidden `progress_section` shown during pipeline, with `progress_bar`, `count_label`, `file_label`, and `error_col`. Present from Phase 08 — correctly wired.

**Error states:**
- Model download failure: caught at `splash.py:138`, logged via `logger.warning`. No user-facing message rendered. Spec declares specific error copy for this case — not shown. Medium severity: on poor connection, the lawyer sees the progress bar just stop at a non-zero value with no explanation.
- Registry pipeline errors: `error_col` element present — errors appended during processing per Phase 08 implementation.

**Empty states:**
- Registry empty state: guards against false trigger when filters are active (`not state.filter_search and active_segment["value"] == "all"` at `registry.py:391–393`). Condition correct per Pitfall 4.
- Calendar toggle buttons hidden when empty state is shown (`list_btn.set_visibility(False)` at `registry.py:397–398`) — prevents illogical calendar offer with zero documents. Good defensive UX.

**Guided tour — one-time trigger:**
- `tour_completed` flag read from settings before rendering tour. Tour only renders when `rows > 0 AND not tour_completed`. Flag saved via `save_setting` on complete or skip. Correct.
- `setTimeout(startTour, 500)` guard gives AG Grid render time (Pitfall 2 guard). Correct.

**Disabled states / destructive confirmations:**
- Delete action shows `ui.dialog` with «Удалить» / «Отмена» — confirmation present (`registry.py:322–333`).
- No disabled button states on wizard CTAs during model download — «Пропустить» works immediately per Pitfall 5 guard. Correct by design.

**Missing:** No user-visible feedback when `ensure_model` fails (only `logger.warning`). No `ui.notify` or label update with error text.

---

## Registry Safety

Registry audit: not applicable — NiceGUI Python project, no component registry (`components.json` not present).

---

## Files Audited

- `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/app/components/onboarding/splash.py`
- `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/app/components/onboarding/tour.py`
- `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/app/components/onboarding/__init__.py`
- `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/app/pages/registry.py`
- `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/app/main.py`
- `.planning/phases/12-onboarding/12-UI-SPEC.md`
- `.planning/phases/12-onboarding/12-01-PLAN.md`
- `.planning/phases/12-onboarding/12-02-PLAN.md`
- `.planning/phases/12-onboarding/12-01-SUMMARY.md`
- `.planning/phases/12-onboarding/12-02-SUMMARY.md`
- `.planning/phases/12-onboarding/12-CONTEXT.md`
