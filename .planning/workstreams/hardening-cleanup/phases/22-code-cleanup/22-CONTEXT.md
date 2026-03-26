# Phase 22: Code Cleanup - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase, discuss skipped)

<domain>
## Phase Boundary

Удалить мёртвый код, починить тесты. 3 requirement-а:
- CLEAN-01: Удалить main.py (Streamlit UI, 1700+ строк) — заменён NiceGUI app/main.py. Одна точка входа.
- CLEAN-02: Удалить неиспользуемые функции и дубликаты из бэкенда:
  - ai_extractor.py: _create_client() (lines 222-268), _try_model() (lines 436-515) — legacy, не вызываются
  - ai_extractor.py: _merge_system_into_user() (lines 189-219) — дубликат openrouter.py:13-42, оставить в одном месте
  - services/registry_service.py — используется только в 1 тесте, production обходит
  - config.py: use_prod_model, model_prod/model_dev (оба = "glm-4.7") — бесполезный toggle
  - reporter.py: unused imports (DataPoint, PatternFillProperties, ColorChoice) lines 302-303
  - app/styles.py: 8 unused style-констант (BTN_PRIMARY, BTN_FLAT, TEXT_HEADING_XL, TEXT_BODY, SECTION_LABEL, DIVIDER, TEMPLATE_CARD, CARD_SECTION)
  - app/pages/: unused imports (empty_state в registry, CARD_SECTION/TEXT_SUBHEAD/HEX в document, TMPL_EMPTY_ICON в templates, TEXT_LABEL_SECTION в settings)
  - app/components/ui_helpers.py: form_dialog(), section_card() — никогда не вызываются
  - app/components/skeleton.py: skeleton_rows(), skeleton_card() — никогда не вызываются
  - app/state.py: 9 полей которые нигде не читаются (output_dir, report_path, show_results, force_reprocess, processing_time, upload_dir, filter_type, filter_status, selected_doc_id)
- CLEAN-03: Починить падающие тесты:
  - 15 FAIL из-за httpx/SOCKS5 proxy — мокать или очищать env vars в conftest.py
  - 8 xfail на тестах lifecycle/versioning/payments — сервисы уже работают, снять xfail
  - 2 хрупких CSS-теста — переписать или удалить

Audit reference: .planning/AUDIT-2026-03-25.md

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure cleanup phase.

Key notes:
- При удалении main.py (Streamlit) проверить что desktop_app.py НЕ зависит от него
- При удалении registry_service.py — обновить тест test_service_layer.py который его импортирует
- При удалении state.py полей — проверить каждое через grep (может быть referenced в комментарии)
- _merge_system_into_user() — оставить в providers/openrouter.py, удалить из ai_extractor.py, добавить import
- xfail тесты: сначала снять xfail, потом посмотреть какие реально падают и починить

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- `main.py` — Streamlit UI, 1700+ строк, НЕ используется с v0.6
- `desktop_app.py` — запускает NiceGUI app/main.py
- `modules/ai_extractor.py` — legacy functions
- `services/registry_service.py` — обёртка над Database, не используется
- `tests/conftest.py` — pytest fixtures, место для proxy fix
- `tests/test_lifecycle.py`, `test_versioning.py`, `test_payments.py` — xfail тесты

</code_context>

<specifics>
## Specific Ideas

No specific requirements — standard cleanup work.

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>
