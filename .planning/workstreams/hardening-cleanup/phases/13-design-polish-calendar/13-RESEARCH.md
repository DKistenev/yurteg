# Phase 13: Design Polish + Calendar — Research

**Researched:** 2026-03-22
**Domain:** NiceGUI CSS injection, Tailwind class migration, FullCalendar.js v6, CSS animations
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Нейтральные — холодные slate/zinc (Tailwind `slate-*`). Лёгкий голубоватый подтон, как Linear/Notion
- **D-02:** Акцентный цвет — индиго (`indigo-600` / `#4f46e5`) для CTA-кнопок и активных элементов
- **D-03:** 60/30/10 правило: white 60% / slate-50 30% / indigo-600 10%
- **D-04:** Статусные цвета остаются семантическими: зелёный (active), жёлтый (expiring), красный (expired), серый (unknown)
- **D-05:** Все нейтральные — tinted: `slate-50`, `slate-100`, `slate-200` для фонов/границ; `slate-600`, `slate-700`, `slate-900` для текста
- **D-06:** Шрифт — IBM Plex Sans (Google Fonts). Хорошая кириллица, профессиональный для юридического продукта
- **D-07:** 2 веса: 400 (normal) для текста, 600 (semibold) для заголовков и CTA
- **D-08:** Modular scale: 12px / 14px / 16px / 20px / 28px
- **D-09:** Загрузка через `ui.add_head_html('<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&subset=cyrillic">')`
- **D-10:** FullCalendar.js интегрирован через `ui.add_head_html` (JS library) + `ui.html` (container)
- **D-11:** Месячный вид по умолчанию
- **D-12:** Два типа событий: даты окончания договоров (indigo), платежи (slate-400)
- **D-13:** Клик по событию → tooltip с инфой + кнопка «Открыть»
- **D-14:** «Открыть» в tooltip → `ui.navigate.to('/document/{id}')`
- **D-15:** Переключатель Список/Календарь — иконка-toggle справа от сегментированного фильтра
- **D-16:** Данные для календаря: `get_calendar_events()` из payment_service + `date_end` из contracts
- **D-17:** Staggered rows — строки реестра появляются каскадом (80ms задержка, cap 8 строк)
- **D-18:** Page transitions — плавный fade (200ms, ease-out) при переключении между страницами
- **D-19:** Hover effects — плавное подсвечивание (150ms ease-out)
- **D-20:** Все анимации через CSS `transform` и `opacity` — не layout properties
- **D-21:** `ease-out-quart` для входных анимаций: `cubic-bezier(0.25, 1, 0.5, 1)`
- **D-22:** Палитра и шрифт применяются глобально через `ui.add_head_html` в `app/main.py`
- **D-23:** Заменить все `bg-gray-*` и `text-gray-*` на `slate-*` эквиваленты по всему `app/`
- **D-24:** Заменить `bg-gray-900` (accent) на `bg-indigo-600` по всему `app/`
- **D-25:** Статусные цвета (green, yellow, red) — НЕ заменять, оставить семантическими

### Claude's Discretion
- FullCalendar.js version и CDN URL
- Exact tooltip component (NiceGUI `ui.menu` vs custom HTML)
- CSS keyframe easing details
- Breakpoint для переключения compact calendar на мобильных (если будет)

### Deferred Ideas (OUT OF SCOPE)
- Dark mode toggle — v2+
- Custom CSS theme file вместо inline — оптимизация, не MVP
- Reduced motion media query — a11y, v2+
- Calendar week/day views — месячный вид достаточен для MVP
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DSGN-01 | Светлая тема с тёплыми нейтральными тонами (без AI slop: no cyan-on-dark, no glassmorphism, no gradient text) | Migration map gray→slate задокументирован в UI-SPEC; 83 usages найдено; `bg-gray-900` x4 (все CTA) → `bg-indigo-600` |
| DSGN-02 | Один акцентный цвет для действий и статусов, палитра по правилу 60-30-10 | Точные hex-значения подтверждены из UI-SPEC; accent применяется только к 4 элементам |
| DSGN-03 | Типографика с чёткой иерархией (display + body font pairing, modular scale) | IBM Plex Sans Google Fonts URL подтверждён; font injection pattern через `ui.add_head_html` установлен в Phase 7 |
| DSGN-04 | Календарь как переключатель вида реестра (FullCalendar.js интеграция) | FullCalendar v6.1.15 jsDelivr CDN; `get_calendar_events()` сигнатура изучена; `calendar_visible` поле нужно добавить в AppState |
| DSGN-05 | Анимации появления элементов (staggered reveals, ease-out-quart) | CSS keyframes для `.ag-row`, `.nicegui-content`; AG Grid не блокирует CSS transitions — подтверждено через UI-SPEC |
</phase_requirements>

---

## Summary

Фаза 13 — финальная полировка UI перед релизом. Два типа изменений: (1) глобальная миграция цветовой палитры и шрифта, (2) additive фича — календарный вид реестра. Никакой новой архитектуры — только CSS-замены и одна новая страница-компонент.

Кодовая база хорошо изучена. Все 83 gray-usages уже пронумерованы в UI-SPEC с точным mapping. `bg-gray-900` встречается ровно 4 раза — все четыре являются CTA-кнопками, все мигрируют в `bg-indigo-600`. `text-gray-900` (заголовки) мигрирует в `text-slate-900`. Различие критически важно — batch-replace сломает продукт.

`get_calendar_events()` в payment_service уже существует, но возвращает цвета по направлению платежа (green/red), а не по схеме Phase 13 (indigo для договоров, slate-400 для платежей). Потребуется либо новая функция, либо адаптация данных при передаче в FullCalendar. Также `AppState` не имеет поля `calendar_visible` — добавить обязательно.

**Primary recommendation:** Разбить на 4 волны: (W0) добавить `calendar_visible` в AppState, (W1) глобальная CSS-инъекция (шрифт + анимации + FullCalendar CDN), (W2) palette migration файл за файлом, (W3) calendar toggle + FullCalendar component.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| NiceGUI | уже установлен | `ui.add_head_html`, `ui.html`, `ui.run_javascript` | Единственный UI-фреймворк в проекте |
| FullCalendar.js | v6.1.15 | Месячный календарь с событиями | v7 — alpha; v6 — стабильная ветка; русская локаль в бандле |
| Google Fonts | CDN | IBM Plex Sans, 400+600, cyrillic | Нет альтернатив — решение зафиксировано в D-06 |
| Tailwind CSS | через NiceGUI | Utility-class palette replacement | Уже используется через `.classes()` везде в проекте |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| jsDelivr CDN | — | Хостинг FullCalendar JS/CSS | Надёжный публичный CDN без auth-барьеров |
| Python `json` | stdlib | Сериализация event-данных для JS | Передача Python-dict → `ui.run_javascript` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom HTML tooltip | NiceGUI `ui.menu` | `ui.menu` требует привязки к DOM-элементу; fixed-position div проще для позиционирования рядом с кликом в FullCalendar |
| FullCalendar v6.1.15 | v7 alpha | v7 меняет API; не стабильна на дату исследования |

**Installation:** Ничего не устанавливается — только CDN-инъекция через `ui.add_head_html`.

---

## Architecture Patterns

### Recommended Project Structure

Изменения вносятся в существующую структуру, новые файлы не добавляются:

```
app/
├── main.py                  ← MODIFY: font + FullCalendar CDN + animations CSS, STATUS_CSS fix
├── state.py                 ← MODIFY: add calendar_visible: bool = False
├── pages/
│   ├── registry.py          ← MODIFY: gray→slate, _SEG_ACTIVE indigo, calendar toggle + component
│   ├── document.py          ← MODIFY: gray→slate in metadata grid and nav
│   ├── settings.py          ← MODIFY: gray→slate, CTA indigo
│   └── templates.py         ← MODIFY: gray→slate, hover transitions
└── components/
    ├── header.py            ← MODIFY: gray→slate, active tab indigo
    ├── registry_table.py    ← VERIFY: no inline gray-* (status CSS in main.py)
    └── onboarding/
        ├── splash.py        ← MODIFY: bg-gray-900 CTAs → indigo, bg-gray-50 → slate-50
        └── tour.py          ← MODIFY: border-gray-200 → slate-200, overlay colors
```

### Pattern 1: Global CSS Injection (шрифт + анимации + FullCalendar)

**What:** Все глобальные стили инъектируются один раз через `ui.add_head_html` на уровне модуля в `app/main.py` — до любого `@ui.page`.

**When to use:** Для стилей, которые должны применяться ко всем страницам (шрифт, анимации, FullCalendar CSS).

**Example:**
```python
# Source: app/main.py — established pattern (Phase 7, Phase 8)
_FONT_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap&subset=cyrillic" rel="stylesheet">
<style>
  * { font-family: 'IBM Plex Sans', sans-serif; }
</style>
"""

_FULLCALENDAR_CSS = """
<link href='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.css' rel='stylesheet' />
<script src='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.js'></script>
"""

_ANIMATION_CSS = """
<style>
@keyframes row-in {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
.ag-row {
  animation: row-in 200ms cubic-bezier(0.25, 1, 0.5, 1) both;
}
.ag-row:nth-child(1)  { animation-delay: 0ms; }
/* ... до :nth-child(8) { animation-delay: 560ms; } */
.ag-row:nth-child(n+9) { animation-delay: 640ms; }

@keyframes page-fade-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}
.nicegui-content {
  animation: page-fade-in 200ms ease-out both;
}
</style>
"""

ui.add_head_html(_FONT_CSS)
ui.add_head_html(_FULLCALENDAR_CSS)
ui.add_head_html(_ANIMATION_CSS)
```

### Pattern 2: FullCalendar инициализация через `ui.run_javascript`

**What:** FullCalendar рендерится в `div#yurteg-calendar`, инициализируется через `ui.run_javascript` после того как контейнер появился в DOM.

**When to use:** Каждый раз когда `calendar_visible` переключается в True.

**Example:**
```python
# Source: 13-UI-SPEC.md FullCalendar Component section
import json

def _init_calendar(events: list[dict]) -> None:
    json_str = json.dumps(events, ensure_ascii=False, default=str)
    ui.run_javascript(f"window.initCalendar({json_str})")
```

```javascript
// Инъектируется через ui.add_head_html — глобальная функция
window.initCalendar = function(events) {
  var el = document.getElementById('yurteg-calendar');
  if (!el) return;
  if (window._cal) { window._cal.destroy(); }
  window._cal = new FullCalendar.Calendar(el, {
    initialView: 'dayGridMonth',
    locale: 'ru',
    headerToolbar: { left: 'prev,next today', center: 'title', right: '' },
    height: 'auto',
    events: events,
    eventClick: function(info) { showCalTooltip(info); },
    buttonText: { today: 'Сегодня' },
    dayMaxEvents: 3,
  });
  window._cal.render();
};
```

### Pattern 3: Palette migration — per-file, не batch replace

**What:** Каждый файл правится вручную по migration map из UI-SPEC. `bg-gray-900` vs `text-gray-900` — разные назначения.

**Critical rule:** `bg-gray-900` (кнопки-CTA) → `bg-indigo-600`. `text-gray-900` (заголовки) → `text-slate-900`. Batch sed/regex сломает это различие.

### Anti-Patterns to Avoid

- **Batch regex replace gray→slate:** Одним проходом нельзя — `bg-gray-900` идёт в `indigo`, `text-gray-900` идёт в `slate-900`. Разные назначения.
- **`ui.run_javascript` до рендера контейнера:** FullCalendar получит `null` для getElementById. Всегда через `ui.timer(0, ...)` или после рендера в async функции.
- **Сохранение `calendar_visible` в module-level переменной:** Состояние должно быть в AppState (per-connection storage). Module-level — shared across всех соединений.
- **Анимировать layout-свойства (width, height, margin):** Только `transform` и `opacity` — иначе jank.
- **Вызывать `window._cal.destroy()` если `_cal` не определён:** Всегда проверять `if (window._cal)` перед destroy.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Месячный календарь | Кастомный grid из div-ов | FullCalendar.js v6 | Рабочие дни, переход месяцев, локализация, перетаскивание — 100+ edge cases |
| Кириллический шрифт | Встроенный в билд | Google Fonts CDN (cyrillic subset) | Уже решено в D-06/D-09; загружается только нужный subset |
| Позиционирование tooltip | `ui.tooltip` или `ui.menu` | Custom `div` с `position: fixed` | AG Grid / FullCalendar overlay конфликтуют с NiceGUI's portal z-index |

---

## Critical Findings from Codebase Scan

### `get_calendar_events()` — несовпадение цветовой схемы

Текущая реализация в `payment_service.py` (строки 147-196) возвращает цвета по **направлению платежа**:
```python
DIRECTION_COLOR = {
    "income":  "#22c55e",   # зелёный
    "expense": "#ef4444",   # красный
}
```

Phase 13 требует **другой схемы**: платежи → `#94a3b8` (slate-400), договорные даты → `#4f46e5` (indigo-600).

**Решение:** При сборке events-массива для FullCalendar в `registry.py` переопределять `color` для payment-событий в `#94a3b8`. Не менять `payment_service.py` — сервис правильный для своих нужд.

### AppState — отсутствует поле `calendar_visible`

В `app/state.py` поля `calendar_visible` нет. Его нужно добавить:
```python
calendar_visible: bool = False
```
Без этого поля переключатель Список/Календарь не сможет хранить состояние per-connection.

### `_SEG_ACTIVE` и `_SEG_INACTIVE` в `registry.py`

```python
_SEG_ACTIVE = "px-4 py-1.5 text-sm font-medium rounded-md bg-gray-900 text-white"
_SEG_INACTIVE = "px-4 py-1.5 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-100"
```

Миграция:
- `bg-gray-900` → `bg-indigo-600`
- `text-gray-600` → `text-slate-600`
- `hover:bg-gray-100` → `hover:bg-slate-100`

### Полный список `bg-gray-900` в кодовой базе (4 штуки, все CTA)

| Файл | Строка | Контекст | Миграция |
|------|--------|---------|---------|
| `app/pages/registry.py` | `_SEG_ACTIVE` | Активный сегмент | → `bg-indigo-600` |
| `app/pages/registry.py` | `_render_empty_state` | CTA «Выбрать папку» | → `bg-indigo-600` |
| `app/components/onboarding/splash.py` | step 1 wizard | «Далее: Telegram» кнопка | → `bg-indigo-600` |
| `app/components/onboarding/splash.py` | step 2 wizard | «Сохранить и начать» кнопка | → `bg-indigo-600` |

### `_ACTIONS_CSS` в `main.py` — hex colours нужна миграция

```python
# Текущие (gray)                        # Новые (slate/indigo)
color: #6b7280   (gray-500)     →       color: #64748b   (slate-500)
color: #111827   (gray-900 hover) →     color: #4f46e5   (indigo-600 hover)
color: #9ca3af   (expand icon)  →       color: #94a3b8   (slate-400)
color: #374151   (expand hover) →       color: #475569   (slate-600)
```

---

## Common Pitfalls

### Pitfall 1: `bg-gray-900` vs `text-gray-900` — разные назначения
**What goes wrong:** Замена всех `gray-900` на `indigo-600` превращает заголовки в индиго вместо тёмного текста.
**Why it happens:** Tailwind использует один стем `gray-900` и для тёмного текста, и для тёмных кнопок.
**How to avoid:** Строго по migration map в UI-SPEC. `bg-gray-900` → `indigo-600`. `text-gray-900` → `slate-900`.
**Warning signs:** Заголовки страниц стали фиолетовыми.

### Pitfall 2: FullCalendar не инициализируется — `getElementById` возвращает null
**What goes wrong:** `ui.run_javascript("initCalendar(...)`)` вызывается до того как `ui.html('<div id="yurteg-calendar"></div>')` отрендерился в DOM.
**Why it happens:** NiceGUI рендерит DOM асинхронно; JS выполняется сразу при вызове.
**How to avoid:** Вызывать `ui.run_javascript` через `ui.timer(0.1, ..., once=True)` после рендера контейнера, или внутри async функции после `await`.
**Warning signs:** Консоль браузера: `Cannot read properties of null (reading 'innerHTML')`.

### Pitfall 3: CSS анимации `@keyframes` на `.ag-row` — не воспроизводятся при перерисовке
**What goes wrong:** Ожидается что stagger-анимация воспроизводится при каждом переключении фильтра.
**Why it happens:** AG Grid переиспользует DOM-узлы при обновлении данных — `animation` не перезапускается.
**How to avoid:** Это ожидаемое поведение (UI-SPEC: «Animation plays only on initial page load»). Не пытаться сделать перезапуск через JS — это усложнение за пределами MVP.
**Warning signs:** Заказчик жалуется что анимация показывается только при первой загрузке.

### Pitfall 4: `ui.add_head_html` — порядок важен для шрифта
**What goes wrong:** FullCalendar CDN загружается раньше шрифта, и `.fc { font-family: ... }` применяется до загрузки шрифта.
**Why it happens:** Браузер применяет font-family немедленно, шрифт подгружается асинхронно.
**How to avoid:** `_FONT_CSS` должен быть первым `add_head_html` вызовом в `main.py`. Всегда добавлять `font-display: swap` в Google Fonts URL.
**Warning signs:** Краткий FOUT (Flash Of Unstyled Text) при первом рендере.

### Pitfall 5: `payment_service.get_calendar_events()` возвращает не ту цветовую схему
**What goes wrong:** Платежные события приходят зелёными (income) или красными (expense) вместо slate-400.
**Why it happens:** Сервис разработан для Streamlit-эры с другой цветовой схемой.
**How to avoid:** В `registry.py` при сборке events-массива переопределить `color` для всех payment-событий в `#94a3b8`. Не менять сам сервис.

### Pitfall 6: AG Grid CSS transition на hover не работает
**What goes wrong:** `.ag-row:hover { background: ... }` работает, но `transition: background-color 150ms` не анимирует.
**Why it happens:** Некоторые версии AG Grid переопределяют inline background через JS `rowStyle`, блокируя CSS transition.
**How to avoid:** Добавить `transition: background-color 150ms ease-out` в `.ag-row` в `_ACTIONS_CSS` в `main.py`. Если не работает — проверить через DevTools какой стиль применяется последним. Fallback: убрать transition (анимация не критична для delivery).

### Pitfall 7: `window.location.href` vs `ui.navigate.to` в tooltip «Открыть»
**What goes wrong:** JS-код в FullCalendar eventClick не может вызвать NiceGUI `ui.navigate.to` напрямую.
**Why it happens:** `ui.navigate.to` — Python-метод, недоступный из чистого JS-контекста.
**How to avoid:** Использовать `window.location.href = '/document/{id}'` в JS-колбэке. NiceGUI перехватит роут через sub_pages.

---

## Code Examples

### Добавление `calendar_visible` в AppState

```python
# Source: app/state.py — добавить в класс AppState
@dataclass
class AppState:
    # ... существующие поля ...

    # Calendar toggle (Phase 13)
    calendar_visible: bool = False
```

### Calendar toggle в registry.py

```python
# Source: 13-UI-SPEC.md — Component 3: Calendar Toggle
# Добавить в build() после блока сегментов

toggle_active = "p-2 rounded-md bg-slate-100 text-slate-700"
toggle_inactive = "p-2 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-50 transition-colors duration-150"

with ui.row().classes("ml-auto items-center gap-1"):
    list_btn = ui.button("≡", on_click=lambda: _switch_view("list")) \
        .props("flat no-caps").classes(toggle_active)
    cal_btn = ui.button("⊞", on_click=lambda: _switch_view("calendar")) \
        .props("flat no-caps").classes(toggle_inactive)
```

### FullCalendar data assembly (с цветовой коррекцией)

```python
# Source: 13-UI-SPEC.md — Data passing section
import json
from nicegui import run, ui
from services.payment_service import get_calendar_events

async def _show_calendar(state, grid_container) -> None:
    db = _client_manager.get_db(state.current_client)

    # Payment events — переопределяем цвет на slate-400
    payment_events = await run.io_bound(get_calendar_events, db)
    for ev in payment_events:
        ev["color"] = "#94a3b8"  # slate-400 — всегда, независимо от direction

    # Contract end-date events — indigo
    contracts = await run.io_bound(db.get_all_results)  # или аналог
    end_events = []
    for c in contracts:
        if c.get("date_end"):
            end_events.append({
                "id": f"contract-{c['id']}",
                "title": f"{c.get('counterparty', '')} · {c.get('contract_type', '')}",
                "start": c["date_end"],
                "color": "#4f46e5",  # indigo-600
                "extendedProps": {
                    "type": "end_date",
                    "contract_id": c["id"],
                    "counterparty": c.get("counterparty"),
                    "doc_type": c.get("contract_type"),
                }
            })

    all_events = payment_events + end_events
    json_str = json.dumps(all_events, ensure_ascii=False, default=str)

    with grid_container:
        ui.html('<div id="yurteg-calendar"></div>').classes("w-full")

    ui.timer(0.1, lambda: ui.run_javascript(f"window.initCalendar({json_str})"), once=True)
```

### Tooltip JS (инъектируется через `ui.add_head_html`)

```javascript
// Source: 13-UI-SPEC.md — Tooltip on event click section
function showCalTooltip(info) {
  var ev = info.event;
  var props = ev.extendedProps || {};
  var tooltip = document.getElementById('cal-tooltip');
  if (!tooltip) return;

  var typeLabel = props.type === 'end_date' ? 'Дата окончания' : 'Платёж';
  var detail = props.type === 'payment'
    ? (props.amount ? props.amount.toLocaleString('ru') + ' ₽' : '')
    : (ev.startStr || '');

  tooltip.innerHTML = `
    <div style="font-size:11px;color:#94a3b8;">${typeLabel}</div>
    <div style="font-size:14px;font-weight:600;color:#0f172a;margin-top:2px;">${props.counterparty || ev.title}</div>
    <div style="font-size:13px;color:#475569;margin-top:2px;">${detail}</div>
    <div style="font-size:13px;color:#4f46e5;font-weight:600;cursor:pointer;margin-top:8px;"
         onclick="window.location.href='/document/${props.contract_id}'">Открыть →</div>
  `;

  var rect = info.el.getBoundingClientRect();
  tooltip.style.display = 'block';
  tooltip.style.top = (rect.bottom + 8) + 'px';
  tooltip.style.left = Math.min(rect.left, window.innerWidth - 280) + 'px';
}

document.addEventListener('click', function(e) {
  var tooltip = document.getElementById('cal-tooltip');
  if (tooltip && !tooltip.contains(e.target)) {
    tooltip.style.display = 'none';
  }
});
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `bg-gray-*` neutral palette | `bg-slate-*` (tinted neutrals) | Phase 13 | Голубоватый подтон вместо нейтрального серого — cohesive с indigo accent |
| `bg-gray-900` для CTA | `bg-indigo-600` | Phase 13 | Явный brand accent вместо безликого тёмно-серого |
| Системный шрифт | IBM Plex Sans | Phase 13 | Профессиональный вид с хорошей кириллицей |
| Только список в реестре | Список + календарь | Phase 13 | Контроль дат окончания без ручного просмотра |

---

## Open Questions

1. **AG Grid hover transition**
   - What we know: CSS `transition` на `.ag-row:hover` должен работать по заявлению UI-SPEC
   - What's unclear: Конкретная версия AG Grid в проекте может переопределять background через JS rowStyle — transition не применится
   - Recommendation: Добавить `transition: background-color 150ms ease-out` в `_ACTIONS_CSS`; проверить в браузере; если не работает — принять без transition (визуально незначительно)

2. **`get_all_results()` как источник для contract end-dates**
   - What we know: Метод существует в Database; возвращает список dict с полем `date_end`
   - What's unclear: Точная сигнатура и возможные None-значения для date_end
   - Recommendation: Использовать `db.get_all_results()` через `run.io_bound`, фильтровать `if c.get("date_end")` перед добавлением в events

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (pytest.ini в корне проекта) |
| Config file | `pytest.ini` + `tests/conftest.py` (добавляет PROJECT_ROOT в sys.path) |
| Quick run command | `pytest tests/test_design_polish.py -x -q` |
| Full suite command | `pytest tests/ -q -m "not slow"` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DSGN-01 | `_STATUS_CSS` содержит `slate-` вместо `gray-` для unknown/terminated | unit | `pytest tests/test_design_polish.py::test_status_css_slate -x` | ❌ Wave 0 |
| DSGN-01 | `_ACTIONS_CSS` содержит slate/indigo hex-значения | unit | `pytest tests/test_design_polish.py::test_actions_css_hex -x` | ❌ Wave 0 |
| DSGN-02 | `_SEG_ACTIVE` содержит `indigo-600`, не `gray-900` | unit | `pytest tests/test_design_polish.py::test_seg_active_indigo -x` | ❌ Wave 0 |
| DSGN-03 | Font link injection присутствует в main.py global CSS | unit | `pytest tests/test_design_polish.py::test_font_injection -x` | ❌ Wave 0 |
| DSGN-04 | `AppState` имеет поле `calendar_visible: bool` | unit | `pytest tests/test_design_polish.py::test_appstate_calendar_visible -x` | ❌ Wave 0 |
| DSGN-04 | `get_calendar_events` возвращает список dict с ключом `color` | unit | `pytest tests/test_design_polish.py::test_calendar_events_color -x` | ❌ Wave 0 |
| DSGN-05 | `_ANIMATION_CSS` содержит `@keyframes row-in` и `page-fade-in` | unit | `pytest tests/test_design_polish.py::test_animation_keyframes -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_design_polish.py -x -q`
- **Per wave merge:** `pytest tests/ -q -m "not slow"`
- **Phase gate:** Full suite green перед `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_design_polish.py` — покрывает DSGN-01 — DSGN-05 (source-level checks, не UI)

Тесты для этой фазы — инспекционные (проверяют строки CSS, классы Python). UI-rendering тесты в NiceGUI требуют браузерного окружения (out of scope для pytest).

---

## Sources

### Primary (HIGH confidence)
- `app/main.py` — текущий `_STATUS_CSS`, `_ACTIONS_CSS`, `ui.add_head_html` pattern
- `app/state.py` — AppState dataclass, отсутствие `calendar_visible`
- `app/pages/registry.py` — `_SEG_ACTIVE`, `_SEG_INACTIVE`, `bg-gray-900` usages
- `app/components/onboarding/splash.py` — `bg-gray-900` CTA кнопки
- `services/payment_service.py` — `get_calendar_events()` сигнатура и цветовая схема
- `.planning/phases/13-design-polish-calendar/13-UI-SPEC.md` — полный migration map, FullCalendar spec
- `.planning/phases/13-design-polish-calendar/13-CONTEXT.md` — все 25 decisions

### Secondary (MEDIUM confidence)
- `pytest.ini` — конфигурация тестов подтверждена
- `tests/conftest.py` — sys.path setup подтверждён

### Tertiary (LOW confidence)
- AG Grid hover CSS transition совместимость — не верифицирована через официальную документацию; UI-SPEC утверждает что работает

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — библиотеки зафиксированы в UI-SPEC, CDN URL явные
- Architecture: HIGH — вся архитектура задокументирована в UI-SPEC; кодовая база полностью изучена
- Palette migration: HIGH — 83 usages подсчитаны; `bg-gray-900` x4 найдены и идентифицированы
- FullCalendar integration: MEDIUM — API взят из UI-SPEC; `ui.run_javascript` interop не верифицирован в реальном рантайме
- AG Grid hover transitions: LOW — поведение предполагается, не подтверждено через DevTools

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (FullCalendar v6 стабилен; Google Fonts URL стабилен)
