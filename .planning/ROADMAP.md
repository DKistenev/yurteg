# Roadmap: ЮрТэг

## Milestones

- ✅ **v0.4 Архитектура и функционал** — Phases 1-3 (shipped 2026-03-20)
- ✅ **v0.5 Локальная LLM** — Phases 4-6 (shipped 2026-03-21)
- ✅ **v0.6 UI-редизайн** — Phases 7-13 (shipped 2026-03-22)
- ✅ **v0.7 Визуальный продукт** — Phases 14-17 (shipped 2026-03-22)
- ✅ **v0.7.1 UI Polish & Fixes** — Phases 18-19 (shipped 2026-03-22)
- 🚧 **v0.8 Hardening & Cleanup** — Phases 20-23 (in progress)

## Phases

<details>
<summary>✅ v0.4–v0.7.1 (Phases 1–19) — SHIPPED</summary>

Phases 1-19 completed across five milestones (v0.4–v0.7.1). See MILESTONES.md for details.

</details>

### 🚧 v0.8 Hardening & Cleanup (In Progress)

**Milestone Goal:** Починить критические баги, вычистить мёртвый код, довести тестовое покрытие — подготовить кодовую базу к production-сборке.

- [x] **Phase 20: Data Integrity** — UPSERT, foreign keys, платёжные поля, деанонимизация subject (completed 2026-03-24)
- [ ] **Phase 21: UI Fixes** — боковая панель, скачивание PDF, переобработка, warning_days, bulk status
- [ ] **Phase 22: Code Cleanup** — удаление Streamlit, legacy-кода, починка тестов
- [ ] **Phase 23: Production Readiness** — тесты для непокрытых модулей, офлайн-ресурсы, requirements.txt, локальная модель

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
**Plans**: TBD
**UI hint**: yes

### Phase 22: Code Cleanup
**Goal**: Кодовая база содержит только живой код — старый UI и мёртвые функции удалены, все тесты зелёные
**Depends on**: Phase 21
**Requirements**: CLEAN-01, CLEAN-02, CLEAN-03
**Success Criteria** (what must be TRUE):
  1. Файл main.py (Streamlit, 1700+ строк) удалён — `streamlit run` не запускает приложение
  2. Legacy-функции и дубликаты в backend удалены — нет dead code warnings в codebase
  3. `pytest` проходит без FAIL и xfail — все 268+ тестов зелёные
**Plans**: TBD

### Phase 23: Production Readiness
**Goal**: Приложение работает офлайн, устанавливается на чистой машине и запускает локальную модель без ручной настройки
**Depends on**: Phase 22
**Requirements**: PROD-01, PROD-02, PROD-03, PROD-04
**Success Criteria** (what must be TRUE):
  1. Тесты для scanner, extractor, reporter, postprocessor, controller написаны и проходят
  2. Приложение запускается без интернета — шрифты и FullCalendar подгружаются из локальных файлов
  3. `pip install -r requirements.txt` устанавливает все зависимости на чистом окружении без ошибок
  4. Локальная QWEN-модель находит llama-server и проверяет качество через провайдер-систему
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-19. Phases 1-19 | v0.4–v0.7.1 | — | Complete | 2026-03-22 |
| 20. Data Integrity | v0.8 | 1/1 | Complete    | 2026-03-24 |
| 21. UI Fixes | v0.8 | 0/? | Not started | - |
| 22. Code Cleanup | v0.8 | 0/? | Not started | - |
| 23. Production Readiness | v0.8 | 0/? | Not started | - |
