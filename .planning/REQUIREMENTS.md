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
- [ ] **REG-06**: Hover-reveal inline actions на строках (чекбоксы, контекстное меню)
- [ ] **REG-07**: Версии документов группируются под основным договором (допсоглашения вложены)

### Карточка документа

- [ ] **DOC-01**: Full-page карточка документа с кнопкой «← Назад к реестру»
- [ ] **DOC-02**: Метаданные документа отображаются в CSS grid-layout
- [ ] **DOC-03**: Навигация «Предыдущий / Следующий» между документами без возврата в реестр
- [ ] **DOC-04**: AI-ревью документа по выбранному шаблону (кнопка в карточке)
- [ ] **DOC-05**: История версий документа в сворачиваемой секции
- [ ] **DOC-06**: Пометки юриста (ручные заметки к документу)

### Обработка

- [ ] **PROC-01**: Загрузка файлов через нативный file picker (поддержка выбора папки)
- [ ] **PROC-02**: Pipeline обработки запускается async через `run.io_bound()`
- [ ] **PROC-03**: Прогресс обработки отображается в реальном времени (прогресс-бар + лог файлов)
- [ ] **PROC-04**: После обработки новые документы автоматически появляются в реестре

### Шаблоны

- [ ] **TMPL-01**: Отдельный таб «Шаблоны» верхнего уровня
- [ ] **TMPL-02**: Список шаблонов с операциями создания, редактирования и удаления
- [ ] **TMPL-03**: Привязка шаблона к типу документа

### Настройки

- [ ] **SETT-01**: Отдельная страница «Настройки» с группировкой по секциям
- [ ] **SETT-02**: Переключение AI-провайдера (ollama / zai / openrouter) с сохранением на blur
- [ ] **SETT-03**: Настройка анонимизации (выбор сущностей для маскировки)
- [ ] **SETT-04**: Настройка Telegram-бота (привязка, статус подключения)
- [ ] **SETT-05**: Переключение клиента через иконку профиля (top-left)

### Онбординг

- [ ] **ONBR-01**: Splash screen при первом запуске с прогрессом загрузки модели и setup wizard (Telegram, провайдер)
- [ ] **ONBR-02**: Empty state реестра при пустой базе — центрированный CTA «Загрузить первые документы»
- [ ] **ONBR-03**: Флаг «первый запуск» — splash и wizard показываются только один раз, при повторных запусках пропускаются
- [ ] **ONBR-04**: Краткое описание возможностей приложения на splash screen (что делает ЮрТэг, 2-3 предложения)

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
| REG-06 | Phase 8 | Pending |
| REG-07 | Phase 8 | Pending |
| DOC-01 | Phase 9 | Pending |
| DOC-02 | Phase 9 | Pending |
| DOC-03 | Phase 9 | Pending |
| DOC-04 | Phase 9 | Pending |
| DOC-05 | Phase 9 | Pending |
| DOC-06 | Phase 9 | Pending |
| PROC-01 | Phase 10 | Pending |
| PROC-02 | Phase 10 | Pending |
| PROC-03 | Phase 10 | Pending |
| PROC-04 | Phase 10 | Pending |
| TMPL-01 | Phase 11 | Pending |
| TMPL-02 | Phase 11 | Pending |
| TMPL-03 | Phase 11 | Pending |
| SETT-01 | Phase 11 | Pending |
| SETT-02 | Phase 11 | Pending |
| SETT-03 | Phase 11 | Pending |
| SETT-04 | Phase 11 | Pending |
| SETT-05 | Phase 11 | Pending |
| ONBR-01 | Phase 12 | Pending |
| ONBR-02 | Phase 12 | Pending |
| ONBR-03 | Phase 12 | Pending |
| ONBR-04 | Phase 12 | Pending |
| DSGN-01 | Phase 13 | Pending |
| DSGN-02 | Phase 13 | Pending |
| DSGN-03 | Phase 13 | Pending |
| DSGN-04 | Phase 13 | Pending |
| DSGN-05 | Phase 13 | Pending |

**Coverage:**
- v0.6 requirements: 39 total
- Mapped to phases: 39
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-21*
*Last updated: 2026-03-22 — added ONBR requirements, remapped to Phases 7-13*
