# Phase 23: Production Readiness - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase, discuss skipped)

<domain>
## Phase Boundary

Подготовить приложение к production-сборке. 4 requirement-а:
- PROD-01: Написать тесты для модулей без покрытия:
  - modules/scanner.py — 0 тестов (empty dir, nested dirs, file size limit, symlinks, hash dedup)
  - modules/extractor.py — 0 тестов (PDF, DOCX, corrupt file, empty file, большой файл)
  - modules/reporter.py — 0 тестов (empty data, large data, Unicode)
  - modules/postprocessor.py — 0 тестов (sanitize_metadata edge cases, cyrillic_only vs NDA/SLA)
  - controller.py — 0 unit тестов (mock modules, verify orchestration)
- PROD-02: Бандлить шрифты и календарь локально:
  - IBM Plex Sans: скачать woff2 файлы, положить в app/static/fonts/, заменить CDN ссылку в app/main.py
  - FullCalendar: скачать JS/CSS, положить в app/static/vendor/, заменить CDN в registry.py
- PROD-03: Зависимости:
  - Добавить numpy, httpx в requirements.txt
  - Пиннуть все версии (>= → ==) через pip freeze
- PROD-04: Локальная модель:
  - OllamaProvider: использовать config.llama_server_port вместо хардкода 8080 в providers/ollama.py:22
  - L5 verification (ai_extractor.py:518-582): рефакторить verify_metadata() чтобы использовал провайдер-систему вместо legacy _create_client()

Audit reference: .planning/AUDIT-2026-03-25.md

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — production hardening phase.

Key notes:
- PROD-01: Тесты должны использовать существующий pytest + conftest patterns. Mock AI responses, не вызывать реальные API.
- PROD-02: Для IBM Plex Sans скачать Regular (400) и Bold (700) в woff2. Для FullCalendar — core + daygrid + interaction plugins.
- PROD-03: Использовать текущие установленные версии (pip freeze), не пытаться обновлять.
- PROD-04: verify_metadata() может принимать provider parameter. Если provider=None → создать по config, но через provider factory, не через legacy _create_client().

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- `requirements.txt` — 14 зависимостей, большинство >=
- `providers/ollama.py` — base_url хардкод line 22
- `modules/ai_extractor.py` — verify_metadata() lines 518-582
- `app/main.py` — IBM Plex Sans CDN lines 91-96
- `app/pages/registry.py` — FullCalendar CDN lines 601-613
- `tests/conftest.py` — fixtures для тестов

</code_context>

<specifics>
## Specific Ideas

No specific requirements — standard production hardening.

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>
