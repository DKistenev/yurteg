---
phase: 02-document-lifecycle
plan: 04
subsystem: ui
tags: [diff, redline, docx, track-changes, python-docx, difflib, versioning, streamlit]

# Dependency graph
requires:
  - phase: 02-document-lifecycle
    plan: 03
    provides: "version_service.py с get_version_group, DocumentVersion, embeddings"
provides:
  - services/version_service.py расширен diff_versions и generate_redline_docx
  - Карточка документа в main.py с 4 вкладками (Основное/Версии/Платежи/Ревью)
  - Вкладка «Версии»: вертикальный таймлайн + diff ключевых полей + скачивание .docx редлайна
affects:
  - 02-05 (tab_payments уже содержит реальный контент — не заглушку)
  - 02-06 (tab_review уже содержит реальный контент — не заглушку)

# Tech tracking
tech-stack:
  added:
    - difflib (stdlib) — SequenceMatcher на уровне предложений
    - python-docx OxmlElement (уже была зависимость) — w:ins/w:del track changes
  patterns:
    - "Redline pattern: difflib.SequenceMatcher + OxmlElement('w:del')/OxmlElement('w:ins') с w:author='ЮрТэг'"
    - "Field diff: dataclasses.asdict() + compare string representation — None → '—'"
    - "DB access inside tab: context manager Database(db_path) — безопасен при Streamlit reruns"

key-files:
  created: []
  modified:
    - services/version_service.py
    - main.py

key-decisions:
  - "Карточка документа структурирована в 4 вкладки — tab_main содержит всё старое содержимое (карточка + замечания + пометки)"
  - "Дублирующий код карточки (оставшийся от предыдущих сессий вне tab_main) удалён"
  - "DB read для diff/redline через Database(db_path) context manager — не через db._conn прямо"
  - "generate_redline_docx использует subject договора как текст (полный текст не хранится в contracts)"

patterns-established:
  - "Streamlit tab pattern: tab_main, tab_versions, tab_payments, tab_review = st.tabs([...])"
  - "Redline docx: generate_redline_docx(old_text, new_text, title) -> bytes, подаётся в st.download_button"

requirements-completed: [LIFE-04]

# Metrics
duration: 10min
completed: 2026-03-20
---

# Phase 2 Plan 04: Version Diff and Redline Summary

**diff_versions (10 полей ContractMetadata) и generate_redline_docx (w:ins/w:del track changes) в version_service.py + карточка документа реструктурирована в 4 вкладки с полнофункциональной вкладкой «Версии»**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-19T22:29:00Z
- **Completed:** 2026-03-20T22:39:39Z
- **Tasks:** 2 (автоматических) + 1 checkpoint:human-verify (approved)
- **Files modified:** 2

## Accomplishments
- `diff_versions`: сравнивает 10 ключевых полей ContractMetadata через `dataclasses.asdict()`, возвращает список `{field, old, new, changed}` — верифицирован тестом
- `generate_redline_docx`: difflib.SequenceMatcher на уровне предложений, OxmlElement w:del/w:ins, возвращает валидный .docx (ZIP magic bytes PK, >1000 байт)
- Карточка документа реструктурирована: 4 вкладки (Основное/Версии/Платежи/Ревью), существующий контент платежей и ревью из 02-05/02-06 сохранён
- Вкладка «Версии»: вертикальный таймлайн версий → выбор пары → diff ключевых полей с зачёркиванием → генерация редлайна с `st.download_button`

## Task Commits

1. **Task 1: diff_versions и generate_redline_docx** - `2d18181` (feat)
2. **Task 2: карточка документа с вкладкой «Версии»** - `f65e77d` (feat)

## Files Created/Modified
- `services/version_service.py` — добавлены `diff_versions` и `generate_redline_docx` (118 строк)
- `main.py` — карточка документа реструктурирована в 4 вкладки; удалён дублирующий код вне контекста tabs

## Decisions Made
- `generate_redline_docx` использует `subject` договора как текст для редлайна — полный текст договора не хранится в таблице `contracts`, только метаданные
- Старый код карточки был продублирован вне `with tab_main:` (из предыдущих сессий) — удалён
- `tab_payments` и `tab_review` уже содержали реальный функциональный контент из планов 02-05 и 02-06 — заглушки не нужны, контент сохранён

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Дублированный код карточки вне with tab_main:**
- **Found during:** Task 2 (реструктуризация карточки документа)
- **Issue:** Предыдущие сессии (02-05/02-06) добавили `tab_versions`, `tab_payments`, `tab_review` без переноса существующего кода карточки внутрь `tab_main`. Код карточки оставался на уровне `if selected_file:`, рендерился вне вкладок и дублировался
- **Fix:** Существующий код карточки перенесён в `with tab_main:`, дублирующий блок вне tabs удалён
- **Files modified:** main.py
- **Committed in:** f65e77d (Task 2 commit)

**2. [Rule 1 - Bug] tab_payments и tab_review уже реализованы в 02-05/02-06:**
- **Found during:** Task 2 (проверка состояния main.py)
- **Issue:** План 02-04 ожидал добавить заглушки для tab_payments и tab_review, но они уже были реализованы предыдущими планами. Вставка заглушек затёрла бы реальный функционал
- **Fix:** Заглушки не добавлялись; существующий функциональный контент вкладок сохранён
- **Files modified:** нет (отклонение от плана не требовало изменений)

---

**Total deviations:** 2 (Rule 1 — дублированный код; Rule 1 — план описывал устаревшее состояние)
**Impact on plan:** Оба исправления необходимы. Функциональность реализована точно как задумано.

## Issues Encountered
Файл main.py содержал код, добавленный после написания плана 02-04 (планами 02-05 и 02-06) — потребовалась аккуратная интеграция без потери существующего функционала.

## User Setup Required
None — зависимости python-docx и difflib уже установлены.

## Next Phase Readiness
- Вкладка «Версии» функциональна: таймлайн, diff, редлайн .docx
- Требует верификации: открыть в Word и убедиться что track changes видны
- plan 02-05 (платежи) и 02-06 (шаблоны/ревью) уже реализованы и интегрированы в карточку

---
*Phase: 02-document-lifecycle*
*Completed: 2026-03-20*
