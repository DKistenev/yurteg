# Phase 11: Settings + Templates - Research

**Researched:** 2026-03-22
**Domain:** NiceGUI forms, settings persistence, template CRUD UI
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Left nav + правая панель (macOS System Preferences pattern). Левая колонка — навигация между секциями, правая — содержимое выбранной секции
- **D-02:** Три секции в left nav: AI, Обработка, Telegram
- **D-03:** Сохранение на blur (не глобальная кнопка Save) — через `~/.yurteg/settings.json`
- **D-04:** Radio buttons для провайдера: Локальный (Qwen) / ZAI GLM-4.7 / OpenRouter
- **D-05:** Поле API-ключа (password input) — показывается только для ZAI и OpenRouter
- **D-06:** При переключении провайдера — немедленное сохранение через `config.active_provider`
- **D-07:** Чекбоксы анонимизации — какие сущности маскировать (ФИО, адреса, телефоны, ИНН и т.д.)
- **D-08:** Числовое поле `warning_days` — за сколько дней предупреждать об истечении (default: 30)
- **D-09:** Поле для токена бота
- **D-10:** Статус подключения: ✓ Подключён / ✗ Не подключён (через `telegram_sync.check_connection`)
- **D-11:** Кнопка «Проверить подключение» — тестирует соединение и обновляет статус
- **D-12:** Таб «Шаблоны» — отдельная страница верхнего уровня
- **D-13:** Список шаблонов в формате карточек: название, тип документа, превью текста (3 строки), дата добавления
- **D-14:** Кнопка «+ Добавить шаблон» → нативный file picker (PDF/DOCX) → ввести название + выбрать тип документа → текст извлекается автоматически через `extractor.py`
- **D-15:** Действия на карточке: Редактировать (название, тип), Удалить (с подтверждением)
- **D-16:** Привязка шаблона к типу документа — dropdown с типами из существующих контрактов
- **D-17:** Client switching уже реализовано в Phase 8 (header dropdown). SETT-05 — считается выполненным

### Claude's Discretion
- Exact Tailwind classes для left nav
- Порядок чекбоксов анонимизации
- Placeholder текст для API-ключа
- Размер карточек шаблонов
- Подтверждение удаления — dialog или inline

### Deferred Ideas (OUT OF SCOPE)
- Логи обработки (история запусков) — v2+
- Backup/restore настроек — v2+
- Импорт шаблонов из библиотеки — v2+
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TMPL-01 | Отдельный таб «Шаблоны» верхнего уровня | Stub уже в `app/pages/templates.py` и роут `/templates` в `app/main.py`; нужно только заполнить `build()` |
| TMPL-02 | Список шаблонов с операциями создания, редактирования и удаления | `review_service.add_template()`, `list_templates()`, `delete_template()` (soft delete через `is_active=0`), `update_template()` — всё есть; нужен UI-слой |
| TMPL-03 | Привязка шаблона к типу документа | `Template.contract_type` поле в БД; типы берутся из `Config.document_types_hints` (150+ типов) |
| SETT-01 | Отдельная страница «Настройки» с группировкой по секциям | Stub в `app/pages/settings.py`; макет — left nav + right panel через `ui.splitter` или `ui.row` |
| SETT-02 | Переключение AI-провайдера с сохранением на blur | `config.active_provider` + `_save_settings()` паттерн из `main.py`; нужно перенести в settings page |
| SETT-03 | Настройка анонимизации (выбор сущностей для маскировки) | `ENTITY_TYPES` из `anonymizer.py` — 9 ключей; `config.anonymize_types` уже в `Config`; сохранение через settings.json |
| SETT-04 | Настройка Telegram-бота (привязка, статус подключения) | `TelegramSync.is_configured()` как check; `telegram_server_url` + `telegram_chat_id` в `Config`; кнопка «Проверить» через `run.io_bound()` |
| SETT-05 | Переключение клиента | Реализовано в Phase 8 (header dropdown). ЗАКРЫТ |
</phase_requirements>

## Summary

Phase 11 — это чисто UI-фаза. Вся бизнес-логика (шаблоны, настройки, Telegram) уже реализована в сервисном слое. Задача: написать два `build()` — `settings.py` и `templates.py` — используя существующие паттерны NiceGUI из Phase 8-10.

Ключевая сложность — settings page: имитация macOS Preferences (left nav + right panel) на NiceGUI без готового компонента. Решение — `ui.row` + selected section state + conditional rendering. Для шаблонов — native file picker (уже есть паттерн в `pick_folder()`) + `run.io_bound()` для `extract_text()`.

**Главная опасность:** `Config()` создаёт новый экземпляр при каждом вызове — настройки надо читать из `settings.json` через `_load_settings()` и писать через `_save_settings()`, а НЕ через `Config()` напрямую (иначе изменения не переживут перезапуск). Этот паттерн уже реализован в `main.py` строки 629-661, его нужно перенести/переиспользовать в `app/pages/settings.py`.

**Primary recommendation:** Перенести `_load_settings`/`_save_settings` в `config.py` как методы класса или утилиты, чтобы обе страницы (старый `main.py` и новый `settings.py`) использовали один и тот же механизм.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| nicegui | уже в проекте | UI компоненты — `ui.row`, `ui.column`, `ui.input`, `ui.checkbox`, `ui.radio`, `ui.dialog` | Весь проект на NiceGUI |
| nicegui `run.io_bound` | уже в проекте | Блокирующие вызовы (extract_text, check_connection) без блокировки event loop | Паттерн всего проекта, FUND-03 |
| webview (через NiceGUI) | уже в проекте | Нативный file picker для выбора файла шаблона | Используется в `pick_folder()` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `modules/extractor.py` | локальный | Извлечение текста из PDF/DOCX для шаблонов | При добавлении шаблона |
| `services/review_service.py` | локальный | CRUD шаблонов | Во всех операциях templates |
| `services/telegram_sync.py` | локальный | Проверка Telegram подключения | В секции Telegram settings |
| `modules/anonymizer.ENTITY_TYPES` | локальный | Список типов ПД для чекбоксов | В секции Обработка |

### Alternatives Considered
Нет — стек фиксирован решениями.

## Architecture Patterns

### Recommended Project Structure
```
app/pages/
├── settings.py      # build() — macOS Preferences layout, 3 секции
└── templates.py     # build() — карточки шаблонов, add/edit/delete
```

Никаких новых файлов не нужно — только заполнить существующие stubs.

### Pattern 1: Left Nav + Right Panel (macOS Preferences)

**What:** Левая колонка с кнопками-секциями, правая — dynamic content пустым контейнером с `.clear()` + перерисовкой.

**When to use:** D-01, D-02, SETT-01

**Example:**
```python
def build() -> None:
    _settings = _load_settings()
    selected: list[str] = ["AI"]  # mutable container для замыкания

    with ui.row().classes("w-full h-full gap-0"):
        # Left nav
        with ui.column().classes("w-48 border-r border-gray-200 p-4 gap-1 bg-gray-50"):
            for section in ["AI", "Обработка", "Telegram"]:
                ui.button(section, on_click=lambda s=section: _switch(s)).props("flat no-caps align-left").classes("w-full text-left text-sm")

        # Right panel
        content = ui.column().classes("flex-1 p-8 gap-6")

    def _switch(section: str) -> None:
        selected[0] = section
        content.clear()
        with content:
            _render_section(section, _settings)

    _switch("AI")  # default
```

**Pitfall:** `content.clear()` + перерисовка работает в NiceGUI — это стандартный паттерн dynamic content. НЕ использовать `ui.tabs` — они рендерят все секции сразу и добавляют Quasar-стиль, не macOS Preferences.

### Pattern 2: Save on Blur

**What:** `ui.input` с `on_change` или `:blur` — немедленное сохранение без кнопки.

**When to use:** D-03, D-05, D-08, D-09

**Example:**
```python
# NiceGUI: on_change вызывается при каждом нажатии клавиши — это слишком часто.
# Правильный подход для blur — событие on_value_change с debounce или
# явный bind с сохранением в on_blur через .on('blur', ...)
api_key_input = ui.input(
    label="API-ключ",
    password=True,
    value=_settings.get("api_key_zai", ""),
).on("blur", lambda e: _save_key(e.sender.value))
```

**Критично:** `ui.input.on("blur", callback)` — рабочий способ в NiceGUI. Callback принимает `CustomEventArguments`, значение через `e.sender.value`.

### Pattern 3: Native File Picker (Single File)

**What:** Адаптация `pick_folder()` для выбора одного файла PDF/DOCX.

**When to use:** D-14 — кнопка «+ Добавить шаблон»

**Example:**
```python
async def pick_file() -> Optional[Path]:
    """Нативный file picker — один файл PDF/DOCX."""
    result = await app.native.main_window.create_file_dialog(
        dialog_type=webview.OPEN_DIALOG,
        file_types=("PDF файлы (*.pdf)", "Word документы (*.docx)"),
    )
    if not result:
        return None
    return Path(result[0])
```

`webview.OPEN_DIALOG` (не `FOLDER_DIALOG`) для выбора одного файла. `file_types` — tuple строк в формате pywebview.

### Pattern 4: Template Card Grid

**What:** Responsive grid карточек через Tailwind `grid grid-cols-2 gap-4` (или 3 на широком экране).

**When to use:** D-13 — список шаблонов

**Example:**
```python
with ui.grid(columns=2).classes("w-full gap-4"):
    for tmpl in templates:
        with ui.card().classes("p-4 cursor-pointer hover:shadow-md transition-shadow"):
            ui.label(tmpl.name).classes("font-semibold text-gray-900 text-sm")
            ui.label(tmpl.contract_type).classes("text-xs text-gray-500 mt-0.5")
            preview = (tmpl.content_text or "")[:200]
            ui.label(preview).classes("text-xs text-gray-400 mt-2 line-clamp-3")
            ui.label(tmpl.created_at or "").classes("text-xs text-gray-300 mt-2")
            # Action row
            with ui.row().classes("gap-2 mt-3 justify-end"):
                ui.button("Изменить", on_click=lambda t=tmpl: _edit_dialog(t)).props("flat no-caps size=sm")
                ui.button("Удалить", on_click=lambda t=tmpl: _delete_confirm(t)).props("flat no-caps size=sm color=negative")
```

**Pitfall:** `line-clamp-3` — Tailwind utility, работает в NiceGUI браузере (Chromium). Требует `overflow-hidden` на том же элементе. Без `overflow-hidden` text обрежется но без "...".

### Pattern 5: Delete Confirmation Dialog

**What:** `ui.dialog()` с подтверждением перед soft-delete.

**When to use:** D-15 — действие «Удалить» на карточке

**Example:**
```python
def _delete_confirm(tmpl: Template, card_col) -> None:
    with ui.dialog() as dlg, ui.card().classes("p-6 gap-4"):
        ui.label(f"Удалить шаблон «{tmpl.name}»?").classes("text-sm text-gray-700")
        with ui.row().classes("gap-2 justify-end"):
            ui.button("Отмена", on_click=dlg.close).props("flat no-caps")
            async def _confirm():
                await run.io_bound(_do_delete, tmpl.id)
                dlg.close()
                card_col.clear()
                _render_template_list(card_col)
            ui.button("Удалить", on_click=_confirm).props("flat no-caps color=negative")
    dlg.open()
```

### Pattern 6: Provider Radio Buttons + Conditional API Key

**What:** Radio group для провайдера, условный показ поля API-ключа.

**When to use:** D-04, D-05, D-06

**Example:**
```python
provider_radio = ui.radio(
    {"ollama": "Локальный (Qwen)", "zai": "ZAI GLM-4.7", "openrouter": "OpenRouter"},
    value=_settings.get("active_provider", "ollama"),
    on_change=lambda e: _on_provider_change(e.value, api_key_row),
).props("dense")

with ui.row().classes("gap-4 items-center") as api_key_row:
    ui.input(label="API-ключ", password=True, ...).on("blur", _save_api_key)

def _on_provider_change(provider: str, api_key_row) -> None:
    api_key_row.set_visibility(provider != "ollama")
    _save_setting("active_provider", provider)
    # Также обновить config в памяти если нужно немедленный эффект
```

### Pattern 7: Settings Persistence (Centralized)

**What:** `_load_settings()` / `_save_settings()` работают с `~/.yurteg/settings.json`. Логика уже написана в `main.py` строки 629-654.

**Critical finding:** `Config()` — dataclass без persistence! Каждый `Config()` создаёт свежий экземпляр с дефолтами. Единственный persistent store — `settings.json`. В `main.py` (Streamlit) это был модуль-уровень; в NiceGUI `app/pages/settings.py` нужно либо:
1. Вызвать те же `_load_settings`/`_save_settings` (скопировать/вынести в utils)
2. Или вынести в `config.py` как статические методы `Config.load()` / `Config.save()`

**Рекомендация:** Вынести в `config.py` — единственное место где есть смысл держать логику персистирования Config.

**Ключи settings.json которые уже используются:**
- `active_provider` — str ("ollama"|"zai"|"openrouter")
- `telegram_server_url` — str
- `telegram_chat_id` — int

**Новые ключи для Phase 11:**
- `api_key_zai` — str (пароль)
- `api_key_openrouter` — str (пароль)
- `anonymize_types` — list[str] (ключи из ENTITY_TYPES)
- `warning_days` — int

### Pattern 8: Template Add Flow

**What:** Кнопка → file picker → dialog с именем+типом → extract_text → add_template.

**When to use:** D-14

**Flow:**
```python
async def _add_template_flow(card_col) -> None:
    path = await pick_file()  # нативный picker
    if not path:
        return

    # Модальный диалог — имя + тип документа
    with ui.dialog() as dlg, ui.card().classes("p-6 min-w-80 gap-4"):
        ui.label("Добавить шаблон").classes("text-base font-medium")
        name_input = ui.input("Название шаблона", value=path.stem).props("outlined dense")
        type_select = ui.select(
            Config().document_types_hints,  # 150+ типов из config
            label="Тип документа",
        ).props("outlined dense use-input")

        async def _confirm():
            name = name_input.value.strip()
            doc_type = type_select.value or "Прочее"
            if not name:
                return
            # extract_text требует FileInfo
            from modules.models import FileInfo
            fi = FileInfo(path=path, filename=path.name, extension=path.suffix.lower())
            extracted = await run.io_bound(extractor.extract_text, fi)
            cm = ClientManager()
            db = cm.get_db(state.current_client)
            await run.io_bound(review_service.add_template, db, doc_type, name, extracted.text, str(path))
            dlg.close()
            card_col.clear()
            _render_template_list(card_col, state)

        with ui.row().classes("gap-2 justify-end"):
            ui.button("Отмена", on_click=dlg.close).props("flat no-caps")
            ui.button("Добавить", on_click=_confirm).props("flat no-caps color=primary")
    dlg.open()
```

### Pattern 9: Telegram Check Connection

**What:** Кнопка проверки → `run.io_bound` → обновить UI-статус dot.

**When to use:** D-10, D-11

**Ключевой факт:** `TelegramSync` НЕ имеет `check_connection()` метода (CONTEXT.md упоминает его, но в коде его нет). Есть `is_configured()` — проверяет только наличие URL и chat_id (не реальное соединение). Реальная проверка — попробовать HTTP-запрос к серверу.

```python
async def _check_telegram(status_label) -> None:
    url = server_url_input.value.strip()
    tg = TelegramSync(server_url=url, chat_id=0)
    try:
        # Реальная проверка: GET /health или /api/bind с пустым кодом
        import httpx
        r = httpx.get(f"{url.rstrip('/')}/health", timeout=5)
        connected = r.status_code < 400
    except Exception:
        connected = False
    if connected:
        status_label.set_text("● Подключён").classes("text-green-600 text-sm")
    else:
        status_label.set_text("● Не подключён").classes("text-red-500 text-sm")
```

### Anti-Patterns to Avoid

- **`ui.tabs` для Settings nav:** Quasar tabs рендерят всё сразу, добавляют таб-стиль — не macOS Preferences. Использовать `ui.button` + `content.clear()`.
- **`Config()` как persistent store:** `Config()` создаёт новый экземпляр. Персистируется только через `settings.json`.
- **`ui.input on_change` для blur:** `on_change` срабатывает на каждую букву. Нужен `.on("blur", cb)`.
- **Блокирующий `extract_text` без `run.io_bound`:** PDF-парсинг блокирует event loop — всегда через `run.io_bound`.
- **`pick_file()` без проверки `if not result`:** pywebview возвращает `None` при отмене — всегда проверять.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Список типов документов | Хардкодить или подтягивать из БД | `Config().document_types_hints` | 150+ типов уже в config.py |
| Сущности анонимизации | Дублировать | `anonymizer.ENTITY_TYPES` | Единственный source of truth |
| Файловый picker | `tkinter.filedialog` | `app.native.main_window.create_file_dialog` | Нативный для OS, паттерн из Phase 10 |
| Persistence настроек | Новый формат / SQLite | `~/.yurteg/settings.json` через `_load_settings`/`_save_settings` | Уже используется с Phase 5 |
| Template CRUD | Прямые SQL-запросы | `review_service.add_template`, `list_templates`, `delete_template` | Готовый слой с локами |
| Text extraction | Новая логика | `modules/extractor.extract_text(FileInfo)` | pdfplumber + python-docx, отлажен |

**Key insight:** Phase 11 — почти чисто UI-фаза. Каждая функция бизнес-логики уже написана и протестирована. Задача — правильно связать UI с существующим кодом.

## Common Pitfalls

### Pitfall 1: `delete_template` — функция не существует в review_service
**What goes wrong:** CONTEXT.md упоминает `delete_template()`, но в `review_service.py` её нет. Есть только `add_template`, `mark_contract_as_template`, `list_templates`, `match_template`, `review_against_template`.
**Why it happens:** CONTEXT.md описывал желаемый интерфейс, не существующий код.
**How to avoid:** Добавить `delete_template(db, template_id)` в `review_service.py` как soft delete (`UPDATE templates SET is_active=0 WHERE id=?`). Аналогично `update_template(db, template_id, name, contract_type)`.

### Pitfall 2: `check_connection()` отсутствует в TelegramSync
**What goes wrong:** D-10 требует `telegram_sync.check_connection()`, но метода нет.
**Why it happens:** Планировалось, не реализовано.
**How to avoid:** Реализовать проверку через HTTP GET к `/health` или использовать `is_configured()` + реальный запрос inline в settings page.

### Pitfall 3: `Config()` — не singleton
**What goes wrong:** `Config().active_provider = "zai"` изменяет экземпляр, который тут же уходит в garbage collection.
**Why it happens:** `Config` — обычный dataclass, не singleton.
**How to avoid:** Читать из `settings.json` напрямую, писать туда же. НЕ рассчитывать на изменение `Config()` instance как persistent store.

### Pitfall 4: `extract_text` принимает `FileInfo`, не `Path`
**What goes wrong:** `extractor.extract_text(path)` вызывает `TypeError`.
**Why it happens:** Сигнатура: `extract_text(file_info: FileInfo) -> ExtractedText`. `FileInfo` — dataclass с `path`, `filename`, `extension`.
**How to avoid:**
```python
from modules.models import FileInfo
fi = FileInfo(path=path, filename=path.name, extension=path.suffix.lower())
result = await run.io_bound(extractor.extract_text, fi)
```

### Pitfall 5: `content.clear()` вызывает re-render без context manager
**What goes wrong:** После `content.clear()` новые элементы нужно добавлять через `with content:`.
**Why it happens:** NiceGUI требует явного context для добавления дочерних элементов.
**How to avoid:** Всегда `content.clear(); with content: _render_section(...)`.

### Pitfall 6: `file_types` в pywebview — tuple строк, не list
**What goes wrong:** `create_file_dialog(file_types=["*.pdf"])` — может не фильтровать на всех ОС.
**Why it happens:** pywebview ожидает tuple строк в формате "Описание (*.ext)".
**How to avoid:** `file_types=("PDF файлы (*.pdf)", "Word документы (*.docx)", "Все файлы (*.*)")`.

### Pitfall 7: Left nav активная секция не подсвечивается
**What goes wrong:** Все кнопки nav выглядят одинаково, нет visual feedback текущей секции.
**Why it happens:** NiceGUI кнопки не имеют "active" состояния автоматически.
**How to avoid:** Хранить текущую секцию, обновлять классы кнопок при переключении. Паттерн: dict nav_buttons, менять `.classes()` при `_switch()`.

## Code Examples

### Получить DB для текущего клиента
```python
# Паттерн из Phase 8-10 — всегда через ClientManager
from services.client_manager import ClientManager
cm = ClientManager()
db = cm.get_db(state.current_client)
```

### Добавить/удалить шаблон (через review_service)
```python
# Добавить
template_id = review_service.add_template(
    db, contract_type="Договор аренды", name="Эталон аренды",
    content_text=extracted.text, original_path=str(path)
)

# Soft delete (нужно добавить функцию в review_service)
# db.conn.execute("UPDATE templates SET is_active=0 WHERE id=?", (template_id,))
# db.conn.commit()

# Редактировать (нужно добавить функцию в review_service)
# db.conn.execute("UPDATE templates SET name=?, contract_type=? WHERE id=?", ...)
```

### Читать/писать settings.json
```python
import json
from pathlib import Path

_SETTINGS_FILE = Path.home() / ".yurteg" / "settings.json"

def _load_settings() -> dict:
    try:
        if _SETTINGS_FILE.exists():
            return json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def _save_setting(key: str, value) -> None:
    s = _load_settings()
    s[key] = value
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
```

### Чекбоксы анонимизации из ENTITY_TYPES
```python
from modules.anonymizer import ENTITY_TYPES
# ENTITY_TYPES = {"ФИО": "Фамилия, имя, отчество", "ТЕЛЕФОН": ..., ...}
# 9 типов: ФИО, ТЕЛЕФОН, EMAIL, ПАСПОРТ, СНИЛС, ИНН, ОГРН, КПП, СЧЁТ

current_types = set(_load_settings().get("anonymize_types") or list(ENTITY_TYPES.keys()))

for key, label in ENTITY_TYPES.items():
    ui.checkbox(
        label,
        value=key in current_types,
        on_change=lambda e, k=key: _toggle_anon_type(k, e.value),
    )

def _toggle_anon_type(key: str, enabled: bool) -> None:
    s = _load_settings()
    types = set(s.get("anonymize_types") or list(ENTITY_TYPES.keys()))
    if enabled:
        types.add(key)
    else:
        types.discard(key)
    _save_setting("anonymize_types", list(types))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `st.session_state` для настроек | `settings.json` + `_load_settings()` | Phase 5 (v0.5) | Настройки переживают перезапуск |
| Отдельные страницы Streamlit | `ui.sub_pages` NiceGUI | Phase 7 | SPA-навигация, persistent header |
| Sidebar для настроек провайдера | Отдельная страница `/settings` | Phase 11 | Полноценный settings UX |

## Open Questions

1. **`delete_template` и `update_template` отсутствуют в review_service**
   - What we know: в `review_service.py` только `add_template`, `list_templates`, `match_template`, `review_against_template`, `mark_contract_as_template`
   - What's unclear: добавлять в `review_service.py` или инлайн в страницу
   - Recommendation: добавить в `review_service.py` — сохранить единообразие сервисного слоя

2. **`check_connection()` не реализован в TelegramSync**
   - What we know: есть `is_configured()` (проверяет только наличие URL и chat_id, не реальное соединение)
   - What's unclear: нужен ли реальный HTTP-пинг или достаточно `is_configured()`
   - Recommendation: добавить `check_connection()` в `TelegramSync` — HTTP GET к `{base}/health`, timeout=5s

3. **Где хранить `_load_settings`/`_save_settings`**
   - What we know: сейчас продублированы в `main.py` (Streamlit) и нужны в `app/pages/settings.py`
   - Recommendation: добавить статические методы `Config.load() -> dict` и `Config.save(settings: dict)` в `config.py` — тогда оба файла импортируют из одного места

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (уже в проекте) |
| Config file | `tests/` директория, стандартный pytest |
| Quick run command | `pytest tests/test_settings_templates.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TMPL-01 | Страница /templates рендерится без ошибок | smoke | `pytest tests/test_settings_templates.py::test_templates_page_builds -x` | ❌ Wave 0 |
| TMPL-02 | add_template + list_templates + delete (soft) | unit | `pytest tests/test_settings_templates.py::test_template_crud -x` | ❌ Wave 0 |
| TMPL-03 | Шаблон сохраняется с contract_type | unit | `pytest tests/test_settings_templates.py::test_template_type_binding -x` | ❌ Wave 0 |
| SETT-01 | Страница /settings рендерится без ошибок | smoke | `pytest tests/test_settings_templates.py::test_settings_page_builds -x` | ❌ Wave 0 |
| SETT-02 | _save_setting("active_provider", ...) персистируется | unit | `pytest tests/test_settings_templates.py::test_provider_persistence -x` | ❌ Wave 0 |
| SETT-03 | anonymize_types сохраняется/читается | unit | `pytest tests/test_settings_templates.py::test_anonymize_types_persistence -x` | ❌ Wave 0 |
| SETT-04 | TelegramSync.check_connection возвращает bool | unit | `pytest tests/test_settings_templates.py::test_telegram_check -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_settings_templates.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green перед `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_settings_templates.py` — все тесты фазы (TMPL-01..03, SETT-01..04)
- [ ] `review_service.delete_template()` — функция отсутствует, нужна перед тестами TMPL-02
- [ ] `review_service.update_template()` — функция отсутствует, нужна для D-15
- [ ] `TelegramSync.check_connection()` — метод отсутствует, нужен для SETT-04

## Sources

### Primary (HIGH confidence)
- Прямое чтение исходного кода — `review_service.py`, `telegram_sync.py`, `anonymizer.py`, `config.py`, `app/pages/settings.py`, `app/pages/templates.py`, `app/components/process.py`, `app/main.py`, `modules/models.py`
- Все API-зависимости верифицированы через код проекта

### Secondary (MEDIUM confidence)
- NiceGUI `.on("blur", cb)` — стандартный паттерн NiceGUI event binding; `.on()` принимает любое DOM-событие
- `webview.OPEN_DIALOG` — из pywebview документации; используется в том же паттерне что `FOLDER_DIALOG` в `process.py`

### Tertiary (LOW confidence)
- Нет

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — весь стек верифицирован через живой код проекта
- Architecture: HIGH — паттерны скопированы из существующих компонентов Phase 7-10
- Pitfalls: HIGH — все pitfalls обнаружены при чтении реального кода (отсутствующие функции, неверные сигнатуры)

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (стабильный стек)
