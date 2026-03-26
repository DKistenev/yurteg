# Phase 30: Redline + Vectors - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Redline-DOCX генерируется на уровне слов и открывается в Word без ошибок. Шаблонные embeddings кэшируются в DB. Пометка как шаблон сохраняет full_text. Автоподбор шаблона работает с порогом 0.70.

Requirements: RED-01, RED-02, RED-03, VEC-01, VEC-02, VEC-03, VEC-04

</domain>

<decisions>
## Implementation Decisions

### Redline Architecture
- Новый модуль `services/redline_service.py` — единый движок для версий и шаблонов
- Алгоритм: difflib.SequenceMatcher на уровне слов (split по пробелам/пунктуации)
- Формат: python-docx OxmlElement — w:ins/w:del с rPr копированием из исходного текста
- Полный текст для сравнения: извлекать из DB (full_text) или из файла через extractor
- Баг rPr в version_service.py: при создании w:ins/w:del нужно копировать rPr (run properties) из исходного run, иначе Word теряет форматирование

### Vectors & Templates
- Полный текст целиком в embedding (не chunks) — модель усечёт до max_seq_length сама
- Кэш: новая таблица template_embeddings в SQLite (миграция v8), file_hash → vector blob
- mark_contract_as_template: фикс бага — сохранять full_text + embedding (сейчас только subject)
- Автоподбор шаблона: cosine_similarity > 0.70 (текущий 0.60 слишком низкий)
- Убрать truncation [:8000] — передавать полный текст документа

### Claude's Discretion
- Структура таблицы template_embeddings (колонки, индексы)
- Как именно передать полный текст из extractor в review_service (через DB или файл)
- Формат возвращаемого redline (скачивание через /download/ route или новый endpoint)

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- `services/version_service.py` — generate_redline_docx() существует но сломан (rPr, sentence-level)
- `services/review_service.py` — mark_contract_as_template(), match_template() — работают частично
- `modules/database.py` — SQLite, миграции v1-v7
- `modules/extractor.py` — extract_text() из PDF/DOCX

### Current State
- version_service.py:231-306 — generate_redline_docx() использует OxmlElement но sentence-level и теряет rPr
- review_service.py:123-164 — match_template() работает но без кэша, пересчитывает каждый раз
- review_service.py:165-228 — review_against_template() — sentence-level difflib
- Embedding модель: paraphrase-multilingual-MiniLM-L12-v2 (sentence-transformers)

</code_context>

<specifics>
## Specific Ideas

- Research показал: python-docx OxmlElement подход верный, нужна word-level алгоритмическая правка (~30 LOC)
- MiniLM-L12-v2 max_seq_length = 128 tokens — для полных документов нужно проверить, достаточно ли первых ~500 символов или нужно менять модель
- IMPORTANT: перед маркировкой фазы done — проверить redline DOCX в Word 365

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>
