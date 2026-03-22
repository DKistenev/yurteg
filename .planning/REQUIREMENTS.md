# Requirements: ЮрТэг v0.7.1

**Defined:** 2026-03-22
**Core Value:** Юрист загружает папку с документами и за 20 минут получает готовый реестр — без ручного ввода, без обучения, без «проекта внедрения»

## v0.7.1 Requirements

Bugfix/polish milestone — починить все проблемы из аудита v0.7.

### Layout

- [x] **LAY-01**: Stats bar — пересоздать labels ВНУТРИ flex-контейнера, горизонтальная раскладка «число · число · число»
- [x] **LAY-02**: Центрирование registry — max-w-6xl mx-auto, контент не прижат влево
- [x] **LAY-03**: Центрирование templates — max-w-5xl mx-auto
- [x] **LAY-04**: Центрирование settings — убрать min-h-screen, flex-1 для высоты
- [x] **LAY-05**: Footer по центру — justify-center вместо justify-end
- [x] **LAY-06**: Search input — max-w-lg вместо max-w-md
- [x] **LAY-07**: Stats bar bg — убрать bg-white или сделать когерентным с slate-100 фоном

### Branding

- [x] **BRND-01**: Лого «Юр» в квадрат + «Тэг» без квадрата
- [x] **BRND-02**: Inactive segment buttons — добавить border/bg, не flat text
- [x] **BRND-03**: Calendar toggle — добавить labels «Список» / «Календарь» или tooltips

### Onboarding

- [x] **ONBR-01**: Guided tour при первом открытии — spotlight на кнопки, карточки с описанием, кнопка «Продолжить»
- [x] **ONBR-02**: Кнопка «Начать тур» для повторного запуска guided tour в любой момент
- [ ] **ONBR-03**: Demo-данные — кнопка «Загрузить тестовые документы» в empty state для демонстрации реестра

### Polish

- [x] **PLSH-01**: Диалог «Новое пространство» — рестайл, не generic Quasar card
- [x] **PLSH-02**: Templates empty state — уменьшить py-20, поднять контент к заголовку
- [x] **PLSH-03**: hero-enter:nth-child(5) — добавить animation-delay: 400ms в design-system.css
- [x] **PLSH-04**: Dead CSS cleanup — удалить settings-nav-item, stats-item-clickable rules
- [ ] **PLSH-05**: Шаблоны empty state — показать demo-карточку как пример

### Robustness

- [x] **RBST-01**: webview.OPEN_DIALOG fallback для web mode — file upload вместо native picker
- [x] **RBST-02**: ARIA labels на stats bar, template cards, empty state CTA
- [x] **RBST-03**: AG Grid console warnings — suppress или fix deprecated API usage

## Out of Scope

| Feature | Reason |
|---------|--------|
| Новый функционал | Только фиксы и polish существующего |
| Full dark mode | Отдельный milestone |
| DMG/EXE сборка | v0.8 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| LAY-01 | Phase 18 | Complete |
| LAY-02 | Phase 18 | Complete |
| LAY-03 | Phase 18 | Complete |
| LAY-04 | Phase 18 | Complete |
| LAY-05 | Phase 18 | Complete |
| LAY-06 | Phase 18 | Complete |
| LAY-07 | Phase 18 | Complete |
| BRND-01 | Phase 18 | Complete |
| BRND-02 | Phase 18 | Complete |
| BRND-03 | Phase 18 | Complete |
| ONBR-01 | Phase 19 | Complete |
| ONBR-02 | Phase 19 | Complete |
| ONBR-03 | Phase 19 | Pending |
| PLSH-01 | Phase 18 | Complete |
| PLSH-02 | Phase 18 | Complete |
| PLSH-03 | Phase 18 | Complete |
| PLSH-04 | Phase 18 | Complete |
| PLSH-05 | Phase 19 | Pending |
| RBST-01 | Phase 19 | Complete |
| RBST-02 | Phase 18 | Complete |
| RBST-03 | Phase 18 | Complete |

**Coverage:**
- v0.7.1 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-22*
