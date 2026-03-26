# Phase 28: Cleanup - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

Кодовая база содержит только живой код — без validator, reporter, deprecated функций, мёртвых import-цепочек. Приложение запускается и тесты проходят после удаления.

Requirements: CLEAN-01, CLEAN-02, CLEAN-03, CLEAN-04, CLEAN-05, STAB-01, STAB-02

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase. Key constraints from research:
- Удаление validator.py: 3 точки вызова в controller.py, 2 места в test_controller.py
- Удаление reporter.py: stats["report_path"] — часть return-контракта process_archive(). Оставить ключ со значением None
- Deprecated _create_client/_try_model в ai_extractor.py — удалить полностью
- Thinking mode setting в settings.py — удалить toggle и config key
- atexit.register() в llama_server.py — вынести из retry-цикла
- Text truncation warning — добавить logging.warning при обрезке >30K в ai_extractor.py

</decisions>

<code_context>
## Existing Code Insights

### Key Files to Modify
- `controller.py` — imports + вызовы validate_metadata, validate_batch, generate_report
- `modules/validator.py` — DELETE
- `modules/reporter.py` — DELETE
- `modules/ai_extractor.py` — удалить _create_client, _try_model, добавить truncation warning
- `services/llama_server.py` — atexit fix
- `app/pages/settings.py` — удалить thinking mode toggle
- `config.py` — удалить ai_disable_thinking
- `tests/` — удалить/обновить тесты

### Dependencies
- reporter.py вызывается только из controller.py
- validator.py вызывается только из controller.py
- _create_client/_try_model — legacy fallback, не используется с OllamaProvider

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase. Refer to ROADMAP phase description and success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
