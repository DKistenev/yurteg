---
phase: 02-document-lifecycle
plan: 07
subsystem: ui
tags: [review, templates, difflib, cosine-similarity, redline, docx, sqlite]

# Dependency graph
requires:
  - phase: 02-document-lifecycle
    plan: 03
    provides: "compute_embedding, _cosine_sim, TEMPLATE_MATCH_THRESHOLD, generate_redline_docx из version_service"
  - phase: 02-document-lifecycle
    plan: 01
    provides: "templates table (migration v6), Template dataclass, Database.conn"
provides:
  - services/review_service.py с функциями add_template, mark_contract_as_template, list_templates, match_template, review_against_template
  - Вкладка «Шаблоны» в главных результатах — управление библиотекой эталонов
  - Вкладка «Ревью» в карточке документа — автоподбор шаблона + цветовая подсветка отступлений + редлайн .docx
affects:
  - Любые будущие фичи поиска по шаблонам или AI-ревью документов

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "review_service не импортирует streamlit — чистый сервисный слой"
    - "Session-state cache для deviations: st.session_state[f'_rev_deviations_{file}'] — результат ревью сохраняется между rerun"
    - "Два способа добавления шаблона: upload file (Extractor) + mark_contract_as_template из реестра"
    - "review_against_template использует difflib.SequenceMatcher на уровне предложений (_split_sentences)"

key-files:
  created:
    - services/review_service.py
  modified:
    - main.py

key-decisions:
  - "review_service использует db.conn (публичный атрибут) — последовательно с lifecycle_service и version_service"
  - "Вкладка Шаблоны добавлена как 5-й top-level таб (рядом с Сводка/Реестр/Детали/Платёжный календарь), не как отдельный раздел sidebar"
  - "Вкладка Ревью внутри карточки документа использует subject как текст документа — полного текста в БД нет"
  - "Деviations кешируются в session_state по ключу '_rev_deviations_{selected_file}' — результат ревью не сбрасывается при смене вкладки"

patterns-established:
  - "Template service pattern: список/поиск через db.conn без st зависимости — переиспользуемо из CLI/Telegram"

requirements-completed: [LIFE-08]

# Metrics
duration: 4min
completed: 2026-03-20
---

# Phase 2 Plan 07: Template Review Summary

**SQLite-библиотека шаблонов с косинусным автоподбором (порог 0.60) и sentence-level difflib подсветкой отступлений (зелёный/красный/жёлтый) + скачиваемый редлайн .docx**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-20T00:13:04Z
- **Completed:** 2026-03-20T00:17:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- services/review_service.py: 5 функций без streamlit — add_template, mark_contract_as_template, list_templates, match_template, review_against_template
- Вкладка «Шаблоны» в main.py: загрузка PDF/DOCX как шаблона + пометка документа из реестра + просмотр библиотеки
- Вкладка «Ревью» в карточке документа: автоподбор шаблона через косинусное сходство, список отступлений с цветовыми блоками, кнопка скачивания редлайна .docx

## Task Commits

1. **Task 1: services/review_service.py** - `2ee109b` (feat)
2. **Task 2: UI шаблонов и вкладка «Ревью» в main.py** - `733ec5d` (feat)

## Files Created/Modified
- `services/review_service.py` — Сервис ревью: 5 экспортируемых функций, cosine similarity через version_service, difflib SequenceMatcher на уровне предложений
- `main.py` — Импорт review_service; 5-й top-level таб «Шаблоны»; заполненная вкладка «Ревью» во внутренних табах карточки документа

## Decisions Made
- `review_service` использует `db.conn` (публичный), не `db._conn` — последовательно с lifecycle_service и version_service из предыдущих планов
- Вкладка «Шаблоны» добавлена как 5-й top-level таб, а не sidebar опция — соответствует существующей навигационной модели приложения
- `subject` поля контракта используется как текст документа для ревью — полного текста в SQLite нет
- Deviations кешируются в `st.session_state` — пользователь не теряет результат при переключении вкладок

## Deviations from Plan

None — план выполнен точно как написан. Единственная адаптация: вкладка «Шаблоны» интегрирована как 5-й top-level таб (план говорил "вкладка или sidebar option"), что соответствует духу плана.

## Issues Encountered
Нет — оба задания выполнены без блокирующих проблем.

## User Setup Required
None — зависимости уже установлены (difflib стандартная библиотека, sentence-transformers из плана 02-03).

## Next Phase Readiness
- review_service.py готов для переиспользования из CLI/Telegram-бота (нет зависимости от streamlit)
- Библиотека шаблонов заполняется пользователем через UI
- Вкладка «Ревью» работает на subject-тексте — если в будущем полный текст будет кешироваться в БД, ревью улучшится автоматически

---
*Phase: 02-document-lifecycle*
*Completed: 2026-03-20*
