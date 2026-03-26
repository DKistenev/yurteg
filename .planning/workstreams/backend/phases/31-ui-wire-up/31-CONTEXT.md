# Phase 31: UI Wire-up - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning
**Mode:** Auto-generated (wiring phase — discuss skipped)

<domain>
## Phase Boundary

Все backend-функции, реализованные в фазах 28-30, доступны из UI: открытие файла, bulk delete, дедлайны, шаблоны.

Requirements: WIRE-01, WIRE-02, WIRE-03, WIRE-04

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All wiring decisions at Claude's discretion. Key constraints from ROADMAP success criteria:

- WIRE-01: «Открыть файл» открывает PDF/DOCX в системном приложении (subprocess open/startfile/xdg-open)
  - Кнопка в карточке документа (document.py)
  - Нужен path из DB + platform detection

- WIRE-02: Bulk delete убирает документы из реестра и БД без следов после обновления
  - bulk_actions.py уже имеет диалог, нужен реальный handler
  - db.delete_contract(id) + refresh AG Grid

- WIRE-03: Виджет дедлайнов показывает результат get_attention_required()
  - lifecycle_service.get_attention_required() уже работает
  - Нужен UI-виджет в registry.py (например, amber badge или expandable list)

- WIRE-04: «Сохранить как шаблон» вызывает backend и показывает подтверждение
  - review_service.mark_contract_as_template() теперь сохраняет full_text + embedding
  - Кнопка в карточке документа (document.py) + notification

</decisions>

<code_context>
## Existing Code Insights

- app/pages/document.py — карточка документа, кнопки действий
- app/pages/registry.py — реестр, trust banner placeholder, calendar
- app/components/bulk_actions.py — bulk dialog, handler stub
- services/lifecycle_service.py — get_attention_required() ready
- services/review_service.py — mark_contract_as_template() ready
- modules/database.py — delete methods exist

</code_context>

<specifics>
## Specific Ideas

None beyond success criteria.

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>
