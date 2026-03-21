# Roadmap: ЮрТэг

## Milestones

- ✅ **v0.4 Архитектура и функционал** — Phases 1-3 (shipped 2026-03-20)
- ✅ **v0.5 Локальная LLM** — Phases 4-6 (shipped 2026-03-21)
- ◆ **v0.6 UI-редизайн** — Phases 7-13 (in progress)

## Phases

<details>
<summary>✅ v0.4 Архитектура и функционал (Phases 1-3) — SHIPPED 2026-03-20</summary>

- [x] Phase 1: Инфраструктура (4 plans) — completed 2026-03-19
- [x] Phase 2: Жизненный цикл документа (8 plans) — completed 2026-03-19
- [x] Phase 3: Интеграции и мультидоступ (12 plans) — completed 2026-03-20

Full details: `.planning/milestones/v0.4-ROADMAP.md`

</details>

<details>
<summary>✅ v0.5 Локальная LLM (Phases 4-6) — SHIPPED 2026-03-21</summary>

- [x] Phase 4: Сервер и провайдер (2 plans) — completed 2026-03-21
- [x] Phase 5: Пайплайн с локальной моделью (1 plan) — completed 2026-03-21
- [x] Phase 6: Проводка ai_extractor (1 plan, gap closure) — completed 2026-03-21

Full details: `.planning/milestones/v0.5-ROADMAP.md`

</details>

### v0.6 UI-редизайн (Phases 7-13)

- [x] **Phase 7: App Scaffold + State Architecture** — NiceGUI запускается, AppState определён, архитектурные паттерны зафиксированы (completed 2026-03-21)
- [ ] **Phase 8: Registry View** — Реестр с реальными данными, AG Grid, фильтры, поиск, статус-бейджи
- [ ] **Phase 9: Document Detail Card** — Full-page карточка документа с ревью, версиями, заметками, навигацией
- [ ] **Phase 10: Pipeline Wiring** — Нативный file picker, async обработка, прогресс в реальном времени
- [ ] **Phase 11: Settings + Templates** — Страница настроек, управление шаблонами, переключение клиента
- [ ] **Phase 12: Onboarding** — Splash screen с wizard, empty states, first-run flow
- [ ] **Phase 13: Design Polish + Calendar** — Цветовая система, типографика, календарь, анимации

## Phase Details

### Phase 7: App Scaffold + State Architecture
**Goal**: Приложение запускается на NiceGUI в нативном окне, архитектурные ограничения зафиксированы до построения любых экранов — предотвращение трёх дорогостоящих паттернов: global state leak, async блокировка, двойная инициализация
**Depends on**: Nothing (first phase of v0.6)
**Requirements**: FUND-01, FUND-02, FUND-03, FUND-04, FUND-05
**Design skills**: `/arrange` (layout structure)
**Success Criteria** (what must be TRUE):
  1. Пользователь запускает `python app/main.py` и видит нативное окно с тремя пустыми табами (Документы · Шаблоны · Настройки)
  2. Переключение между тремя табами работает без перезагрузки страницы — заголовок остаётся на месте
  3. llama-server запускается при старте приложения и корректно останавливается при закрытии окна (процесс не остаётся висеть в Activity Monitor)
  4. Повторный запуск приложения не создаёт второй экземпляр llama-server на том же порту
**Plans:** 2/2 plans complete
Plans:
- [x] 07-01-PLAN.md — AppState dataclass, page stubs, header, test scaffold
- [x] 07-02-PLAN.md — NiceGUI entrypoint, llama-server lifecycle, requirements.txt

### Phase 8: Registry View
**Goal**: Реестр документов показывает реальные данные из SQLite через AG Grid — юрист видит все свои документы, может фильтровать и искать без зависания UI
**Depends on**: Phase 7
**Requirements**: REG-01, REG-02, REG-03, REG-04, REG-05, REG-06, REG-07
**Design skills**: `/arrange` (table layout, spacing), `/typeset` (column hierarchy), `/harden` (edge cases, overflow)
**Success Criteria** (what must be TRUE):
  1. Все документы из базы данных отображаются в таблице с колонками (тип, контрагент, статус, дата окончания, качество)
  2. Клик по строке открывает полноэкранную карточку документа (не модальное окно, не аккордеон)
  3. Текстовый поиск сужает список в реальном времени (с debounce); фильтры по типу и контрагенту работают совместно
  4. Строки с истекающими/истёкшими договорами визуально выделены цветом статус-бейджа
  5. Переключение клиента через иконку профиля меняет набор документов без перезапуска
**Plans:** 3 plans
Plans:
- [ ] 08-01-PLAN.md — Data layer (_fetch_rows, _fuzzy_filter), AG Grid table с status badges
- [ ] 08-02-PLAN.md — Search bar, segmented filter, row click navigation, client switching
- [ ] 08-03-PLAN.md — Hover-actions, version grouping, visual verification

### Phase 9: Document Detail Card
**Goal**: Карточка документа содержит всю информацию и действия — юрист может просмотреть метаданные, запустить AI-ревью, посмотреть версии и оставить заметку, не возвращаясь в реестр
**Depends on**: Phase 8
**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06
**Design skills**: `/arrange` (card layout, grid), `/typeset` (metadata hierarchy), `/clarify` (labels, microcopy)
**Success Criteria** (what must be TRUE):
  1. Кнопка «← Назад к реестру» возвращает на ту же позицию прокрутки, откуда был открыт документ
  2. Метаданные документа (стороны, даты, сумма, тип) отображаются в структурированной сетке, не стеком строк
  3. Кнопки «Предыдущий» / «Следующий» переключают между документами без возврата в реестр
  4. AI-ревью по выбранному шаблону запускается кнопкой и отображает результат с подсветкой отступлений
  5. Заметка юриста автосохраняется при потере фокуса (blur), без кнопки «Сохранить»
**Plans**: TBD

### Phase 10: Pipeline Wiring
**Goal**: Юрист выбирает папку с документами и видит прогресс обработки в реальном времени — новые документы появляются в реестре автоматически после завершения
**Depends on**: Phase 7
**Requirements**: PROC-01, PROC-02, PROC-03, PROC-04
**Design skills**: `/onboard` (empty state, first run), `/clarify` (progress messages, error states)
**Success Criteria** (what must be TRUE):
  1. Кнопка «Загрузить документы» открывает нативный диалог выбора папки macOS (не браузерный input)
  2. Прогресс-бар обновляется в реальном времени по мере обработки файлов (например «3/12 файлов»); UI не зависает
  3. После завершения обработки таблица реестра автоматически обновляется новыми строками без ручного перезапуска
  4. Ошибка на одном файле не останавливает обработку остальных; в логе виден файл и причина ошибки
**Plans**: TBD

### Phase 11: Settings + Templates
**Goal**: Юрист управляет провайдером AI, настройками анонимизации, Telegram-ботом и шаблонами ревью через отдельные страницы — без редактирования конфигов вручную
**Depends on**: Phase 7
**Requirements**: TMPL-01, TMPL-02, TMPL-03, SETT-01, SETT-02, SETT-03, SETT-04, SETT-05
**Design skills**: `/distill` (strip complexity), `/clarify` (form labels, grouping)
**Success Criteria** (what must be TRUE):
  1. Страница настроек открывается как отдельный таб верхнего уровня и содержит секции (AI-провайдер, анонимизация, уведомления, Telegram)
  2. Изменение провайдера сохраняется при потере фокуса и применяется к следующей обработке без перезапуска приложения
  3. Страница «Шаблоны» показывает список существующих шаблонов с операциями добавить / редактировать / удалить
  4. Новый шаблон привязывается к типу документа, и в карточке документа доступен в выпадающем списке при запуске ревью
**Plans**: TBD

### Phase 12: Onboarding
**Goal**: Первый контакт юриста с приложением — splash screen с прогрессом загрузки модели и setup wizard, empty states для пустых экранов, first-run flow который показывается только один раз
**Depends on**: Phase 10, Phase 11
**Requirements**: ONBR-01, ONBR-02, ONBR-03, ONBR-04
**Design skills**: `/onboard` (first-run experience, empty states), `/clarify` (wizard copy, CTA labels)
**Success Criteria** (what must be TRUE):
  1. При первом запуске юрист видит splash screen с прогрессом загрузки модели и шагами setup wizard (Telegram, провайдер)
  2. Wizard можно пропустить — кнопка «Пропустить» на каждом шаге
  3. После загрузки модели splash закрывается, открывается реестр с empty state «Загрузить первые документы»
  4. При повторном запуске splash и wizard не показываются — приложение открывается сразу
**Plans**: TBD

### Phase 13: Design Polish + Calendar
**Goal**: Интерфейс выглядит профессионально: светлая утилитарная тема без AI slop и возможность переключить реестр в вид платёжного календаря
**Depends on**: Phase 8, Phase 9, Phase 11, Phase 12
**Requirements**: DSGN-01, DSGN-02, DSGN-03, DSGN-04, DSGN-05
**Design skills**: `/colorize` (palette), `/typeset` (font system), `/animate` (motion), `/polish` (final pass), `/audit` (a11y, quality check), `frontend-design` (AI slop test)
**Success Criteria** (what must be TRUE):
  1. Переключатель «Список / Календарь» в реестре меняет вид таблицы на месячный календарь с отметками дат окончания договоров
  2. Весь интерфейс использует светлую тему с одним акцентным цветом (без cyan, glassmorphism, gradient text)
  3. Типографика читается чётко: заголовок карточки, метки полей и тело заметки визуально отличаются по размеру и весу
  4. Появление строк в реестре при первой загрузке анимировано (staggered reveal, не мгновенный рендер)
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Инфраструктура | v0.4 | 4/4 | Complete | 2026-03-19 |
| 2. Жизненный цикл | v0.4 | 8/8 | Complete | 2026-03-19 |
| 3. Интеграции | v0.4 | 12/12 | Complete | 2026-03-20 |
| 4. Сервер и провайдер | v0.5 | 2/2 | Complete | 2026-03-21 |
| 5. Пайплайн с локальной LLM | v0.5 | 1/1 | Complete | 2026-03-21 |
| 6. Проводка ai_extractor | v0.5 | 1/1 | Complete | 2026-03-21 |
| 7. App Scaffold + State | v0.6 | 2/2 | Complete   | 2026-03-21 |
| 8. Registry View | v0.6 | 0/3 | Planned | - |
| 9. Document Detail Card | v0.6 | 0/? | Not started | - |
| 10. Pipeline Wiring | v0.6 | 0/? | Not started | - |
| 11. Settings + Templates | v0.6 | 0/? | Not started | - |
| 12. Onboarding | v0.6 | 0/? | Not started | - |
| 13. Design Polish + Calendar | v0.6 | 0/? | Not started | - |
