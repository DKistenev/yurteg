---
phase: 02-document-lifecycle
plan: 01
subsystem: database
tags: [sqlite, migrations, lifecycle, status, dataclasses]

# Dependency graph
requires:
  - phase: 01-infrastructure
    provides: Database class with migration pattern (_migrate_v1_review_columns, schema_migrations table)
provides:
  - Миграции v2–v6 в database.py (manual_status, warning_days, embeddings, document_versions, payments, templates)
  - Dataclasses DocumentVersion, Payment, Template, DeadlineAlert в models.py
  - Config.warning_days_threshold = 30
  - lifecycle_service.py: get_computed_status_sql, set_manual_status, clear_manual_status, get_attention_required
affects:
  - 02-02 (версионирование документов использует document_versions)
  - 02-03 (платежи используют payments)
  - 02-04 (шаблоны используют templates)
  - Все планы Phase 2 используют lifecycle_service.get_computed_status_sql

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SQL CASE для вычисления статуса на лету: manual_status приоритетнее авто"
    - "Stateless service: функции принимают db как параметр, не хранят состояние"
    - "db._lock + db.conn.commit() для атомарных обновлений статуса"

key-files:
  created:
    - services/lifecycle_service.py
  modified:
    - modules/database.py
    - modules/models.py
    - config.py

key-decisions:
  - "lifecycle_service использует db.conn (не db._conn) — публичный атрибут Database класса"
  - "get_attention_required исключает manual_status документы — юрист берёт их под контроль явно"
  - "Статус expiring/expired вычисляется через SQL julianday — без Python datetime в сервисном слое"

patterns-established:
  - "Lifecycle SQL: CASE WHEN manual_status IS NOT NULL THEN manual_status ... END"
  - "Миграция: _is_migration_applied() guard + _mark_migration_applied() + try/except OperationalError"
  - "Сервис без streamlit-зависимости — вызывается из UI и Telegram-бота одинаково"

requirements-completed: [LIFE-01, LIFE-02, LIFE-06]

# Metrics
duration: 2min
completed: 2026-03-19
---

# Phase 2 Plan 01: Document Lifecycle Foundation Summary

**SQLite миграции v2–v6 (manual_status, embeddings, document_versions, payments, templates) + lifecycle_service с SQL CASE приоритета ручного статуса над автоматическим**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-19T22:21:01Z
- **Completed:** 2026-03-19T22:23:10Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Пять новых миграций (v2–v6) применяются идемпотентно при инициализации Database
- Четыре dataclass для Phase 2: DocumentVersion, Payment, Template, DeadlineAlert
- lifecycle_service.py без Streamlit-зависимости — get_computed_status_sql возвращает SQL CASE где manual_status приоритетнее авто
- get_attention_required корректно исключает документы под ручным контролем юриста

## Task Commits

Каждая задача закоммичена атомарно:

1. **Task 1: Миграции v2–v6 + dataclasses** - `093ba7d` (feat)
2. **Task 2: config.warning_days_threshold + lifecycle_service** - `08f9760` (feat)

## Files Created/Modified
- `modules/database.py` - Добавлены _migrate_v2..v6, зарегистрированы в _run_migrations()
- `modules/models.py` - Добавлены DocumentVersion, Payment, Template, DeadlineAlert
- `config.py` - Добавлено поле warning_days_threshold: int = 30
- `services/lifecycle_service.py` - Новый модуль: статусы и панель внимания

## Decisions Made
- `lifecycle_service` использует `db.conn` (публичный атрибут), а не `db._conn` — план содержал ошибку, исправлено автоматически (Rule 1)
- `get_attention_required` фильтрует `status = 'done'` — только обработанные документы попадают в панель внимания
- SQL вычисляет `days_until_expiry` через `julianday` — отрицательное значение означает уже истёкший

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Исправлена ссылка на db._conn → db.conn в lifecycle_service**
- **Found during:** Task 2 (создание services/lifecycle_service.py)
- **Issue:** План указывал `db._conn`, но Database класс использует публичный атрибут `db.conn`. Также план передавал `Database(db_path, db_path.parent)` — конструктор принимает один аргумент.
- **Fix:** Использован `db.conn` вместо `db._conn` во всех функциях lifecycle_service
- **Files modified:** services/lifecycle_service.py
- **Verification:** python-тест завершился "OK: Config, SQL, set/clear/get_attention_required работают корректно"
- **Committed in:** 08f9760 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in plan's API reference)
**Impact on plan:** Необходимое исправление, план функционирует точно как задумано.

## Issues Encountered
Нет — оба задания выполнены без блокирующих проблем.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Фундамент жизненного цикла готов: миграции v2–v6, lifecycle_service
- Plan 02 (версионирование) может использовать document_versions таблицу
- Plan 03 (платежи) может использовать payments таблицу
- Plan 04 (шаблоны) может использовать templates таблицу
- Все планы могут импортировать get_computed_status_sql для вычисления статуса в SELECT

---
*Phase: 02-document-lifecycle*
*Completed: 2026-03-19*
