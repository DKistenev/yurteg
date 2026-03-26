# Phase 9: Document Detail Card - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Full-page карточка документа: юрист видит все метаданные, может запустить AI-ревью, посмотреть версии с diff, оставить заметку — не возвращаясь в реестр. Навигация prev/next между документами. Кнопка «← Назад к реестру».

</domain>

<decisions>
## Implementation Decisions

### Page layout
- **D-01:** Одна колонка с секциями (не 2-колоночный grid). Сверху вниз: header → метаданные grid → статус → пометки → ревью → версии
- **D-02:** Header карточки: «← Назад к реестру» слева, название документа (contract_type) по центру, кнопки ◀ ▶ (prev/next) справа
- **D-03:** Prev/next переключают `doc_id` в URL через `ui.navigate.to` без возврата в реестр

### Metadata fields
- **D-04:** 7 полей в structured grid: Тип, Контрагент, Предмет (subject), Дата начала, Дата окончания, Сумма, Особые условия (special_conditions как bulleted list)
- **D-05:** Стороны (parties) и технические поля (filename, model_used, processed_at, validation_score) — НЕ показываются

### Status section
- **D-06:** Статус отображается с цветным бейджем (из STATUS_LABELS) + кнопка «Изменить» → dropdown с MANUAL_STATUSES
- **D-07:** «Сбросить» рядом с dropdown — вызывает `clear_manual_status`, возвращает к автоматическому статусу

### Lawyer notes
- **D-08:** Одно текстовое поле (`lawyer_comment`), автосохранение на blur через `database.update_review`
- **D-09:** Без статуса ревью (reviewed/pending) — минимализм. Статус управляется через manual_status

### AI review
- **D-10:** Сворачиваемая секция «Ревью». Кнопка «Проверить по шаблону»
- **D-11:** При клике — автоподбор шаблона через `match_template()`. Если нет подходящего — dropdown для ручного выбора из `list_templates()`
- **D-12:** Ревью запускается через `run.io_bound(review_against_template, ...)` — async, не блокирует UI
- **D-13:** Результат — список отступлений с цветовыми метками: зелёный (добавлено), красный (удалено), жёлтый (изменено). Текст шаблона vs текст документа для каждого отступления
- **D-14:** Если нет шаблонов — сообщение «Нет шаблонов. Добавьте в разделе Шаблоны» с ссылкой

### Version history
- **D-15:** Сворачиваемая секция «Версии». По умолчанию свёрнута
- **D-16:** Список версий из `get_version_group()` — каждая строка: номер версии, метод привязки, дата
- **D-17:** Кнопка «Сравнить» рядом с каждой версией — показывает результат `diff_versions()` inline: таблица полей с пометками changed/unchanged
- **D-18:** Кнопка «Скачать redline» — вызывает `generate_redline_docx()`, скачивается .docx через FastAPI FileResponse (не ui.download — pitfall #6)

### Navigation
- **D-19:** `← Назад к реестру` → `ui.navigate.to('/')` — возвращает на реестр
- **D-20:** Prev/next: нужен список doc_ids из текущего отфильтрованного реестра в AppState. Навигация: `ui.navigate.to(f'/document/{prev_id}')`

### Database
- **D-21:** Нужен новый метод `Database.get_contract_by_id(contract_id: int) -> dict` — сейчас нет, нужно добавить

### Claude's Discretion
- Exact grid layout for metadata (Tailwind classes, gap, columns)
- Spinner/loading state during AI review
- Scroll position restore on back navigation
- Placeholder text for empty lawyer_comment
- Keyboard shortcuts for prev/next (если просто)

</decisions>

<specifics>
## Specific Ideas

- Карточка должна выглядеть как Notion page — чистая, спокойная, content-first
- Особые условия — bulleted list, не JSON dump
- Diff метаданных — простая таблица: поле | старое | новое | изменено?
- Цветовые метки отступлений — не яркие блоки, а тонкие полоски слева (как в GitHub diff)
- Пометки юриста — textarea с placeholder «Добавьте заметку...», 3-4 строки высоты

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Services for document card
- `services/version_service.py` — `get_version_group()`, `diff_versions()`, `generate_redline_docx()`
- `services/review_service.py` — `match_template()`, `review_against_template()`, `list_templates()`
- `services/lifecycle_service.py` — `set_manual_status()`, `clear_manual_status()`, `STATUS_LABELS`, `MANUAL_STATUSES`
- `modules/database.py` — `get_all_results()`, `update_review()` — ⚠ need to add `get_contract_by_id()`

### Phase 7-8 artifacts
- `app/state.py` — AppState.selected_doc_id, AppState.current_client
- `app/pages/document.py` — current stub with `build(doc_id)` signature
- `app/main.py` — sub_pages routes `/document/{doc_id}`
- `app/components/registry_table.py` — `_fetch_rows()` returns filtered list of doc dicts (for prev/next list)

### Pitfalls
- `.planning/research/PITFALLS.md` §Pitfall 2 — run.io_bound for DB calls
- `.planning/research/PITFALLS.md` §Pitfall 6 — large download via FastAPI FileResponse, not ui.download

### Design skills
- `/arrange` — card layout, section spacing
- `/typeset` — metadata label hierarchy
- `/clarify` — microcopy for empty states, button labels

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `STATUS_LABELS` dict — emoji + label + hex for status badges (same as registry)
- `MANUAL_STATUSES` — frozenset for dropdown options
- `_STATUS_CSS` in `app/main.py` — already defines Tailwind @layer for status badges
- `review_against_template()` returns `[{"type": "added"|"removed"|"changed", "template_text", "document_text", "color"}]`
- `diff_versions()` returns `[{"field", "old", "new", "changed": bool}]`
- `generate_redline_docx()` returns bytes — ready for FileResponse

### Established Patterns
- `run.io_bound()` for all DB and AI calls
- `ui.navigate.to()` for SPA navigation
- `get_state()` for AppState access
- FastAPI FileResponse for large file downloads (from PITFALLS.md)

### Integration Points
- `app/pages/document.py` — stub ready, receives `doc_id` as URL param
- `app/main.py` — already has route `/document/{doc_id}` in sub_pages
- `modules/database.py` — needs `get_contract_by_id()` method added

</code_context>

<deferred>
## Deferred Ideas

- Полнотекстовый просмотр документа (PDF/DOCX viewer) — v2+
- Таблица сравнения двух версий side-by-side — v2+ (сейчас inline diff)
- Теги/метки на документах — не в scope v0.6
- Экспорт карточки в PDF — v2+

</deferred>

---

*Phase: 09-document-detail-card*
*Context gathered: 2026-03-22*
