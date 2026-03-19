---
phase: 02-document-lifecycle
verified: 2026-03-20T12:00:00Z
status: human_needed
score: 8/8 must-haves verified
human_verification:
  - test: "Панель «требует внимания» отображается при наличии истекающих/истёкших договоров"
    expected: "Expander с иконкой ⚠ и счётчиком договоров виден выше реестра"
    why_human: "Требует запущенного Streamlit с реальными данными"
  - test: "Колонка «Статус» с иконками в таблице реестра"
    expected: "Каждая строка реестра показывает ✔/⚠/✗/↻/... рядом с договором"
    why_human: "Визуальный рендер Streamlit — не верифицируется статически"
  - test: "Ручной override статуса через selectbox + кнопку «Применить»"
    expected: "После выбора «Расторгнут» и нажатия «Применить» страница перезагружается, статус меняется"
    why_human: "Интерактивное взаимодействие UI с состоянием"
  - test: "Вкладка «Версии» показывает таймлайн и diff"
    expected: "Для документов с версиями — вертикальный список v1/v2/..., секция сравнения, кнопка редлайна"
    why_human: "Требует договоров с несколькими версиями в БД"
  - test: "Платёжный календарь в стиле Google Calendar"
    expected: "Вкладка «Платёжный календарь» — сетка месяца с цветными событиями (красный=расход, зелёный=доход)"
    why_human: "streamlit-calendar визуальный компонент — нельзя проверить grep-ом"
  - test: "Клик по событию в календаре показывает детали"
    expected: "Expander «Детали платежа» с контрагентом, суммой, типом договора"
    why_human: "Событийная модель JavaScript/Streamlit — требует браузера"
  - test: "Ревью договора против шаблона с подсветкой отступлений"
    expected: "Зелёный фон = добавлено, красный = удалено, жёлтый = изменено"
    why_human: "HTML-рендер с цветами — визуально"
  - test: "Скачивание редлайна .docx открывается в Word с track changes"
    expected: "Файл .docx содержит w:ins/w:del теги, видимые как правки в Word"
    why_human: "Требует открытия в Word — нельзя автоматизировать"
---

# Phase 02: Document Lifecycle Verification Report

**Phase Goal:** Юрист видит что происходит с каждым документом — без ручной проверки сроков и статусов
**Verified:** 2026-03-20T12:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Статусы документов вычисляются автоматически по date_end (LIFE-01) | VERIFIED | `services/lifecycle_service.py` — `get_computed_status_sql()` возвращает SQL CASE с expired/expiring/active/unknown |
| 2 | Ручной статус приоритетнее автоматического (LIFE-02) | VERIFIED | SQL CASE проверяет `manual_status IS NOT NULL` первым; `set_manual_status()` / `clear_manual_status()` работают |
| 3 | При загрузке обновлённого договора система находит предыдущую версию (LIFE-03) | VERIFIED | `services/version_service.py` — `find_version_match()` с порогом 0.85; хук в `controller.py` строки 279-284 |
| 4 | Diff версий + генерация redline .docx (LIFE-04) | VERIFIED | `diff_versions()` сравнивает 10 полей; `generate_redline_docx()` создаёт валидный ZIP с w:del/w:ins |
| 5 | Панель «требует внимания» при открытии приложения (LIFE-05) | VERIFIED | `get_attention_required()` вызывается в `main.py` строка 966; исключает документы с manual_status |
| 6 | Порог предупреждения 30/60/90 дней настраивается (LIFE-06) | VERIFIED | selectbox в сайдбаре `main.py` строка 607; `warning_days_threshold: int = 30` в `config.py` строка 31 |
| 7 | Платёжный календарь с периодическими платежами (LIFE-07) | VERIFIED | `payment_service.py` — unroll monthly/quarterly/yearly через relativedelta; `st_calendar()` в `main.py` строка 1880 |
| 8 | AI-ревью против шаблона-эталона с подсветкой отступлений (LIFE-08) | VERIFIED | `review_service.py` — 4 функции; `review_against_template()` находит added/removed/changed; вкладка «Ревью» в main.py строки 1634+ |

**Score:** 8/8 truths verified (автоматически), 8 items требуют human verification

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_lifecycle.py` | Тест-скелеты LIFE-01/02/05/06 | VERIFIED | 4 функции: `test_auto_status_computation`, `test_manual_status_override`, `test_attention_panel`, `test_configurable_threshold` |
| `tests/test_versioning.py` | Тест-скелеты LIFE-03/04 | VERIFIED | 2 функции: `test_auto_version_linking`, `test_redline_generation` |
| `tests/test_payments.py` | Тест-скелет LIFE-07 | VERIFIED | 2 функции: `test_payment_unroll`, `test_payment_save_and_load` |
| `services/lifecycle_service.py` | Статусы и панель внимания | VERIFIED | 4 функции: `get_computed_status_sql`, `set_manual_status`, `clear_manual_status`, `get_attention_required` + STATUS_LABELS |
| `services/version_service.py` | Версионирование + diff + redline | VERIFIED | 7 функций включая `diff_versions`, `generate_redline_docx`, порог VERSION_LINK_THRESHOLD=0.85 |
| `services/payment_service.py` | Платёжный сервис | VERIFIED | 3 функции: `unroll_payments`, `save_payments`, `get_calendar_events`; relativedelta для корректных месяцев |
| `services/review_service.py` | Ревью против шаблона | VERIFIED | 5 функций: `add_template`, `mark_contract_as_template`, `list_templates`, `match_template`, `review_against_template` |
| `modules/database.py` | Миграции v2–v6 | VERIFIED | Все 5 миграций определены и вызываются в `_run_migrations()`; Python-тест подтвердил создание таблиц |
| `modules/models.py` | 4 новых dataclass + 4 поля ContractMetadata | VERIFIED | `DocumentVersion`, `Payment`, `Template`, `DeadlineAlert`; `payment_terms/amount/frequency/direction` с None-дефолтами |
| `config.py` | `warning_days_threshold: int = 30` | VERIFIED | Строка 31 |
| `requirements.txt` | `streamlit-calendar==1.4.0` | VERIFIED | Присутствует |
| `main.py` | UI всех фич Phase 2 | VERIFIED | Все импорты и вызовы сервисов подтверждены; 4 вкладки карточки документа |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `main.py` | `lifecycle_service.get_attention_required` | вызов при загрузке страницы | WIRED | Строка 966, `main.py` |
| `main.py` | `lifecycle_service.set_manual_status / clear_manual_status` | selectbox + кнопка «Применить» + `st.rerun()` | WIRED | Строки 1261-1264 |
| `main.py` | `lifecycle_service.get_computed_status_sql` | SQL-запрос реестра с параметром warning_days | WIRED | Строка 1045 |
| `main.py` | `version_service.get_version_group` | вкладка «Версии» | WIRED | Строка 1521 |
| `main.py` | `version_service.diff_versions` | кнопка «Сравнить» | WIRED | Строка 1566 |
| `main.py` | `version_service.generate_redline_docx` | `st.download_button` | WIRED | Строки 1598, 1720 |
| `main.py` | `payment_service.get_calendar_events` | вкладка «Платёжный календарь» | WIRED | Строки 1613, 1847 |
| `main.py` | `streamlit_calendar()` | вкладка «Платёжный календарь» | WIRED | Строка 1880 |
| `main.py` | `review_service.review_against_template` | вкладка «Ревью» | WIRED | Строка 1676 |
| `main.py` | `review_service.match_template` | автоподбор при открытии вкладки | WIRED | Строка 1644 |
| `controller.py` | `version_service.find_version_match + link_versions` | после `database.save()` для каждого файла | WIRED | Строки 279-284 — хук в `controller.py`, не `pipeline_service.py` (архитектурное отклонение от плана, но функционально эквивалентно) |
| `controller.py` | `payment_service.save_payments` | после успешной обработки, если `payment_amount is not None` | WIRED | Строка 299 |
| `services/version_service.py` | `embeddings` table в SQLite | `_store_embedding / _load_embedding` через numpy BLOB | WIRED | Строки 47-70 |
| `services/review_service.py` | `version_service._cosine_sim + TEMPLATE_MATCH_THRESHOLD` | `match_template()` — косинусное сходство | WIRED | Импорт строка 18-22 |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| LIFE-01 | 02-00, 02-01 | Авто-статус по date_end | SATISFIED | `get_computed_status_sql()` — SQL CASE с 4 состояниями; функционально протестировано |
| LIFE-02 | 02-00, 02-01, 02-02 | Ручной статус приоритетнее авто | SATISFIED | SQL CASE: `WHEN manual_status IS NOT NULL THEN manual_status`; UI override в main.py |
| LIFE-03 | 02-00, 02-03 | Авто-версионирование по эмбеддингам | SATISFIED | `find_version_match()` + `link_versions()`; хук в controller.py |
| LIFE-04 | 02-04 | Diff версий + redline .docx | SATISFIED | `diff_versions()` — 10 полей; `generate_redline_docx()` — w:del/w:ins; вкладка «Версии» |
| LIFE-05 | 02-00, 02-02 | Панель «требует внимания» | SATISFIED | `get_attention_required()` — expander в main.py перед реестром |
| LIFE-06 | 02-00, 02-01, 02-02 | Порог 30/60/90 дней | SATISFIED | selectbox в сайдбаре; `warning_days_threshold = 30` в Config |
| LIFE-07 | 02-00, 02-05, 02-06 | Платёжный календарь | SATISFIED | `payment_service.py` + `streamlit_calendar` + хук в controller.py |
| LIFE-08 | 02-07 | AI-ревью против шаблона | SATISFIED | `review_service.py` — библиотека шаблонов + автоподбор + цветовая подсветка |

Все 8 требований покрыты. Orphaned requirements: нет.

---

## Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `services/pipeline_service.py` | Версионирование и платёжные хуки фактически в `controller.py`, а не в `pipeline_service.py` как указано в планах 02-03 и 02-05 | INFO | Архитектурное отклонение, но функционально эквивалентно — хуки работают при любом вызове через Controller |

Blockers: нет. Warnings: нет. Info: 1 (архитектурная ремарка).

---

## Human Verification Required

### 1. Панель «требует внимания»

**Test:** Запустить `streamlit run main.py`, открыть реестр при наличии договоров с `date_end` в прошлом или в ближайшие 30 дней
**Expected:** Expander «⚠ Требует внимания — N договор(ов)» виден выше таблицы реестра; при отсутствии проблем — не отображается
**Why human:** Требует запущенного Streamlit с реальными данными в БД

### 2. Колонка «Статус» в реестре

**Test:** Открыть вкладку «Реестр» с обработанными договорами
**Expected:** В таблице присутствует колонка «Статус» с иконками ✔/⚠/✗/↻/? для каждого договора
**Why human:** Визуальный рендер Streamlit DataFrame

### 3. Ручной override статуса

**Test:** Выбрать договор в секции «Ручная коррекция» → статус «Расторгнут» → «Применить»
**Expected:** Страница перезагружается, статус договора меняется на «✖ Расторгнут»; выбрать «Авто (сбросить)» → статус возвращается к автоматическому
**Why human:** Интерактивная сессия Streamlit

### 4. Вкладка «Версии»

**Test:** Открыть карточку договора → вкладка «Версии»
**Expected:** При отсутствии версий — «Версии не найдены»; при наличии нескольких — вертикальный таймлайн v1/v2/..., секция «Сравнение версий», кнопка «Сгенерировать редлайн»
**Why human:** Требует договоров с реальными версиями в document_versions

### 5. Платёжный календарь

**Test:** Перейти в «Платёжный календарь» в главном меню
**Expected:** Сетка месяца Google Calendar-style; красные события = расход, зелёные = доход; сводка расходов/доходов вверху
**Why human:** streamlit-calendar — JavaScript-компонент, не верифицируется статически

### 6. Клик по событию в календаре

**Test:** Кликнуть на событие в платёжном календаре
**Expected:** Появляется expander «Детали платежа» с контрагентом, суммой, типом договора, ID договора
**Why human:** Событийная модель JavaScript → Streamlit session_state

### 7. Ревью договора с цветовой подсветкой

**Test:** Загрузить шаблон в «Библиотека шаблонов» → открыть договор того же типа → вкладка «Ревью» → «Запустить ревью»
**Expected:** Список отступлений с цветными блоками: зелёный (добавлено), красный (удалено), жёлтый (изменено)
**Why human:** HTML-рендер с цветами — визуально

### 8. Редлайн .docx открывается в Word

**Test:** Нажать «Сгенерировать редлайн .docx» → скачать файл → открыть в Microsoft Word
**Expected:** Документ открывается без ошибок, видны пометки изменений (track changes)
**Why human:** Требует Microsoft Word или совместимого редактора

---

## Gaps Summary

Gaps не обнаружены. Все 8 требований LIFE-01 — LIFE-08 имеют реализованные, импортированные и используемые артефакты.

Единственное структурное отклонение: планы 02-03 и 02-05 предписывали добавить хуки версионирования и платежей в `services/pipeline_service.py`, однако они реализованы в `controller.py`. Это эквивалентно с точки зрения результата — хуки срабатывают при каждой обработке архива через любой интерфейс (UI, CLI, Telegram-бот).

---

_Verified: 2026-03-20T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
