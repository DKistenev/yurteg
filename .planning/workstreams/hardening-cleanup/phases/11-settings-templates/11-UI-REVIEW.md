# Phase 11 — UI Review

**Audited:** 2026-03-22
**Baseline:** Abstract 6-pillar standards (no UI-SPEC for this phase)
**Screenshots:** Not captured (no dev server detected)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Copy is contextual and Russian throughout; empty state secondary line is weak |
| 2. Visuals | 3/4 | Clean macOS Preferences layout; template cards lack visual anchor/icon |
| 3. Color | 4/4 | Tight slate palette, no hardcoded hex values, accent used sparingly and correctly |
| 4. Typography | 3/4 | 5 distinct sizes in use — one more than ideal; weights are clean (2 only) |
| 5. Spacing | 3/4 | Mostly consistent scale; arbitrary min-w values in dialogs are minor deviations |
| 6. Experience Design | 2/4 | No loading state during "Добавить" confirm, no error handling if add_template fails |

**Overall: 18/24**

---

## Top 3 Priority Fixes

1. **No loading/disabled state during template extraction** — user can click "Добавить" twice or receive no feedback if extraction takes several seconds on a large PDF — disable the button and set `status_label` to "Читаю документ..." before the await, then re-enable on completion (`templates.py:177-212`)

2. **No error handling in _confirm() for extract and add_template** — if `extract_text` throws (corrupted PDF, unsupported encoding), the dialog silently hangs with no user feedback — wrap the two `run.io_bound` calls in try/except and call `ui.notify("Не удалось прочитать документ", type="negative")` on failure (`templates.py:196-213`)

3. **Empty state secondary label is generic** — "Добавьте первый шаблон-эталон для ревью договоров" is fine as a hint but the primary label "Нет шаблонов" is a bare noun phrase; changing to "Шаблонов пока нет" softens the abruptness, and the CTA could point the user to the button above: add `ui.button("+ Добавить шаблон", ...).props(...)` directly in the empty state rather than requiring the user to look up (`templates.py:49-52`)

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

Strengths:
- All labels are in Russian — consistent with project preference
- Section headers are descriptive: "AI-провайдер", "Анонимизация", "Предупреждения", "Telegram-бот"
- Telegram status uses dot + natural phrase: "● Подключён" / "● Не подключён" — exactly per spec
- Dialog titles are action-specific: "Добавить шаблон", "Изменить шаблон", "Удалить шаблон?" — the question mark on delete is a good affordance

Issues:
- `settings.py:91` — the AI section description "Выберите модель для извлечения метаданных из документов." is technically correct but reads formally. Could be "Выберите AI-модель для анализа документов." (shorter)
- `templates.py:49` — "Нет шаблонов" as a standalone label is abrupt. NiceGUI renders it prominently; a verb form ("Шаблоны не добавлены") or softer phrasing ("Шаблонов пока нет") is more natural in Russian UI
- `templates.py:108,180` — validation notification "Введите название шаблона" appears twice (edit and add flows) — this is correct and consistent
- No generic English fallback strings found. No "Submit", "OK", "Cancel" — the file uses "Отмена", "Сохранить", "Удалить", "Добавить"

### Pillar 2: Visuals (3/4)

Strengths:
- macOS Preferences layout (w-48 left nav + flex-1 right panel) matches stated design intent from CONTEXT.md
- Active nav highlight via class swap (`text-slate-900 bg-white shadow-sm rounded-lg`) creates clear affordance without aggressive color
- Template cards have clear information hierarchy: name (font-semibold) > type (text-xs slate-500) > preview (text-xs slate-400 line-clamp-3) > date (text-xs slate-300) — each level is visually quieter
- Hover states on both nav buttons (`hover:bg-slate-50`) and cards (`hover:shadow-md hover:bg-slate-100`) with `transition-shadow transition-colors duration-150`

Issues:
- Template cards have no icon or visual anchor — in a 2-column grid, cards that differ only in text can look uniform and hard to scan. Even a document-type icon or color tag would aid orientation
- The settings nav label "Настройки" (`settings.py:39-41`) uses `text-xs font-semibold text-slate-400 uppercase tracking-wide` — this is standard macOS style but in NiceGUI/Quasar it may render too small depending on the base font. No visual screenshot to confirm actual rendering
- `templates.py:228-233` — the page header has `items-start justify-between` but the subtitle `mb-4` pushes spacing into the header row rather than below it — the "+" button may not vertically align with the title on some screen heights

### Pillar 3: Color (4/4)

No issues found.

- Zero hardcoded hex or rgb() values across both files
- Color palette is cohesive: slate-900 (primary text), slate-600/500/400/300 (secondary hierarchy), slate-50/100/200 (backgrounds/borders)
- Accent (Quasar `color=primary`) appears only on 3 action elements: "Изменить" card button, "Добавить"/"Сохранить" dialog confirm buttons — appropriate usage
- Destructive color (`color=negative`) appears only on "Удалить" — correct semantic usage
- Status dot correctly uses `text-green-600` / `text-red-500` — two semantic colors, not decorative
- Registry audit: shadcn not initialized — skipped

### Pillar 4: Typography (3/4)

Font sizes in use across both files:
- `text-2xl` — page title "Шаблоны" (1 use)
- `text-lg` — section headers (5 uses)
- `text-base` — subsection "Предупреждения" (1 use)
- `text-sm` — body copy and descriptions (7 uses)
- `text-xs` — metadata, card details, nav label (9 uses)

That is 5 distinct sizes. Abstract standard flags >4. The `text-base` at `settings.py:157` is the outlier — "Предупреждения" subsection header could use `text-sm font-semibold` since it sits below a `text-lg` section header and `text-base` creates an awkward intermediate step.

Font weights:
- `font-semibold` — titles and card names (5 uses)
- `font-medium` — section headers (4 uses)

Only 2 weights in use — clean and correct. No `font-bold` or `font-light` outliers.

### Pillar 5: Spacing (3/4)

Top spacing classes (occurrences):
- `mb-4` (6), `mt-2` (4), `p-6` (3), `mb-2` (3), `gap-2` (3), `p-8` (2), `p-3` (2)

The scale is Tailwind-standard throughout (steps of 1-2 base units). No arbitrary `[N]rem` values found.

Issues:
- `templates.py:90,127,162` — dialog cards use `min-w-[400px]` and `min-w-[360px]` (arbitrary pixel values). These are acceptable for dialog width constraints where Tailwind doesn't have a standard class, but they represent deviations from the pure utility scale. Consider `min-w-96` (384px) or `min-w-80` (320px) instead
- `templates.py:226` — page wrapper uses `p-8` but settings page also uses `p-8` for the right panel — consistent cross-page
- Settings nav uses `p-3 gap-1` for the column, `px-3 py-2` for buttons — the 1-unit gap between nav buttons is very tight; `gap-0.5` or `gap-1` works but `gap-2` would breathe better

### Pillar 6: Experience Design (2/4)

Positive:
- Empty state is present and handled in `_render_cards()` with both primary label and helper text (`templates.py:47-53`)
- Deletion has a confirmation dialog showing the template name — prevents accidental data loss (`templates.py:125-144`)
- Add flow: `status_label.set_text("Читаю документ...")` is set before the await (`templates.py:184`) — partial loading feedback
- Telegram check updates status dot live after the async call (`settings.py:215-219`)
- Settings save on blur, not on every keystroke — correct pattern for a settings form

Issues (significant):
- `templates.py:177-213` — `_confirm()` button is not disabled during the two `run.io_bound` awaits. User can click "Добавить" multiple times, triggering duplicate template insertions. The button should be disabled before the first await and re-enabled in a finally block
- `templates.py:196-213` — zero error handling around `extract_text` and `add_template`. If extraction fails (bad PDF, read error, DB error), the dialog freezes with "Читаю документ..." and no way to dismiss without cancelling. Minimum fix: wrap in try/except, call `ui.notify(...)` on failure and re-enable the button
- `settings.py:167` — `int(e.sender.value or 30)` silently resets to 30 if the field is cleared; no user feedback that the value was corrected. A `ui.notify("Значение сброшено до 30", type="info")` would be more transparent
- `settings.py` — no error feedback if `save_setting()` fails (e.g. disk full, permissions). The function silently swallows exceptions in `load_settings` but `save_setting` itself can raise. Low probability but zero resilience
- No disabled states on "Проверить подключение" during the async health check — double-clicks can queue multiple requests

---

## Files Audited

- `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/app/pages/settings.py` (223 lines)
- `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/app/pages/templates.py` (247 lines)
- `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/.planning/phases/11-settings-templates/11-CONTEXT.md`
- `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/.planning/phases/11-settings-templates/11-01-SUMMARY.md`
- `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/.planning/phases/11-settings-templates/11-02-SUMMARY.md`
- `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/.planning/phases/11-settings-templates/11-03-SUMMARY.md`
- `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/.planning/phases/11-settings-templates/11-01-PLAN.md`
- `/Users/danilakistenev/Downloads/Личное/ЮР тэг/yurteg/.planning/phases/11-settings-templates/11-02-PLAN.md`
