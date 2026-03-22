# Requirements: ЮрТэг v0.6 UI-редизайн

**Defined:** 2026-03-21
**Core Value:** Юрист загружает папку с документами и за 20 минут получает готовый реестр с метаданными — без ручного ввода, без обучения, без «проекта внедрения»

## v0.6 Requirements

### Фундамент

- [x] **FUND-01**: Приложение запускается на NiceGUI с `app/` структурой и `@ui.page` архитектурой
- [x] **FUND-02**: Состояние управляется через typed `AppState` dataclass (замена 45 `st.session_state` ключей)
- [x] **FUND-03**: Все DB-вызовы из UI обёрнуты в `run.io_bound()` (не блокируют event loop)
- [x] **FUND-04**: llama-server запускается через `app.on_startup`, останавливается через тройную защиту (`on_shutdown` + `on_disconnect` + `atexit`)
- [x] **FUND-05**: Приложение запускается с `reload=False` в production entrypoint

### Реестр

- [x] **REG-01**: Реестр отображается в AG Grid таблице с данными из существующих сервисов
- [x] **REG-02**: Клик по строке реестра открывает full-page карточку документа
- [x] **REG-03**: Фильтры по типу, контрагенту, качеству и текстовый поиск
- [x] **REG-04**: Статус-бейджи в строках (действует / истекает / истёк)
- [x] **REG-05**: Сегментированный фильтр верхнего уровня (Все · Истекают · Требуют внимания)
- [x] **REG-06**: Hover-reveal inline actions на строках (чекбоксы, контекстное меню)
- [x] **REG-07**: Версии документов группируются под основным договором (допсоглашения вложены)

### Карточка документа

- [x] **DOC-01**: Full-page карточка документа с кнопкой «← Назад к реестру»
- [x] **DOC-02**: Метаданные документа отображаются в CSS grid-layout
- [x] **DOC-03**: Навигация «Предыдущий / Следующий» между документами без возврата в реестр
- [x] **DOC-04**: AI-ревью документа по выбранному шаблону (кнопка в карточке)
- [x] **DOC-05**: История версий документа в сворачиваемой секции
- [x] **DOC-06**: Пометки юриста (ручные заметки к документу)

### Обработка

- [x] **PROC-01**: Загрузка файлов через нативный file picker (поддержка выбора папки)
- [x] **PROC-02**: Pipeline обработки запускается async через `run.io_bound()`
- [x] **PROC-03**: Прогресс обработки отображается в реальном времени (прогресс-бар + лог файлов)
- [x] **PROC-04**: После обработки новые документы автоматически появляются в реестре

### Шаблоны

- [x] **TMPL-01**: Отдельный таб «Шаблоны» верхнего уровня
- [x] **TMPL-02**: Список шаблонов с операциями создания, редактирования и удаления
- [x] **TMPL-03**: Привязка шаблона к типу документа

### Настройки

- [x] **SETT-01**: Отдельная страница «Настройки» с группировкой по секциям
- [x] **SETT-02**: Переключение AI-провайдера (ollama / zai / openrouter) с сохранением на blur
- [x] **SETT-03**: Настройка анонимизации (выбор сущностей для маскировки)
- [x] **SETT-04**: Настройка Telegram-бота (привязка, статус подключения)
- [x] **SETT-05**: Переключение клиента через иконку профиля (top-left)

### Онбординг

- [x] **ONBR-01**: Splash screen при первом запуске с прогрессом загрузки модели и setup wizard (Telegram, провайдер)
- [x] **ONBR-02**: Empty state реестра при пустой базе — центрированный CTA «Загрузить первые документы»
- [x] **ONBR-03**: Флаг «первый запуск» — splash и wizard показываются только один раз, при повторных запусках пропускаются
- [x] **ONBR-04**: Краткое описание возможностей приложения на splash screen (что делает ЮрТэг, 2-3 предложения)
- [x] **ONBR-05**: Guided tour после первой обработки — пошаговая подсветка элементов (реестр → фильтры → загрузка)

### Дизайн

- [ ] **DSGN-01**: Светлая тема с тёплыми нейтральными тонами (без AI slop: no cyan-on-dark, no glassmorphism, no gradient text)
- [ ] **DSGN-02**: Один акцентный цвет для действий и статусов, палитра по правилу 60-30-10
- [ ] **DSGN-03**: Типографика с чёткой иерархией (display + body font pairing, modular scale)
- [ ] **DSGN-04**: Календарь как переключатель вида реестра (FullCalendar.js интеграция)
- [ ] **DSGN-05**: Анимации появления элементов (staggered reveals, ease-out-quart)

## v0.7 Requirements

### Доставка

- **DLVR-01**: Сборка DMG для macOS через PyInstaller + NiceGUI native mode
- **DLVR-02**: Сборка EXE для Windows
- **DLVR-03**: Автообновление или уведомление о новых версиях

## Out of Scope

| Feature | Reason |
|---------|--------|
| Dark mode | Светлая тема — осознанное решение против AI slop. Dark mode — v2+ |
| Split-view (master-detail) | Full-page transition проще, лучше на узких экранах. Может быть добавлен позже |
| Drag-and-drop загрузка | NiceGUI `ui.upload` ограничен, нативный picker надёжнее |
| Мобильная адаптация | Desktop-first приложение, responsive — v2+ |
| Real-time collaboration | Требует серверной БД, v2+ |
| Google Drive автообработка | Telegram покрывает сценарий |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FUND-01 | Phase 7 | Complete |
| FUND-02 | Phase 7 | Complete |
| FUND-03 | Phase 7 | Complete |
| FUND-04 | Phase 7 | Complete |
| FUND-05 | Phase 7 | Complete |
| REG-01 | Phase 8 | Complete |
| REG-02 | Phase 8 | Complete |
| REG-03 | Phase 8 | Complete |
| REG-04 | Phase 8 | Complete |
| REG-05 | Phase 8 | Complete |
| REG-06 | Phase 8 | Complete |
| REG-07 | Phase 8 | Complete |
| DOC-01 | Phase 9 | Complete |
| DOC-02 | Phase 9 | Complete |
| DOC-03 | Phase 9 | Complete |
| DOC-04 | Phase 9 | Complete |
| DOC-05 | Phase 9 | Complete |
| DOC-06 | Phase 9 | Complete |
| PROC-01 | Phase 10 | Complete |
| PROC-02 | Phase 10 | Complete |
| PROC-03 | Phase 10 | Complete |
| PROC-04 | Phase 10 | Complete |
| TMPL-01 | Phase 11 | Complete |
| TMPL-02 | Phase 11 | Complete |
| TMPL-03 | Phase 11 | Complete |
| SETT-01 | Phase 11 | Complete |
| SETT-02 | Phase 11 | Complete |
| SETT-03 | Phase 11 | Complete |
| SETT-04 | Phase 11 | Complete |
| SETT-05 | Phase 11 | Complete |
| ONBR-01 | Phase 12 | Complete |
| ONBR-02 | Phase 12 | Complete |
| ONBR-03 | Phase 12 | Complete |
| ONBR-04 | Phase 12 | Complete |
| ONBR-05 | Phase 12 | Complete |
| DSGN-01 | Phase 13 | Pending |
| DSGN-02 | Phase 13 | Pending |
| DSGN-03 | Phase 13 | Pending |
| DSGN-04 | Phase 13 | Pending |
| DSGN-05 | Phase 13 | Pending |

**Coverage:**
- v0.6 requirements: 40 total
- Mapped to phases: 40
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-21*
*Last updated: 2026-03-22 — added ONBR requirements, remapped to Phases 7-13*
