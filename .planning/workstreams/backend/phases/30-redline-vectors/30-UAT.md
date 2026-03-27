---
status: complete
phase: 30-redline-vectors
source: 30-01-SUMMARY.md, 30-02-SUMMARY.md, 30-03-SUMMARY.md
started: 2026-03-27T15:20:00Z
updated: 2026-03-27T15:22:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Word-level redline DOCX
expected: redline_service.generate_redline_docx() создаёт DOCX с w:delText/w:ins track changes на уровне слов (не предложений).
result: pass

### 2. Кэш embeddings шаблонов
expected: Миграция v8 создаёт template_embeddings. mark_contract_as_template сохраняет embedding сразу. match_template загружает из кэша.
result: pass

### 3. full_text вместо subject для шаблонов
expected: review_service использует full_text из contracts (не короткий subject). Миграция v9 добавляет full_text в contracts. version_service re-exports из redline_service.
result: pass

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
