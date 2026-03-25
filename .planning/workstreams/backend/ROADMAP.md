---
milestone: v0.9
milestone_name: Backend Hardening
workstream: backend
phases: 4
requirements_total: 21
requirements_mapped: 21
phase_start: 28
phase_end: 31
last_updated: "2026-03-26"
---

# Roadmap: ЮрТэг v0.9 Backend Hardening

**Milestone goal:** Привести бэкенд в рабочее состояние — снести устаревшую валидацию, доработать GBNF, убрать Excel, реализовать полноценный redline и векторную систему, оптимизировать под локальную модель.

**Phases:** 4 (Phase 28 → 31)
**Coverage:** 21/21 requirements mapped

---

## Phases

- [x] **Phase 28: Cleanup** — Удалить validator, reporter, мёртвый код; кодовая база чистая и стабильная (completed 2026-03-25)
- [ ] **Phase 29: AI Pipeline** — Доработать GBNF, реализовать confidence через logprobs, починить постпроцессор
- [ ] **Phase 30: Redline + Vectors** — Word-level redline DOCX, векторное кэширование шаблонов, миграция v8
- [ ] **Phase 31: UI Wire-up** — Открытие файла, bulk delete, дедлайны, кнопка «Сохранить как шаблон»

---

## Phase Details

### Phase 28: Cleanup
**Goal**: Кодовая база содержит только живой код — без validator, reporter, deprecated функций, мёртвых import-цепочек
**Depends on**: Nothing (first phase of milestone)
**Requirements**: CLEAN-01, CLEAN-02, CLEAN-03, CLEAN-04, CLEAN-05, STAB-01, STAB-02
**Success Criteria** (what must be TRUE):
  1. Приложение запускается без ошибок после удаления validator.py и reporter.py
  2. controller.py не импортирует validator или reporter — grep возвращает ноль совпадений
  3. Тест-сюит проходит без патчей на удалённые модули
  4. Пользователь видит предупреждение в UI, если документ обрезан до 30K символов
  5. llama-server регистрирует atexit-хук ровно один раз при запуске приложения
**Plans**: 3 plans
Plans:
- [x] 28-01-PLAN.md — Удалить validator.py и reporter.py из controller + тестов
- [ ] 28-02-PLAN.md — Удалить _create_client/_try_model, thinking mode, мёртвые imports
- [x] 28-03-PLAN.md — atexit fix в llama_server + truncation warning в ai_extractor

### Phase 29: AI Pipeline
**Goal**: AI-слой выдаёт реальный confidence через logprobs, GBNF-грамматика отражает актуальную схему, постпроцессор не ломает латинские аббревиатуры
**Depends on**: Phase 28
**Requirements**: AI-01, AI-02, AI-03
**Success Criteria** (what must be TRUE):
  1. Поле confidence в ответе модели вычислено из logprobs, а не взято из GBNF-вывода
  2. GBNF не содержит поля confidence; дата и contract_number проходят грамматику без ошибок
  3. Аббревиатуры NDA, SLA, GPS, ИНН не транслитерируются и не заменяются в cyrillic_only профиле
  4. Документ с низким logprobs-confidence помечается для перепроверки (отображается в карточке)
**Plans**: 3 plans
Plans:
- [ ] 29-01-PLAN.md — GBNF: убрать confidence, добавить contract_number, ужесточить даты; убрать --grammar-file из llama_server
- [ ] 29-02-PLAN.md — Двухзапросный flow: grammar в request body + logprobs confidence в OllamaProvider и ai_extractor
- [ ] 29-03-PLAN.md — Whitelist аббревиатур NDA/SLA/GPS/ИНН в постпроцессоре (cyrillic_only профиль)

### Phase 30: Redline + Vectors
**Goal**: Redline-DOCX генерируется на уровне слов и открывается в Word без диалога «восстановить документ»; шаблонные embeddings кэшируются и используют полный текст документа
**Depends on**: Phase 28
**Requirements**: RED-01, RED-02, RED-03, VEC-01, VEC-02, VEC-03, VEC-04
**Success Criteria** (what must be TRUE):
  1. Скачанный redline.docx открывается в Microsoft Word 365 с видимыми track changes без предупреждений о повреждении файла
  2. Пользователь видит изменения на уровне слов (не предложений) при сравнении версий документа
  3. Сравнение с шаблоном и сравнение версий используют один redline-движок — один файл скачивается в обоих случаях
  4. После пометки документа как шаблона автоподбор шаблона находит его при следующей обработке похожего документа
  5. Миграция v8 применяется автоматически при запуске — таблица template_embeddings создана
**Plans**: TBD

### Phase 31: UI Wire-up
**Goal**: Все реализованные backend-функции доступны из UI — открытие файла, удаление из реестра, дедлайны, сохранение шаблона
**Depends on**: Phase 29, Phase 30
**Requirements**: WIRE-01, WIRE-02, WIRE-03, WIRE-04
**Success Criteria** (what must be TRUE):
  1. Кнопка «Открыть файл» в карточке документа открывает оригинальный PDF/DOCX в системном приложении (Finder/Word/Preview)
  2. Bulk delete удаляет выбранные документы из реестра и БД — после удаления они не появляются при обновлении страницы
  3. Виджет дедлайнов в реестре отображает документы, требующие внимания, — список формируется через get_attention_required()
  4. Кнопка «Сохранить как шаблон» в карточке документа вызывает mark_contract_as_template() и отображает подтверждение
**Plans**: TBD
**UI hint**: yes

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 28. Cleanup | 2/3 | Complete    | 2026-03-25 |
| 29. AI Pipeline | 0/3 | Planned | - |
| 30. Redline + Vectors | 0/? | Not started | - |
| 31. UI Wire-up | 0/? | Not started | - |

---

## Coverage Map

| Requirement | Phase |
|-------------|-------|
| CLEAN-01 | Phase 28 |
| CLEAN-02 | Phase 28 |
| CLEAN-03 | Phase 28 |
| CLEAN-04 | Phase 28 |
| CLEAN-05 | Phase 28 |
| STAB-01 | Phase 28 |
| STAB-02 | Phase 28 |
| AI-01 | Phase 29 |
| AI-02 | Phase 29 |
| AI-03 | Phase 29 |
| RED-01 | Phase 30 |
| RED-02 | Phase 30 |
| RED-03 | Phase 30 |
| VEC-01 | Phase 30 |
| VEC-02 | Phase 30 |
| VEC-03 | Phase 30 |
| VEC-04 | Phase 30 |
| WIRE-01 | Phase 31 |
| WIRE-02 | Phase 31 |
| WIRE-03 | Phase 31 |
| WIRE-04 | Phase 31 |

**Total mapped:** 21/21

---

*Roadmap created: 2026-03-26*
*Last updated: 2026-03-26 — Phase 29 plans created (3 plans)*
