# Roadmap: ЮрТэг

## Milestones

- ✅ **v0.4 Архитектура и функционал** — Phases 1-3 (shipped 2026-03-20)
- ✅ **v0.5 Локальная LLM** — Phases 4-6 (shipped 2026-03-21)
- ✅ **v0.6 UI-редизайн** — Phases 7-13 (shipped 2026-03-22)
- 🚧 **v0.7 Визуальный продукт** — Phases 14-16 (in progress)

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

<details>
<summary>✅ v0.6 UI-редизайн (Phases 7-13) — SHIPPED 2026-03-22</summary>

- [x] Phase 7: App Scaffold + State Architecture (2/2 plans) — completed 2026-03-21
- [x] Phase 8: Registry View (3/3 plans) — completed 2026-03-21
- [x] Phase 9: Document Detail Card (2/2 plans) — completed 2026-03-21
- [x] Phase 10: Pipeline Wiring (2/2 plans) — completed 2026-03-21
- [x] Phase 11: Settings + Templates (3/3 plans) — completed 2026-03-22
- [x] Phase 12: Onboarding (2/2 plans) — completed 2026-03-22
- [x] Phase 13: Design Polish + Calendar (4/4 plans) — completed 2026-03-22

Full details: `.planning/milestones/v0.6-ROADMAP.md`

</details>

### 🚧 v0.7 Визуальный продукт (In Progress)

**Milestone Goal:** Полная переработка визуального слоя — из wireframe в дерзкий, уверенный продукт с характером

- [ ] **Phase 14: Фундамент — дизайн-система + header** — tokens.css, app.colors(), типографика, тёмный chrome header
- [ ] **Phase 15: Splash + Registry + Card** — hero splash, stats bar, AG Grid theming, карточка документа
- [ ] **Phase 16: Полировка — templates, settings, анимации, сквозное** — карточки, секции, transitions, footer

## Phase Details

### Phase 14: Фундамент — дизайн-система + header
**Goal**: Единый визуальный язык установлен + тёмный chrome header как якорь — фундамент для всех экранов
**Depends on**: Phase 13 (v0.6 shipped)
**Requirements**: DSGN-01, DSGN-02, DSGN-03, DSGN-04, XCUT-03, HEAD-01, HEAD-02, HEAD-03, HEAD-04
**Success Criteria** (what must be TRUE):
  1. Все цвета, отступы, тени и радиусы приложения читаются из --yt-* CSS переменных в tokens.css
  2. IBM Plex Sans грузится с весами 300/400/500/600/700, все визуально различимы
  3. app.colors() вызван в main.py — Quasar primary/secondary синхронизированы с токенами
  4. CSS вне @layer не ломает существующие стили (layer-дисциплина работает)
  5. Header тёмный на всех страницах, лого-марка «Ю» слева, filled indigo CTA, active tab indicator
  6. FullCalendar calendar view открывается без артефактов после --yt-* переменных
**Plans**: TBD
**UI hint**: yes

### Phase 15: Splash + Registry + Card
**Goal**: Три главных поверхности приложения обретают визуальный характер — hero splash, реестр с данными, карточка документа
**Depends on**: Phase 14
**Requirements**: SPLS-01, SPLS-02, SPLS-03, REGI-01, REGI-02, REGI-03, REGI-04, REGI-05, CARD-01, CARD-02, CARD-03
**Success Criteria** (what must be TRUE):
  1. Splash занимает весь экран с тёмным фоном и крупным заголовком IBM Plex Sans 700 — первое впечатление не wireframe
  2. Stats bar над реестром показывает актуальные числа (документы / истекают / требуют внимания)
  3. Статусные бейджи в AG Grid отображаются цветными filled pills (зелёный/жёлтый/красный), а не текстом
  4. Карточка документа открывается с breadcrumbs и структурированными секциями с разделителями
  5. Rich empty state реестра показывает карточки возможностей с иконками (не пустой экран)
**Plans**: TBD
**UI hint**: yes

### Phase 16: Полировка — templates, settings, анимации, сквозное
**Goal**: Все оставшиеся экраны получают визуальную структуру + приложение ощущается живым и завершённым
**Depends on**: Phase 15
**Requirements**: TMPL-01, TMPL-02, TMPL-03, SETT-01, SETT-02, ANIM-01, ANIM-02, ANIM-03, ANIM-04, XCUT-01, XCUT-02
**Success Criteria** (what must be TRUE):
  1. Карточки шаблонов с тенями и rounded-xl, цветные badges типов
  2. Настройки разделены на секции с заголовками и 1px разделителями, sidebar с выделенным пунктом
  3. Переходы между страницами анимированы (fade/slide)
  4. Все интерактивные элементы реагируют на hover
  5. Footer с версией на всех страницах
  6. Skeleton-loader при загрузке реестра
**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Инфраструктура | v0.4 | 4/4 | Complete | 2026-03-19 |
| 2. Жизненный цикл | v0.4 | 8/8 | Complete | 2026-03-19 |
| 3. Интеграции | v0.4 | 12/12 | Complete | 2026-03-20 |
| 4. Сервер и провайдер | v0.5 | 2/2 | Complete | 2026-03-21 |
| 5. Пайплайн с локальной LLM | v0.5 | 1/1 | Complete | 2026-03-21 |
| 6. Проводка ai_extractor | v0.5 | 1/1 | Complete | 2026-03-21 |
| 7. App Scaffold + State | v0.6 | 2/2 | Complete | 2026-03-21 |
| 8. Registry View | v0.6 | 3/3 | Complete | 2026-03-21 |
| 9. Document Detail Card | v0.6 | 2/2 | Complete | 2026-03-21 |
| 10. Pipeline Wiring | v0.6 | 2/2 | Complete | 2026-03-21 |
| 11. Settings + Templates | v0.6 | 3/3 | Complete | 2026-03-22 |
| 12. Onboarding | v0.6 | 2/2 | Complete | 2026-03-22 |
| 13. Design Polish + Calendar | v0.6 | 4/4 | Complete | 2026-03-22 |
| 14. Фундамент: дизайн-система + header | v0.7 | 0/TBD | Not started | - |
| 15. Splash + Registry + Card | v0.7 | 0/TBD | Not started | - |
| 16. Полировка: templates, settings, анимации | v0.7 | 0/TBD | Not started | - |
