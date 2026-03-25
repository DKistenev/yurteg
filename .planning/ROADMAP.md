# Roadmap: ЮрТэг

## Milestones

- ✅ **v0.4 Архитектура и функционал** — Phases 1-3 (shipped 2026-03-20)
- ✅ **v0.5 Локальная LLM** — Phases 4-6 (shipped 2026-03-21)
- ✅ **v0.6 UI-редизайн** — Phases 7-13 (shipped 2026-03-22)
- ✅ **v0.7 Визуальный продукт** — Phases 14-17 (shipped 2026-03-22)
- ✅ **v0.7.1 UI Polish & Fixes** — Phases 18-19 (shipped 2026-03-22)
- ✅ **v0.8 Hardening & Cleanup** — Phases 20-23 (shipped 2026-03-25)
- 🔄 **v0.8.1 UI Polish** — Phases 24-27 (current)

## Phases

<details>
<summary>✅ v0.4–v0.7.1 (Phases 1–19) — SHIPPED</summary>

Phases 1-19 completed across five milestones (v0.4–v0.7.1). See MILESTONES.md for details.

</details>

### ✅ v0.8 Hardening & Cleanup (Shipped 2026-03-25)

**Milestone Goal:** Починить критические баги, вычистить мёртвый код, довести тестовое покрытие — подготовить кодовую базу к production-сборке.

- [x] **Phase 20: Data Integrity** — UPSERT, foreign keys, платёжные поля, деанонимизация subject (completed 2026-03-24)
- [x] **Phase 21: UI Fixes** — боковая панель, скачивание PDF, переобработка, warning_days, bulk status (completed 2026-03-24)
- [x] **Phase 22: Code Cleanup** — удаление Streamlit, legacy-кода, починка тестов (completed 2026-03-24)
- [x] **Phase 23: Production Readiness** — тесты для непокрытых модулей, офлайн-ресурсы, requirements.txt, локальная модель (completed 2026-03-24)

### 🔄 v0.8.1 UI Polish (Current)

**Milestone Goal:** Полная переработка визуала всех экранов по утверждённым HTML-мокапам — от реестра до онбординга.

- [x] **Phase 24: Registry** — реестр без «Уверенности», Linear-style панель, русский footer, таймлайн-календарь (completed 2026-03-25)
- [ ] **Phase 25: Document Card** — двухколоночная раскладка с превью PDF/DOCX на всю высоту
- [ ] **Phase 26: Dialogs & Pages** — диалог пространства, пустое состояние шаблонов, страница настроек
- [ ] **Phase 27: Onboarding & Processing** — 3-шаговый wizard, гид-тур, живой реестр при обработке

## Phase Details

### Phase 20: Data Integrity
**Goal**: Данные пользователя не теряются при повторной обработке; все AI-поля сохраняются в базу
**Depends on**: Nothing (first phase of milestone)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04
**Success Criteria** (what must be TRUE):
  1. Повторная обработка документа сохраняет заметку и ручной статус юриста без изменений
  2. Связи между версиями документа остаются целыми после повторной обработки
  3. Поля сумма/частота/направление платежа отображаются в карточке документа после обработки
  4. В поле «предмет» договора отображаются реальные имена контрагентов, а не маски [ФИО_1]
**Plans**: 1 plan
Plans:
- [x] 20-01-PLAN.md — UPSERT, FK pragma, migration v7, deanonymization, db.conn fix

### Phase 21: UI Fixes
**Goal**: Все кнопки и элементы интерфейса работают без ошибок и крашей
**Depends on**: Phase 20
**Requirements**: UIFIX-01, UIFIX-02, UIFIX-03, UIFIX-04, UIFIX-05, UIFIX-06
**Success Criteria** (what must be TRUE):
  1. Клик по строке реестра открывает боковую панель предпросмотра без исключений в консоли
  2. Кнопка «Скачать PDF» отдаёт файл браузеру (не 404)
  3. Кнопка «Переобработать» запускает pipeline и показывает прогресс
  4. Порог напоминаний, сохранённый в настройках, применяется после перезапуска приложения
  5. Диалог массовой смены статуса показывает читаемые русские названия статусов
**Plans**: 2 plans
Plans:
- [x] 21-01-PLAN.md — Fix get_contract method name, warning_days key, bulk status labels, logging
- [x] 21-02-PLAN.md — Download PDF route, reprocess button handler
**UI hint**: yes

### Phase 22: Code Cleanup
**Goal**: Кодовая база содержит только живой код — старый UI и мёртвые функции удалены, все тесты зелёные
**Depends on**: Phase 21
**Requirements**: CLEAN-01, CLEAN-02, CLEAN-03
**Success Criteria** (what must be TRUE):
  1. Файл main.py (Streamlit, 1700+ строк) удалён — `streamlit run` не запускает приложение
  2. Legacy-функции и дубликаты в backend удалены — нет dead code warnings в codebase
  3. `pytest` проходит без FAIL и xfail — все 268+ тестов зелёные
**Plans**: 2 plans
Plans:
- [x] 22-01-PLAN.md — Delete Streamlit main.py/desktop_app.py, remove dead functions/imports/fields
- [x] 22-02-PLAN.md — Fix proxy test failures, remove xfail markers, clean CSS tests

### Phase 23: Production Readiness
**Goal**: Приложение работает офлайн, устанавливается на чистой машине и запускает локальную модель без ручной настройки
**Depends on**: Phase 22
**Requirements**: PROD-01, PROD-02, PROD-03, PROD-04
**Success Criteria** (what must be TRUE):
  1. Тесты для scanner, extractor, reporter, postprocessor, controller написаны и проходят
  2. Приложение запускается без интернета — шрифты и FullCalendar подгружаются из локальных файлов
  3. `pip install -r requirements.txt` устанавливает все зависимости на чистом окружении без ошибок
  4. Локальная QWEN-модель находит llama-server и проверяет качество через провайдер-систему
**Plans**: 2 plans
Plans:
- [x] 23-01-PLAN.md — Bundle offline fonts/calendar, pin requirements.txt, fix OllamaProvider port, refactor verify_metadata
- [x] 23-02-PLAN.md — Tests for scanner, extractor, reporter, postprocessor, controller

### Phase 24: Registry
**Goal**: Реестр выглядит профессионально и без лишнего шума — убрана внутренняя метрика, интерфейс на русском, боковая панель в стиле Linear, календарь показывает реальный таймлайн

**Visual Reference:** Исполнитель ОБЯЗАН прочитать мокапы перед работой:
- `.superpowers/brainstorm/99248-1774442361/registry-redesign.html` — таблица реестра и bulk toolbar
- `.superpowers/brainstorm/99248-1774442361/side-panel-v2.html` — Linear-style боковая панель
- `.superpowers/brainstorm/99248-1774442361/side-panel-options.html` — варианты панели
- `.superpowers/brainstorm/99248-1774442361/calendar-redesign.html` — таймлайн + мини-календарь

**Depends on**: Phase 23
**Requirements**: REG-01, REG-02, REG-03, REG-04, REG-05
**Success Criteria** (what must be TRUE):
  1. Колонка «Уверенность» отсутствует в таблице реестра — пользователь её не видит
  2. Bulk toolbar содержит только «Изменить статус», «Удалить», «Снять выбор» с шрифтом IBM Plex Sans
  3. Pagination footer полностью на русском — нет английских слов «Page Size» и «of»
  4. Боковая панель предпросмотра использует Linear-style: секции ДОКУМЕНТ/СРОКИ/ФИНАНСЫ с мини-заголовками, тег-бейдж типа, сумма крупным шрифтом, field labels без КАПСА
  5. Кнопка «Календарь» открывает таймлайн с лентой событий слева и мини-календарём справа с цветными точками
**Plans**: 2 plans
Plans:
- [x] 24-01-PLAN.md — Таблица: убрать Уверенность и Excel, русифицировать footer, Linear-style панель
- [x] 24-02-PLAN.md — Календарь: таймлайн событий + мини-календарь вместо FullCalendar
**UI hint**: yes

### Phase 25: Document Card
**Goal**: Карточка документа предоставляет полный контекст без переключения между окнами — метаданные и превью файла видны одновременно

**Visual Reference:** Исполнитель ОБЯЗАН прочитать мокапы перед работой:
- `.superpowers/brainstorm/99248-1774442361/document-card-final.html` — финальная раскладка (приоритет)
- `.superpowers/brainstorm/99248-1774442361/document-card-left-right.html` — двухколоночная раскладка
- `.superpowers/brainstorm/99248-1774442361/document-card-preview.html` — секция предпросмотра
- `.superpowers/brainstorm/99248-1774442361/document-card-compact.html` — компактный вариант
- `.superpowers/brainstorm/99248-1774442361/document-card-v2.html` — альтернативный вариант

**Depends on**: Phase 24
**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06
**Success Criteria** (what must be TRUE):
  1. Карточка открывается в раскладке «380px метаданные слева + превью справа на всю высоту экрана»
  2. PDF-документ рендерится встроенно в правой панели (iframe); DOCX показывает извлечённый текст на тёмном фоне
  3. Кнопка «Открыть файл» открывает оригинальный файл в системном приложении на компьютере пользователя
  4. Field labels отображаются в обычном регистре (не КАПС), секционные заголовки — uppercase
  5. Блок «Проверка по шаблону» содержит две кнопки: «Найти шаблон» (primary indigo) и «Добавить» (outlined)
  6. История версий показана как таймлайн с точками: indigo для текущей версии, серые для старых, каждая со ссылкой «Сравнить →»
**Plans**: TBD
**UI hint**: yes

### Phase 26: Dialogs & Pages
**Goal**: Диалог создания пространства понятно объясняет концепцию; страница шаблонов направляет к действию при пустом состоянии; настройки собраны в единую удобную страницу без navigation sidebar

**Visual Reference:** Исполнитель ОБЯЗАН прочитать мокапы перед работой:
- `.superpowers/brainstorm/99248-1774442361/workspace-dialog-v2.html` — финальный диалог (приоритет)
- `.superpowers/brainstorm/99248-1774442361/workspace-dialog.html` — исходный вариант диалога
- `.superpowers/brainstorm/99248-1774442361/templates-empty-state.html` — пустое состояние шаблонов
- `.superpowers/brainstorm/99248-1774442361/settings-final.html` — финальная страница настроек (приоритет)
- `.superpowers/brainstorm/99248-1774442361/settings-redesign.html` — альтернативный вариант настроек

**Depends on**: Phase 24
**Requirements**: WS-01, TPL-01, SET-01, SET-02, SET-03
**Success Criteria** (what must be TRUE):
  1. Диалог «Новое пространство» показывает 3 карточки-пояснения (реестр/сроки/шаблоны) + выбор из 8 цветов + превью «Так будет в меню»
  2. Пустое состояние шаблонов содержит hero с CTA, чипы-пресеты типов (Поставка, Аренда, Трудовой и др.) и 3 карточки-примера
  3. Страница настроек — единая без sidebar, разбита на секции со скроллом: ИИ-модель → Обработка → Уведомления → О программе
  4. Секция «ИИ-модель» содержит карточку с gradient bar и кольцо точности 97%, зелёный баннер «Данные обрабатываются локально», поле резервного провайдера
  5. Поле «Thinking mode» отсутствует в настройках
**Plans**: TBD
**UI hint**: yes

### Phase 27: Onboarding & Processing
**Goal**: Новый пользователь проходит настройку за три понятных шага и получает интерактивный тур; во время обработки документов можно работать с уже готовыми записями

**Visual Reference:** Исполнитель ОБЯЗАН прочитать мокапы перед работой:
- `.superpowers/brainstorm/99248-1774442361/onboarding-redesign.html` — 3-шаговый wizard
- `.superpowers/brainstorm/99248-1774442361/guided-tour-cards.html` — гид-тур с подсветкой
- `.superpowers/brainstorm/99248-1774442361/processing-final.html` — экран обработки (приоритет)
- `.superpowers/brainstorm/99248-1774442361/processing-experience.html` — альтернативный вариант

**Depends on**: Phase 25
**Requirements**: ONB-01, ONB-02, ONB-03, ONB-04, PROC-01, PROC-02, PROC-03
**Success Criteria** (what must be TRUE):
  1. Онбординг показывает прогресс-индикатор «Модель → Telegram → Готово» — пользователь видит на каком шаге находится
  2. После завершения онбординга автоматически запускается гид-тур: затемнение фона, подсветка элемента, tooltip с шагом X из 5
  3. Кнопка «?» в header запускает тур повторно из любого места приложения
  4. Во время обработки новые строки появляются в реестре в реальном времени с анимацией пульсации — пользователь может кликать по готовым строкам
  5. Справа от реестра при обработке видна лента файлов (300px) с категориями: готовые (✓), текущий (⟳), ошибки (!), очередь
**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-19. Phases 1-19 | v0.4–v0.7.1 | — | Complete | 2026-03-22 |
| 20. Data Integrity | v0.8 | 1/1 | Complete    | 2026-03-24 |
| 21. UI Fixes | v0.8 | 2/2 | Complete    | 2026-03-24 |
| 22. Code Cleanup | v0.8 | 2/2 | Complete    | 2026-03-24 |
| 23. Production Readiness | v0.8 | 2/2 | Complete    | 2026-03-24 |
| 24. Registry | v0.8.1 | 2/2 | Complete    | 2026-03-25 |
| 25. Document Card | v0.8.1 | 0/? | Not started | - |
| 26. Dialogs & Pages | v0.8.1 | 0/? | Not started | - |
| 27. Onboarding & Processing | v0.8.1 | 0/? | Not started | - |
