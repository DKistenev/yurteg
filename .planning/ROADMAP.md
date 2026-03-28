# Roadmap: ЮрТэг — v1.0 Hackathon-Ready Frontend

## Milestones

- ✅ **v0.9 Backend Hardening** — Phases 28–31 (shipped 2026-03-27)
- 🚧 **v1.0 Hackathon-Ready** — Phases 32–37 (in progress)

## Phases

<details>
<summary>✅ Previous milestones (Phases 1–31) — SHIPPED</summary>

Phases 1–6: v0.4 Архитектура и функционал
Phases 7–13: v0.6 UI-редизайн
Phases 14–17: v0.7 Визуальный продукт
Phases 18–19: v0.7.1 UI Polish & Fixes
Phases 20–23: v0.8 Hardening & Cleanup
Phases 28–31: v0.9 Backend Hardening

</details>

### 🚧 v1.0 Hackathon-Ready Frontend (In Progress)

**Milestone Goal:** Устранить все баги из аудита и довести каждый экран до демо-качества — приложение должно быть стабильным для живой демонстрации на хакатоне.

- [ ] **Phase 32: P0 Critical Fixes** — Шрифты, AG Grid API, двойные вызовы — без этого приложение выглядит сломанным
- [ ] **Phase 33: Code Quality & Error Resilience** — P1 фиксы: inline colors → tokens, a11y, дублированный код, loading/error states
- [ ] **Phase 34: Registry & Document Card** — Поиск, календарь, превью файлов, feedback при сохранении
- [ ] **Phase 35: Templates, Settings & Onboarding** — Visual consistency вспомогательных экранов, wizard end-to-end
- [ ] **Phase 36: Cross-Scope Integration** — Подключение STATUS_LABELS, APP_VERSION, убрать dict cast (ждёт CalmBridge)
- [ ] **Phase 37: Final Visual Pass** — Spacing, typography, animations — консистентность по всем экранам перед хакатоном

## Phase Details

### Phase 32: P0 Critical Fixes
**Goal**: Устранить критические баги, из-за которых приложение выглядит сломанным при первом запуске
**Depends on**: Nothing (first phase of milestone)
**Requirements**: AUDIT-01, AUDIT-02, AUDIT-03
**Success Criteria** (what must be TRUE):
  1. IBM Plex Sans шрифт отображается на всех экранах (не системный fallback)
  2. AG Grid таблица реестра работает без console errors (checkboxSelection через gridOptions)
  3. Виджет дедлайнов в реестре обновляется ровно один раз, нет двойных вызовов
**Plans**: TBD
**UI hint**: yes

### Phase 33: Code Quality & Error Resilience
**Goal**: Устранить P1 технический долг и добавить graceful degradation при сбоях бэкенда
**Depends on**: Phase 32
**Requirements**: AUDIT-04, AUDIT-05, AUDIT-06, AUDIT-07, ERRES-01, ERRES-02
**Success Criteria** (what must be TRUE):
  1. Все цвета в компонентах идут из CSS custom properties (нет inline hardcoded hex)
  2. Bulk action кнопки доступны с клавиатуры (Tab + Enter работают)
  3. При падении обработки документов пользователь видит error toast, приложение не зависает
  4. При недоступности llama-server пользователь видит понятное сообщение с рекомендацией
  5. _MONTHS_RU / _format_date_ru существуют в одном месте, без дублей в разных файлах
**Plans**: TBD
**UI hint**: yes

### Phase 34: Registry & Document Card
**Goal**: Основные рабочие экраны (реестр + карточка документа) работают без замечаний при демо
**Depends on**: Phase 33
**Requirements**: REG-01, REG-02, REG-03, DOC-01, DOC-02
**Success Criteria** (what must be TRUE):
  1. Поле поиска реестра имеет иконку лупы и кнопку очистки, работает с клавиатуры
  2. Мини-календарь позволяет переключаться между месяцами кнопками < >
  3. Вкладка «На этой неделе» показывает только будущие события, не прошедшие
  4. Карточка документа показывает превью PDF/DOCX справа в двухколоночном layout
  5. При потере фокуса на поле заметки появляется toast «Сохранено»
**Plans**: TBD
**UI hint**: yes

### Phase 35: Templates, Settings & Onboarding
**Goal**: Вспомогательные экраны визуально консистентны и работают end-to-end
**Depends on**: Phase 33
**Requirements**: TMPL-01, SETT-01, ONBR-01
**Success Criteria** (what must be TRUE):
  1. Страница шаблонов: empty state отображается корректно, карточки консистентны с дизайн-системой
  2. Настройки: клик по summary card прокручивает к соответствующей секции
  3. Onboarding wizard и гид-тур проходятся от начала до конца без ошибок
**Plans**: TBD
**UI hint**: yes

### Phase 36: Cross-Scope Integration
**Goal**: Подключить единые STATUS_LABELS, APP_VERSION и убрать защитные cast-ы после поставки CalmBridge
**Depends on**: Phase 35 + CalmBridge commits (lifecycle_service STATUS_LABELS, config.py APP_VERSION, database.py dict-only)
**Requirements**: XSCOPE-01, XSCOPE-02, XSCOPE-03
**Success Criteria** (what must be TRUE):
  1. Footer показывает актуальный номер версии из config.py (не хардкод «v0.7.1»)
  2. split_panel использует STATUS_LABELS из lifecycle_service, нет дублированного _STATUS_STYLE
  3. registry.py не делает dict(doc) cast — данные из database.py уже dict
**Plans**: TBD
**UI hint**: yes

### Phase 37: Final Visual Pass
**Goal**: Все экраны выглядят консистентно и полированно — приложение готово к демо на хакатоне
**Depends on**: Phase 36
**Requirements**: VIS-01
**Success Criteria** (what must be TRUE):
  1. Spacing, typography и анимации консистентны на всех 4 основных экранах (реестр, карточка, шаблоны, настройки)
  2. Нет видимых «сырых» элементов или несоответствий дизайн-системе при прохождении demo flow
**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 32. P0 Critical Fixes | v1.0 | 0/TBD | Not started | - |
| 33. Code Quality & Error Resilience | v1.0 | 0/TBD | Not started | - |
| 34. Registry & Document Card | v1.0 | 0/TBD | Not started | - |
| 35. Templates, Settings & Onboarding | v1.0 | 0/TBD | Not started | - |
| 36. Cross-Scope Integration | v1.0 | 0/TBD | Not started | - |
| 37. Final Visual Pass | v1.0 | 0/TBD | Not started | - |
