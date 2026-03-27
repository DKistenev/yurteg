---
status: complete
phase: 28-cleanup
source: 28-01-SUMMARY.md, 28-02-SUMMARY.md, 28-03-SUMMARY.md
started: 2026-03-27T15:20:00Z
updated: 2026-03-27T15:22:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Мёртвый код удалён
expected: modules/validator.py и modules/reporter.py не существуют. controller.py работает без них.
result: pass

### 2. atexit.register вызывается один раз
expected: llama_server.py: atexit.register внутри if started:, не в retry loop.
result: pass

### 3. Warning при обрезке текста >30K
expected: ai_extractor.py: logger.warning при original_len > 30_000.
result: pass

### 4. Тесты проходят
expected: pytest tests/test_controller.py — все проходят. 160/161 тест-сьюта зелёный.
result: issue
reported: "test_manual_status_override fails — MANUAL_STATUSES = {'negotiation'}, тест ожидает 'extended'"
severity: major

## Summary

total: 4
passed: 3
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "Весь тест-сьют проходит без ошибок"
  status: failed
  reason: "User reported: test_manual_status_override fails — MANUAL_STATUSES = frozenset({'negotiation'}), тест ожидает 'extended' который не в списке"
  severity: major
  test: 4
  root_cause: "MANUAL_STATUSES в lifecycle_service.py содержит только 'negotiation', а тест test_lifecycle.py:90 вызывает set_manual_status(db, cid, 'extended'). Либо тест не обновлён после сужения списка, либо 'extended' забыли добавить."
  artifacts:
    - path: "services/lifecycle_service.py"
      issue: "MANUAL_STATUSES = frozenset({'negotiation'}) — слишком узкий набор"
    - path: "tests/test_lifecycle.py"
      issue: "line 90: set_manual_status(db, cid, 'extended') — статус не в MANUAL_STATUSES"
  missing:
    - "Добавить 'extended' в MANUAL_STATUSES или обновить тест на 'negotiation'"
  debug_session: ""
