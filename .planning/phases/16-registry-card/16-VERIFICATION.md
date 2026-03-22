---
phase: 16-registry-card
verified: 2026-03-22T20:30:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
---

# Phase 16: Registry + Card Verification Report

**Phase Goal:** Два главных рабочих экрана приложения обретают визуальный характер — реестр с данными и карточка документа
**Verified:** 2026-03-22T20:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Stats bar над таблицей со светлым фоном и тремя числами: Всего / Истекают / Требуют внимания | VERIFIED | `ui.row().classes(STATS_BAR)` в registry.py:123; три label-элемента с `STAT_NUMBER`; `_refresh_stats()` вызывается в `_init()` |
| 2 | Заголовок «Реестр» с визуальным весом (text-2xl font-semibold) | VERIFIED | registry.py:144 — `ui.label("Реестр").classes("text-2xl font-semibold text-slate-900 mr-auto")` |
| 3 | Фильтр-бар с filled active state (SEG_ACTIVE) | VERIFIED | registry.py:172 — `btn.classes(SEG_ACTIVE if key == "all" else SEG_INACTIVE)`; три сегмента в `bg-slate-100 p-1 rounded-lg` враппере |
| 4 | Статусные бейджи — цветные filled pills (green/amber/red) | VERIFIED | design-system.css:218-225 — 8 классов `status-*` с `display:inline-flex; border-radius:9999px`; STATUS_CELL_RENDERER возвращает `<span class="${cls}">` |
| 5 | AG Grid тематически оформлен через --ag-* CSS variables в .ag-theme-quartz | VERIFIED | design-system.css:199-212 — блок `.ag-theme-quartz` с 10 переменными `--ag-*`, маппинг из `--yt-*` токенов |
| 6 | Анимация строк не перезапускается при переключении сегмента (Pitfall 7 guard) | VERIFIED | registry.py:334-337 — `ui.run_javascript("document.querySelectorAll('.ag-row').forEach(r => r.style.animation = 'none')")` перед `load_table_data` |
| 7 | При пустой БД страница показывает rich empty state с CTA и тремя карточками | VERIFIED | registry.py:42-110 — `_render_empty_state` содержит `CAPABILITIES` список с тремя карточками; кнопка «Выбрать папку» с `BTN_ACCENT_FILLED` |
| 8 | Карточка документа содержит breadcrumbs «Реестр → {тип}» с кликабельным «Реестр» | VERIFIED | document.py:156-163 — `ui.label("Реестр", on_click=lambda: ui.navigate.to("/")).classes(BREADCRUMB_LINK)` + стрелка + тип документа |
| 9 | Секции карточки: uppercase dividers, amber AI-ревью, timeline версий | VERIFIED | document.py — 6 использований `SECTION_DIVIDER_HEADER`; `AI_REVIEW_BLOCK`+`AI_REVIEW_BORDER_STYLE` на строке 292; `VERSION_DOT` на строке 382 |

**Score:** 9/9 truths verified

---

### Required Artifacts

| Artifact | Provides | Level 1: Exists | Level 2: Substantive | Level 3: Wired | Status |
|----------|----------|----------------|---------------------|----------------|--------|
| `app/pages/registry.py` | stats bar, heading, filter bar, empty state | Yes | Yes (509 строк, `_refresh_stats`, `_render_empty_state`, `CAPABILITIES`) | Yes (импортируется через main.py, `_init()` вызывает все компоненты) | VERIFIED |
| `app/components/registry_table.py` | STATUS_CELL_RENDERER с filled pills, `_fetch_counts` | Yes | Yes (`_fetch_counts` с реальными SQL-запросами; `STATUS_CELL_RENDERER` со `status-*` классами) | Yes (`_fetch_counts` импортируется в registry.py:33; `STATUS_CELL_RENDERER` используется в `COLUMN_DEFS`) | VERIFIED |
| `app/static/design-system.css` | AG Grid theming, status-pill CSS | Yes | Yes (`.ag-theme-quartz` блок + 8 `.status-*` правил) | Yes (CSS загружается глобально через main.py) | VERIFIED |
| `app/styles.py` | STATS_BAR, STATS_ITEM, BREADCRUMB_*, SECTION_DIVIDER_HEADER, AI_REVIEW_BLOCK, META_KEY, VERSION_DOT | Yes | Yes (все 11 констант Phase 16 присутствуют) | Yes (импортируются в registry.py и document.py) | VERIFIED |
| `app/pages/document.py` | breadcrumbs, section dividers, amber AI-ревью, timeline | Yes | Yes (breadcrumbs на строке 154, 6 SECTION_DIVIDER_HEADER, AI_REVIEW_BLOCK на 292, VERSION_DOT на 382) | Yes (все async callbacks сохранены; импортируется через main.py) | VERIFIED |

---

### Key Link Verification

| From | To | Via | Status | Detail |
|------|----|-----|--------|--------|
| `registry.py (_refresh_stats)` | `registry_table.py (_fetch_counts)` | `run.io_bound(_fetch_counts, ...)` в `_refresh_stats()` | WIRED | registry.py:206; `_fetch_counts` в импорте строка 33 |
| `design-system.css (.ag-theme-quartz)` | `registry_table.py (render_registry_table)` | CSS variables подхватываются AG Grid автоматически | WIRED | `.ag-theme-quartz` блок в CSS + `ui.aggrid` создаёт элемент с этим классом |
| `registry.py (_render_empty_state)` | вызов из `_init()` | прямой вызов при 0 строках и отсутствии фильтров | WIRED | registry.py:476 — `_render_empty_state(grid_container, state)` |
| `document.py (breadcrumbs «Реестр»)` | `ui.navigate.to('/')` | `on_click=lambda: ui.navigate.to("/")` на label | WIRED | document.py:158 — кликабельный Реестр |
| `document.py (AI-ревью блок)` | `services/review_service.py` | `_run_review()` → `match_template` + `review_against_template` | WIRED | document.py:295-361 — полный async callback без изменений |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `registry.py` stats bar | `counts["total"]`, `counts["expiring"]`, `counts["attention"]` | `_fetch_counts()` → три SQL `SELECT COUNT(*)` из таблицы `contracts` | Yes — реальные DB-запросы | FLOWING |
| `registry_table.py` grid | `rowData` | `_fetch_rows()` → `SELECT ... FROM contracts WHERE status = 'done'` | Yes — полный SQL с `get_computed_status_sql` | FLOWING |
| `document.py` metadata | `contract` dict | `db.get_contract_by_id(int(doc_id))` через `run.io_bound` | Yes — DB lookup по ID | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Python импорты без ошибок | `python3 -c "import app.pages.registry; import app.components.registry_table; import app.styles; import app.pages.document; print('ALL IMPORTS OK')"` | ALL IMPORTS OK | PASS |
| `_fetch_counts` экспортируется | `python3 -c "from app.components.registry_table import _fetch_counts; print('OK')"` | OK | PASS |
| `.ag-theme-quartz` в CSS | `grep -c "\.ag-theme-quartz" app/static/design-system.css` | 3 (определение + 2 комментария) | PASS |
| 8 filled pill классов | `grep -c "display:inline-flex" app/static/design-system.css` | 8 | PASS |
| Pitfall 7 guard присутствует | `grep "animation.*none" app/pages/registry.py` | найдена строка с `r.style.animation = 'none'` | PASS |
| 6 секций с divider в document.py | `grep -c "SECTION_DIVIDER_HEADER" app/pages/document.py` | 6 | PASS |
| `ui.expansion` удалён из document.py | `grep "ui.expansion" app/pages/document.py` | 0 совпадений | PASS |
| Все git-коммиты существуют | `git log --oneline` | f56994d, d15180f, fdca665, 39bfd44, c8787fc — все найдены | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| REGI-01 | 16-01 | Stats bar над реестром (документы · истекают · требуют внимания) | SATISFIED | `_refresh_stats()` + три live label в `STATS_BAR` враппере |
| REGI-02 | 16-01 | Filled semantic status badges (green/amber/red) вместо text-only | SATISFIED | 8 `.status-*` CSS правил с `display:inline-flex; border-radius:9999px` |
| REGI-03 | 16-01 | AG Grid theming через --ag-* CSS variables с .ag-theme-quartz scope | SATISFIED | `.ag-theme-quartz` блок с 10 `--ag-*` переменными в design-system.css |
| REGI-04 | 16-02 | Rich empty state — мощный CTA с визуальным якорем и карточками возможностей | SATISFIED | `_render_empty_state` с `CAPABILITIES` (3 карточки) + `BTN_ACCENT_FILLED` CTA |
| REGI-05 | 16-01 | Заголовок «Документы» с визуальным весом | SATISFIED | `text-2xl font-semibold text-slate-900` на «Реестр» label |
| REGI-06 | 16-01 | Фильтр-бар с визуальным весом — segment buttons с filled active state | SATISFIED | `SEG_ACTIVE` (bg-indigo-600) для активного сегмента, `SEG_INACTIVE` для остальных |
| CARD-01 | 16-03 | Breadcrumbs навигация | SATISFIED | «Реестр» → {тип документа} с `on_click → ui.navigate.to("/")` |
| CARD-02 | 16-03 | Структурированные секции с uppercase заголовками и 1px разделителями | SATISFIED | 6 секций с `SECTION_DIVIDER_HEADER` (border-b border-slate-200) |
| CARD-03 | 16-03 | Визуально различимые блоки: compact key-value метаданные, amber AI-ревью, timeline версий | SATISFIED | `_render_metadata` без card wrapper; `AI_REVIEW_BLOCK+AI_REVIEW_BORDER_STYLE` (4px amber); `VERSION_DOT+VERSION_LINE` timeline |

**Orphaned requirements check:** REQUIREMENTS.md содержит ровно 9 IDs (REGI-01..06, CARD-01..03), все заявлены в планах 16-01, 16-02, 16-03. Незаявленных (orphaned) нет.

---

### Anti-Patterns Found

Сканирование файлов, изменённых в фазе: `app/pages/registry.py`, `app/components/registry_table.py`, `app/static/design-system.css`, `app/styles.py`, `app/pages/document.py`

| File | Pattern | Assessment | Severity |
|------|---------|------------|----------|
| `registry.py:124` | `total_num = ui.label("—")` | Начальное значение "—" — инициализатор, не stub. `_refresh_stats()` перезаписывает при `_init()`. | Info (не stub) |
| `registry_table.py:185` | `return {"total": 0, "expiring": 0, "attention": 0}` | Fallback в `except Exception` блоке — корректная обработка ошибок, не stub. | Info (не stub) |

Блокирующих anti-patterns не найдено. TODO/FIXME/placeholder строк в изменённых файлах нет.

---

### Human Verification Required

#### 1. Визуальный вид stats bar

**Test:** Запустить приложение с непустой БД, открыть экран реестра
**Expected:** Над таблицей виден светлый бар с тремя числами — общий count, истекающие (amber), требуют внимания (red); числа обновляются после загрузки
**Why human:** Не тестируется без запущенного сервера; визуальное расположение и цвета требуют проверки глазом

#### 2. Filled pills в AG Grid ячейках

**Test:** Реестр с документами различных статусов (active, expiring, expired)
**Expected:** Статусные бейджи отображаются как цветные rounded pills (не текст), цвета: зелёный/янтарный/красный
**Why human:** AG Grid cell renderer выполняется в браузере; programmatic проверка не возможна без headless browser

#### 3. Breadcrumbs в карточке

**Test:** Перейти на страницу любого документа `/document/{id}`
**Expected:** В верхней части видна строка «Реестр → {тип документа}», клик на «Реестр» возвращает на главную страницу
**Why human:** Визуальное положение и интерактивность навигации требуют проверки в браузере

#### 4. Amber left-border у AI-ревью блока

**Test:** На карточке документа найти секцию «Проверка по шаблону»
**Expected:** Блок имеет заметную 4px янтарную левую полосу, фон слегка желтоватый (#fffbeb)
**Why human:** Inline CSS через `.style()` требует браузерной проверки

---

### Gaps Summary

Критических пробелов нет. Все 9 must-haves из трёх планов верифицированы:

- Plan 01 (REGI-01, 02, 03, 05, 06): AG Grid theming, filled pills, stats bar, heading, filter bar — все реализованы и связаны
- Plan 02 (REGI-04): Rich empty state с CTA и тремя карточками — реализован inline, без регрессий в `_on_pick_folder` callback
- Plan 03 (CARD-01, 02, 03): Breadcrumbs, section dividers, amber AI-ревью, timeline версий — реализованы; `ui.expansion` удалены (0 вхождений); все async callbacks сохранены

---

_Verified: 2026-03-22T20:30:00Z_
_Verifier: Claude (gsd-verifier)_
