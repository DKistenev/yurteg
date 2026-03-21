# Feature Research

**Domain:** Registry-centric legal document UI — NiceGUI desktop app, v0.6 UI redesign
**Researched:** 2026-03-21
**Confidence:** HIGH — patterns verified across Linear, Notion, Finder, enterprise DMS docs, NiceGUI official docs, NN/g and Pencil & Paper UX research

---

## Context: What This Milestone Is Actually Solving

This is a UI architecture milestone, not a feature-addition milestone. All business logic already exists (v0.4–v0.5). The question is: **how do these features behave in the new "registry = app" architecture?**

Six UI pattern areas to research and define:
1. Master table with inline actions
2. Document detail card with tabs
3. Filter/search UX
4. Calendar view toggle
5. Settings page
6. Empty states and onboarding

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that are standard across modern document management UIs (Finder, Notion, Linear, Coda). Missing them makes the product feel unfinished by 2026 standards.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Clickable rows that open detail | Any modern list UI — Finder, Notion, Linear — rows navigate to detail. A row that does nothing on click feels broken | LOW | NiceGUI `ui.table` supports `on_row_click` via `@ui.table.on('rowClick')` event binding; navigate to detail route on click |
| Hover state on rows | Users need affordance that rows are interactive. Without hover highlight, clickability isn't discoverable | LOW | Apply Tailwind `hover:bg-gray-50` or equivalent on row; NiceGUI supports custom CSS per component |
| Persistent column widths | Users adjust column widths and expect them to survive navigation. Not saving = losing work | MEDIUM | Store per-column widths in SQLite user_prefs or JSON sidecar; restore on mount |
| Sort by column header click | Standard table affordance since the 90s. Every CLM, every spreadsheet | LOW | NiceGUI `ui.table` has built-in `sortBy` support via column definitions |
| Active filter chips visible above table | When filters are applied, show them as dismissible chips. Without this, users forget filters are on and trust the data incorrectly | LOW | Row of chip components above table; each chip has X to clear; "Сбросить всё" button appears when any filter active |
| Document count in header | "Показано 12 из 47 документов" — users need to know if they're seeing everything | LOW | Compute on the fly from filtered vs total queryset |
| Keyboard navigation (Cmd+K, arrows) | Power users expect keyboard-first. Finder, Linear, Notion all support it | MEDIUM | NiceGUI `ui.keyboard` component for global shortcuts; arrow key navigation within table requires custom JS |
| Loading state during processing | AI extraction takes 2–30 seconds. Without progress feedback, users think app crashed | LOW | NiceGUI `ui.spinner` + progress bar; already exists in Streamlit version, migrate logic |

### Differentiators (Competitive Advantage)

Patterns that go beyond what local Russian legal tools offer. Reference apps are Linear (issue tracker), Finder (file manager), and Apple Notes — all examples of "tool that feels fast and gets out of the way."

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Full-page transition to document detail | Linear pattern: clicking an issue replaces the list with a full detail view. Feels native, not modal-heavy. Modals feel like a web app; full-page feels like a desktop tool | MEDIUM | NiceGUI `ui.navigate.to('/document/{id}')` for route-based navigation; back button returns to registry at same scroll position |
| Scroll position memory on back navigation | When user goes into a document and comes back, they're returned to the same row in the list. Finder does this. Losing scroll position is a known frustration in web-style apps | MEDIUM | Store scroll offset in app state (not URL); restore on registry mount |
| Inline status badge with quick-change dropdown | User can change document status directly from the registry row without entering detail view. Linear does this with priority/status badges in list rows | MEDIUM | Single-field edit: clicking status badge opens a small dropdown in-place. Commit on select, no save button needed. NiceGUI `ui.select` can render inline |
| Context menu on right-click | Right-click on a row shows: Открыть, Изменить статус, Копировать путь, Удалить. Finder-style. Power users expect it | MEDIUM | NiceGUI does not natively support context menus on table rows; implement via `@ui.table.on('rowContextmenu')` + `ui.menu` positioned at cursor |
| Row density toggle (compact / normal) | Users with large registries (100+ docs) want compact density. Users reviewing individual documents want normal. Linear offers this | LOW | Toggle between row height classes; store preference in user_prefs |
| AI confidence indicator per row | For each row, small icon shows extraction confidence. Red = AI was unsure, needs review. Green = high confidence. Builds trust by being honest about uncertainty | LOW | Already computed by validator (L1–L5); surface as icon in a "Качество" column — can be hidden by default |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Expandable inline rows (accordion) | "Show more details without leaving the list" | Creates two reading modes (list + expanded) — users end up ignoring one. Linear moved away from inline expand toward full-page. Creates accessibility and keyboard nav complexity | Full-page detail view. Don't build both |
| Modals for document detail | "Quick and simple to implement" | Modals feel web-ish, not native. For a detail view with 5+ tabs, a modal becomes a cramped popup. Users can't resize it or use it side-by-side with the list | Full-page transition. Commit to it |
| Sidebar split-pane (master-detail) | "Like Mail.app or Finder with preview" | Requires both panels to be functional at the same time — doubles the layout surface area, doubles the bug surface, complicates keyboard focus management. Complex in NiceGUI without native split components | Full-page transition. Simpler, more focused |
| Infinite scroll | "Modern, no pagination" | With 500+ documents, infinite scroll breaks Cmd+F, makes it hard to reason about position, and causes performance issues in NiceGUI's virtual DOM. Also breaks "Показано X из Y" pattern | Pagination with page size selector (25 / 50 / 100). Familiar, predictable |
| Drag-and-drop column reorder | "Customization" | High implementation cost in NiceGUI tables; minimal user value for legal document registry where columns are stable | Column show/hide toggle is sufficient |
| Animated transitions between views | "Feels polished" | In Python/NiceGUI desktop app, JS-driven animations add latency. Users notice jank more than they enjoy smooth transitions | Instant navigation. Speed feels more professional than animation |
| Real-time auto-refresh of table | "Always up to date" | In single-user desktop app, nothing changes while the user is looking at the table. Auto-refresh creates unnecessary DB queries and can reset scroll position | Manual refresh button + refresh on focus return from processing |

---

## Pattern Specifications

### 1. Master Table with Inline Actions

**Pattern: hover-reveal actions + click-to-navigate**

The table is the primary workspace. Rows are the atoms. Clicking a row is the primary action.

**Row anatomy:**
```
[ ] Checkbox | Имя файла (bold) | Тип | Контрагент | Дата | Истекает | [Статус badge] | ... (3-dot menu on hover)
```

- Checkbox appears on row hover, not always — reduces visual noise
- Status badge is always visible — it's the most important status signal
- Three-dot menu appears on hover — contains: Открыть, Изменить статус, Скопировать путь, Удалить
- Entire row is clickable and navigates to detail
- Clicking the status badge opens inline dropdown without navigating (stops propagation)

**Hover state behavior (verified: Pencil & Paper pattern research):**
- Row background: `gray-50` on hover
- Checkbox fades in
- Three-dot menu fades in
- Status badge becomes interactive (cursor changes)
- No other visual changes — keep it calm

**Bulk actions (appear when rows selected):**
- Selection triggers a floating action bar below the table header: "Выбрано 3 → [Изменить статус ▾] [Удалить] [Сбросить]"
- Matches Linear's bulk action bar pattern

**Complexity: MEDIUM.** NiceGUI table supports `on_row_click` and selection. Hover CSS is achievable via Tailwind. Context menu requires custom JS event binding.

---

### 2. Document Detail Card with Tabs

**Pattern: full-page, tab-based, breadcrumb back**

When user clicks a row, the registry view is replaced by a full-page document detail. No modal. No split pane.

**Layout:**
```
← Реестр        [Имя документа]                          [Статус badge ▾]  [...]

[Обзор] [Ревью по шаблону] [Версии] [Платежи] [Заметки]

─────────────────────────────────────────────────────────
[tab content]
```

**Tab: Обзор**
- Two-column grid: left = extracted metadata (key-value pairs with confidence icons), right = file info + action buttons
- Action buttons: "Открыть файл", "Переобработать", "Скопировать путь"
- No editing of AI-extracted fields — they're output, not input (except status and custom notes)

**Tab: Ревью по шаблону**
- Existing AI review output, reformatted for new UI
- Show template diff as a structured list of findings
- Each finding has status: ОК / Отклонение / Требует внимания

**Tab: Версии**
- Chronological list of document versions
- Each version: date, source file, extraction confidence, diff summary
- "Текущая" badge on latest

**Tab: Платежи**
- Payment schedule table extracted by AI
- Columns: Дата, Сумма, Описание, Статус оплаты
- Simple, no editing in v0.6

**Tab: Заметки**
- Free-text textarea, user-written notes
- Auto-save on blur (no save button)
- Timestamp of last edit shown below

**Back navigation:**
- "← Реестр" breadcrumb at top left
- Returns to registry at same scroll position (store before navigating)
- Browser back button also works (NiceGUI router-based navigation)

**Complexity: MEDIUM.** Tab structure is straightforward in NiceGUI (`ui.tabs` + `ui.tab_panels`). Scroll position memory requires app state management. Full-page navigation with route requires NiceGUI `@ui.page` decorator per route.

---

### 3. Filter/Search UX for Legal Documents

**Pattern: search bar + filter chips + sidebar toggles**

Legal documents have predictable filter dimensions: type, status, counterparty, date range, confidence level.

**Layout:**
```
[🔍 Поиск по имени, контрагенту...] [+ Фильтры ▾]     [Дата ↕] [Тип ↕]

[Тип: Договор ×] [Статус: Истекает ×] [Сбросить всё]

[table rows...]
```

**Search:**
- Single search box, full-width above table
- Searches across: filename, counterparty, contract number, notes
- Debounced (300ms) before querying SQLite — avoids query-per-keystroke
- `Cmd+F` or `/` focuses search bar globally (via `ui.keyboard`)
- Results highlighted in rows (bold match text)

**Filters:**
- "Фильтры" button opens a small popover (not a sidebar panel — sidebar wastes horizontal space in a wide table)
- Popover contains: checkboxes for Тип, multi-select for Статус, date range picker for Истекает
- Applied filters render as dismissible chips above the table
- "Сбросить всё" clears all chips

**Filter dimensions for legal docs (from CLM research + domain knowledge):**
- Тип документа: Договор / Доп. соглашение / Акт / НДА / Другое
- Статус: Действует / Истекает / Истёк / Расторгнут / Черновик
- Истекает в диапазоне: date range picker
- Контрагент: text search within filter
- Уверенность AI: Высокая / Средняя / Низкая (maps to validator L1–L5)
- Клиент (мультиклиентский режим): dropdown of loaded client DBs

**Sorting:**
- Column headers are clickable for sort
- Active sort column shows ↑ or ↓ icon
- Default sort: Истекает ascending (most urgent first — matches user mental model)

**Complexity: LOW-MEDIUM.** SQLite LIKE queries for search; filter state is a dict of active conditions. NiceGUI `ui.input` + `ui.select` + `ui.date` for filter inputs. Chip components for active filter display.

---

### 4. Calendar View Toggle

**Pattern: segmented control toggle, same data, different layout**

The calendar view is not a separate page — it's an alternative rendering of the same filtered registry data. Useful for seeing expiry dates distributed across months.

**Toggle placement:**
```
[Таблица] [Календарь]  ← segmented control, top right of registry header
```
This placement is consistent with how Linear, Notion, and Asana implement view switching.

**Calendar view behavior:**
- Shows current month by default
- Each day shows document chips: "Договор с Ромашка ООО" (expiry date = that day)
- Color matches status badge: red = истёк, yellow = истекает, gray = normal
- Clicking a document chip in calendar navigates to same full-page detail view
- Month navigation: ← → arrows, "Сегодня" button
- Empty days show nothing (no placeholder text — it's a calendar, not a todo list)
- Filter state carries over: if "Статус: Истекает" is active, calendar only shows those docs

**What calendar does NOT do:**
- Does not show payment dates (too much data — clutters calendar)
- Does not allow drag-and-drop date editing (dates come from AI, not user input)
- Does not support week or day view (month is sufficient for contract expiry tracking)

**Implementation options for NiceGUI:**
- Option A: Use FullCalendar.js via `ui.html` + JS interop — full-featured, good docs, MIT license
- Option B: Build custom grid with NiceGUI layout components — more control, more work
- Recommendation: **FullCalendar.js via `ui.add_head_html`** — proven library, handles month navigation, event rendering, click handling. Pass data as JSON from Python to JS.

**Complexity: MEDIUM.** FullCalendar integration requires JS interop pattern. Filter state sync between views requires shared app state. NiceGUI `ui.add_head_html` supports loading external JS.

---

### 5. Settings Page

**Pattern: vertical nav + section groups, Linear/macOS System Preferences style**

Settings is a top-level tab (Настройки), not a modal or drawer. It's a separate page with its own internal navigation.

**Layout:**
```
[Документы] [Шаблоны] [Настройки]   ← top-level tabs

┌─────────────────┬────────────────────────────────────────┐
│ AI провайдер    │  [section content]                      │
│ Обработка       │                                          │
│ Уведомления     │                                          │
│ Telegram        │                                          │
│ Интерфейс       │                                          │
│ О программе     │                                          │
└─────────────────┴────────────────────────────────────────┘
```

Left nav selects section; right panel shows that section's settings.

**Section: AI провайдер**
- Radio group: Локальная модель (QWEN 1.5B) / GLM-4.7 (облако) / OpenRouter / Другой
- Per-provider: API key input (masked), model name, base URL
- "Проверить подключение" button with status indicator
- Warning when cloud provider selected: "Документы будут отправлены в облако. Убедитесь, что анонимизация включена"

**Section: Обработка**
- Toggle: Анонимизировать перед отправкой (disabled and forced ON when cloud provider)
- Prompt: порог уверенности (slider 0–100, default 70)
- Batch size (for multi-file processing)

**Section: Уведомления**
- Threshold: за сколько дней напоминать (input, default 30)
- Toggle: показывать напоминание при запуске

**Section: Telegram**
- Token input + /start инструкция
- "Протестировать бота" button

**Section: Интерфейс**
- Row density: Компактный / Стандартный
- Отображать по умолчанию: Таблица / Календарь
- Язык (locked to RU for now)

**Section: О программе**
- Version, license, GitHub link, "Проверить обновления"

**Design rules:**
- Changes save immediately on blur (no global Save button) — macOS System Preferences pattern
- Show saved confirmation with subtle checkmark animation
- Dangerous actions (Очистить базу данных) require confirmation dialog

**Complexity: LOW.** Mostly form components. NiceGUI `ui.input`, `ui.toggle`, `ui.slider`, `ui.radio`. Left nav is `ui.list` with `ui.item` clicks changing visible panel. State persistence writes to `config.json` or SQLite `user_prefs`.

---

### 6. Empty States and Onboarding

**Pattern: contextual empty states, not a wizard. Action-first, explanation-second.**

There are three distinct empty states in ЮрТэг. Each has different context and requires different treatment.

**Empty State 1: First Launch (no documents ever processed)**

This is the most important empty state. It's the first thing a new user sees.

Layout:
```
        [app icon / logo mark]

        Добро пожаловать в ЮрТэг

        Выберите папку с договорами — и мы автоматически
        создадим реестр с метаданными за несколько минут.

        [  Выбрать папку   ]    [  Добавить файлы  ]

        Поддерживаются PDF и DOCX. Данные остаются на вашем компьютере.
```

Key principles (from NN/g + Pencil & Paper research):
- Lead with action, not description. Button is the visual center.
- One sentence on privacy (addresses #1 adoption barrier from CustDev)
- No tutorial, no video, no checklist. Legal professionals distrust "product tours"
- Illustration: simple, monochrome, non-generic. Not stock art, not emoji art. Consider: outline of a contract stack or folder icon.

**Empty State 2: No Results After Filtering**

User has documents but current filter combination returns nothing.

Layout:
```
        [search/filter icon]

        Ничего не найдено

        Нет документов, соответствующих выбранным фильтрам.

        [  Сбросить фильтры  ]
```

Rules:
- Always offer the action to escape the empty state (clear filters)
- Don't explain what filters are — user just applied them, they know
- Don't show suggestions — legal docs don't benefit from "Did you mean?"

**Empty State 3: Empty Tab in Document Detail**

When a tab in the detail view has no data (e.g., no versions yet, no payments extracted).

Layout (inline, no full-page):
```
        Версий пока нет
        Версия появится после повторной обработки документа.
```

Rules:
- No icon, no button — just two lines of text, subdued color
- Explain why it's empty and what would populate it
- Don't offer navigation away — user is mid-task

**Onboarding Philosophy:**
- No wizard. No step-by-step. No "complete your profile" progress bar.
- The app teaches through use. After first processing, the registry appears — that IS the onboarding.
- The only guided moment: first-launch empty state with clear CTA.
- If AI extraction fails or confidence is low, surface the explanation inline in the registry row — not in a separate "errors" section.

**Complexity: LOW.** Three conditional renders based on data state. NiceGUI conditional rendering via Python `if/else`. Illustration as SVG inline component.

---

## Feature Dependencies

```
[Master Table]
    └──requires──> [NiceGUI ui.table with on_row_click]
    └──requires──> [Route-based navigation (ui.navigate.to)]
    └──enhances──> [Filter/Search] (filter state drives table query)

[Document Detail]
    └──requires──> [Route per document (/document/{id})]
    └──requires──> [Scroll position stored in app state]
    └──requires──> [Tab component (ui.tabs)]
    └──enhances──> [Inline status edit] (status change reflected in registry on back)

[Calendar View]
    └──requires──> [Filter state shared between views]
    └──requires──> [FullCalendar.js or custom grid]
    └──requires──> [Same detail navigation as table rows]
    └──conflicts──> [Building custom calendar from scratch] (use FullCalendar.js)

[Filter/Search]
    └──requires──> [SQLite full-text search or LIKE queries]
    └──enhances──> [Calendar View] (filter carries over)

[Settings]
    └──requires──> [config.py or user_prefs in SQLite]
    └──enhances──> [All features] (provider, threshold, density affect everything)

[Empty States]
    └──requires──> [Data state detection (0 docs, 0 results, 0 tab data)]
    └──enhances──> [First Launch] (guides to folder selection CTA)
```

---

## MVP Definition (v0.6 Scope)

### Build in v0.6

These constitute the "registry = app" architecture. Without them, the milestone is incomplete.

- [ ] Master table: clickable rows, hover state, inline status change, column sort — *the registry IS the product*
- [ ] Full-page document detail with 5 tabs — *currently done as separate Streamlit pages; unify under one route*
- [ ] Filter chips + search bar — *existing filters, redesigned as persistent chip UI*
- [ ] Calendar view toggle (month view) — *differentiator; payment calendar already in app, needs UI surface*
- [ ] Settings page (3-section structure: AI, Уведомления, Telegram) — *provider switching already works; needs proper settings UI*
- [ ] Empty states (all 3 types) — *critical for first-launch experience at hackathon demo*

### Defer to v0.7

- [ ] Keyboard navigation within table (arrow keys) — *nice to have, not blocking*
- [ ] Persistent column widths — *cosmetic polish, not blocking*
- [ ] Row density toggle — *can be added post-launch*
- [ ] Context menu (right-click) — *three-dot menu covers same actions*

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Clickable rows + full-page detail | HIGH — core navigation pattern | LOW | P1 |
| Filter chips + search | HIGH — top CustDev pain (поиск документов 9/9) | LOW | P1 |
| Inline status badge | HIGH — avoids opening doc just to change status | MEDIUM | P1 |
| Empty state: first launch | HIGH — first impression, hackathon demo | LOW | P1 |
| Settings page | MEDIUM — needed for provider + notification config | LOW | P1 |
| Calendar toggle | MEDIUM — differentiator, payment tracking UX | MEDIUM | P2 |
| Hover reveal + context menu | MEDIUM — power user UX | MEDIUM | P2 |
| Scroll position memory | LOW — polish, not core | MEDIUM | P3 |
| Row density toggle | LOW — nice to have | LOW | P3 |
| AI confidence column | LOW — v0.6 has enough to show | LOW | P3 |

---

## Reference App Analysis

| Pattern | Linear | Notion | Finder | Apple Notes | ЮрТэг Approach |
|---------|--------|--------|--------|-------------|----------------|
| Row click | Full-page issue detail | Full-page page detail | Full-page in new pane OR preview | Full-page note detail | Full-page document detail |
| List + detail | Full-page replace | Full-page replace | Split pane optional | Split pane optional | Full-page replace (simpler for NiceGUI) |
| Status change | Inline badge click in list | Inline property edit | N/A | N/A | Inline badge dropdown in registry row |
| Filter display | Active filter chips in toolbar | Filter button reveals panel | Spotlight search only | Search only | Chips above table + popover for adding |
| View switching | List / Board / Timeline / Calendar | List / Board / Calendar / Gallery | List / Grid / Column | N/A | Table / Calendar (two views) |
| Empty state | Action-first CTA with illustration | "Click to start" inline | OS-level (nothing) | "No notes" + compose | Action-first CTA, single button, privacy note |
| Settings | Full-page Preferences window | Left-nav + sections | System Preferences style | Minimal | Left-nav + sections (Linear/macOS style) |
| Search | Cmd+K command palette + inline search | Cmd+P command palette | Spotlight | Cmd+F | Single search bar + Cmd+F focus shortcut |

**Key insight from reference app analysis:** Linear and Notion both chose "full-page replace" over "split pane" for their primary workflow. Split pane is an affordance that sounds good but creates focus problems — users don't know which pane has focus. For a tool used by lawyers who need to concentrate, full-page is better. Finder and Mail offer split pane but they're OS-level apps with richer keyboard focus handling than a Python desktop app can achieve.

---

## Sources

- [NiceGUI Table Documentation](https://nicegui.io/documentation/table) — HIGH confidence (official docs)
- [NiceGUI Keyboard Documentation](https://nicegui.io/documentation/keyboard) — HIGH confidence (official docs)
- [NiceGUI Discussion: Row click to navigate](https://github.com/zauberzeug/nicegui/discussions/802) — HIGH confidence (official GitHub)
- [Data Table UX Patterns — Pencil & Paper](https://www.pencilandpaper.io/articles/ux-pattern-analysis-enterprise-data-tables) — HIGH confidence (verified UX research)
- [Enterprise Filtering UX — Pencil & Paper](https://www.pencilandpaper.io/articles/ux-pattern-analysis-enterprise-filtering) — HIGH confidence (verified UX research)
- [Empty States in Complex Apps — Nielsen Norman Group](https://www.nngroup.com/articles/empty-state-interface-design/) — HIGH confidence (NN/g authoritative)
- [Linear UI Redesign — Linear Blog](https://linear.app/now/how-we-redesigned-the-linear-ui) — HIGH confidence (primary source)
- [Calendar View UX Pattern — uxpatterns.dev](https://uxpatterns.dev/patterns/data-display/calendar) — MEDIUM confidence (secondary source, consistent with other findings)
- [Tabs UX Best Practices — Eleken](https://www.eleken.co/blog-posts/tabs-ux) — MEDIUM confidence (design agency, consistent with NN/g)
- [Settings UX — Setproduct](https://www.setproduct.com/blog/settings-ui-design) — MEDIUM confidence (design reference, consistent with macOS HIG)
- CustDev findings (9 interviews, 3 real + 6 synthetic) — HIGH confidence for pain points (поиск документов 9/9, хаос нейминга 6/9)

---

*Feature research for: ЮрТэг v0.6 — registry-centric UI, NiceGUI migration*
*Researched: 2026-03-21*
