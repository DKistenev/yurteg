# Phase 8: Registry View - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Реестр документов показывает реальные данные из SQLite через AG Grid — юрист видит все свои документы, может фильтровать и искать без зависания UI. Клик по строке открывает карточку документа (Phase 9). Переключение клиента меняет набор документов.

</domain>

<decisions>
## Implementation Decisions

### Колонки таблицы
- **D-01:** 4 колонки по умолчанию: Тип документа (`contract_type`), Контрагент (`counterparty`), Статус (computed, цветной бейдж), Сумма (`amount`)
- **D-02:** Скрытые колонки (не показываются по умолчанию): дата окончания, качество AI, имя файла, дата обработки
- **D-03:** Сортировка по умолчанию — по дате обработки (`processed_at`) descending, новейшие сверху

### Сегментированный фильтр
- **D-04:** Три сегмента над таблицей: «Все» · «Истекают ⚠» (с badge-счётчиком) · «Требуют внимания»
- **D-05:** «Истекают» = status `expiring` (через `get_computed_status_sql`)
- **D-06:** «Требуют внимания» = документы с `validation_score < 0.7` ИЛИ с непустыми `validation_warnings`

### Поиск
- **D-07:** Multi-field fuzzy search — каждое слово ищется нечётко по ВСЕМ полям (contract_type, counterparty, subject, filename, amount) через rapidfuzz
- **D-08:** Threshold для fuzzy match — 80% (rapidfuzz уже используется в client_manager с этим порогом)
- **D-09:** Разбивка по словам: «аренда Ромашка» → ищет «аренда» И «Ромашка» по разным полям, обе должны совпасть

### Фильтры по колонкам
- **D-10:** AG Grid column filters — встроенные в заголовки колонок, не отдельные dropdown'ы над таблицей
- **D-11:** Фильтры работают совместно с сегментами и поиском (AND-логика)

### Hover-actions
- **D-12:** При hover на строке появляются: иконка ⋯ (контекстное меню) и иконка быстрой смены статуса
- **D-13:** Контекстное меню ⋯: Открыть, Скачать оригинал, Переобработать, Удалить
- **D-14:** Быстрый статус — dropdown с MANUAL_STATUSES из lifecycle_service, применяется через `set_manual_status`

### Версии документов
- **D-15:** Вложенные строки с раскрытием ▶/▼ — допсоглашения под основным договором с отступом
- **D-16:** По умолчанию свёрнуто (▶). Клик раскрывает дочерние версии
- **D-17:** Группировка через `version_service.get_version_group()` — уже реализовано

### Клик по строке
- **D-18:** Клик по строке → `ui.navigate.to(f'/document/{doc_id}')` — full-page карточка (Phase 9)
- **D-19:** Клик по иконкам hover-actions НЕ триггерит навигацию (stopPropagation)

### Переключение клиента
- **D-20:** Иконка профиля 👤▾ в header → dropdown список клиентов + «Добавить клиента» внизу
- **D-21:** При переключении — таблица мгновенно перезагружается данными нового клиента, фильтры сбрасываются, остаёмся на странице реестра
- **D-22:** `ClientManager.list_clients()` для списка, `ClientManager.get_db(name)` для получения БД

### Статус-бейджи
- **D-23:** Цвета из `STATUS_LABELS` в lifecycle_service (зелёный/жёлтый/красный/серый)
- **D-24:** Tailwind literal classes (не dynamic) — lookup dict по статусу, как описано в PITFALLS.md

### Claude's Discretion
- Точные Tailwind классы для бейджей и hover-actions
- AG Grid columnDefs конфигурация (ширина, flex, sortable, filter type)
- Debounce interval для fuzzy search
- UI для «Добавить клиента» (inline input или dialog)
- Пагинация / virtual scroll при >200 документах

</decisions>

<specifics>
## Specific Ideas

- Таблица должна выглядеть как Linear/Notion — чистая, утилитарная, без декораций
- Hover-actions появляются плавно, не скачком
- Сегментированный фильтр — как Apple segmented control (не табы, не кнопки)
- Поиск должен быть полем ввода над таблицей или в header, всегда видимым
- При пустом результате поиска — «Ничего не найдено. Попробуйте другой запрос» + кнопка сброса

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### NiceGUI components
- `.planning/research/ARCHITECTURE.md` §Pattern 5 — ui.aggrid wrapper, columnDefs, rowClicked handler
- `.planning/research/STACK.md` — NiceGUI v3.9.0 AG Grid API, `.classes()` styling

### Pitfalls
- `.planning/research/PITFALLS.md` §Pitfall 2 — sync SQLite blocking (run.io_bound for all DB calls)
- `.planning/research/PITFALLS.md` §Pitfall 7 — Tailwind dynamic classes (use literal lookup dict)

### Existing services
- `services/lifecycle_service.py` — `get_computed_status_sql()`, `STATUS_LABELS`, `set_manual_status()`, `MANUAL_STATUSES`
- `services/version_service.py` — `get_version_group()` for version grouping
- `services/client_manager.py` — `list_clients()`, `get_db()`, `add_client()`
- `modules/database.py` — `get_all_results()` returns list[dict] with 20+ fields

### Phase 7 artifacts
- `app/state.py` — AppState with `filter_type`, `filter_status`, `filter_search`, `current_client`, `selected_doc_id`
- `app/pages/registry.py` — stub with `build()` to be implemented
- `app/components/header.py` — persistent header with profile placeholder

### Design skills
- `/arrange` — table layout, spacing, visual rhythm
- `/typeset` — column hierarchy, font weights
- `/harden` — edge cases, overflow, empty results

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Database.get_all_results()` — returns all contracts as list[dict], ordered by processed_at
- `get_computed_status_sql(warning_days)` — SQL CASE fragment for status computation
- `STATUS_LABELS` — dict with emoji, Russian label, hex color per status
- `MANUAL_STATUSES` — list of valid manual status values
- `rapidfuzz` — already in requirements.txt, used in `client_manager.find_client_by_counterparty`
- `get_version_group(db, doc_id)` — returns version chain for a document

### Established Patterns
- `run.io_bound()` — established in Phase 7 for all DB calls from UI
- `get_state()` — AppState accessor from app.storage.client
- `ui.navigate.to()` — SPA navigation without page reload
- Tailwind literal class lookup — `STATUS_COLORS = {'active': 'bg-green-50 text-green-700', ...}`

### Integration Points
- `app/pages/registry.py` — stub ready, imports `get_state` from `app.state`
- `app/components/header.py` — profile indicator placeholder → wire to ClientManager dropdown
- `app/main.py` — sub_pages already routes `/` to `registry.build`

</code_context>

<deferred>
## Deferred Ideas

- Кнопка «+ Загрузить документы» в реестре — Phase 10 (Pipeline Wiring)
- Переключатель вида Список/Календарь — Phase 13 (Design Polish + Calendar)
- Excel-экспорт реестра — Phase 10 (Pipeline Wiring) или Phase 11
- Empty state при пустом реестре — Phase 12 (Onboarding)

</deferred>

---

*Phase: 08-registry-view*
*Context gathered: 2026-03-22*
