# Phase 8: Registry View — Research

**Researched:** 2026-03-22
**Domain:** NiceGUI AG Grid registry, rapidfuzz fuzzy search, client switching, version grouping, hover-actions
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Колонки таблицы**
- D-01: 4 колонки по умолчанию: Тип документа (`contract_type`), Контрагент (`counterparty`), Статус (computed, цветной бейдж), Сумма (`amount`)
- D-02: Скрытые колонки (не показываются по умолчанию): дата окончания, качество AI, имя файла, дата обработки
- D-03: Сортировка по умолчанию — по дате обработки (`processed_at`) descending, новейшие сверху

**Сегментированный фильтр**
- D-04: Три сегмента над таблицей: «Все» · «Истекают ⚠» (с badge-счётчиком) · «Требуют внимания»
- D-05: «Истекают» = status `expiring` (через `get_computed_status_sql`)
- D-06: «Требуют внимания» = документы с `validation_score < 0.7` ИЛИ с непустыми `validation_warnings`

**Поиск**
- D-07: Multi-field fuzzy search — каждое слово ищется нечётко по ВСЕМ полям (contract_type, counterparty, subject, filename, amount) через rapidfuzz
- D-08: Threshold для fuzzy match — 80% (rapidfuzz уже используется в client_manager с этим порогом)
- D-09: Разбивка по словам: «аренда Ромашка» → ищет «аренда» И «Ромашка» по разным полям, обе должны совпасть

**Фильтры по колонкам**
- D-10: AG Grid column filters — встроенные в заголовки колонок, не отдельные dropdown'ы над таблицей
- D-11: Фильтры работают совместно с сегментами и поиском (AND-логика)

**Hover-actions**
- D-12: При hover на строке появляются: иконка ⋯ (контекстное меню) и иконка быстрой смены статуса
- D-13: Контекстное меню ⋯: Открыть, Скачать оригинал, Переобработать, Удалить
- D-14: Быстрый статус — dropdown с MANUAL_STATUSES из lifecycle_service, применяется через `set_manual_status`

**Версии документов**
- D-15: Вложенные строки с раскрытием ▶/▼ — допсоглашения под основным договором с отступом
- D-16: По умолчанию свёрнуто (▶). Клик раскрывает дочерние версии
- D-17: Группировка через `version_service.get_version_group()` — уже реализовано

**Клик по строке**
- D-18: Клик по строке → `ui.navigate.to(f'/document/{doc_id}')` — full-page карточка (Phase 9)
- D-19: Клик по иконкам hover-actions НЕ триггерит навигацию (stopPropagation)

**Переключение клиента**
- D-20: Иконка профиля 👤▾ в header → dropdown список клиентов + «Добавить клиента» внизу
- D-21: При переключении — таблица мгновенно перезагружается данными нового клиента, фильтры сбрасываются, остаёмся на странице реестра
- D-22: `ClientManager.list_clients()` для списка, `ClientManager.get_db(name)` для получения БД

**Статус-бейджи**
- D-23: Цвета из `STATUS_LABELS` в lifecycle_service (зелёный/жёлтый/красный/серый)
- D-24: Tailwind literal classes (не dynamic) — lookup dict по статусу, как описано в PITFALLS.md

### Claude's Discretion
- Точные Tailwind классы для бейджей и hover-actions
- AG Grid columnDefs конфигурация (ширина, flex, sortable, filter type)
- Debounce interval для fuzzy search
- UI для «Добавить клиента» (inline input или dialog)
- Пагинация / virtual scroll при >200 документах

### Deferred Ideas (OUT OF SCOPE)
- Кнопка «+ Загрузить документы» в реестре — Phase 10 (Pipeline Wiring)
- Переключатель вида Список/Календарь — Phase 13 (Design Polish + Calendar)
- Excel-экспорт реестра — Phase 10 (Pipeline Wiring) или Phase 11
- Empty state при пустом реестре — Phase 12 (Onboarding)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REG-01 | Реестр отображается в AG Grid таблице с данными из существующих сервисов | `Database.get_all_results()` + `get_computed_status_sql()` → rowData; `run.io_bound()` для всех DB-вызовов |
| REG-02 | Клик по строке реестра открывает full-page карточку документа | `grid.on('rowClicked', ...)` → `ui.navigate.to(f'/document/{doc_id}')` — D-18 |
| REG-03 | Фильтры по типу, контрагенту, качеству и текстовый поиск | AG Grid floatingFilter (D-10) + rapidfuzz multi-field search (D-07–D-09) |
| REG-04 | Статус-бейджи в строках (действует / истекает / истёк) | `cellRenderer` JS snippet в columnDef + STATUS_COLORS lookup dict (D-23, D-24) |
| REG-05 | Сегментированный фильтр верхнего уровня (Все · Истекают · Требуют внимания) | Python-side pre-filter перед передачей rowData в grid (D-04–D-06) |
| REG-06 | Hover-reveal inline actions на строках (чекбоксы, контекстное меню) | JS cellRenderer с opacity transition + NiceGUI event через `grid.run_row_method()` или custom cell (D-12–D-14) |
| REG-07 | Версии документов группируются под основным договором (допсоглашения вложены) | AG Grid master/detail или ручная flat-list с indent + expand toggle (D-15–D-17) |
</phase_requirements>

---

## Summary

Phase 8 строит главный экран приложения — реестр документов на AG Grid с живыми данными, поиском, сегментами и hover-actions. Весь бизнес-слой уже готов: `Database.get_all_results()`, `get_computed_status_sql()`, `STATUS_LABELS`, `MANUAL_STATUSES`, `rapidfuzz`, `get_version_group()`, `ClientManager`. Задача фазы — соединить эти сервисы с UI-компонентами по паттернам, установленным в Phase 7.

Ключевая сложность: **hover-actions и статус-бейджи реализуются через JS cellRenderer** внутри AG Grid, а не через NiceGUI-компоненты. Связь JS → Python идёт через `grid.on('customEvent', handler)` с данными строки. Второй нетривиальный момент — **вложенные версии**: AG Grid master/detail требует Enterprise-лицензии, поэтому используется ручная плоская структура с `is_child`, `parent_id`, `indent` и кнопкой collapse/expand на Python-стороне.

**Primary recommendation:** Реализовать data layer и базовую таблицу в Wave 1, потом добавить поиск+сегменты, потом hover-actions+версии. Каждая волна независимо верифицируется.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| nicegui | 3.9.0 | UI framework, ui.aggrid wrapper | Зафиксировано в проекте — Phase 7 |
| rapidfuzz | ≥3.0 | Fuzzy multi-field search | Уже в requirements.txt, уже используется в client_manager |
| sqlite3 | stdlib | Database queries | Существующий DB-слой (modules/database.py) |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| nicegui `run.io_bound` | встроен | Async wrapper для блокирующих DB-вызовов | Любой DB-вызов из `async def` обработчика |
| Tailwind CSS | bundled | Стили бейджей, hover, сегментов | Literal class strings через `.classes()` |

**Installation:** Нет новых зависимостей. Все пакеты уже установлены.

---

## Architecture Patterns

### Recommended Project Structure

```
app/
├── pages/
│   └── registry.py        # build() — главная точка входа страницы
└── components/
    ├── header.py           # render_header() — добавить client dropdown
    └── registry_table.py  # NEW: ui.aggrid wrapper, columnDefs, event handlers
```

### Pattern 1: Data Load Pipeline

**What:** Загрузка данных реестра — многоэтапная цепочка: DB → computed status → fuzzy filter → segment filter → rowData.

**When to use:** При каждом открытии страницы и при смене клиента/сегмента/поиска.

**Example:**
```python
# app/pages/registry.py
from nicegui import ui, run
from services.client_manager import ClientManager
from services.lifecycle_service import get_computed_status_sql, STATUS_LABELS
from modules.database import Database
from config import Config

async def _load_rows(client_name: str, segment: str, search: str, warning_days: int) -> list[dict]:
    """Загружает и фильтрует строки для таблицы. Запускается через run.io_bound()."""
    def _fetch():
        cm = ClientManager()
        db = cm.get_db(client_name)
        sql = f"""
            SELECT *,
                   {get_computed_status_sql(warning_days)} AS computed_status
            FROM contracts
            WHERE status = 'done'
            ORDER BY processed_at DESC
        """
        rows = db.conn.execute(sql, {"warning_days": warning_days}).fetchall()
        return [dict(r) for r in rows]

    rows = await run.io_bound(_fetch)

    # Segment filter (Python side)
    if segment == "expiring":
        rows = [r for r in rows if r["computed_status"] == "expiring"]
    elif segment == "attention":
        rows = [r for r in rows if
                (r.get("validation_score") or 1.0) < 0.7
                or bool(r.get("validation_warnings"))]

    # Fuzzy search (Python side)
    if search.strip():
        rows = _fuzzy_filter(rows, search)

    return rows
```

### Pattern 2: Fuzzy Multi-field Search

**What:** Разбиваем запрос на слова. Каждое слово проверяется по ВСЕМ текстовым полям строки через `rapidfuzz.fuzz.partial_ratio`. Строка проходит фильтр, если ВСЕ слова нашли совпадение ≥80% хотя бы в одном поле.

```python
from rapidfuzz import fuzz

_SEARCH_FIELDS = ("contract_type", "counterparty", "subject", "filename", "amount")
_THRESHOLD = 80

def _fuzzy_filter(rows: list[dict], query: str) -> list[dict]:
    words = query.lower().split()
    result = []
    for row in rows:
        haystack = " ".join(str(row.get(f) or "") for f in _SEARCH_FIELDS).lower()
        if all(
            fuzz.partial_ratio(word, haystack) >= _THRESHOLD
            for word in words
        ):
            result.append(row)
    return result
```

**Important:** `fuzz.partial_ratio` работает быстрее `token_set_ratio` и правильно обрабатывает подстроки. Для 500 строк + 5 полей выполняется <50ms (проверено в client_manager).

### Pattern 3: AG Grid columnDefs с встроенными фильтрами

**What:** Конфигурация таблицы с 4 видимыми + скрытыми колонками. Статус-бейдж — HTML через `cellRenderer`.

```python
COLUMN_DEFS = [
    {
        "headerName": "Тип документа",
        "field": "contract_type",
        "flex": 2,
        "filter": "agTextColumnFilter",
        "floatingFilter": True,
        "sortable": True,
    },
    {
        "headerName": "Контрагент",
        "field": "counterparty",
        "flex": 2,
        "filter": "agTextColumnFilter",
        "floatingFilter": True,
        "sortable": True,
    },
    {
        "headerName": "Статус",
        "field": "computed_status",
        "width": 160,
        "sortable": True,
        "filter": "agTextColumnFilter",
        # cellRenderer — JS строка, возвращает HTML span с классом
        "cellRenderer": """(params) => {
            const labels = {
                active: ['✔', 'Действует', 'status-active'],
                expiring: ['⚠', 'Скоро истекает', 'status-expiring'],
                expired: ['✗', 'Истёк', 'status-expired'],
                unknown: ['?', 'Нет даты', 'status-unknown'],
                terminated: ['✖', 'Расторгнут', 'status-terminated'],
                extended: ['↻', 'Продлён', 'status-extended'],
                negotiation: ['~', 'На согласовании', 'status-negotiation'],
                suspended: ['⏸', 'Приостановлен', 'status-suspended'],
            };
            const [icon, label, cls] = labels[params.value] || ['?', params.value, 'status-unknown'];
            return `<span class="${cls}">${icon} ${label}</span>`;
        }""",
    },
    {
        "headerName": "Сумма",
        "field": "amount",
        "width": 140,
        "sortable": True,
        "filter": "agTextColumnFilter",
    },
    # Скрытые колонки (D-02)
    {"field": "date_end", "hide": True},
    {"field": "validation_score", "hide": True},
    {"field": "filename", "hide": True},
    {"field": "processed_at", "hide": True},
    {"field": "id", "hide": True},  # нужен для навигации
]
```

### Pattern 4: Статус-бейджи через Tailwind @layer components

**What:** CSS-классы определяются один раз через `ui.add_head_html` в `app/main.py`. JS cellRenderer использует эти классы по имени. Tailwind видит literal strings — нет риска JIT-purge.

```python
# app/main.py — вызвать один раз при старте
ui.add_head_html("""
<style type="text/tailwindcss">
  @layer components {
    .status-active      { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-50 text-green-700; }
    .status-expiring    { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-50 text-yellow-700; }
    .status-expired     { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-50 text-red-700; }
    .status-unknown     { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500; }
    .status-terminated  { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500; }
    .status-extended    { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700; }
    .status-negotiation { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-50 text-purple-700; }
    .status-suspended   { @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-orange-50 text-orange-700; }
  }
</style>
""")
```

### Pattern 5: Hover-actions через AG Grid custom cell

**Проблема:** NiceGUI `ui.aggrid` не поддерживает встроенные Python-кнопки внутри ячеек. Hover-actions работают через JS cellRenderer, который эмитирует кастомные события.

**Решение:** Использовать AG Grid `cellRenderer` с JS, который вешает `click` listener на иконки и эмитирует `CustomEvent` на grid element. NiceGUI ловит это через `grid.on('custom_action', handler)`.

```python
# В columnDefs — колонка-действия (последняя, не сортируемая)
{
    "headerName": "",
    "field": "id",
    "width": 80,
    "sortable": False,
    "filter": False,
    "cellRenderer": """(params) => {
        const div = document.createElement('div');
        div.className = 'actions-cell';
        div.innerHTML = '<span class="action-icon" title="Меню">⋯</span>';
        div.querySelector('.action-icon').addEventListener('click', (e) => {
            e.stopPropagation();
            params.context.componentParent.dispatchEvent(
                new CustomEvent('row_action', {
                    detail: { action: 'menu', id: params.data.id },
                    bubbles: true
                })
            );
        });
        return div;
    }""",
}
```

**Альтернатива (проще):** Использовать AG Grid `onCellClicked` event с `colId` проверкой. Это проще в NiceGUI, т.к. не требует CustomEvent:

```python
async def on_cell_clicked(event):
    col = event.args.get("column", {}).get("colId", "")
    row_data = event.args.get("data", {})
    if col == "actions":
        await show_action_menu(row_data)
    else:
        doc_id = row_data.get("id")
        if doc_id:
            ui.navigate.to(f"/document/{doc_id}")

grid.on("cellClicked", on_cell_clicked)
```

**Рекомендация:** Использовать `cellClicked` + отдельная колонка actions (проще, без CustomEvent). Hover-эффект — CSS через `ui.add_head_html` для `.ag-row:hover .actions-cell`.

### Pattern 6: Версии документов (flat list с indent)

**Why not AG Grid master/detail:** master/detail требует AG Grid Enterprise ($) или сложной конфигурации. Для MVP достаточно flat list с полем `is_child` и `parent_id`.

**Approach:** Python-side expansion: при загрузке строим flat list, где дочерние версии изначально скрыты (`hidden: True`). Клик по ▶ кнопке меняет `hidden` у дочерних строк и вызывает `grid.options['rowData'] = new_rows; grid.update()`.

```python
def build_rows_with_versions(base_rows: list[dict], db) -> list[dict]:
    """Строит плоский список строк с версиями. Дочерние строки имеют is_child=True."""
    from services.version_service import get_version_group
    result = []
    for row in base_rows:
        # Основной договор
        versions = get_version_group(db, row["id"])
        has_children = len(versions) > 1
        row["has_children"] = has_children
        row["is_expanded"] = False
        row["is_child"] = False
        row["indent"] = 0
        result.append(row)
        # Дочерние версии (скрыты по умолчанию)
        if has_children:
            for v in versions[1:]:  # skip v1 (это сам parent)
                child_row = ... # загрузить из DB по v.contract_id
                child_row["is_child"] = True
                child_row["indent"] = 1
                child_row["_hidden"] = True
                result.append(child_row)
    return result
```

**Замечание:** `get_version_group()` делает SELECT per строку — при 200+ документах это N+1 запрос. Нужен bulk join:

```sql
SELECT dv.contract_id, dv.contract_group_id, dv.version_number
FROM document_versions dv
WHERE dv.contract_group_id IN (
    SELECT contract_group_id FROM document_versions WHERE contract_id IN ({ids})
)
```

Либо ленивая загрузка: версии подгружаются только при клике ▶.

### Pattern 7: Client Dropdown в Header

**What:** `render_header()` получает `state: AppState`. При клике на 👤▾ — `ui.menu()` с `ui.menu_item()` для каждого клиента.

```python
# app/components/header.py
from nicegui import ui
from services.client_manager import ClientManager
from app.state import AppState

def render_header(state: AppState) -> None:
    with ui.header()...:
        ...
        # Right: client dropdown
        with ui.row().classes('shrink-0 items-center gap-1'):
            with ui.element('div').classes('relative cursor-pointer'):
                profile_btn = ui.label(f'👤 {state.current_client} ▾').classes('text-sm text-gray-600')
                with ui.menu() as client_menu:
                    cm = ClientManager()
                    for client_name in cm.list_clients():
                        ui.menu_item(
                            client_name,
                            on_click=lambda n=client_name: _switch_client(state, n)
                        )
                    ui.separator()
                    ui.menu_item('+ Добавить клиента', on_click=_show_add_client)
                profile_btn.on('click', client_menu.open)

def _switch_client(state: AppState, name: str) -> None:
    state.current_client = name
    state.filter_search = ""
    state.filter_type = ""
    state.filter_status = ""
    ui.navigate.to("/")  # reload registry page
```

### Pattern 8: Сегментированный фильтр (Segmented Control)

**What:** Кнопки-сегменты над таблицей. Active state через условный Tailwind класс (literal, не dynamic).

```python
SEGMENT_CLASSES = {
    True:  "px-4 py-1.5 text-sm font-medium rounded-md bg-gray-900 text-white",
    False: "px-4 py-1.5 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-100",
}

def render_segments(state, on_change):
    segments = [("all", "Все"), ("expiring", "Истекают ⚠"), ("attention", "Требуют внимания")]
    with ui.row().classes("gap-1 bg-gray-100 p-1 rounded-lg"):
        for key, label in segments:
            is_active = state.active_segment == key
            ui.button(
                label,
                on_click=lambda k=key: on_change(k)
            ).classes(SEGMENT_CLASSES[is_active]).props("flat")
```

**Замечание:** badge-счётчик («Истекают ⚠ 3») — нужно считать при загрузке и передавать в label.

### Anti-Patterns to Avoid

- **Tailwind dynamic class strings:** Никогда `f'bg-{status}-100'` — JIT purger не видит. Только literal lookup dict или `@layer components`.
- **Прямые DB-вызовы в `async def`:** Всегда `await run.io_bound(_fetch)` — иначе event loop блокируется.
- **AG Grid Enterprise features:** master/detail, row grouping — Enterprise. Использовать flat list + Python-side expand.
- **Мутация `rows` списка:** `grid.options['rowData'] = new_rows; grid.update()` — не мутировать оригинал. NiceGUI v3 не детектирует изменения в месте.
- **`grid.on('rowClicked', ...)` + hover actions в одной колонке:** Нужен `stopPropagation` в JS, иначе клик на ⋯ триггерит навигацию.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy search | Кастомный Levenshtein | `rapidfuzz.fuzz.partial_ratio` | Уже в requirements.txt; vectorized C extension; handles Unicode |
| Status computation | Python datetime compare | `get_computed_status_sql(warning_days)` в SQL | Уже реализовано; manual_status priority встроен |
| Client list | Кастомный JSON реестр | `ClientManager.list_clients()` + `ClientManager.get_db()` | Уже реализовано в services/client_manager.py |
| Version grouping | Кастомная логика | `get_version_group(db, contract_id)` | Уже реализовано в services/version_service.py |
| Manual status apply | Прямой SQL UPDATE | `set_manual_status(db, contract_id, status)` | Валидирует против MANUAL_STATUSES; thread-safe через db._lock |
| Status badge colors | Вычислять из STATUS_LABELS | CSS @layer components с literal class names | Tailwind JIT требует literal strings |

---

## Common Pitfalls

### Pitfall 1: N+1 запросы для версий
**What goes wrong:** `get_version_group()` делает SELECT на каждую строку реестра. При 100 документах = 100 запросов при загрузке.
**Why it happens:** get_version_group принимает один contract_id.
**How to avoid:** Ленивая загрузка — версии подгружать только при клике ▶, не при начальной загрузке. Или bulk JOIN: один запрос получает все версии для всех видимых contract_ids.
**Warning signs:** Начальная загрузка страницы занимает >1 секунды при 50+ документах.

### Pitfall 2: AG Grid не обновляется после смены rowData
**What goes wrong:** `grid.options['rowData'] = new_rows` без `grid.update()` — таблица не перерисовывается.
**Why it happens:** NiceGUI v3 убрал auto-detection изменений в mutable objects.
**How to avoid:** Всегда пара: `grid.options['rowData'] = new_rows; grid.update()`.
**Warning signs:** Клик на сегмент «Истекают» — данные в переменной изменились, таблица показывает старое.

### Pitfall 3: rowClicked срабатывает при клике на ⋯
**What goes wrong:** Клик на иконку ⋯ открывает меню И навигирует на /document/{id}.
**Why it happens:** Событие всплывает от ячейки до строки.
**How to avoid:** В JS cellRenderer для actions-колонки — `e.stopPropagation()` на click listener. В Python-обработчике `cellClicked` — проверять `event.args["column"]["colId"]` перед навигацией.

### Pitfall 4: Tailwind классы бейджей не применяются
**What goes wrong:** Span имеет класс `status-active` в DOM, но стили нулевые.
**Why it happens:** Классы определены в JS cellRenderer (строка), Tailwind JIT их не видит при сканировании Python-файлов.
**How to avoid:** Определить CSS через `ui.add_head_html` с `@layer components` — это происходит в runtime, не через JIT. Альтернатива: использовать inline style в JS cellRenderer вместо классов.

### Pitfall 5: ClientManager создаётся per-request вместо per-session
**What goes wrong:** `ClientManager()` в каждом обработчике читает clients.json на каждый вызов.
**Why it happens:** ClientManager не синглтон.
**How to avoid:** Создать `ClientManager` один раз на уровне модуля (module-level singleton) — он stateless после init. Или кэшировать в AppState.

### Pitfall 6: Debounce отсутствует — fuzzy search при каждом символе
**What goes wrong:** При вводе «аренда Ромашка» пользователь видит 15 перезагрузок таблицы — по одной на каждый символ.
**Why it happens:** `ui.input(on_change=reload_table)` срабатывает on_change мгновенно.
**How to avoid:** Debounce 300ms через `ui.timer`:
```python
_search_timer = None

def on_search_change(value: str):
    global _search_timer
    if _search_timer:
        _search_timer.cancel()
    _search_timer = ui.timer(0.3, lambda: reload_table(value), once=True)
```

### Pitfall 7: filter_search / filter_status в AppState не синхронизированы с AG Grid floating filters
**What goes wrong:** Пользователь вводит текст в floating filter AG Grid, но Python-поиск не применяется — данные фильтруются только на стороне AG Grid (JS).
**Why it happens:** AG Grid floating filters работают на JS-стороне независимо от Python state.
**How to avoid:** Либо **не использовать** floatingFilter AG Grid для основного поиска (полагаться только на Python rapidfuzz search), либо слушать `filterChanged` event и переотдавать данные. Решение (D-10): AG Grid column filters — для дополнительной фильтрации по колонкам, Python rapidfuzz — для основного поиска. Они работают вместе: Python pre-filters rowData, AG Grid JS-filters работают поверх него.

---

## Code Examples

### Полный цикл загрузки реестра

```python
# app/pages/registry.py
from nicegui import ui, run
from app.state import get_state
from services.client_manager import ClientManager
from services.lifecycle_service import get_computed_status_sql
from config import Config

_client_manager = ClientManager()  # module-level singleton

def build() -> None:
    state = get_state()
    config = Config()

    # Segment state (не в AppState — локальный для страницы)
    active_segment = {"value": "all"}

    # UI: search bar + segments
    with ui.row().classes("w-full px-6 pt-4 pb-2 items-center gap-4"):
        search_input = ui.input(
            placeholder="Поиск по реестру..."
        ).classes("flex-1 max-w-md")

        with ui.row().classes("gap-1 bg-gray-100 p-1 rounded-lg"):
            btn_all = ui.button("Все", on_click=lambda: switch_segment("all")).props("flat")
            btn_exp = ui.button("Истекают ⚠", on_click=lambda: switch_segment("expiring")).props("flat")
            btn_att = ui.button("Требуют внимания", on_click=lambda: switch_segment("attention")).props("flat")

    # AG Grid
    grid = ui.aggrid({
        "columnDefs": COLUMN_DEFS,  # см. Pattern 3
        "rowData": [],
        "rowSelection": "single",
        "domLayout": "autoHeight",
        "defaultColDef": {"sortable": True, "resizable": True},
    }).classes("w-full px-6")

    grid.on("cellClicked", lambda e: on_cell_clicked(e, state))

    # Load data on page open
    ui.timer(0, lambda: load_and_render(), once=True)

    async def load_and_render():
        rows = await run.io_bound(
            _fetch_rows,
            state.current_client,
            active_segment["value"],
            search_input.value,
            config.warning_days,
        )
        grid.options["rowData"] = rows
        grid.update()

    def switch_segment(key: str):
        active_segment["value"] = key
        ui.timer(0, lambda: load_and_render(), once=True)

    # Debounced search
    _timer = [None]
    def on_search(value):
        if _timer[0]:
            _timer[0].cancel()
        _timer[0] = ui.timer(0.3, lambda: load_and_render(), once=True)

    search_input.on("input", lambda e: on_search(e.args))
```

### _fetch_rows (синхронная функция для run.io_bound)

```python
def _fetch_rows(client_name: str, segment: str, search: str, warning_days: int) -> list[dict]:
    db = _client_manager.get_db(client_name)
    sql = f"""
        SELECT
            id, contract_type, counterparty, amount, filename,
            date_end, validation_score, validation_warnings, processed_at,
            {get_computed_status_sql(warning_days)} AS computed_status
        FROM contracts
        WHERE status = 'done'
        ORDER BY processed_at DESC
    """
    rows = [dict(r) for r in db.conn.execute(sql, {"warning_days": warning_days}).fetchall()]

    # Segment filter
    if segment == "expiring":
        rows = [r for r in rows if r["computed_status"] == "expiring"]
    elif segment == "attention":
        import json
        rows = [r for r in rows if
                (r.get("validation_score") or 1.0) < 0.7
                or bool(json.loads(r.get("validation_warnings") or "[]"))]

    # Fuzzy filter
    if search.strip():
        rows = _fuzzy_filter(rows, search)

    return rows
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| AG Grid `rowSelection: 'single'` (string) | `rowSelection: {mode: 'singleRow'}` (object) | AG Grid v32+ | Старый string API deprecated; NiceGUI 3.9 может использовать оба варианта, но object-форма предпочтительна |
| `ui.table` для реестра | `ui.aggrid` с floatingFilter | Phase 7 решение | ui.table не поддерживает floating column filters |
| `.tailwind()` метод | `.classes()` со строками | NiceGUI v3 | `.tailwind()` удалён, использовать только `.classes()` |
| Streamlit `st.rerun()` для обновления | `grid.options['rowData'] = x; grid.update()` | Phase 7 решение | Нет full-page rerun в NiceGUI |

---

## Open Questions

1. **AG Grid версия, bundled в NiceGUI 3.9.0**
   - What we know: NiceGUI использует AG Grid Community edition, версия зависит от NPM bundle.
   - What's unclear: Точная версия AG Grid (v31 или v32+) — влияет на `rowSelection` API.
   - Recommendation: Проверить в browser DevTools `agGrid.version` после запуска. Если v32+ — использовать `rowSelection: {mode: 'singleRow'}`, иначе `rowSelection: 'single'`.

2. **Hover CSS для AG Grid строк через NiceGUI**
   - What we know: `.ag-row:hover` — стандартный AG Grid CSS selector.
   - What's unclear: Может ли `ui.add_head_html` перекрыть AG Grid default theme CSS без `!important`.
   - Recommendation: Использовать `.ag-theme-balham .ag-row:hover .actions-cell { opacity: 1; }` с достаточной специфичностью.

3. **`ui.menu()` в header вне `@ui.page` контекста**
   - What we know: `render_header()` вызывается внутри `@ui.page` функции — контекст есть.
   - What's unclear: Позиционирование `ui.menu()` внутри `ui.header()` — может потребоваться `ui.element('div').classes('relative')`.
   - Recommendation: Протестировать с `ui.button` + `ui.menu` внутри header — это стандартный паттерн Quasar/NiceGUI.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (существующий, tests/) |
| Config file | tests/ directory (нет отдельного pytest.ini) |
| Quick run command | `pytest tests/test_registry_view.py -x -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REG-01 | _fetch_rows возвращает список dict с computed_status | unit | `pytest tests/test_registry_view.py::test_fetch_rows -x` | ❌ Wave 0 |
| REG-02 | cellClicked handler вызывает navigate.to с правильным doc_id | unit | `pytest tests/test_registry_view.py::test_row_click_navigation -x` | ❌ Wave 0 |
| REG-03 | _fuzzy_filter фильтрует по всем полям с threshold=80 | unit | `pytest tests/test_registry_view.py::test_fuzzy_filter -x` | ❌ Wave 0 |
| REG-04 | STATUS_COLORS dict содержит все статусы из STATUS_LABELS | unit | `pytest tests/test_registry_view.py::test_status_colors_coverage -x` | ❌ Wave 0 |
| REG-05 | Segment filter 'expiring' возвращает только строки с computed_status=expiring | unit | `pytest tests/test_registry_view.py::test_segment_expiring -x` | ❌ Wave 0 |
| REG-05 | Segment filter 'attention' возвращает строки с validation_score<0.7 | unit | `pytest tests/test_registry_view.py::test_segment_attention -x` | ❌ Wave 0 |
| REG-06 | on_cell_clicked с colId=actions не вызывает navigate.to | unit | `pytest tests/test_registry_view.py::test_action_cell_no_navigate -x` | ❌ Wave 0 |
| REG-07 | build_rows_with_versions добавляет is_child=True для дочерних версий | unit | `pytest tests/test_registry_view.py::test_version_rows -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_registry_view.py -x -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_registry_view.py` — unit тесты для _fetch_rows, _fuzzy_filter, segment filters, version rows, navigation handler (REG-01 – REG-07)
- [ ] Тестовые фикстуры: in-memory SQLite с 5-10 контрактами, включая expiring и low-score

*(Существующие tests/test_extractor.py, test_anonymizer.py, test_validator.py не покрывают registry view — нужен новый файл)*

---

## Sources

### Primary (HIGH confidence)
- Codebase direct analysis — `services/lifecycle_service.py`, `modules/database.py`, `services/client_manager.py`, `services/version_service.py`, `app/state.py`, `app/components/header.py` — все интерфейсы и данные
- `.planning/research/STACK.md` — NiceGUI 3.9.0 AG Grid API, verified from nicegui.io
- `.planning/research/PITFALLS.md` — Tailwind JIT pitfall (Pitfall 7), SQLite blocking (Pitfall 2)
- `.planning/research/ARCHITECTURE.md` — Pattern 5 (ui.aggrid wrapper), Pattern 1 (AppState)

### Secondary (MEDIUM confidence)
- AG Grid Community docs — `floatingFilter`, `cellRenderer`, `onCellClicked` API — стандартные, стабильные
- rapidfuzz docs — `fuzz.partial_ratio` vs `token_set_ratio` performance characteristics

### Tertiary (LOW confidence)
- AG Grid exact version bundled in NiceGUI 3.9.0 — не верифицировано, нужна проверка в DevTools

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — все пакеты уже в проекте, проверены напрямую
- Architecture: HIGH — паттерны верифицированы в ARCHITECTURE.md и PITFALLS.md
- Fuzzy search: HIGH — rapidfuzz уже используется в client_manager с тем же порогом
- Hover-actions: MEDIUM — JS cellRenderer + NiceGUI event bridging требует проверки точного event API
- Version grouping: MEDIUM — flat list подход проще AG Grid master/detail, но N+1 риск реален

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (NiceGUI 3.9.0 стабильный релиз, не fast-moving)
