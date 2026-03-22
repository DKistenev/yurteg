# Roadmap: ЮрТэг

## Milestones

- ✅ **v0.4 Архитектура и функционал** — Phases 1-3 (shipped 2026-03-20)
- ✅ **v0.5 Локальная LLM** — Phases 4-6 (shipped 2026-03-21)
- ✅ **v0.6 UI-редизайн** — Phases 7-13 (shipped 2026-03-22)
- ✅ **v0.7 Визуальный продукт** — Phases 14-17 (shipped 2026-03-22)
- 🚧 **v0.7.1 UI Polish & Fixes** — Phases 18-19 (in progress)

## Phases

<details>
<summary>✅ v0.4 Архитектура и функционал (Phases 1-3) — SHIPPED 2026-03-20</summary>

Full details: `.planning/milestones/v0.4-ROADMAP.md`

</details>

<details>
<summary>✅ v0.5 Локальная LLM (Phases 4-6) — SHIPPED 2026-03-21</summary>

Full details: `.planning/milestones/v0.5-ROADMAP.md`

</details>

<details>
<summary>✅ v0.6 UI-редизайн (Phases 7-13) — SHIPPED 2026-03-22</summary>

Full details: `.planning/milestones/v0.6-ROADMAP.md`

</details>

<details>
<summary>✅ v0.7 Визуальный продукт (Phases 14-17) — SHIPPED 2026-03-22</summary>

Full details: `.planning/milestones/v0.7-ROADMAP.md`

</details>

### 🚧 v0.7.1 UI Polish & Fixes (In Progress)

**Milestone Goal:** Починить все проблемы из аудита v0.7 — layout, onboarding, demo-данные, баги

- [ ] **Phase 18: Layout + Visual Fixes** — stats bar, центрирование, лого, footer, segments, CSS cleanup
- [ ] **Phase 19: Onboarding + Demo Data** — guided tour, кнопка тура, demo-данные, web mode fallback

## Phase Details

### Phase 18: Layout + Visual Fixes
**Goal**: Все страницы центрированы, stats bar работает, лого правильное, footer по центру, visual polish
**Depends on**: Phase 17 (v0.7 shipped)
**Requirements**: LAY-01, LAY-02, LAY-03, LAY-04, LAY-05, LAY-06, LAY-07, BRND-01, BRND-02, BRND-03, PLSH-01, PLSH-02, PLSH-03, PLSH-04, RBST-02, RBST-03
**Success Criteria** (what must be TRUE):
  1. Stats bar — горизонтальная раскладка с числами и labels в одном контейнере
  2. Registry, templates, settings — контент центрирован с max-w, не прижат влево
  3. Footer «ЮрТэг v0.7.1» по центру страницы
  4. Лого: «Юр» в indigo квадрате + «Тэг» белым
  5. Inactive segments с border/bg, calendar toggle с labels
  6. hero-enter:nth-child(5) работает, dead CSS удалён
**Plans**: TBD
**UI hint**: yes

### Phase 19: Onboarding + Demo Data
**Goal**: Юрист открывает приложение и сразу понимает что делать — guided tour, demo-данные, web mode работает
**Depends on**: Phase 18
**Requirements**: ONBR-01, ONBR-02, ONBR-03, PLSH-05, RBST-01
**Success Criteria** (what must be TRUE):
  1. Guided tour с spotlight запускается при первом входе — подсвечивает кнопки, объясняет в карточках
  2. Кнопка «Гид по приложению» в header или settings для повторного запуска
  3. Кнопка «Тестовые документы» в empty state загружает demo-данные и показывает реестр с документами
  4. Template empty state показывает demo-карточку как пример
  5. В web mode file picker работает через upload fallback вместо native dialog
**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 18. Layout + Visual Fixes | v0.7.1 | 0/TBD | Not started | - |
| 19. Onboarding + Demo Data | v0.7.1 | 0/TBD | Not started | - |
