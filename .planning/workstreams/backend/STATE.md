---
gsd_state_version: 1.0
milestone: v0.9
milestone_name: milestone
status: Executing Phase 30
stopped_at: Completed 30-03-PLAN.md
last_updated: "2026-03-26T19:31:00Z"
last_activity: 2026-03-26
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 9
  completed_plans: 8
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-26)

**Core value:** Юрист загружает папку с документами и за 20 минут получает готовый реестр с метаданными — без ручного ввода, без обучения, без «проекта внедрения»
**Current focus:** Phase 30 — Redline + Vectors

## Current Position

Phase: 30 (Redline + Vectors) — EXECUTING
Plan: 3 of 3 — COMPLETE

## Accumulated Context

### Decisions

- [v0.9 2026-03-26]: Облачные провайдеры остаются как архив, всё строим под Ollama
- [v0.9 2026-03-26]: Анонимизация остаётся, но скипается для Ollama (как сейчас)
- [v0.9 2026-03-26]: Валидация L1-L5 сносится целиком, GBNF = гарантия формата
- [v0.9 2026-03-26]: Excel reporter удаляется полностью
- [v0.9 2026-03-26]: Confidence считается через logprobs Ollama, не из модели
- [v0.9 2026-03-26]: Единый redline-движок для версий и шаблонов (DOCX track changes)
- [v0.9 2026-03-26]: Telegram и OCR — не в этой вехе
- [v0.9 2026-03-26]: GBNF/logprobs несовместимы в b5606 — grammar передаётся через per-request body, не server flag
- [v0.9 2026-03-26]: python-docx OxmlElement подход верный, нужна word-level алгоритмическая правка (~30 LOC)
- [v0.9 2026-03-26]: MiniLM-L12-v2 достаточен для русских договоров, truncation исправляем 8000→3000
- [30-02 2026-03-26]: mark_contract_as_template сохраняет full_text + embedding в template_embeddings
- [30-02 2026-03-26]: TEMPLATE_MATCH_THRESHOLD поднят 0.60 → 0.70, compute_embedding без среза
- [30-03 2026-03-26]: version_service.generate_redline_docx — re-export из redline_service, старый sentence-level удалён
- [30-03 2026-03-26]: Миграция v9 добавляет full_text в contracts (blocking fix)
- [30-03 2026-03-26]: review_service.get_redline_for_template(db, contract_id, template_id) → bytes|None
- [Phase 28-cleanup]: stress_test.py validator sections deferred — слишком большой scope, залогировано в deferred-items.md
- [28-03 2026-03-26]: atexit.register перемещён внутрь if started: — вызывается ровно 1 раз при успехе
- [28-03 2026-03-26]: logging.warning при обрезке >30K — юрист видит что часть документа не проанализирована
- [29-03 2026-03-26]: Placeholder «i» (кавычки-ёлочки) пережи фильтрацию _RE_CYRILLIC_ONLY — NDA/SLA/GPS сохраняются в cyrillic_only полях

### Critical Risks

- ~~**Phase 29**: Перед написанием кода — curl-тест logprobs против работающего llama-server b5606~~ RESOLVED: оба теста прошли, реализация завершена
- **Phase 30**: Перед маркировкой фазы done — проверить Word 365, не только LibreOffice (XML compatibility MEDIUM confidence)

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last activity: 2026-03-26
Stopped at: Completed 30-03-PLAN.md
Resume file: None
Next: Phase 30 полностью завершена — все 3 плана выполнены (redline_service, vectors/templates, wiring)
