# Phase 10: Pipeline Wiring - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Юрист выбирает папку с документами через нативный file picker и видит прогресс обработки в реальном времени. Новые документы появляются в реестре автоматически после завершения. Ошибки видны в логе, не останавливают обработку остальных файлов.

</domain>

<decisions>
## Implementation Decisions

### Upload button placement
- **D-01:** Кнопка «+ Загрузить» в persistent header приложения, рядом с табами, перед иконкой профиля
- **D-02:** Кнопка видна с любой страницы (header persistent), не только на реестре

### File picker
- **D-03:** Нативный OS file picker через `app.native.main_window.create_file_dialog` (не `ui.upload` — pitfall #5)
- **D-04:** Выбор папки (не отдельных файлов) — юрист выбирает директорию с документами
- **D-05:** Pipeline получает `Path` объекты напрямую — совместимо с `scanner.py` и `controller.py`

### Progress display
- **D-06:** Прогресс отображается inline над таблицей реестра (не полноэкранный режим)
- **D-07:** Прогресс-бар + текст «3/12 файлов» + имя текущего файла
- **D-08:** Таблица реестра остаётся доступной во время обработки — юрист может просматривать уже обработанные документы
- **D-09:** `on_progress(current, total, message)` callback через `loop.call_soon_threadsafe` для обновления UI из thread pool

### After completion
- **D-10:** Toast-уведомление «Обработано 12 документов (2 ошибки)» — через `ui.notify`
- **D-11:** Таблица реестра автоматически обновляется (`load_table_data`) — новые строки появляются без ручного действия
- **D-12:** Прогресс-бар скрывается после завершения

### Error display
- **D-13:** Ошибочные файлы отмечены ✗ красным в логе прогресса (рядом с прогресс-баром)
- **D-14:** Клик по ошибке показывает причину (expand или tooltip)
- **D-15:** Ошибка одного файла не останавливает обработку остальных (уже реализовано в controller)

### Async pipeline
- **D-16:** `await run.io_bound(pipeline_service.process_archive, ...)` — не блокирует event loop
- **D-17:** `on_file_done` callback добавляет результат в state и обновляет таблицу инкрементально

### Claude's Discretion
- Exact CSS для прогресс-секции
- Debounce для progress UI updates (не чаще 500ms)
- Spinner animation во время обработки
- Disable/enable логика кнопки «+ Загрузить» во время обработки
- Excel-экспорт кнопка (если время позволяет)

</decisions>

<specifics>
## Specific Ideas

- Прогресс должен быть ненавязчивым — тонкая полоска над таблицей, не огромный блок
- После завершения — лог ошибок остаётся видимым 10 секунд, потом сворачивается
- Кнопка «+ Загрузить» неактивна во время обработки (disabled state)
- При обработке 1-3 файлов прогресс-бар не нужен — достаточно спиннера

</specifics>

<canonical_refs>
## Canonical References

### Pipeline services
- `services/pipeline_service.py` — `process_archive(source_dir, config, on_progress, on_file_done)` — main entry point
- `controller.py` — `Controller.process_archive()` — orchestrates per-file processing, error isolation
- `.planning/research/ARCHITECTURE.md` §Pattern 4 — blocking pipeline in background thread, progress callbacks

### Pitfalls
- `.planning/research/PITFALLS.md` §Pitfall 5 — `ui.upload` gives no path, use native picker
- `.planning/research/PITFALLS.md` §Pitfall 2 — sync blocking, use `run.io_bound`

### Phase 7-8 artifacts
- `app/components/header.py` — persistent header, add upload button here
- `app/pages/registry.py` — add progress section above table
- `app/components/registry_table.py` — `load_table_data()` for refreshing after processing

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pipeline_service.process_archive()` — accepts `on_progress` and `on_file_done` callbacks, returns stats dict
- `controller.process_archive()` — handles per-file error isolation, ThreadPoolExecutor
- `Config()` — all processing config (provider, anonymization settings)
- `load_table_data()` in `registry_table.py` — refreshes AG Grid with current data

### Established Patterns
- `run.io_bound()` for all blocking calls
- `loop.call_soon_threadsafe()` for UI updates from background threads
- `ui.notify()` for toast messages
- `get_state()` for AppState access

### Integration Points
- `app/components/header.py` — add «+ Загрузить» button
- `app/pages/registry.py` — add progress section (conditionally visible)
- `app/components/process.py` — new component (placeholder from research architecture)

</code_context>

<deferred>
## Deferred Ideas

- Drag-and-drop загрузка — NiceGUI `ui.upload` ограничен, v2+
- Excel-экспорт реестра — может быть добавлен как FastAPI route, но не в scope PROC requirements
- Повторная обработка отдельных файлов — через контекстное меню в реестре (Phase 8 placeholder)

</deferred>

---

*Phase: 10-pipeline-wiring*
*Context gathered: 2026-03-22*
