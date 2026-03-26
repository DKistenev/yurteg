---
gsd_state_version: 1.0
milestone: v0.9
milestone_name: milestone
status: Executing Phase 29
stopped_at: Completed 29-ai-pipeline-03-PLAN.md
last_updated: "2026-03-26T19:00:00.000Z"
last_activity: 2026-03-26
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 6
  completed_plans: 5
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-26)

**Core value:** Юрист загружает папку с документами и за 20 минут получает готовый реестр с метаданными — без ручного ввода, без обучения, без «проекта внедрения»
**Current focus:** Phase 29 — AI Pipeline

## Current Position

Phase: 29 (AI Pipeline) — EXECUTING
Plan: 3 of 3 (COMPLETE)

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
- [Phase 28-cleanup]: stress_test.py validator sections deferred — слишком большой scope, залогировано в deferred-items.md
- [28-03 2026-03-26]: atexit.register перемещён внутрь if started: — вызывается ровно 1 раз при успехе
- [28-03 2026-03-26]: logging.warning при обрезке >30K — юрист видит что часть документа не проанализирована
- [29-03 2026-03-26]: Placeholder «i» (кавычки-ёлочки) пережи фильтрацию _RE_CYRILLIC_ONLY — NDA/SLA/GPS сохраняются в cyrillic_only полях

### Critical Risks

- **Phase 29**: Перед написанием кода — curl-тест logprobs против работающего llama-server b5606 (MEDIUM confidence, требует валидации)
- **Phase 30**: Перед маркировкой фазы done — проверить Word 365, не только LibreOffice (XML compatibility MEDIUM confidence)

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last activity: 2026-03-26
Stopped at: Completed 29-ai-pipeline-03-PLAN.md
Resume file: None
Next: Phase 29 complete — все 3 плана выполнены (GBNF, logprobs, whitelist)
