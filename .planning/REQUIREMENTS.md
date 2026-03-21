# Requirements: ЮрТэг v0.6 UI-редизайн

**Defined:** 2026-03-21
**Core Value:** Юрист загружает папку с документами и за 20 минут получает готовый реестр с метаданными — без ручного ввода, без обучения, без «проекта внедрения»

## v0.6 Requirements

### Фундамент

- [ ] **FUND-01**: Приложение запускается на NiceGUI с `app/` структурой и `@ui.page` архитектурой
- [ ] **FUND-02**: Состояние управляется через typed `AppState` dataclass (замена 45 `st.session_state` ключей)
- [ ] **FUND-03**: Все DB-вызовы из UI обёрнуты в `run.io_bound()` (не блокируют event loop)
- [ ] **FUND-04**: llama-server запускается через `app.on_startup`, останавливается через тройную защиту (`on_shutdown` + `on_disconnect` + `atexit`)
- [ ] **FUND-05**: Приложение запускается с `reload=False` в production entrypoint

### Реестр

- [ ] **REG-01**: Реестр отображается в AG Grid таблице с данными из существующих сервисов
- [ ] **REG-02**: Клик по строке реестра открывает full-page карточку документа
- [ ] **REG-03**: Фильтры по типу, контрагенту, качеству и текстовый поиск
- [ ] **REG-04**: Статус-бейджи в строках (действует / истекает / истёк)
- [ ] **REG-05**: Сегментированный фильтр верхнего уровня (Все · Истекают · Требуют внимания)
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

### Дизайн

- [ ] **DSGN-01**: Светлая тема с тёплыми нейтральными тонами (без AI slop: no cyan-on-dark, no glassmorphism, no gradient text)
- [ ] **DSGN-02**: Один акцентный цвет для действий и статусов, палитра по правилу 60-30-10
- [ ] **DSGN-03**: Типографика с чёткой иерархией (display + body font pairing, modular scale)
- [ ] **DSGN-04**: Empty state с onboarding при первом запуске (центрированный CTA + подсказка)
- [ ] **DSGN-05**: Календарь как переключатель вида реестра (FullCalendar.js интеграция)
- [ ] **DSGN-06**: Анимации появления элементов (staggered reveals, ease-out-quart)

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
| FUND-01 | — | Pending |
| FUND-02 | — | Pending |
| FUND-03 | — | Pending |
| FUND-04 | — | Pending |
| FUND-05 | — | Pending |
| REG-01 | — | Pending |
| REG-02 | — | Pending |
| REG-03 | — | Pending |
| REG-04 | — | Pending |
| REG-05 | — | Pending |
| REG-06 | — | Pending |
| REG-07 | — | Pending |
| DOC-01 | — | Pending |
| DOC-02 | — | Pending |
| DOC-03 | — | Pending |
| DOC-04 | — | Pending |
| DOC-05 | — | Pending |
| DOC-06 | — | Pending |
| PROC-01 | — | Pending |
| PROC-02 | — | Pending |
| PROC-03 | — | Pending |
| PROC-04 | — | Pending |
| TMPL-01 | — | Pending |
| TMPL-02 | — | Pending |
| TMPL-03 | — | Pending |
| SETT-01 | — | Pending |
| SETT-02 | — | Pending |
| SETT-03 | — | Pending |
| SETT-04 | — | Pending |
| SETT-05 | — | Pending |
| DSGN-01 | — | Pending |
| DSGN-02 | — | Pending |
| DSGN-03 | — | Pending |
| DSGN-04 | — | Pending |
| DSGN-05 | — | Pending |
| DSGN-06 | — | Pending |

**Coverage:**
- v0.6 requirements: 36 total
- Mapped to phases: 0
- Unmapped: 36 ⚠️

---
*Requirements defined: 2026-03-21*
*Last updated: 2026-03-21 after initial definition*
