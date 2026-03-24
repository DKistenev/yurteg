# Phase 21: UI Fixes - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase, discuss skipped)

<domain>
## Phase Boundary

Починить все сломанные кнопки и элементы интерфейса. 6 requirement-ов:
- UIFIX-01: db.get_contract(doc_id) → db.get_contract_by_id(doc_id) в registry.py:917 и bulk_actions.py:62
- UIFIX-02: Реализовать /download/{doc_id} route в app/main.py ИЛИ убрать кнопку «Скачать PDF»
- UIFIX-03: Кнопка «Переобработать» должна запускать pipeline для конкретного документа
- UIFIX-04: settings.py сохраняет "warning_days_threshold" но main.py читает "warning_days" — унифицировать ключ
- UIFIX-05: bulk_actions.py:117-118 STATUS_LABELS значения — кортежи (icon, label, color), нужно извлечь только label
- UIFIX-06: 30+ except Exception: без логирования в app/pages/ — добавить logger.exception() + logging.basicConfig() в entry points

Audit reference: .planning/AUDIT-2026-03-25.md

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure bugfix phase. Key constraints from audit:

- UIFIX-02: Предпочтительно реализовать route /download/{doc_id} — отдать оригинальный файл по original_path из БД. Если original_path не существует — вернуть 404 с понятным сообщением.
- UIFIX-03: «Переобработать» = вызвать pipeline для одного файла. Использовать существующий controller.process_single() или аналог. Показать прогресс в UI.
- UIFIX-06: Не менять логику except — только добавить logging. Использовать logger = logging.getLogger(__name__) в каждом файле.
- app/pages/document.py имеет 2 кнопки «Проверить по шаблону» — action_review_btn (мёртвая) и review_btn (рабочая). Убрать мёртвую action_review_btn.

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- `app/pages/registry.py` — реестр, split panel click handler line ~917
- `app/pages/document.py` — карточка документа, action bar lines 228-237
- `app/pages/settings.py` — настройки, save_setting line 366
- `app/components/bulk_actions.py` — массовые действия, STATUS_LABELS line 117
- `app/main.py` — entry point, routes, warning_days read line 157
- `modules/database.py` — get_contract_by_id() method

### Established Patterns
- NiceGUI routing via @ui.page decorators
- FastAPI routes added via app.add_api_route() in main.py
- logging.getLogger(__name__) pattern used in modules/

</code_context>

<specifics>
## Specific Ideas

No specific requirements — standard bugfix work.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
