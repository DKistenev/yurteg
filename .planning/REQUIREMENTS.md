# Requirements: ЮрТэг v0.7

**Defined:** 2026-03-22
**Core Value:** Юрист загружает папку с документами и за 20 минут получает готовый реестр — без ручного ввода, без обучения, без «проекта внедрения»

## v0.7 Requirements

Полная переработка визуального слоя — из wireframe в дерзкий, уверенный продукт.

### Дизайн-система

- [x] **DSGN-01**: tokens.css с --yt-* переменными: палитра, spacing scale, shadows, radii
- [x] **DSGN-02**: app.colors() Quasar bridge — интеграция токенов с NiceGUI компонентами
- [x] **DSGN-03**: IBM Plex Sans weights 300/400/500/600/700 с размерной шкалой и ролевым маппингом (hero=text-4xl font-bold, page title=text-2xl font-semibold, section=text-xs uppercase tracking-wider, body=text-sm)
- [x] **DSGN-04**: @layer discipline — components + overrides для безопасных Quasar переопределений
- [x] **DSGN-05**: Фон контентных зон — не чисто белый (--yt-surface-bg), hero-зоны — тёмный accent surface; --nicegui-default-padding: 0 и --nicegui-default-gap: 0 в :root

### Header

- [x] **HEAD-01**: Dark chrome band — тёмный header как якорь визуальной идентичности
- [x] **HEAD-02**: Лого-марка «Ю» с accent цветом
- [x] **HEAD-03**: Accent CTA кнопка «Загрузить документы» (filled, не flat)
- [x] **HEAD-04**: Навигация с hover states и active indicator

### Splash

- [ ] **SPLS-01**: Hero-секция на весь экран с крупной типографикой и визуальной уверенностью
- [ ] **SPLS-02**: Dark accent surface для hero-зоны
- [ ] **SPLS-03**: Staggered entrance анимация элементов *(stretch — cut first if phase slips)*

### Registry

- [ ] **REGI-01**: Stats bar над реестром (документы · истекают · требуют внимания)
- [ ] **REGI-02**: Filled semantic status badges (green/amber/red) вместо text-only
- [ ] **REGI-03**: AG Grid theming через --ag-* CSS variables с .ag-theme-quartz scope
- [ ] **REGI-04**: Rich empty state — мощный CTA с визуальным якорем и карточками возможностей
- [ ] **REGI-05**: Заголовок «Документы» с визуальным весом
- [ ] **REGI-06**: Фильтр-бар с визуальным весом — segment buttons с filled active state

### Карточка документа

- [ ] **CARD-01**: Breadcrumbs навигация
- [ ] **CARD-02**: Структурированные секции с uppercase заголовками и 1px разделителями
- [ ] **CARD-03**: Визуально различимые блоки для метаданных (compact key-value), AI-ревью (accent border + иконка), версий (timeline-стиль) — не identical cards

### Шаблоны

- [ ] **TMPL-01**: Карточки с color-coded левой полосой (4px) по типу документа, иконкой типа в accent-цвете, shadow-md hover lift — визуально различимы друг от друга с первого взгляда
- [ ] **TMPL-02**: Цветные badges типов документов
- [ ] **TMPL-03**: Rich empty state — иконка + заголовок + описание что такое шаблоны и зачем, CTA «Добавить первый шаблон»

### Настройки

- [ ] **SETT-01**: Секции с заголовками, описаниями и визуальными разделителями
- [ ] **SETT-02**: Sidebar с визуальной структурой (активный пункт выделен, не голый текст)

### Анимации

- [ ] **ANIM-01**: Page transitions между экранами (fade/slide)
- [ ] **ANIM-02**: Stagger-эффекты при появлении карточек и строк таблицы
- [ ] **ANIM-03**: Micro-interactions на кнопках (ripple, scale)
- [ ] **ANIM-04**: Skeleton-loading вместо пустого экрана при загрузке данных

### Сквозное

- [ ] **XCUT-01**: Footer с версией приложения
- [ ] **XCUT-02**: Consistent hover states на всех интерактивных элементах
- [x] **XCUT-03**: Consistent spacing по всем экранам через токены
- [ ] **XCUT-04**: Visual seam check — все экраны визуально когерентны при навигации header→splash→registry→card→settings

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
| Sidebar navigation | Структурное изменение main.py, не визуальное; 3 таба не оправдывают |
| Parallax / scroll на splash | Splash — setup screen, не marketing page; анимация добавляет friction |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DSGN-01 | Phase 14 | Complete |
| DSGN-02 | Phase 14 | Complete |
| DSGN-03 | Phase 14 | Complete |
| DSGN-04 | Phase 14 | Complete |
| DSGN-05 | Phase 14 | Complete |
| XCUT-03 | Phase 14 | Complete |
| HEAD-01 | Phase 14 | Complete |
| HEAD-02 | Phase 14 | Complete |
| HEAD-03 | Phase 14 | Complete |
| HEAD-04 | Phase 14 | Complete |
| SPLS-01 | Phase 15 | Pending |
| SPLS-02 | Phase 15 | Pending |
| SPLS-03 | Phase 15 | Pending |
| REGI-01 | Phase 16 | Pending |
| REGI-02 | Phase 16 | Pending |
| REGI-03 | Phase 16 | Pending |
| REGI-04 | Phase 16 | Pending |
| REGI-05 | Phase 16 | Pending |
| REGI-06 | Phase 16 | Pending |
| CARD-01 | Phase 16 | Pending |
| CARD-02 | Phase 16 | Pending |
| CARD-03 | Phase 16 | Pending |
| TMPL-01 | Phase 17 | Pending |
| TMPL-02 | Phase 17 | Pending |
| TMPL-03 | Phase 17 | Pending |
| SETT-01 | Phase 17 | Pending |
| SETT-02 | Phase 17 | Pending |
| ANIM-01 | Phase 17 | Pending |
| ANIM-02 | Phase 17 | Pending |
| ANIM-03 | Phase 17 | Pending |
| ANIM-04 | Phase 17 | Pending |
| XCUT-01 | Phase 17 | Pending |
| XCUT-02 | Phase 17 | Pending |
| XCUT-04 | Phase 17 | Pending |

**Coverage:**
- v0.7 requirements: 34 total
- Mapped to phases: 34
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-22*
*Last updated: 2026-03-22 — post-review revision: +DSGN-05, +REGI-06, +XCUT-04, rewrote DSGN-03/TMPL-01/TMPL-03/CARD-03, 4 phases*
