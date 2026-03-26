# Phase 11: Settings + Templates - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Юрист управляет провайдером AI, настройками анонимизации, Telegram-ботом и шаблонами ревью через отдельные страницы — без редактирования конфигов вручную. Переключение клиента уже реализовано в Phase 8.

</domain>

<decisions>
## Implementation Decisions

### Settings page layout
- **D-01:** Left nav + правая панель (macOS System Preferences pattern). Левая колонка — навигация между секциями, правая — содержимое выбранной секции
- **D-02:** Три секции в left nav: AI, Обработка, Telegram
- **D-03:** Сохранение на blur (не глобальная кнопка Save) — через `~/.yurteg/settings.json`

### AI section
- **D-04:** Radio buttons для провайдера: Локальный (Qwen) / ZAI GLM-4.7 / OpenRouter
- **D-05:** Поле API-ключа (password input) — показывается только для ZAI и OpenRouter
- **D-06:** При переключении провайдера — немедленное сохранение через `config.active_provider`

### Обработка section
- **D-07:** Чекбоксы анонимизации — какие сущности маскировать (ФИО, адреса, телефоны, ИНН и т.д.)
- **D-08:** Числовое поле `warning_days` — за сколько дней предупреждать об истечении (default: 30)

### Telegram section
- **D-09:** Поле для токена бота
- **D-10:** Статус подключения: ✓ Подключён / ✗ Не подключён (через `telegram_sync.check_connection`)
- **D-11:** Кнопка «Проверить подключение» — тестирует соединение и обновляет статус

### Templates page
- **D-12:** Таб «Шаблоны» — отдельная страница верхнего уровня
- **D-13:** Список шаблонов в формате карточек: название, тип документа, превью текста (3 строки), дата добавления
- **D-14:** Кнопка «+ Добавить шаблон» → нативный file picker (PDF/DOCX) → ввести название + выбрать тип документа → текст извлекается автоматически через `extractor.py`
- **D-15:** Действия на карточке: Редактировать (название, тип), Удалить (с подтверждением)
- **D-16:** Привязка шаблона к типу документа — dropdown с типами из существующих контрактов

### Client switching
- **D-17:** Уже реализовано в Phase 8 (header dropdown). SETT-05 — считается выполненным

### Claude's Discretion
- Exact Tailwind classes для left nav
- Порядок чекбоксов анонимизации
- Placeholder текст для API-ключа
- Размер карточек шаблонов
- Подтверждение удаления — dialog или inline

</decisions>

<specifics>
## Specific Ideas

- Settings должны выглядеть как macOS System Preferences — спокойно, чисто, без декораций
- Карточки шаблонов — как файлы в Finder Cover Flow (но проще). Название жирным, тип меньшим шрифтом, превью серым
- Telegram статус — зелёная/красная точка рядом с текстом, не бейдж

</specifics>

<canonical_refs>
## Canonical References

### Services
- `services/review_service.py` — `list_templates()`, `create_template()`, `delete_template()`, `update_template()`
- `services/telegram_sync.py` — `check_connection()`, `start_bot()`, `stop_bot()`
- `config.py` — `Config`, `active_provider`, persistence through `settings.json`
- `modules/anonymizer.py` — `ENTITY_TYPES` or similar for anonymization checklist

### Phase artifacts
- `app/pages/settings.py` — stub from Phase 7
- `app/pages/templates.py` — stub from Phase 7 (if exists, otherwise new)
- `app/main.py` — sub_pages routing for `/settings` and `/templates`

### Design skills
- `/distill` — strip complexity from settings forms
- `/clarify` — form labels, section headers

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Config()` — reads/writes `~/.yurteg/settings.json`, already has `active_provider`, `warning_days`
- `review_service` — full CRUD for templates, `Template` dataclass with fields
- `telegram_sync` — `check_connection()`, bot lifecycle management
- `modules/extractor.py` — `extract_text(path)` for template text extraction from PDF/DOCX
- `app/components/process.py` — `pick_folder()` pattern for native file picker (reuse for single file)

### Established Patterns
- `run.io_bound()` for blocking calls
- `ui.navigate.to()` for SPA navigation
- Autosave on blur — same pattern as lawyer notes in Phase 9
- Native file picker — pattern from Phase 10 `process.py`

### Integration Points
- `app/pages/settings.py` — stub ready
- `app/pages/templates.py` — stub ready
- `app/main.py` — routes already configured

</code_context>

<deferred>
## Deferred Ideas

- Логи обработки (история запусков) — v2+
- Backup/restore настроек — v2+
- Импорт шаблонов из библиотеки — v2+

</deferred>

---

*Phase: 11-settings-templates*
*Context gathered: 2026-03-22*
