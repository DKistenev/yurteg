---
phase: 02-document-lifecycle
plan: 03
subsystem: database
tags: [embeddings, sentence-transformers, versioning, sqlite, document-lifecycle]

# Dependency graph
requires:
  - phase: 02-document-lifecycle
    plan: 01
    provides: "embeddings table, document_versions table, DocumentVersion dataclass, Database.conn"
provides:
  - services/version_service.py с функциями compute_embedding, ensure_embedding, find_version_match, link_versions, get_version_group
  - ContractMetadata расширен полями payment_terms, payment_amount, payment_frequency, payment_direction
  - Хук версионирования в controller.py после db.save_result()
  - Эмбеддинги кэшируются в SQLite — не пересчитываются при повторном запуске
affects:
  - 02-05 (платёжный календарь использует payment_terms/payment_amount/payment_frequency/payment_direction)
  - 02-04 (шаблоны используют embedding-сравнение через version_service)
  - main.py (карточка документа — вкладка «Версии» вызывает get_version_group)

# Tech tracking
tech-stack:
  added:
    - sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2, 384-мерные векторы)
  patterns:
    - "Embedding singleton: thread-safe lazy load через global + _model_lock"
    - "Embedding cache: store_embedding/load_embedding через numpy BLOB в SQLite"
    - "Version hook: non-blocking try/except вокруг find_version_match + link_versions после db.save_result()"
    - "group_id convention: contract_id нового документа = его contract_group_id"

key-files:
  created:
    - services/version_service.py
  modified:
    - modules/models.py
    - modules/ai_extractor.py
    - controller.py

key-decisions:
  - "version_service использует db.conn (публичный атрибут) — не db._conn, аналогично lifecycle_service"
  - "Хук версионирования добавлен в controller.py (не pipeline_service.py) — план указывал неправильный файл, save_result вызывается в controller"
  - "Версионирование non-blocking: ошибки логируются как WARNING, не прерывают обработку"
  - "find_version_match сужает кандидатов по contract_type + counterparty перед cosine_sim — O(1) SQL, не O(N)"

patterns-established:
  - "Non-blocking side effect: try/except с logger.warning после основного db.save_result()"
  - "Embedding singleton: global _model + threading.Lock() — безопасен для ThreadPoolExecutor в controller"
  - "Version group convention: новый документ получает group_id = contract_id, не отдельный sequence"

requirements-completed: [LIFE-03]

# Metrics
duration: 8min
completed: 2026-03-20
---

# Phase 2 Plan 03: Document Versioning Summary

**Автоматическое версионирование через sentence-transformers MiniLM-L12-v2 с кэшем в SQLite и порогом cosine_sim >= 0.85 для русских юридических текстов**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-20T00:30:00Z
- **Completed:** 2026-03-20T00:38:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- services/version_service.py: 5 экспортируемых функций, thread-safe singleton модели, embedding BLOB cache в SQLite
- ContractMetadata расширен 4 платёжными полями с None-дефолтами — полная обратная совместимость
- AI-промпт расширен для извлечения payment_terms/amount/frequency/direction из текста договора
- Хук версионирования интегрирован в controller.py после каждого успешного save_result() — non-blocking

## Task Commits

Каждая задача закоммичена атомарно:

1. **Task 1: services/version_service.py** - `a6eaf26` (feat)
2. **Task 2: payment fields + version hook** - `ca5a582` (feat)

## Files Created/Modified
- `services/version_service.py` - Сервис версионирования: embedding singleton, SQLite BLOB cache, find/link/get_version_group
- `modules/models.py` - ContractMetadata + 4 платёжных поля (payment_terms, payment_amount, payment_frequency, payment_direction)
- `modules/ai_extractor.py` - USER_PROMPT_TEMPLATE расширен; _safe_float() helper; _json_to_metadata() маппит 4 новых поля
- `controller.py` - import version_service; хук find_version_match + link_versions после db.save_result()

## Decisions Made
- `version_service` использует `db.conn` (публичный атрибут Database), не `db._conn` — последовательно с lifecycle_service (02-01)
- Хук версионирования добавлен в `controller.py`, а не в `pipeline_service.py` — план ошибочно указывал pipeline_service, который является тонкой обёрткой над Controller; реальный `save_result()` находится в controller
- `find_version_match` предварительно фильтрует кандидатов по `contract_type` и `counterparty` через SQL — исключает O(N) сравнений по всей БД
- group_id = contract_id для первого документа в группе — простое соглашение, не требует отдельной sequence

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Хук версионирования добавлен в controller.py вместо pipeline_service.py**
- **Found during:** Task 2 (добавление хука в pipeline)
- **Issue:** План указывал `pipeline_service.py` как место вставки хука, но `pipeline_service.py` — тонкая обёртка над `Controller`. Вызов `db.save_result(result)` находится в `controller.py`, доступ к `contract_id` и `result.text` доступен только там.
- **Fix:** Импорт `find_version_match, link_versions` добавлен в `controller.py`; хук добавлен после `db.save_result(result)` в основном цикле ThreadPoolExecutor
- **Files modified:** controller.py
- **Verification:** `python -c "import controller; print('OK')"` завершился успешно; `grep -n "find_version_match\|link_versions" controller.py` вернул 3 строки
- **Committed in:** ca5a582 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — некорректная ссылка на файл в плане)
**Impact on plan:** Необходимое исправление. Функциональность реализована точно как задумано — только в правильном месте.

## Issues Encountered
Нет — оба задания выполнены без блокирующих проблем.

## User Setup Required
None — sentence-transformers скачивает модель автоматически при первом запуске (~90 МБ).

## Next Phase Readiness
- Версионирование активно: каждый новый документ со статусом done автоматически связывается с предыдущими версиями
- Plan 04 (шаблоны) может использовать version_service.compute_embedding для сравнения с эталонами
- Plan 05 (платёжный календарь) может читать payment_terms/amount/frequency/direction из ContractMetadata
- get_version_group(db, contract_id) готова для карточки документа (вкладка «Версии»)

---
*Phase: 02-document-lifecycle*
*Completed: 2026-03-20*
