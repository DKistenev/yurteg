# Phase 13: Design Polish + Calendar - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Финальная полировка интерфейса: единая цветовая система, шрифт, анимации появления — по всем экранам. Плюс переключатель вида реестра Список/Календарь через FullCalendar.js.

</domain>

<decisions>
## Implementation Decisions

### Цветовая палитра
- **D-01:** Нейтральные — холодные slate/zinc (Tailwind `slate-*`). Лёгкий голубоватый подтон, как Linear/Notion
- **D-02:** Акцентный цвет — индиго (`indigo-600` / `#4f46e5`) для CTA-кнопок и активных элементов
- **D-03:** 60/30/10 правило: white 60% / slate-50 30% / indigo-600 10%
- **D-04:** Статусные цвета остаются семантическими: зелёный (active), жёлтый (expiring), красный (expired), серый (unknown)
- **D-05:** Все нейтральные — tinted: `slate-50`, `slate-100`, `slate-200` для фонов/границ; `slate-600`, `slate-700`, `slate-900` для текста

### Типографика
- **D-06:** Шрифт — IBM Plex Sans (Google Fonts). Хорошая кириллица, профессиональный для юридического продукта
- **D-07:** 2 веса: 400 (normal) для текста, 600 (semibold) для заголовков и CTA — продолжение Phase 12
- **D-08:** Modular scale: 12px (caption) / 14px (body) / 16px (large body) / 20px (heading) / 28px (display)
- **D-09:** Загрузка через `ui.add_head_html('<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&subset=cyrillic">')`

### Календарь
- **D-10:** FullCalendar.js интегрирован через `ui.add_head_html` (JS library) + `ui.html` (container)
- **D-11:** Месячный вид по умолчанию
- **D-12:** Два типа событий на одном календаре:
  - Даты окончания договоров — цвет indigo
  - Платежи — цвет slate-400 (серый, вторичный)
- **D-13:** Клик по событию → tooltip с краткой инфой: тип, контрагент, сумма + кнопка «Открыть»
- **D-14:** Кнопка «Открыть» в tooltip → `ui.navigate.to('/document/{id}')`
- **D-15:** Переключатель Список/Календарь — иконка-toggle справа от сегментированного фильтра в реестре
- **D-16:** Данные для календаря: `get_calendar_events()` из payment_service + `date_end` из contracts

### Анимации
- **D-17:** Staggered rows — строки реестра появляются каскадом (80ms задержка между строками) при первой загрузке страницы. CSS `@keyframes` + `animation-delay`
- **D-18:** Page transitions — плавный fade (200ms, ease-out) при переключении между страницами через sub_pages
- **D-19:** Hover effects — плавное подсвечивание строк таблицы и карточек шаблонов (150ms ease-out, `bg-slate-50` → `bg-slate-100`)
- **D-20:** Все анимации через CSS `transform` и `opacity` — не layout properties (per Impeccable motion ref)
- **D-21:** `ease-out-quart` для входных анимаций: `cubic-bezier(0.25, 1, 0.5, 1)`

### Применение по всем экранам
- **D-22:** Палитра и шрифт применяются глобально через `ui.add_head_html` в `app/main.py` — один раз, влияет на все страницы
- **D-23:** Заменить все `bg-gray-*` и `text-gray-*` на `slate-*` эквиваленты по всему `app/`
- **D-24:** Заменить `bg-gray-900` (accent) на `bg-indigo-600` по всему `app/`
- **D-25:** Статусные цвета (green, yellow, red) — НЕ заменять, оставить семантическими

### Claude's Discretion
- FullCalendar.js version и CDN URL
- Exact tooltip component (NiceGUI `ui.menu` vs custom HTML)
- CSS keyframe easing details
- Breakpoint для переключения compact calendar на мобильных (если будет)

</decisions>

<specifics>
## Specific Ideas

- Палитра должна быть cohesive — один подтон через весь интерфейс, не микс warm и cool
- IBM Plex Sans при 14px и 400 weight — проверить читаемость, может потребоваться 15px или line-height 1.6
- Календарь — НЕ должен выглядеть как Google Calendar. Минималистичный, утилитарный. Дни с событиями — точка, не полный блок
- Staggered reveal — тонкий эффект. Если юрист не заметит — значит правильно. Если бросается в глаза — слишком

</specifics>

<canonical_refs>
## Canonical References

### Design skills (MUST reference during implementation)
- `/colorize` — palette generation, tinted neutrals, accent placement
- `/typeset` — font pairing, scale, weight hierarchy
- `/animate` — motion timing, easing curves, reduced motion
- `/polish` — final pass before shipping
- `/audit` — a11y, responsive, quality check
- `frontend-design` — AI slop test (final check)

### Existing code to modify
- `app/main.py` — `_STATUS_CSS`, `_ACTIONS_CSS` (replace gray→slate, gray-900→indigo-600)
- `app/pages/registry.py` — all Tailwind classes
- `app/pages/document.py` — all Tailwind classes
- `app/pages/settings.py` — all Tailwind classes
- `app/pages/templates.py` — all Tailwind classes
- `app/components/header.py` — all Tailwind classes
- `app/components/registry_table.py` — status badge CSS
- `app/components/onboarding/splash.py` — splash styles
- `app/components/onboarding/tour.py` — tour styles

### Services for calendar
- `services/payment_service.py` — `get_calendar_events()` returns calendar event dicts
- `modules/database.py` — `get_all_results()` has `date_end` field

### Phase 12 UI-SPEC (baseline)
- `.planning/phases/12-onboarding/12-UI-SPEC.md` — spacing scale, typography weights (compatible with D-07/D-08)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_STATUS_CSS` in `main.py` — CSS classes for status badges (need color migration gray→slate)
- `STATUS_LABELS` in lifecycle_service — hex colors for statuses (keep as-is, semantic)
- `get_calendar_events()` — returns `[{"title", "start", "end", "color", "contract_id"}]` — ready for FullCalendar
- Phase 12 splash/tour already use `bg-gray-50`, `bg-gray-900` → need migration to slate/indigo

### Established Patterns
- `ui.add_head_html()` for global CSS — established in Phase 7
- `.classes()` for Tailwind on NiceGUI elements — used everywhere
- `run.io_bound()` for blocking calls

### Integration Points
- `app/main.py` — global CSS injection point (font, palette, animations)
- `app/pages/registry.py` — calendar toggle + staggered rows
- All `app/pages/*.py` and `app/components/*.py` — palette migration

</code_context>

<deferred>
## Deferred Ideas

- Dark mode toggle — v2+ (light theme is a conscious anti-AI-slop decision)
- Custom CSS theme file instead of inline — optimization, not MVP
- Reduced motion media query — a11y improvement, v2+
- Calendar week/day views — month view sufficient for MVP

</deferred>

---

*Phase: 13-design-polish-calendar*
*Context gathered: 2026-03-22*
