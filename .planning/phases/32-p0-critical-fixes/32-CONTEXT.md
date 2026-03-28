# Phase 32: P0 Critical Fixes - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Устранить 3 критических бага которые ломают базовый вид приложения при первом запуске: шрифты не грузятся, AG Grid выдаёт console warnings, двойные вызовы.

</domain>

<decisions>
## Implementation Decisions

### Шрифты (AUDIT-01)
- **D-01:** Добавить `app.add_static_files("/static", str(_STATIC))` в main.py сразу после объявления `_STATIC` (строка ~87). Файлы уже в `app/static/fonts/`.
- **D-02:** Font-weight 500 для body оставить как есть (IBM Plex Sans Regular подгружается для 400 и 500).

### AG Grid Migration (AUDIT-02)
- **D-03:** Перенести `checkboxSelection: True`, `headerCheckboxSelection: True` из COLUMN_DEFS[0] в gridOptions в `render_registry_table()`.
- **D-04:** Перенести `suppressRowClickSelection: True` из gridOptions в `rowSelection` config per AG Grid 32.2 migration.
- **D-05:** rowSelection должен стать объектом `{"mode": "multiRow", "checkboxes": True, "headerCheckbox": True}` вместо строки `"multiple"`.

### Двойные вызовы (AUDIT-03)
- **D-06:** Удалить дублирующий `await _refresh_deadline_widget()` в registry.py:1205 (оставить только строку 1204).
- **D-07:** Удалить дублирующий вызов в registry.py:1138 (оставить только 1137).

### Claude's Discretion
Все три фикса технические, с очевидным решением. Пользователь делегировал полностью.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### NiceGUI
- `CLAUDE.md` §NiceGUI UI-правила — pitfalls и workarounds для NiceGUI
- `app/main.py:82-115` — текущая загрузка шрифтов и CSS

### AG Grid
- `app/components/registry_table.py:67-145` — текущие COLUMN_DEFS
- `app/components/registry_table.py:392-441` — render_registry_table с gridOptions

### Registry
- `app/pages/registry.py:1203-1205` — двойной вызов _refresh_deadline_widget
- `app/pages/registry.py:1137-1138` — второй двойной вызов

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_STATIC = _Path(__file__).parent / "static"` — уже определён в main.py:87
- AG Grid конфиг: `render_registry_table()` в registry_table.py уже принимает gridOptions dict

### Established Patterns
- Шрифты подключаются через `ui.add_head_html(@font-face)` — shared=True
- AG Grid конфигурация через options dict переданный в `ui.aggrid()`

### Integration Points
- `app.add_static_files()` вызывается на уровне NiceGUI app — в main.py до `ui.run()`
- AG Grid gridOptions — в `render_registry_table()`, registry_table.py

</code_context>

<specifics>
## Specific Ideas

No specific requirements — all three fixes have obvious implementations.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 32-p0-critical-fixes*
*Context gathered: 2026-03-28*
