---
phase: 30-redline-vectors
plan: "01"
subsystem: redline
tags: [redline, docx, track-changes, embeddings, migration, word-level-diff]
dependency_graph:
  requires: []
  provides: [services/redline_service.py, template_embeddings table]
  affects: [services/version_service.py, services/review_service.py, modules/database.py]
tech_stack:
  added: []
  patterns: [word-level difflib.SequenceMatcher, OxmlElement w:ins/w:delText, SQLite migration pattern]
key_files:
  created:
    - services/redline_service.py
    - tests/test_redline_service.py
  modified:
    - modules/database.py
decisions:
  - "w:delText для удалений (не w:t) — критично для Word 365, иначе диалог восстановления"
  - "w:rPr пустой для plain text, архитектурно готов к копированию из исходного run"
  - "Токенизация re.findall(r'\\S+|\\s+') — пробелы как отдельные токены, сохраняют форматирование"
  - "PRIMARY KEY (template_id) в template_embeddings — один вектор на шаблон"
metrics:
  duration: "~15 min"
  completed_date: "2026-03-26"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 1
---

# Phase 30 Plan 01: Redline Engine + Migration v8 Summary

**One-liner:** Word-level DOCX redline движок через difflib.SequenceMatcher + w:delText/w:ins OOXML, и миграция v8 для кэша эмбеддингов шаблонов.

## What Was Built

### Task 1: services/redline_service.py (TDD)

Создан единый word-level redline движок, заменяющий sentence-level реализацию в `version_service.py`.

Ключевые свойства:
- Токенизация `re.findall(r'\S+|\s+', text)` — слова и пробелы как отдельные токены
- `difflib.SequenceMatcher(autojunk=False)` на токенах, а не предложениях
- `w:delText` для удалённого контента (не `w:t`) — обязательно для Word 365
- `w:ins`/`w:del` — прямые дети `w:p`, `w:id` уникальный через `itertools.count(1)`
- `w:rPr` создаётся в каждом track changes run (пустой для plain text)
- Разбивка по абзацам через `text.split('\n')`

Тесты (6/6 GREEN): `test_returns_bytes`, `test_equal_texts`, `test_word_insert`, `test_word_delete`, `test_word_replace`, `test_rpr_copy`.

### Task 2: modules/database.py — миграция v8

Добавлена `_migrate_v8_template_embeddings(conn)` по паттерну v7:

```sql
CREATE TABLE IF NOT EXISTS template_embeddings (
    template_id   INTEGER NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
    file_hash     TEXT NOT NULL,
    vector        BLOB NOT NULL,
    model_version TEXT NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (template_id)
)
```

Индекс `idx_tmpl_emb_hash` на `file_hash`. Вызов добавлен в `_run_migrations()` после v7.

## Commits

| Task | Hash | Message |
|------|------|---------|
| 1 | 100aff1 | feat(30-01): word-level redline движок services/redline_service.py |
| 2 | 8178571 | feat(30-01): миграция v8 — таблица template_embeddings |

## Deviations from Plan

None — план выполнен точно как написан.

## Known Stubs

None.

## Self-Check: PASSED

- `services/redline_service.py` — существует
- `tests/test_redline_service.py` — существует, 6/6 тестов GREEN
- `modules/database.py` — содержит `_migrate_v8_template_embeddings` (2 вхождения: определение + вызов)
- Коммиты 100aff1 и 8178571 — подтверждены
- XML проверка: `w:delText` и `w:ins` присутствуют в выводе

## Critical Risk Note

Из STATE.md: перед маркировкой фазы 30 done — проверить redline DOCX в Word 365 (не только LibreOffice). Этот план создаёт движок, финальная проверка совместимости — ответственность плана 30-03 или ручной верификации.
