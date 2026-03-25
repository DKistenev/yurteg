# Phase 24: Registry UI Polish - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning
**Source:** PRD Express Path (docs/superpowers/specs/2026-03-25-ui-polish-registry-document-design.md)

<domain>
## Phase Boundary

Переработать визуал реестра по утверждённым мокапам. 5 requirements: REG-01..05.

</domain>

<decisions>
## Implementation Decisions

### Таблица реестра
- Убрать колонку «Уверенность» из COLUMN_DEFS в registry_table.py — обновить html_columns indices
- Оставить колонки: ☐, Тип, Контрагент, Предмет, Статус, Сумма

### Bulk actions toolbar
- Убрать кнопку «Экспорт в Excel» из bulk_actions.py
- Оставить: «Изменить статус», «Удалить», «Снять выбор»
- Шрифт кнопок = IBM Plex Sans (font-family: inherit), не системный
- Стиль: border border-slate-200, rounded-md, text-slate-600, font-size 12px

### Pagination footer
- Русифицировать: «Page Size:» → убрать или заменить на «Размер:»
- AG Grid localeText для русификации всех строк пагинации

### Боковая панель (Linear-style)
- Заголовок: контрагент крупным (15px, font-weight 600) + кнопка ✕
- Тег-бейдж: тип документа как indigo метка (10px, bg-eef2ff, color-4f46e5, rounded-4px)
- Секции с мини-заголовками uppercase (10px, color-94a3b8, letter-spacing 0.06em): ДОКУМЕНТ, СРОКИ, ФИНАНСЫ
- Статус badge в секции «Документ»
- Даты в 2-колоночном grid
- Сумма: 20px, font-weight 700, в отдельной секции
- Кнопка «Открыть карточку →» внизу (border, rounded-8px, text-475569)
- Labels БЕЗ КАПСА (обычный регистр)

### Календарь (таймлайн + мини-календарь)
- Слева: лента событий, группированная по времени (Сегодня → Эта неделя → Месяц)
- Карточки событий с цветными полосками: красная = окончание, синяя = платёж, жёлтая = скоро истекает
- На карточке: тип, контрагент, предмет, сумма справа, дата
- Справа (220px): мини-календарь с цветными точками на датах + сводка (количество + сумма платежей)
- Клик по карточке → карточка документа

### Claude's Discretion
- AG Grid localeText конкретные ключи для русификации
- Реализация мини-календаря (NiceGUI ui.html или отдельный компонент)
- Переключение реестр ↔ календарь через существующие сегменты

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design Spec
- `docs/superpowers/specs/2026-03-25-ui-polish-registry-document-design.md` — полная спецификация всех изменений

### Visual Mockups (ОБЯЗАТЕЛЬНО ПРОЧИТАТЬ)
- `.superpowers/brainstorm/99248-1774442361/registry-redesign.html` — варианты реестра (выбран B)
- `.superpowers/brainstorm/99248-1774442361/side-panel-v2.html` — варианты панели (выбран C: Linear)
- `.superpowers/brainstorm/99248-1774442361/calendar-redesign.html` — варианты календаря (выбран B: таймлайн)

### Current Code
- `app/pages/registry.py` — реестр, split panel, calendar view
- `app/components/registry_table.py` — COLUMN_DEFS, AG Grid config
- `app/components/bulk_actions.py` — bulk toolbar
- `app/components/split_panel.py` — боковая панель
- `app/styles.py` — стили
- `app/static/tokens.css` — CSS переменные
- `app/static/design-system.css` — анимации и overrides

</canonical_refs>

<specifics>
## Specific Ideas

Пользователь подчеркнул: мокапы — обязательный референс. «Чтобы не получился мем ожидание/реальность.» Визуал должен точно соответствовать утверждённым мокапам.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
