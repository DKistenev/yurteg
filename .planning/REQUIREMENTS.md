# Requirements: ЮрТэг v0.7

**Defined:** 2026-03-22
**Core Value:** Юрист загружает папку с документами и за 20 минут получает готовый реестр — без ручного ввода, без обучения, без «проекта внедрения»

## v0.7 Requirements

Полная переработка визуального слоя — из wireframe в дерзкий, уверенный продукт.

### Дизайн-система

- [ ] **DSGN-01**: tokens.css с --yt-* переменными: палитра, spacing scale, shadows, radii
- [ ] **DSGN-02**: app.colors() Quasar bridge — интеграция токенов с NiceGUI компонентами
- [ ] **DSGN-03**: IBM Plex Sans weights 300/400/500/600/700 с размерной шкалой
- [ ] **DSGN-04**: @layer discipline — components + overrides для безопасных Quasar переопределений

### Header

- [ ] **HEAD-01**: Dark chrome band — тёмный header как якорь визуальной идентичности
- [ ] **HEAD-02**: Лого-марка «Ю» с accent цветом
- [ ] **HEAD-03**: Accent CTA кнопка «Загрузить документы» (filled, не flat)
- [ ] **HEAD-04**: Навигация с hover states и active indicator

### Splash

- [ ] **SPLS-01**: Hero-секция на весь экран с крупной типографикой и визуальной уверенностью
- [ ] **SPLS-02**: Dark accent surface для hero-зоны
- [ ] **SPLS-03**: Staggered entrance анимация элементов

### Registry

- [ ] **REGI-01**: Stats bar над реестром (документы · истекают · требуют внимания)
- [ ] **REGI-02**: Filled semantic status badges (green/amber/red) вместо text-only
- [ ] **REGI-03**: AG Grid theming через --ag-* CSS variables
- [ ] **REGI-04**: Rich empty state — карточки возможностей с иконками
- [ ] **REGI-05**: Заголовок «Документы» с визуальным весом

### Карточка документа

- [ ] **CARD-01**: Breadcrumbs навигация
- [ ] **CARD-02**: Структурированные секции с визуальными разделителями
- [ ] **CARD-03**: Карточки-блоки с тенями для метаданных, ревью, версий

### Шаблоны

- [ ] **TMPL-01**: Карточки с shadow-sm, border, rounded-xl
- [ ] **TMPL-02**: Цветные badges типов документов
- [ ] **TMPL-03**: Rich empty state для пустого списка шаблонов

### Настройки

- [ ] **SETT-01**: Секции с заголовками, описаниями и визуальными разделителями
- [ ] **SETT-02**: Sidebar с визуальной структурой (не голый текст)

### Анимации

- [ ] **ANIM-01**: Page transitions между экранами (fade/slide)
- [ ] **ANIM-02**: Stagger-эффекты при появлении карточек и строк таблицы
- [ ] **ANIM-03**: Micro-interactions на кнопках (ripple, scale)
- [ ] **ANIM-04**: Skeleton-loading вместо пустого экрана при загрузке данных

### Сквозное

- [ ] **XCUT-01**: Footer с версией приложения
- [ ] **XCUT-02**: Consistent hover states на всех интерактивных элементах
- [ ] **XCUT-03**: Consistent spacing по всем экранам через токены

## Future Requirements

- Полный dark mode (light ↔ dark toggle) — отдельный milestone
- Иллюстрации / SVG-графика для empty states
- Анимированные page transitions с shared element

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full dark mode toggle | Требует аудит ~2800 LOC, это отдельный milestone |
| backdrop-filter: blur() | CPU spikes в pywebview на macOS |
| Новые pip-зависимости | Всё реализуемо через CSS + существующий стек |
| Изменения функционала | Только визуал, логика не трогается |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DSGN-01 | Phase 14 | Pending |
| DSGN-02 | Phase 14 | Pending |
| DSGN-03 | Phase 14 | Pending |
| DSGN-04 | Phase 14 | Pending |
| HEAD-01 | Phase 14 | Pending |
| HEAD-02 | Phase 14 | Pending |
| HEAD-03 | Phase 14 | Pending |
| HEAD-04 | Phase 14 | Pending |
| SPLS-01 | Phase 15 | Pending |
| SPLS-02 | Phase 15 | Pending |
| SPLS-03 | Phase 15 | Pending |
| REGI-01 | Phase 15 | Pending |
| REGI-02 | Phase 15 | Pending |
| REGI-03 | Phase 15 | Pending |
| REGI-04 | Phase 15 | Pending |
| REGI-05 | Phase 15 | Pending |
| CARD-01 | Phase 15 | Pending |
| CARD-02 | Phase 15 | Pending |
| CARD-03 | Phase 15 | Pending |
| TMPL-01 | Phase 16 | Pending |
| TMPL-02 | Phase 16 | Pending |
| TMPL-03 | Phase 16 | Pending |
| SETT-01 | Phase 16 | Pending |
| SETT-02 | Phase 16 | Pending |
| ANIM-01 | Phase 16 | Pending |
| ANIM-02 | Phase 16 | Pending |
| ANIM-03 | Phase 16 | Pending |
| ANIM-04 | Phase 16 | Pending |
| XCUT-01 | Phase 16 | Pending |
| XCUT-02 | Phase 16 | Pending |
| XCUT-03 | Phase 14 | Pending |

**Coverage:**
- v0.7 requirements: 31 total
- Mapped to phases: 31
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-22*
*Last updated: 2026-03-22 — traceability mapped to Phases 14-16 (consolidated)*
