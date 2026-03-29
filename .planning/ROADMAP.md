# Roadmap: ЮрТэг — v1.0 Hackathon-Ready

## Milestones

- ✅ **v0.9 Backend Hardening** — Phases 28–31 (shipped 2026-03-27)
- 🚧 **v1.0 Hackathon-Ready** — Phases 32–43 (Frontend: VioletRiver, Backend: CalmBridge)

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

### ✅ v1.0 Hackathon-Ready (Shipped: 2026-03-29)

**Milestone Goal:** Устранить все баги из аудита и довести каждый экран до демо-качества — приложение должно быть стабильным для живой демонстрации на хакатоне.

- [x] **Phase 32: P0 Critical Fixes** — Шрифты, AG Grid API, двойные вызовы
- [x] **Phase 33: Code Quality & Error Resilience** — P1 фиксы: inline colors → tokens, a11y, loading/error states
- [x] **Phase 34: Registry & Document Card** — Поиск, календарь, превью файлов, feedback при сохранении
- [x] **Phase 35: Templates, Settings & Onboarding** — Visual consistency, wizard end-to-end
- [x] **Phase 36: Cross-Scope Integration** — STATUS_LABELS, APP_VERSION, убран dict cast
- [x] **Phase 37: Final Visual Pass** — Spacing, typography, animations — консистентность
- [x] **Phase 38: Cross-Scope + Config Hardening** — Config __post_init__ + atomic settings
- [x] **Phase 39: Provider Cleanup** — Timeout, get_logprobs контракт, API key validation
- [x] **Phase 40: Data Integrity** — contract_number chain, деанонимизация, redline дата
- [x] **Phase 41: Thread Safety** — RLock, locks на read-методы, атомарные операции
- [x] **Phase 42: Error Handling** — Bare excepts → конкретные, input validation, GBNF fail-loud
- [x] **Phase 43: Test Coverage** — 15 test gaps закрыты
- [x] **Phase 44: Logging & Single Instance** — Файловые логи, BetterStack Logtail, file lock (completed 2026-03-29)
- [x] **Phase 45: Icon & Splash** — Иконка «Ю» .icns/.ico, splash screen (completed 2026-03-29)
- [ ] **Phase 46: Offline & Disk Safety** — Offline first run, проверка места на диске
- [ ] **Phase 47: Runtime Safety** — storage_secret, quarantine, freeze_support, hidden imports
- [ ] **Phase 48: Feature Verification** — Redline, document preview, Guide button

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

### Phase 44: Logging & Single Instance
**Goal**: Приложение пишет структурированные логи локально и в BetterStack, безопасно идентифицирует тестеров, не пропускает контент документов, не запускается дважды
**Depends on**: Nothing (first phase of v1.2)
**Requirements**: LOG-01, LOG-02, LOG-03, LOG-04, LOG-05
**Success Criteria** (what must be TRUE):
  1. Файл ~/.yurteg/logs/yurteg.log создаётся при запуске и ротируется после 5 МБ (максимум 3 файла)
  2. Логи появляются в BetterStack Logtail dashboard с полем machine_id
  3. При попытке запустить второй экземпляр появляется сообщение «ЮрТэг уже запущен» и второй процесс завершается
  4. В удалённых логах нет текста из юридических документов (только события INFO/WARNING/ERROR)
**Plans**: 2 plans
Plans:
- [x] 44-01-PLAN.md — File + BetterStack logging with rotation, machine_id, content filter
- [x] 44-02-PLAN.md — Single instance file lock (fcntl/msvcrt)

### Phase 45: Icon & Splash
**Goal**: Приложение визуально идентифицировано — иконка «Ю» в Dock/Taskbar, splash вместо пустоты при запуске
**Depends on**: Phase 44
**Requirements**: DUX-01, DUX-02
**Success Criteria** (what must be TRUE):
  1. Иконка «Ю» в индиго отображается в macOS Dock и Finder (все размеры 16–512px в .icns)
  2. При запуске PyInstaller-бандла отображается splash с логотипом — пустого экрана нет
  3. .ico файл для Windows содержит все стандартные размеры (16/32/128/256px)
**Plans**: 1 plan
Plans:
- [x] 45-01-PLAN.md — Icon generation (Ю .icns/.ico) + startup loading overlay

### Phase 46: Offline & Disk Safety
**Goal**: Приложение не крашится при первом запуске без интернета и предупреждает о нехватке места
**Depends on**: Phase 44
**Requirements**: DUX-03, DUX-04
**Success Criteria** (what must be TRUE):
  1. При первом запуске без интернета — понятное сообщение «подключитесь к интернету», не краш
  2. При <1.5 ГБ свободного места — предупреждение с указанием нужного объёма
  3. При достаточном месте и интернете — скачивание продолжается без предупреждений
**Plans**: TBD

### Phase 47: Runtime Safety
**Goal**: Приложение корректно работает в PyInstaller-бандле: storage_secret, quarantine, freeze_support, hidden imports
**Depends on**: Phase 46
**Requirements**: RUN-01, RUN-02, RUN-03, RUN-04
**Success Criteria** (what must be TRUE):
  1. При первом запуске settings.json содержит storage_secret (64-символьная hex-строка)
  2. llama-server запускается на macOS без «разработчик не верифицирован» (quarantine снят)
  3. PyInstaller-бандл запускается без ошибок multiprocessing (freeze_support вызван до ui.run)
  4. PyInstaller-бандл включает natasha, pymorphy2, sentence-transformers, pdfplumber
**Plans**: TBD

### Phase 48: Feature Verification
**Goal**: Три ключевые функции (redline, предпросмотр, гид-тур) работают корректно end-to-end
**Depends on**: Phase 47
**Requirements**: VER-01, VER-02, VER-03
**Success Criteria** (what must be TRUE):
  1. Загрузка шаблона → сравнение → скачивание .docx с track changes — файл содержит изменения
  2. PDF и DOCX файлы отображаются в карточке документа без ошибок
  3. Кнопка «Гид» запускает guided tour без JS-ошибок в консоли
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 32. P0 Critical Fixes | v1.0-FE | 1/1 | Complete | 2026-03-29 |
| 33. Code Quality & Error Resilience | v1.0-FE | 1/1 | Complete | 2026-03-28 |
| 34. Registry & Document Card | v1.0-FE | 1/1 | Complete | 2026-03-28 |
| 35. Templates, Settings & Onboarding | v1.0-FE | 1/1 | Complete | 2026-03-28 |
| 36. Cross-Scope Integration | v1.0-FE | 1/1 | Complete | 2026-03-29 |
| 37. Final Visual Pass | v1.0-FE | 1/1 | Complete | 2026-03-29 |
| 38. Cross-Scope + Config Hardening | v1.0-BE | 2/2 | Complete | 2026-03-29 |
| 39. Provider Cleanup | v1.0-BE | 1/1 | Complete | 2026-03-29 |
| 40. Data Integrity | v1.0-BE | 1/1 | Complete | 2026-03-29 |
| 41. Thread Safety | v1.0-BE | 1/1 | Complete | 2026-03-29 |
| 42. Error Handling | v1.0-BE | 1/1 | Complete | 2026-03-29 |
| 43. Test Coverage | v1.0-BE | 1/1 | Complete | 2026-03-29 |
| 44. Logging & Single Instance | v1.2 | 2/2 | Complete    | 2026-03-29 |
| 45. Icon & Splash | v1.2 | 1/1 | Complete   | 2026-03-29 |
| 46. Offline & Disk Safety | v1.2 | 0/? | Not started | - |
| 47. Runtime Safety | v1.2 | 0/? | Not started | - |
| 48. Feature Verification | v1.2 | 0/? | Not started | - |
