# Roadmap: ЮрТэг — v1.0 Hackathon-Ready

## Milestones

- ✅ **v0.9 Backend Hardening** — Phases 28–31 (shipped 2026-03-27)
- 🚧 **v1.0 Hackathon-Ready Frontend** — Phases 32–37 (VioletRiver)
- 🚧 **v1.0 Hackathon-Ready Backend** — Phases 38–43 (CalmBridge)

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
- [x] **Phase 33: Code Quality & Error Resilience** — P1 фиксы: inline colors → tokens, a11y, дублированный код, loading/error states
- [x] **Phase 34: Registry & Document Card** — Поиск, календарь, превью файлов, feedback при сохранении
- [x] **Phase 35: Templates, Settings & Onboarding** — Visual consistency вспомогательных экранов, wizard end-to-end
- [ ] **Phase 36: Cross-Scope Integration** — Подключение STATUS_LABELS, APP_VERSION, убрать dict cast (ждёт CalmBridge)
- [ ] **Phase 37: Final Visual Pass** — Spacing, typography, animations — консистентность по всем экранам перед хакатоном
- [ ] **Phase 38: Cross-Scope + Config Hardening** — Разблокировать VioletRiver + Config __post_init__ + atomic settings
- [ ] **Phase 39: Provider Cleanup** — Timeout, get_logprobs контракт, API key validation, resource cleanup
- [ ] **Phase 40: Data Integrity** — contract_number chain, деанонимизация, truncation flag, redline дата
- [ ] **Phase 41: Thread Safety** — RLock, locks на read-методы, атомарные операции, llama_server race fix
- [ ] **Phase 42: Error Handling** — Bare excepts → конкретные, input validation guards, GBNF fail-loud
- [ ] **Phase 43: Test Coverage** — 15 test gaps: concurrent writes, migrations, payment edges, helpers

## Phase Details

### Phase 32: P0 Critical Fixes
**Goal**: Устранить критические баги, из-за которых приложение выглядит сломанным при первом запуске
**Depends on**: Nothing (first phase of milestone)
**Requirements**: AUDIT-01, AUDIT-02, AUDIT-03
**Success Criteria** (what must be TRUE):
  1. IBM Plex Sans шрифт отображается на всех экранах (не системный fallback)
  2. AG Grid таблица реестра работает без console errors (checkboxSelection через gridOptions)
  3. Виджет дедлайнов в реестре обновляется ровно один раз, нет двойных вызовов
**Plans**: 1 plan
Plans:
- [ ] 32-01-PLAN.md — Три P0 фикса: static files, AG Grid rowSelection v32, дедлайн дубли
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
**Plans**: 2 plans
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
**Plans**: 2 plans
**UI hint**: yes

### Phase 35: Templates, Settings & Onboarding
**Goal**: Вспомогательные экраны визуально консистентны и работают end-to-end
**Depends on**: Phase 33
**Requirements**: TMPL-01, SETT-01, ONBR-01
**Success Criteria** (what must be TRUE):
  1. Страница шаблонов: empty state отображается корректно, карточки консистентны с дизайн-системой
  2. Настройки: клик по summary card прокручивает к соответствующей секции
  3. Onboarding wizard и гид-тур проходятся от начала до конца без ошибок
**Plans**: 2 plans
**UI hint**: yes

### Phase 36: Cross-Scope Integration
**Goal**: Подключить единые STATUS_LABELS, APP_VERSION и убрать защитные cast-ы после поставки CalmBridge
**Depends on**: Phase 35 + CalmBridge commits (lifecycle_service STATUS_LABELS, config.py APP_VERSION, database.py dict-only)
**Requirements**: XSCOPE-01, XSCOPE-02, XSCOPE-03
**Success Criteria** (what must be TRUE):
  1. Footer показывает актуальный номер версии из config.py (не хардкод «v0.7.1»)
  2. split_panel использует STATUS_LABELS из lifecycle_service, нет дублированного _STATUS_STYLE
  3. registry.py не делает dict(doc) cast — данные из database.py уже dict
**Plans**: 2 plans
**UI hint**: yes

### Phase 37: Final Visual Pass
**Goal**: Все экраны выглядят консистентно и полированно — приложение готово к демо на хакатоне
**Depends on**: Phase 36
**Requirements**: VIS-01
**Success Criteria** (what must be TRUE):
  1. Spacing, typography и анимации консистентны на всех 4 основных экранах (реестр, карточка, шаблоны, настройки)
  2. Нет видимых «сырых» элементов или несоответствий дизайн-системе при прохождении demo flow
**Plans**: 2 plans
**UI hint**: yes

### Phase 38: Cross-Scope + Config Hardening
**Goal**: Разблокировать VioletRiver Phase 36 и сделать Config безопасным
**Depends on**: Nothing (first backend phase)
**Requirements**: XSCOPE-04, XSCOPE-05, XSCOPE-06, CONF-01, CONF-02, CONF-03, CONF-04, CONF-05, CONF-06
**Success Criteria** (what must be TRUE):
  1. `from config import APP_VERSION` работает, footer показывает актуальную версию
  2. `STATUS_LABELS["terminated"]` содержит 4-й элемент css_class (Tailwind classes)
  3. `db.get_contract_by_id(id)` возвращает dict, не sqlite3.Row
  4. `Config(llama_server_port=-1)` поднимает ValueError
  5. `active_model` возвращает корректное имя модели для текущего provider
**Plans**: 2 plans

### Phase 39: Provider Cleanup
**Goal**: LLM провайдеры не зависают, имеют явный контракт, валидируют ключи
**Depends on**: Phase 38 (Config.ai_disable_thinking resolved)
**Requirements**: PROV-01, PROV-02, PROV-03, PROV-04, PROV-05, PROV-06, PROV-07, PROV-08, PROV-09
**Success Criteria** (what must be TRUE):
  1. OllamaProvider timeout = 120s read (холодный старт не вызывает fallback)
  2. ZAIProvider("") raises ValueError, не молча принимает пустой ключ
  3. `LLMProvider.get_logprobs()` определён в base class с default `return {}`
  4. `provider.close()` метод существует на всех провайдерах
**Plans**: 2 plans

### Phase 40: Data Integrity
**Goal**: contract_number в БД, полная деанонимизация, truncation tracking
**Depends on**: Phase 38 (Config ready)
**Requirements**: DINT-01, DINT-02, DINT-03, DINT-04, DINT-05, DINT-06, DINT-07
**Success Criteria** (what must be TRUE):
  1. `SELECT contract_number FROM contracts` не крашится (миграция v10 применена)
  2. Деанонимизация применяется ко всем строковым полям ContractMetadata (не только 4)
  3. Redline DOCX содержит актуальную дату, не "2026-01-01"
  4. Telegram sync: отсутствие ключа в item не крашит обработку
**Plans**: 2 plans

### Phase 41: Thread Safety
**Goal**: 5 параллельных потоков работают без OperationalError и deadlock
**Depends on**: Phase 40 (contract_number exists for version_service)
**Requirements**: TSAFE-01, TSAFE-02, TSAFE-03, TSAFE-04, TSAFE-05, TSAFE-06, TSAFE-07, TSAFE-08
**Success Criteria** (what must be TRUE):
  1. `database.py` использует RLock (не Lock) — вложенные вызовы не deadlock'ят
  2. `get_all_results()`, `get_stats()`, `is_processed()` обёрнуты в `with self._lock:`
  3. `version_service.ensure_embedding()` атомарен (check-and-store под одним lock)
  4. `save_setting()` атомарен (tempfile → os.replace под Lock)
**Plans**: 2 plans

### Phase 42: Error Handling
**Goal**: Нет bare excepts, все публичные функции валидируют входы
**Depends on**: Phase 41
**Requirements**: ERRH-01 through ERRH-18
**Success Criteria** (what must be TRUE):
  1. `grep -r "except:" modules/ services/` возвращает 0 результатов (нет bare except)
  2. `payment_service.unroll_payments(start, end, -100, "monthly")` raises ValueError
  3. GBNF grammar file missing → FileNotFoundError (не silent None)
  4. `_split_sentences(None)` возвращает [], не AttributeError
  5. `import json` нет внутри функций (module-level only)
**Plans**: 2 plans

### Phase 43: Test Coverage
**Goal**: 15 test gaps закрыты, все новые фиксы покрыты тестами
**Depends on**: Phases 41 + 42
**Requirements**: TEST-01 through TEST-15
**Success Criteria** (what must be TRUE):
  1. Concurrent write test: 5 потоков пишут в database.py одновременно — 0 OperationalError
  2. Migration tests: каждая миграция v2-v9 тестируется независимо на свежей БД
  3. Payment edge cases: start>end, amount=0, amount<0, max_iter — все проверены
  4. `conftest.py` содержит autouse fixture для reset `version_service._model`
  5. `pytest` проходит зелёным с новыми тестами
**Plans**: 2 plans

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 32. P0 Critical Fixes | v1.0-FE | 0/1 | Planned | - |
| 33. Code Quality & Error Resilience | v1.0-FE | 1/1 | Complete | 2026-03-28 |
| 34. Registry & Document Card | v1.0-FE | 1/1 | Complete | 2026-03-28 |
| 35. Templates, Settings & Onboarding | v1.0-FE | 1/1 | Complete | 2026-03-28 |
| 36. Cross-Scope Integration | v1.0-FE | 0/TBD | Not started | - |
| 37. Final Visual Pass | v1.0-FE | 0/TBD | Not started | - |
| 38. Cross-Scope + Config Hardening | v1.0-BE | 0/2 | Planned | - |
| 39. Provider Cleanup | v1.0-BE | 0/TBD | Not started | - |
| 40. Data Integrity | v1.0-BE | 0/TBD | Not started | - |
| 41. Thread Safety | v1.0-BE | 0/TBD | Not started | - |
| 42. Error Handling | v1.0-BE | 0/TBD | Not started | - |
| 43. Test Coverage | v1.0-BE | 0/TBD | Not started | - |
