# Phase 9: Document Detail Card — Research

**Researched:** 2026-03-22
**Domain:** NiceGUI SPA page — document metadata display, AI review, version diff, lawyer notes
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Page layout**
- D-01: Одна колонка с секциями (не 2-колоночный grid). Сверху вниз: header → метаданные grid → статус → пометки → ревью → версии
- D-02: Header карточки: «← Назад к реестру» слева, название документа (contract_type) по центру, кнопки ◀ ▶ (prev/next) справа
- D-03: Prev/next переключают `doc_id` в URL через `ui.navigate.to` без возврата в реестр

**Metadata fields**
- D-04: 7 полей в structured grid: Тип, Контрагент, Предмет (subject), Дата начала, Дата окончания, Сумма, Особые условия (special_conditions как bulleted list)
- D-05: Стороны (parties) и технические поля (filename, model_used, processed_at, validation_score) — НЕ показываются

**Status section**
- D-06: Статус отображается с цветным бейджем (из STATUS_LABELS) + кнопка «Изменить» → dropdown с MANUAL_STATUSES
- D-07: «Сбросить» рядом с dropdown — вызывает `clear_manual_status`, возвращает к автоматическому статусу

**Lawyer notes**
- D-08: Одно текстовое поле (`lawyer_comment`), автосохранение на blur через `database.update_review`
- D-09: Без статуса ревью (reviewed/pending) — минимализм. Статус управляется через manual_status

**AI review**
- D-10: Сворачиваемая секция «Ревью». Кнопка «Проверить по шаблону»
- D-11: При клике — автоподбор шаблона через `match_template()`. Если нет подходящего — dropdown для ручного выбора из `list_templates()`
- D-12: Ревью запускается через `run.io_bound(review_against_template, ...)` — async, не блокирует UI
- D-13: Результат — список отступлений с цветовыми метками: зелёный (добавлено), красный (удалено), жёлтый (изменено). Текст шаблона vs текст документа для каждого отступления
- D-14: Если нет шаблонов — сообщение «Нет шаблонов. Добавьте в разделе Шаблоны» с ссылкой

**Version history**
- D-15: Сворачиваемая секция «Версии». По умолчанию свёрнута
- D-16: Список версий из `get_version_group()` — каждая строка: номер версии, метод привязки, дата
- D-17: Кнопка «Сравнить» рядом с каждой версией — показывает результат `diff_versions()` inline: таблица полей с пометками changed/unchanged
- D-18: Кнопка «Скачать redline» — вызывает `generate_redline_docx()`, скачивается .docx через FastAPI FileResponse (не ui.download — pitfall #6)

**Navigation**
- D-19: `← Назад к реестру` → `ui.navigate.to('/')` — возвращает на реестр
- D-20: Prev/next: нужен список doc_ids из текущего отфильтрованного реестра в AppState. Навигация: `ui.navigate.to(f'/document/{prev_id}')`

**Database**
- D-21: Нужен новый метод `Database.get_contract_by_id(contract_id: int) -> dict` — сейчас нет, нужно добавить

### Claude's Discretion
- Exact grid layout for metadata (Tailwind classes, gap, columns)
- Spinner/loading state during AI review
- Scroll position restore on back navigation
- Placeholder text for empty lawyer_comment
- Keyboard shortcuts for prev/next (если просто)

### Deferred Ideas (OUT OF SCOPE)
- Полнотекстовый просмотр документа (PDF/DOCX viewer) — v2+
- Таблица сравнения двух версий side-by-side — v2+ (сейчас inline diff)
- Теги/метки на документах — не в scope v0.6
- Экспорт карточки в PDF — v2+
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOC-01 | Full-page карточка документа с кнопкой «← Назад к реестру» | `app/pages/document.py` stub exists with `build(doc_id)` signature; route `/document/{doc_id}` already wired in `app/main.py` |
| DOC-02 | Метаданные документа отображаются в CSS grid-layout | 7 полей из `contracts` table; `special_conditions` — JSON array, нужен `json.loads` + bulleted list render |
| DOC-03 | Навигация «Предыдущий / Следующий» между документами без возврата в реестр | AppState has `selected_doc_id` and filters; `_fetch_rows` returns ordered list — extract `id` list for prev/next |
| DOC-04 | AI-ревью документа по выбранному шаблону (кнопка в карточке) | `match_template()`, `review_against_template()`, `list_templates()` — все готовы в `review_service.py`; async через `run.io_bound` |
| DOC-05 | История версий документа в сворачиваемой секции | `get_version_group()` + `diff_versions()` + `generate_redline_docx()` — все готовы в `version_service.py` |
| DOC-06 | Пометки юриста (ручные заметки к документу) | `database.update_review(file_hash, review_status, comment)` существует; `lawyer_comment` поле в contracts |
</phase_requirements>

---

## Summary

Phase 9 строит полноценную карточку документа в NiceGUI. Инфраструктура полностью готова: сервисный слой (`version_service`, `review_service`, `lifecycle_service`) реализован и протестирован в предыдущих фазах, stub-страница `app/pages/document.py` существует с правильной сигнатурой `build(doc_id)`, маршрут `/document/{doc_id}` уже прописан в `app/main.py`. Единственный недостающий кусок — метод `Database.get_contract_by_id()`.

Главные технические задачи: (1) добавить `get_contract_by_id` в `database.py`, (2) реализовать `build()` в `document.py` с секционной структурой, (3) добавить FastAPI route для redline .docx download (Pitfall 6), (4) выстроить prev/next через список `doc_ids` из `AppState`.

**Primary recommendation:** Реализовывать волнами: Wave 0 — тесты + `get_contract_by_id`, Wave 1 — header + metadata + статус + notes, Wave 2 — AI review section, Wave 3 — versions section + redline download route.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| nicegui | уже установлен | SPA UI, layout, events | Проект уже на NiceGUI |
| fastapi | уже установлен (через nicegui) | FileResponse для redline download | Pitfall 6 — ui.download блокирует event loop |
| python-docx | уже установлен | Используется в `generate_redline_docx` | Уже в requirements |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlite3 | stdlib | `get_contract_by_id` query | Только через `run.io_bound` |
| json | stdlib | Deserialize `special_conditions` JSON array | При чтении поля из БД |
| sentence-transformers | уже установлен | В `match_template` через version_service | Вызывается внутри review_service, не напрямую |

**Installation:** Никаких новых зависимостей. Всё уже в requirements.txt.

---

## Architecture Patterns

### Recommended Project Structure

```
app/pages/document.py           # основной файл фазы — полная реализация build()
modules/database.py             # добавить get_contract_by_id()
app/main.py                     # добавить FastAPI route для redline download
app/state.py                    # добавить filtered_doc_ids: list[int] = field(default_factory=list)
```

### Pattern 1: Page Entry Point

`build(doc_id: str)` — async-функция, вызывается из `ui.sub_pages`. Получает состояние через `get_state()`, загружает данные через `run.io_bound(db.get_contract_by_id, int(doc_id))`.

```python
# app/pages/document.py
from nicegui import ui, run
from app.state import get_state
from services.client_manager import ClientManager

_client_manager = ClientManager()

async def build(doc_id: str = "") -> None:
    state = get_state()
    if not doc_id:
        ui.navigate.to('/')
        return
    contract = await run.io_bound(
        _client_manager.get_db(state.current_client).get_contract_by_id,
        int(doc_id)
    )
    if contract is None:
        ui.label('Документ не найден').classes('text-red-500')
        return
    # ... render sections
```

### Pattern 2: get_contract_by_id (новый метод)

Добавить в `Database` класс. Возвращает `dict` с десериализованными JSON-полями (аналогично `get_all_results`).

```python
def get_contract_by_id(self, contract_id: int) -> dict | None:
    with self._lock:
        row = self.conn.execute(
            "SELECT * FROM contracts WHERE id = ?", (contract_id,)
        ).fetchone()
    if row is None:
        return None
    d = dict(row)
    for field in ("special_conditions", "parties", "validation_warnings"):
        raw = d.get(field)
        if raw:
            try:
                parsed = json.loads(raw)
                d[field] = parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, TypeError):
                d[field] = []
        else:
            d[field] = []
    d.setdefault("review_status", "not_reviewed")
    d.setdefault("lawyer_comment", "")
    d.setdefault("manual_status", None)
    return d
```

### Pattern 3: Computed Status в карточке

Вычисляется через отдельный SQL-запрос с `get_computed_status_sql()` — аналогично реестру. Не вычислять в Python.

```python
from services.lifecycle_service import get_computed_status_sql, STATUS_LABELS

sql = f"SELECT {get_computed_status_sql(state.warning_days_threshold)} AS computed_status FROM contracts WHERE id = ?"
row = db.conn.execute(sql, {"warning_days": state.warning_days_threshold, 1: contract_id}).fetchone()
# Правильный вариант с именованными параметрами:
sql = f"""
    SELECT {get_computed_status_sql(30)} AS computed_status
    FROM contracts WHERE id = :contract_id
"""
row = db.conn.execute(sql, {"warning_days": 30, "contract_id": contract_id}).fetchone()
```

### Pattern 4: Collapsible Section

NiceGUI не имеет встроенного collapsible. Использовать `ui.expansion` или ручной toggle через `ui.column().bind_visibility_from(...)`.

```python
# Рекомендуемый вариант через ui.expansion:
with ui.expansion('Версии', icon='history').classes('w-full border rounded-lg'):
    # content here — не рендерится до раскрытия
    build_versions_section(contract, db)
```

`ui.expansion` — встроенный NiceGUI компонент (Quasar QExpansionItem), lazy render, идеально для D-15.

### Pattern 5: Async AI Review без блокировки UI

```python
async def _run_review(contract: dict, db, result_container) -> None:
    spinner = ui.spinner('dots').classes('text-blue-500')
    template = await run.io_bound(
        match_template, db, contract.get('subject', ''), contract.get('contract_type')
    )
    if template is None:
        # показать dropdown для ручного выбора
        templates = await run.io_bound(list_templates, db)
        if not templates:
            result_container.clear()
            with result_container:
                ui.label('Нет шаблонов. Добавьте в разделе Шаблоны')
            spinner.delete()
            return
        # ui.select с templates
        ...
    else:
        deviations = await run.io_bound(
            review_against_template,
            template.content_text,
            contract.get('subject', '')
        )
    spinner.delete()
    _render_deviations(result_container, deviations)
```

### Pattern 6: FastAPI route для redline download

Добавить в `app/main.py` (через `nicegui app`):

```python
from fastapi.responses import Response
from nicegui import app as nicegui_app

@nicegui_app.get('/download/redline/{contract_id}/{other_id}')
async def download_redline(contract_id: int, other_id: int):
    # получить тексты обоих документов из DB
    # вызвать generate_redline_docx через run.io_bound
    docx_bytes = await run.io_bound(generate_redline_docx, text_old, text_new, title)
    return Response(
        content=docx_bytes,
        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        headers={'Content-Disposition': f'attachment; filename="redline_{contract_id}_vs_{other_id}.docx"'}
    )
```

В UI: `ui.link('Скачать redline', f'/download/redline/{doc_id}/{other_id}')`.

### Pattern 7: Prev/Next navigation

`AppState.filtered_doc_ids` — новый список int, заполняется в реестре при клике на документ. `document.py` читает его для prev/next.

```python
# В registry при переходе в карточку:
state.filtered_doc_ids = [r['id'] for r in current_rows]
state.selected_doc_id = clicked_id
ui.navigate.to(f'/document/{clicked_id}')

# В document.py:
doc_ids = state.filtered_doc_ids
if doc_ids and int(doc_id) in doc_ids:
    idx = doc_ids.index(int(doc_id))
    prev_id = doc_ids[idx - 1] if idx > 0 else None
    next_id = doc_ids[idx + 1] if idx < len(doc_ids) - 1 else None
```

### Anti-Patterns to Avoid

- **Динамический Tailwind через f-string:** `f'bg-{color}-100'` — класс не будет применён (Pitfall 7). Использовать словарь с литеральными строками.
- **`ui.download(docx_bytes)`** для redline файла — блокирует event loop (Pitfall 6). Только FastAPI FileResponse.
- **Прямой вызов `db.get_contract_by_id()` внутри `async def`** без `run.io_bound` — блокирует event loop (Pitfall 2).
- **`match_template()` и `review_against_template()` синхронно** — оба вычисляют эмбеддинги, занимают 1-5 секунд. Обязательно через `run.io_bound`.
- **Хранение `deviations` или `versions` в module-level переменной** — будет shared across all clients (Pitfall 1). Только в локальных переменных функции `build()`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Template auto-match | Собственный алгоритм подбора | `match_template(db, text, contract_type)` | Уже реализован с cosine sim + threshold |
| Diff отклонений | Собственный text diff | `review_against_template(template_text, doc_text)` | Возвращает готовый список `{"type", "template_text", "document_text", "color"}` |
| Version list | SQL запрос вручную | `get_version_group(db, contract_id)` | Инкапсулирует group lookup + sorted fetch |
| Field-level diff | Сравнение словарей | `diff_versions(meta_old, meta_new)` | Возвращает готовый список `{"field", "old", "new", "changed"}` |
| Redline DOCX | python-docx вручную | `generate_redline_docx(text_old, text_new, title)` | Реализован с w:ins/w:del track changes |
| Status badge colors | Свой CSS | `STATUS_LABELS` dict + `_STATUS_CSS` уже в `app/main.py` | Все 8 статусов уже определены |
| Manual status change | Прямой UPDATE SQL | `set_manual_status(db, id, status)` / `clear_manual_status(db, id)` | Валидация + лог включены |
| Collapsible section | Свой JS toggle | `ui.expansion(label)` | Нативный Quasar QExpansionItem в NiceGUI |

---

## Common Pitfalls

### Pitfall 1: `ui.download()` для redline .docx
**What goes wrong:** `ui.download(docx_bytes, 'redline.docx')` блокирует event loop перед отправкой.
**Why it happens:** NiceGUI serializes bytes synchronously (PITFALLS.md §Pitfall 6).
**How to avoid:** FastAPI `@nicegui_app.get('/download/redline/...')` route + `Response(content=bytes, ...)`.
**Warning signs:** UI зависает на 2-3 секунды при нажатии «Скачать redline».

### Pitfall 2: Sync DB call в async context
**What goes wrong:** `contract = db.get_contract_by_id(doc_id)` внутри `async def build()` — event loop заблокирован.
**Why it happens:** sqlite3 синхронный (PITFALLS.md §Pitfall 2).
**How to avoid:** `contract = await run.io_bound(db.get_contract_by_id, doc_id)`.
**Warning signs:** Карточка «висит» при открытии из реестра.

### Pitfall 3: match_template() без run.io_bound
**What goes wrong:** `match_template()` вычисляет эмбеддинги (SentenceTransformer) — это CPU-bound операция на 1-5 секунд. Заблокирует UI.
**Why it happens:** sentence-transformers — синхронная библиотека.
**How to avoid:** `template = await run.io_bound(match_template, db, text, contract_type)`.
**Warning signs:** Кнопка «Проверить по шаблону» не отвечает несколько секунд без спиннера.

### Pitfall 4: Tailwind dynamic classes в diff
**What goes wrong:** `f'border-l-{color}'` или `style=f'border-color: {deviation["color"]}'` — Tailwind purge срежет динамические классы.
**Why it happens:** Tailwind JIT не видит строки, собранные в runtime (PITFALLS.md §Pitfall 7).
**How to avoid:** Использовать inline `style` для hex-цветов из `_DIFF_COLORS` (`style=f'border-left: 3px solid {d["color"]}'`), либо предопределённый словарь с literal Tailwind классами.
**Warning signs:** Цветовая разметка отступлений не отображается в production.

### Pitfall 5: filtered_doc_ids не синхронизированы с текущим фильтром
**What goes wrong:** Юрист меняет фильтр в реестре и открывает карточку — prev/next ведут к старым doc_ids.
**Why it happens:** `state.filtered_doc_ids` обновляется только при клике на строку в реестре, а не при смене фильтра.
**How to avoid:** Обновлять `filtered_doc_ids` при каждой загрузке данных реестра, а не только при клике. В `load_table_data` добавить `state.filtered_doc_ids = [r['id'] for r in rows]`.
**Warning signs:** Prev/next переходят к документам, не совпадающим с текущим фильтром.

### Pitfall 6: update_review принимает file_hash, не contract_id
**What goes wrong:** `database.update_review(contract_id, review_status, comment)` — неверный тип первого параметра.
**Why it happens:** Существующая сигнатура: `update_review(self, file_hash: str, review_status: str, comment: str)`. В карточке известен `id`, а не `file_hash`.
**How to avoid:** Читать `file_hash` из загруженного `contract` dict (`contract['file_hash']`) и передавать его в `update_review`. Либо добавить `update_review_by_id`. Проще — из contract dict.
**Warning signs:** `update_review` не обновляет запись (WHERE условие не совпадает).

---

## Code Examples

### Metadata grid (Notion-style, 2-column label+value)

```python
def _render_metadata(contract: dict) -> None:
    FIELDS = [
        ("Тип договора",    contract.get("contract_type") or "—"),
        ("Контрагент",      contract.get("counterparty") or "—"),
        ("Предмет",         contract.get("subject") or "—"),
        ("Дата начала",     contract.get("date_start") or "—"),
        ("Дата окончания",  contract.get("date_end") or "—"),
        ("Сумма",           contract.get("amount") or "—"),
    ]
    with ui.grid(columns=2).classes('gap-x-6 gap-y-3 w-full'):
        for label, value in FIELDS:
            ui.label(label).classes('text-xs font-medium text-gray-400 uppercase tracking-wide')
            ui.label(value).classes('text-sm text-gray-900')
    # special_conditions — отдельно как bulleted list
    conditions = contract.get("special_conditions") or []
    if conditions:
        ui.label("Особые условия").classes('text-xs font-medium text-gray-400 uppercase tracking-wide mt-4')
        with ui.column().classes('gap-1'):
            for cond in conditions:
                with ui.row().classes('items-start gap-2'):
                    ui.label("•").classes('text-gray-400 text-sm')
                    ui.label(cond).classes('text-sm text-gray-900')
```

### Status badge (reusing existing CSS classes)

```python
def _render_status_badge(status_key: str) -> None:
    icon, label, _hex = STATUS_LABELS.get(status_key, ("?", status_key, "#9ca3af"))
    # Использовать существующие CSS-классы из _STATUS_CSS в main.py
    STATUS_CLASS = {
        "active":      "status-active",
        "expiring":    "status-expiring",
        "expired":     "status-expired",
        "unknown":     "status-unknown",
        "terminated":  "status-terminated",
        "extended":    "status-extended",
        "negotiation": "status-negotiation",
        "suspended":   "status-suspended",
    }
    cls = STATUS_CLASS.get(status_key, "status-unknown")
    ui.html(f'<span class="{cls}">{icon} {label}</span>')
```

### Deviation rendering (diff с цветными полосками)

```python
def _render_deviations(container, deviations: list[dict]) -> None:
    TYPE_LABEL = {"added": "добавлено", "removed": "удалено", "changed": "изменено"}
    container.clear()
    with container:
        if not deviations:
            ui.label("Отступлений не найдено").classes('text-green-600 text-sm')
            return
        for d in deviations:
            # inline style для hex-цвета — не Tailwind dynamic class
            with ui.row().classes('w-full rounded-md overflow-hidden mb-2'):
                ui.html(
                    f'<div style="border-left: 3px solid {d["color"]}; padding: 8px 12px; '
                    f'background: {d["color"]}22; width: 100%">'
                    f'<div class="text-xs text-gray-400 mb-1">{TYPE_LABEL.get(d["type"], d["type"])}</div>'
                    f'{"<div class=\'text-xs text-gray-500 line-through\'>" + (d.get("template_text") or "") + "</div>" if d.get("template_text") else ""}'
                    f'{"<div class=\'text-sm text-gray-900\'>" + (d.get("document_text") or "") + "</div>" if d.get("document_text") else ""}'
                    f'</div>'
                )
```

### Versions diff table

```python
def _render_diff_table(diffs: list[dict]) -> None:
    with ui.table(
        columns=[
            {'name': 'field', 'label': 'Поле', 'field': 'field', 'align': 'left'},
            {'name': 'old',   'label': 'Было',  'field': 'old',   'align': 'left'},
            {'name': 'new',   'label': 'Стало', 'field': 'new',   'align': 'left'},
        ],
        rows=[d for d in diffs if d['changed']],
    ).classes('w-full text-sm') as table:
        table.add_slot('body-cell-old', '<q-td :props="props"><span class="text-red-600 line-through">{{ props.value }}</span></q-td>')
        table.add_slot('body-cell-new', '<q-td :props="props"><span class="text-green-700">{{ props.value }}</span></q-td>')
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Streamlit tab-карточка (4 вкладки) | NiceGUI full-page, single column | Phase 7 milestone | Чище, больше пространства для контента |
| `st.session_state` для doc_id | `AppState.selected_doc_id` + URL param | Phase 7 | Type-safe, per-connection |
| `ui.download(bytes)` | FastAPI FileResponse | Pitfall 6, v0.6 | Event loop не блокируется |

**Deprecated/outdated:**
- Streamlit tabs (5-tab card): replaced by NiceGUI page sections
- `st.cache_resource` для singleton: replaced by module-level `_client_manager` pattern

---

## Open Questions

1. **Как получить `subject` для `generate_redline_docx` второй версии?**
   - Что мы знаем: `generate_redline_docx(text_old, text_new)` принимает тексты, но полного текста в БД нет. Используется `subject` как proxy (per STATE.md decision из Phase 2).
   - Что неясно: при сравнении версий нужен `subject` обоих contract_id. Это требует загрузки second contract.
   - Recommendation: При клике «Скачать redline» FastAPI route получает оба `contract_id`, загружает оба `subject`, вызывает `generate_redline_docx`. Добавить `get_contract_by_id` позволяет это сделать чисто.

2. **`AppState.filtered_doc_ids` — где инициализировать?**
   - Что мы знаем: `AppState` в `app/state.py` не имеет `filtered_doc_ids` поля.
   - Recommendation: Добавить `filtered_doc_ids: list = field(default_factory=list)` в AppState. Заполнять в `load_table_data` после fetch. Карточка читает его для prev/next.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `tests/conftest.py` (добавляет PROJECT_ROOT в sys.path) |
| Quick run command | `pytest tests/test_document_card.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOC-01 | `build()` без doc_id → navigate to `/` | unit | `pytest tests/test_document_card.py::test_build_empty_doc_id -x` | ❌ Wave 0 |
| DOC-01 | `build(doc_id)` с несуществующим id → сообщение ошибки | unit | `pytest tests/test_document_card.py::test_build_not_found -x` | ❌ Wave 0 |
| DOC-02 | `get_contract_by_id` возвращает dict с десериализованными JSON | unit | `pytest tests/test_document_card.py::test_get_contract_by_id -x` | ❌ Wave 0 |
| DOC-02 | `get_contract_by_id` для несуществующего id → None | unit | `pytest tests/test_document_card.py::test_get_contract_by_id_none -x` | ❌ Wave 0 |
| DOC-03 | Prev/next logic из filtered_doc_ids | unit | `pytest tests/test_document_card.py::test_prevnext_logic -x` | ❌ Wave 0 |
| DOC-04 | `match_template` возвращает None если нет шаблонов | unit | уже в test_versioning.py / review_service tests | ✅ существующие |
| DOC-05 | `get_version_group` возвращает список `DocumentVersion` | unit | уже в `tests/test_versioning.py` | ✅ существующие |
| DOC-06 | `update_review` обновляет `lawyer_comment` по file_hash | unit | уже в `tests/test_service_layer.py` | ✅ существующие |

### Wave 0 Gaps

- [ ] `tests/test_document_card.py` — покрывает DOC-01, DOC-02, DOC-03

*(DOC-04, DOC-05, DOC-06 покрыты существующими тестами сервисного слоя.)*

---

## Sources

### Primary (HIGH confidence)
- Исходный код `services/version_service.py` — сигнатуры `get_version_group`, `diff_versions`, `generate_redline_docx`
- Исходный код `services/review_service.py` — сигнатуры `match_template`, `review_against_template`, `list_templates`, `_DIFF_COLORS`
- Исходный код `services/lifecycle_service.py` — `STATUS_LABELS`, `MANUAL_STATUSES`, `set_manual_status`, `clear_manual_status`
- Исходный код `modules/database.py` — `update_review` сигнатура (file_hash, не id), `get_all_results` паттерн JSON deserialize
- Исходный код `app/state.py` — `AppState` поля, `get_state()`
- Исходный код `app/pages/document.py` — существующий stub
- Исходный код `app/main.py` — `_STATUS_CSS` классы, sub_pages routing, FastAPI pattern
- Исходный код `app/components/registry_table.py` — `_fetch_rows` структура строк
- `.planning/research/PITFALLS.md` — Pitfall 2 (sync DB), Pitfall 6 (large download), Pitfall 7 (Tailwind dynamic)

### Secondary (MEDIUM confidence)
- NiceGUI docs: `ui.expansion` (Quasar QExpansionItem wrapper) — collapsible sections
- NiceGUI docs: `ui.table` slots для custom cell rendering
- FastAPI `Response` с bytes content для inline redline download

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — всё уже в requirements, новых зависимостей нет
- Architecture: HIGH — сервисный слой полностью исследован из исходников
- Pitfalls: HIGH — верифицированы из PITFALLS.md + исходников существующего кода

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (стабильная кодовая база)
