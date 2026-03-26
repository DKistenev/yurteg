# Phase 10: Pipeline Wiring - Research

**Researched:** 2026-03-22
**Domain:** NiceGUI async pipeline integration — native file picker, run.io_bound, loop.call_soon_threadsafe, progress UI
**Confidence:** HIGH (codebase analyzed directly, patterns established in Phases 7-9, PITFALLS.md and ARCHITECTURE.md consulted)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Upload button placement**
- D-01: Кнопка «+ Загрузить» в persistent header, рядом с табами, перед иконкой профиля
- D-02: Кнопка видна с любой страницы

**File picker**
- D-03: Нативный OS file picker через `app.native.main_window.create_file_dialog` (не `ui.upload`)
- D-04: Выбор папки (не отдельных файлов) — диалог открытия директории
- D-05: Pipeline получает `Path` объекты напрямую

**Progress display**
- D-06: Прогресс inline над таблицей реестра (не полноэкранный)
- D-07: Прогресс-бар + текст «3/12 файлов» + имя текущего файла
- D-08: Таблица остаётся доступной во время обработки
- D-09: `on_progress(current, total, message)` callback через `loop.call_soon_threadsafe`

**After completion**
- D-10: Toast «Обработано 12 документов (2 ошибки)» через `ui.notify`
- D-11: Таблица реестра автоматически обновляется (`load_table_data`)
- D-12: Прогресс-бар скрывается после завершения

**Error display**
- D-13: Ошибочные файлы отмечены ✗ красным в логе прогресса
- D-14: Клик по ошибке показывает причину (expand или tooltip)
- D-15: Ошибка одного файла не останавливает обработку остальных

**Async pipeline**
- D-16: `await run.io_bound(pipeline_service.process_archive, ...)` — не блокирует event loop
- D-17: `on_file_done` callback добавляет результат в state и обновляет таблицу инкрементально

### Claude's Discretion
- Exact CSS для прогресс-секции
- Debounce для progress UI updates (не чаще 500ms)
- Spinner animation во время обработки
- Disable/enable логика кнопки «+ Загрузить» во время обработки
- Excel-экспорт кнопка (если время позволяет)

### Deferred Ideas (OUT OF SCOPE)
- Drag-and-drop загрузка — NiceGUI `ui.upload` ограничен, v2+
- Excel-экспорт реестра — может быть FastAPI route, но не в scope PROC
- Повторная обработка отдельных файлов — через контекстное меню в реестре (Phase 8 placeholder)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PROC-01 | Загрузка файлов через нативный file picker (поддержка выбора папки) | D-03/D-04: `app.native.main_window.create_file_dialog` с webkitdirectory / dialog mode |
| PROC-02 | Pipeline обработки запускается async через `run.io_bound()` | D-16: `await run.io_bound(pipeline_service.process_archive, ...)` + loop.call_soon_threadsafe для callbacks |
| PROC-03 | Прогресс обработки отображается в реальном времени (прогресс-бар + лог файлов) | D-06–D-09, D-13–D-14: `ui.linear_progress` + error log list, inline в registry.py над таблицей |
| PROC-04 | После обработки новые документы автоматически появляются в реестре | D-10–D-12, D-17: `on_file_done` + `load_table_data` + `ui.notify` toast |
</phase_requirements>

---

## Summary

Phase 10 подключает уже готовый пайплайн (`pipeline_service.process_archive`) к уже готовому UI (header + registry). Вся бизнес-логика реализована; задача — написать тонкий «клей» из трёх частей:

1. **Кнопка в header** — открывает нативный folder picker, передаёт `Path` в обработчик.
2. **Прогресс-секция в registry** — `ui.linear_progress` + счётчик + лог ошибок, появляется при старте обработки, скрывается после завершения.
3. **Async wiring** — `run.io_bound` для запуска пайплайна в thread pool, `loop.call_soon_threadsafe` для обновления UI из callback-потока.

Ключевое ограничение: callbacks из `controller.py` вызываются из `ThreadPoolExecutor` — напрямую трогать NiceGUI UI-объекты из них нельзя. Всё через `loop.call_soon_threadsafe`.

**Primary recommendation:** Создать `app/components/process.py` — единственный новый файл. Кнопку добавить в `header.py`, прогресс-секцию в `registry.py` над таблицей.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `nicegui` | already installed | `ui.linear_progress`, `ui.notify`, `run.io_bound`, `app.native.main_window` | Единственный UI-фреймворк проекта |
| `asyncio` | stdlib | `get_event_loop()`, `call_soon_threadsafe` | Нужен для thread-safe UI updates из callback |
| `pipeline_service` | local | `process_archive(source_dir, config, on_progress, on_file_done)` | Уже реализован, принимает все нужные callbacks |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `config.Config` | local | Конфиг для pipeline (provider, анонимизация) | Передаётся в `process_archive` |
| `app.components.registry_table.load_table_data` | local | Обновление AG Grid после обработки | После завершения каждого файла (D-17) |
| `app.state.get_state` | local | Доступ к `AppState.processing` | Для disable/enable кнопки |

**Installation:** Ничего нового не устанавливается — всё уже есть.

---

## Architecture Patterns

### Recommended Component Structure

```
app/
├── components/
│   ├── header.py           # + кнопка «+ Загрузить» (D-01) — редактируется
│   └── process.py          # НОВЫЙ: folder picker + async pipeline runner
├── pages/
│   └── registry.py         # + прогресс-секция над таблицей (D-06) — редактируется
```

### Pattern 1: Нативный folder picker

**Что:** `app.native.main_window.create_file_dialog` — метод pywebview, доступный только в `native=True` режиме.

**Важно:** Для выбора папки используется `webview.FOLDER_DIALOG` constant. Возвращает `list[str] | None` (пути как строки). Если юрист отменил — `None`.

**Пример:**
```python
# Source: PITFALLS.md §Pitfall 5 + NiceGUI docs
import webview
from pathlib import Path
from nicegui import app

async def pick_folder() -> Path | None:
    result = await app.native.main_window.create_file_dialog(
        dialog_type=webview.FOLDER_DIALOG,
    )
    if result:
        return Path(result[0])
    return None
```

**Критично:** `create_file_dialog` — это корутина в NiceGUI native mode, её нужно `await`. Не вызывать в sync-функции.

### Pattern 2: Blocking pipeline в thread pool с thread-safe UI updates

**Что:** `run.io_bound` запускает синхронный `process_archive` в executor. Callbacks из пайплайна приходят из другого потока — NiceGUI UI-объекты thread-unsafe. Используем `loop.call_soon_threadsafe` для безопасных обновлений.

**Пример (из ARCHITECTURE.md §Pattern 4, адаптирован):**
```python
# Source: .planning/research/ARCHITECTURE.md §Pattern 4
import asyncio
from nicegui import run, ui
from config import Config
from pathlib import Path
import services.pipeline_service as pipeline_service

async def run_pipeline(source_dir: Path, state, grid, grid_state):
    loop = asyncio.get_event_loop()
    config = Config()

    # UI refs — захвачены в closure
    # progress_bar, count_label, file_label определены снаружи

    def on_progress(current: int, total: int, message: str):
        val = current / total if total > 0 else 0
        loop.call_soon_threadsafe(progress_bar.set_value, val)
        loop.call_soon_threadsafe(
            count_label.set_text,
            f"{current}/{total} файлов"
        )
        loop.call_soon_threadsafe(file_label.set_text, message)

    def on_file_done(result):
        if result.status == "error":
            # добавить ошибку в лог
            loop.call_soon_threadsafe(
                _add_error_entry, result.file_info.filename, result.error_message
            )
        # инкрементальное обновление таблицы
        loop.call_soon_threadsafe(
            asyncio.ensure_future,
            load_table_data(grid, state, grid_state["segment"])
        )

    stats = await run.io_bound(
        pipeline_service.process_archive,
        source_dir,
        config,
        on_progress=on_progress,
        on_file_done=on_file_done,
    )
    return stats
```

**Важно для `on_file_done` + async:** `load_table_data` — это `async def`. Из `call_soon_threadsafe` нельзя напрямую `await`. Используй `asyncio.ensure_future(coro)` внутри `call_soon_threadsafe`, или упрости: обновляй таблицу только по завершении всего пайплайна (D-11), не на каждый файл.

**Рекомендация (Claude's discretion):** Инкрементальное обновление таблицы на каждый файл — сложно и создаёт WebSocket flood при больших архивах (PITFALLS.md Performance Traps). Лучше: прогресс показывает файлы через `loop.call_soon_threadsafe`, а `load_table_data` вызывается один раз после завершения `await run.io_bound(...)`.

### Pattern 3: Прогресс-секция как условно-видимая область

**Что:** Секция прогресса в `registry.py` над таблицей. Скрыта по умолчанию (`visible=False`), показывается при старте, скрывается после завершения (D-12).

**Пример:**
```python
# В registry.py — над grid_container
progress_section = ui.column().classes("w-full px-6 py-3 gap-2")
progress_section.set_visibility(False)

with progress_section:
    with ui.row().classes("items-center gap-3 w-full"):
        progress_bar = ui.linear_progress(value=0).classes("flex-1")
        count_label = ui.label("0/0 файлов").classes("text-sm text-gray-500 shrink-0")
    file_label = ui.label("").classes("text-xs text-gray-400")
    error_log = ui.column().classes("gap-1")  # список ошибок
```

**Ключевые точки:**
- `progress_section.set_visibility(True)` при старте обработки
- `progress_section.set_visibility(False)` после завершения (с задержкой 10с если есть ошибки — D specifics)
- Кнопка «+ Загрузить» в header: `.set_enabled(False)` при `state.processing = True`

### Pattern 4: Передача UI-объектов между header и registry

**Проблема:** Кнопка «+ Загрузить» в `header.py`, прогресс-секция в `registry.py`. Как связать?

**Решение:** `process.py` — отдельный модуль с функцией `start_processing(source_dir, state, ui_refs)`. `header.py` вызывает picker и передаёт `Path` в `process.py`. `registry.py` создаёт ui_refs и регистрирует их в `state` (или передаёт через closure).

**Конкретно для Phase 10:** Использовать `AppState` как канал — добавить поля `processing_ui` или пробросить `grid_ref` и `progress_ref` через `state`. Проще: кнопка в header пишет `source_dir` в state и вызывает callback, зарегистрированный в `registry.py` при его инициализации.

**Рекомендация:** Хранить `grid_ref` в модульном dict в `registry.py` (уже есть паттерн `grid_ref = {"grid": None}`). Добавить `progress_ref = {"section": None, "bar": None, "count": None, "file": None, "errors": None}`. Кнопка в header получает callback через `state` или через аргумент `render_header(state, on_upload=...)`.

### Anti-Patterns to Avoid

- **Вызов `load_table_data` из on_file_done через `call_soon_threadsafe`** — создаёт флуд WebSocket-сообщений при 20+ файлах. Обновлять таблицу только после завершения.
- **Прямой вызов `.set_value()` на UI-объекте из `on_progress` без `call_soon_threadsafe`** — race condition, UI-объекты не thread-safe в NiceGUI.
- **`ui.upload` вместо native picker** — не даёт Path (Pitfall 5).
- **`asyncio.get_event_loop()` без сохранения в переменную** — в Python 3.10+ в async-контексте всегда использовать `asyncio.get_event_loop()` до запуска thread-pool задачи, или `asyncio.get_running_loop()`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Folder picker диалог | Кастомный input с вводом пути | `app.native.main_window.create_file_dialog(dialog_type=webview.FOLDER_DIALOG)` | Нативный OS диалог, Path возвращается напрямую |
| Thread-safe UI update | Очередь + polling timer | `loop.call_soon_threadsafe(fn, args)` | Именно для этого сделан — безопасно, без полинга |
| Async wrapper для sync pipeline | Кастомный ThreadPoolExecutor | `await run.io_bound(fn, *args)` | NiceGUI pattern, уже установлен в проекте |
| Toast notification | Кастомный overlay div | `ui.notify(text, type='positive')` | Уже используется в проекте (header.py, registry.py) |
| Progress bar | `ui.html` с CSS | `ui.linear_progress(value=0)` | Встроенный NiceGUI компонент |

---

## Common Pitfalls

### Pitfall 1: `create_file_dialog` возвращает None при отмене

**What goes wrong:** Юрист нажал «Отмена» в диалоге. `result` равен `None`. Код пробует сделать `Path(result[0])` → `TypeError`.

**How to avoid:** Всегда проверять `if result:` перед использованием.

```python
result = await app.native.main_window.create_file_dialog(dialog_type=webview.FOLDER_DIALOG)
if not result:
    return  # юрист отменил — ничего не делать
source_dir = Path(result[0])
```

### Pitfall 2: `on_progress` вызывается из thread pool — нельзя трогать UI напрямую

**What goes wrong:** `progress_bar.set_value(0.5)` внутри `on_progress` callback → silently fails или race condition.

**How to avoid:** Всегда `loop.call_soon_threadsafe(progress_bar.set_value, val)`. Захватить `loop = asyncio.get_event_loop()` ДО запуска `run.io_bound`.

### Pitfall 3: `load_table_data` — async из sync context

**What goes wrong:** `loop.call_soon_threadsafe(load_table_data, grid, state, segment)` — не работает, `load_table_data` — корутина, не callable.

**How to avoid:** Два варианта:
1. Не вызывать `load_table_data` из `on_file_done`. Вызвать один раз после `await run.io_bound(...)` завершился — это нормальный async context.
2. Если нужен инкрементальный update: `loop.call_soon_threadsafe(asyncio.ensure_future, load_table_data(grid, state, segment))`.

**Рекомендация: вариант 1** (проще, нет flood).

### Pitfall 4: `state.processing = True` не блокирует повторный клик автоматически

**What goes wrong:** Кнопка остаётся кликабельной пока обрабатывается архив. Юрист кликает снова — запускается второй пайплайн параллельно, два процесса пишут в одну БД.

**How to avoid:** Явно `.set_enabled(False)` на кнопке + `state.processing = True`. После завершения — обратно.

### Pitfall 5: `asyncio.get_event_loop()` deprecated warning в Python 3.10+

**What goes wrong:** В async-функции `get_event_loop()` выдаёт DeprecationWarning в Python 3.12+.

**How to avoid:** Использовать `asyncio.get_running_loop()` внутри async-функции (это точно текущий loop). `get_event_loop()` — только если есть сомнения в контексте.

---

## Code Examples

### Folder picker — полный рабочий паттерн

```python
# Source: PITFALLS.md §Pitfall 5 + NiceGUI native docs
import webview
from nicegui import app

async def pick_folder() -> "Path | None":
    from pathlib import Path
    result = await app.native.main_window.create_file_dialog(
        dialog_type=webview.FOLDER_DIALOG,
    )
    if not result:
        return None
    return Path(result[0])
```

### Pipeline runner — полный паттерн с callbacks

```python
# Source: .planning/research/ARCHITECTURE.md §Pattern 4
import asyncio
from nicegui import run, ui
from config import Config
import services.pipeline_service as pipeline_service
from pathlib import Path

async def start_pipeline(source_dir: Path, state, grid, grid_state, ui_refs: dict):
    """
    ui_refs: {
        'section': ui.column,    # прогресс-секция
        'bar': ui.linear_progress,
        'count': ui.label,
        'file_label': ui.label,
        'error_col': ui.column,
        'upload_btn': ui.button,
    }
    """
    loop = asyncio.get_running_loop()
    config = Config()
    error_entries = []

    state.processing = True
    ui_refs['upload_btn'].set_enabled(False)
    ui_refs['section'].set_visibility(True)
    ui_refs['bar'].set_value(0)

    def on_progress(current: int, total: int, message: str):
        val = current / total if total > 0 else 0
        loop.call_soon_threadsafe(ui_refs['bar'].set_value, val)
        loop.call_soon_threadsafe(
            ui_refs['count'].set_text, f"{current}/{total} файлов"
        )
        loop.call_soon_threadsafe(ui_refs['file_label'].set_text, message)

    def on_file_done(result):
        if result.status == "error":
            error_entries.append((result.file_info.filename, result.error_message))

    stats = await run.io_bound(
        pipeline_service.process_archive,
        source_dir,
        config,
        on_progress=on_progress,
        on_file_done=on_file_done,
    )

    # После завершения — обновить таблицу и показать toast
    await load_table_data(grid, state, grid_state["segment"])

    done = stats.get("done", 0)
    errors = stats.get("errors", 0)
    msg = f"Обработано {done} документов"
    if errors:
        msg += f" ({errors} ошибки)"
    ui.notify(msg, type="positive" if not errors else "warning")

    # Рендер ошибок в лог
    _render_error_log(ui_refs['error_col'], error_entries)

    # Скрыть прогресс — сразу если нет ошибок, через 10с если есть
    if not error_entries:
        ui_refs['section'].set_visibility(False)
    else:
        ui.timer(10, lambda: ui_refs['section'].set_visibility(False), once=True)

    state.processing = False
    ui_refs['upload_btn'].set_enabled(True)


def _render_error_log(error_col, error_entries: list):
    """Рендерит список ошибок под прогресс-баром."""
    error_col.clear()
    with error_col:
        for filename, message in error_entries:
            with ui.expansion(f"✗ {filename}").classes("text-red-600 text-sm"):
                ui.label(message).classes("text-xs text-gray-500 pl-4")
```

### Кнопка в header — интеграция

```python
# В render_header — добавить перед правым блоком с профилем
async def _on_upload_click():
    source_dir = await pick_folder()
    if source_dir and state.on_upload_callback:
        await state.on_upload_callback(source_dir)

ui.button(
    "+ Загрузить",
    on_click=_on_upload_click,
).props("flat no-caps").classes("text-sm text-gray-700")
```

**Альтернатива:** `render_header(state, on_upload=callback)` — передавать callback как аргумент, не хранить в state. Чище с точки зрения типизации.

---

## State Changes Required

`AppState` нужно расширить (или использовать без расширения через callback-аргумент):

```python
# Добавить в AppState (app/state.py)
processing: bool = False  # уже есть
# Опционально: on_upload_callback — но лучше передавать через аргумент render_header
```

`AppState.processing` уже есть — достаточно. Новых полей не нужно.

---

## Integration Surface

| Файл | Изменение | Что добавляется |
|------|-----------|-----------------|
| `app/components/process.py` | НОВЫЙ | `pick_folder()`, `start_pipeline(...)`, `_render_error_log(...)` |
| `app/components/header.py` | РЕДАКТИРУЕТСЯ | + кнопка «+ Загрузить» с async `pick_folder()` |
| `app/pages/registry.py` | РЕДАКТИРУЕТСЯ | + `progress_section` с `progress_bar`, `count_label`, `file_label`, `error_col` над `grid_container` |
| `app/state.py` | НЕ МЕНЯЕТСЯ | `processing: bool` уже есть |
| `services/pipeline_service.py` | НЕ МЕНЯЕТСЯ | `process_archive` уже принимает все нужные callbacks |
| `controller.py` | НЕ МЕНЯЕТСЯ | `on_progress` и `on_file_done` уже вызываются |

---

## Common Pitfalls (ссылки из PITFALLS.md)

| Pitfall | Относится к Phase 10 | Как избежать |
|---------|---------------------|--------------|
| Pitfall 2: Sync blocking в event loop | Прямой вызов `process_archive()` без `run.io_bound` | `await run.io_bound(pipeline_service.process_archive, ...)` |
| Pitfall 5: `ui.upload` не даёт Path | Ошибка выбора file picker API | `app.native.main_window.create_file_dialog(FOLDER_DIALOG)` |
| Pitfall 9: `app.storage.user` в wrong context | Хранение progress state в storage | Хранить ссылки на UI-объекты в closure, не в storage |
| Performance Trap: flood WebSocket updates | `load_table_data` на каждый файл | Обновлять таблицу только после завершения |

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (существующий) |
| Config file | `tests/` directory |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROC-01 | Folder picker открывает диалог и возвращает Path | manual-only | — | N/A |
| PROC-02 | `run.io_bound` вызывается, pipeline не блокирует event loop | unit (mock) | `pytest tests/test_process.py -x` | ❌ Wave 0 |
| PROC-03 | `on_progress` callback обновляет UI через `call_soon_threadsafe` | unit (mock loop) | `pytest tests/test_process.py::test_on_progress -x` | ❌ Wave 0 |
| PROC-04 | После `process_archive` таблица обновляется, toast показан | integration (mock pipeline) | `pytest tests/test_process.py::test_completion -x` | ❌ Wave 0 |

**PROC-01 — manual-only:** `create_file_dialog` требует pywebview GUI окна, не тестируется в headless CI.

### Wave 0 Gaps
- [ ] `tests/test_process.py` — unit tests для `start_pipeline` с mock `pipeline_service.process_archive` и mock event loop

---

## Open Questions

1. **`render_header` signature — callback vs state**
   - Что знаем: header.py вызывается из `app/main.py` через `render_header(state)`. Добавить `on_upload` аргумент чище (нет mutable callback в dataclass), но требует изменения сигнатуры во всех вызовах.
   - Что неясно: Есть ли другие места вызова кроме `app/main.py`? По коду — нет.
   - Рекомендация: изменить на `render_header(state, on_upload=None)` — явно и типобезопасно.

2. **Инкрементальное обновление таблицы vs только по завершении**
   - Что знаем: D-17 говорит «обновляет таблицу инкрементально». PITFALLS говорит — flood WebSocket при 20+ файлах.
   - Рекомендация (Claude's discretion): Обновлять по завершении всего `await run.io_bound(...)`. Прогресс-бар даёт достаточно обратной связи во время обработки.

3. **Debounce для progress updates**
   - CONTEXT.md: «debounce не чаще 500ms» в Claude's Discretion.
   - Реализация: хранить `last_update_time` в closure, в `on_progress` проверять `time.monotonic() - last_update > 0.5` перед вызовом `call_soon_threadsafe`. Или использовать `ui.timer` для polling state dict вместо прямого push.

---

## Sources

### Primary (HIGH confidence)
- `/yurteg/services/pipeline_service.py` — `process_archive(source_dir, config, on_progress, on_file_done)` — сигнатура проверена напрямую
- `/yurteg/controller.py` — логика `_notify(on_progress, ...)` и вызов `on_file_done(result)` проверены напрямую
- `/yurteg/app/components/header.py` — место вставки кнопки, `render_header(state)` сигнатура
- `/yurteg/app/pages/registry.py` — место вставки прогресс-секции, `grid_ref` паттерн
- `/yurteg/.planning/research/ARCHITECTURE.md §Pattern 4` — проверенный паттерн blocking pipeline
- `/yurteg/.planning/research/PITFALLS.md §Pitfall 5` — `ui.upload` vs native picker

### Secondary (MEDIUM confidence)
- NiceGUI `app.native.main_window.create_file_dialog` — паттерн из PITFALLS.md (Pitfall 5), ссылается на официальное pywebview API

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — все библиотеки уже в проекте
- Architecture: HIGH — паттерны установлены в ARCHITECTURE.md и реализованы в Phases 7-9
- Integration surface: HIGH — все файлы прочитаны напрямую
- `create_file_dialog` exact API: MEDIUM — проверен через PITFALLS.md, не через официальный NiceGUI docs напрямую

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (NiceGUI API стабилен, изменения маловероятны)
