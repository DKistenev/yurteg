---
phase: 04-server-provider
plan: 02
subsystem: infra
tags: [ollama, llama-server, openai-sdk, streamlit, cache-resource, local-llm, qwen]

# Dependency graph
requires:
  - phase: 04-server-provider plan 01
    provides: LlamaServerManager (start/stop/is_running/base_url/ensure_model/ensure_server_binary), get_grammar_path, data/contract.gbnf
  - phase: 03-integrations-multitenancy
    provides: provider abstraction (LLMProvider base class, OllamaProvider stub, providers/__init__.py factory)
provides:
  - OllamaProvider — полноценный провайдер для llama-server через openai SDK
  - config.py с active_provider='ollama' по умолчанию и llama-server полями
  - main.py автозапуск llama-server через @st.cache_resource при старте приложения
affects:
  - 05 (PROC-01): ai_extractor.py вызывает sanitize_metadata после ответа OllamaProvider
  - providers/__init__.py: get_provider('ollama') теперь возвращает рабочий провайдер

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "@st.cache_resource для singleton-менеджера llama-server — переживает Streamlit reruns"
    - "OllamaProvider принимает base_url в конструкторе с дефолтом — позволяет тестировать без реального сервера"
    - "api_key='not-needed' — openai SDK требует непустой ключ, llama-server игнорирует"

key-files:
  created: []
  modified:
    - providers/ollama.py (35 lines) — полноценный OllamaProvider вместо stub
    - config.py — active_provider='ollama', fallback='zai', + 3 llama-server поля
    - main.py — автозапуск llama-server через @st.cache_resource _get_llama_manager()

key-decisions:
  - "OllamaProvider.complete() возвращает сырой текст — sanitize_metadata применяется в ai_extractor.py (Phase 5)"
  - "base_url передаётся в конструктор OllamaProvider с дефолтом localhost:8080/v1 — не захардкожен"
  - "fallback_provider='zai' вместо 'openrouter' — ZAI основной облачный провайдер для fallback"
  - "@st.cache_resource решает blocker из STATE.md: сервер не перезапускается на каждый Streamlit rerun"

patterns-established:
  - "@st.cache_resource pattern: использовать для singleton-ресурсов (subprocess, соединения) в Streamlit"
  - "verify_key() pattern: возвращает False (не raises) при недоступном сервере — безопасно для fallback-роутинга"

requirements-completed: [PROV-01, PROV-02]

# Metrics
duration: ~2min
completed: 2026-03-21
---

# Phase 04 Plan 02: Server Provider — OllamaProvider + Config + Autostart Summary

**OllamaProvider с openai SDK для llama-server, дефолт active_provider='ollama' и автозапуск сервера через @st.cache_resource при старте Streamlit**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-21T14:09:33Z
- **Completed:** 2026-03-21T14:10:55Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `providers/ollama.py` — полноценный OllamaProvider: OpenAI SDK клиент с base_url, temperature=0.05/max_tokens=512 из Modelfile, verify_key() возвращает False без exception при недоступном сервере
- `config.py` — дефолт active_provider='ollama', fallback_provider='zai', 3 новых поля: llama_server_port, llama_model_repo, llama_model_filename
- `main.py` — `_get_llama_manager()` с `@st.cache_resource`: скачивает модель + бинарник + запускает сервер с grammar при старте; warning + graceful fallback если что-то пошло не так

## Task Commits

1. **Task 1: Реализовать OllamaProvider** - `3278bba` (feat)
2. **Task 2: Обновить config.py + подключить автозапуск в main.py** - `8109d23` (feat)

## Files Created/Modified

- `providers/ollama.py` — заменён stub на полноценный провайдер (35 строк)
- `config.py` — active_provider='ollama', fallback_provider='zai', добавлены llama-server поля
- `main.py` — импорт LlamaServerManager + get_grammar_path, блок _get_llama_manager()

## Decisions Made

- `base_url` передаётся в конструктор OllamaProvider с дефолтом `http://localhost:8080/v1` — позволяет тестировать без реального сервера
- `fallback_provider='zai'` вместо 'openrouter' — ZAI является основным облачным провайдером
- Post-processing (`sanitize_metadata`) не вызывается внутри OllamaProvider — возвращает сырой текст, Phase 5 подключает sanitize в ai_extractor.py
- `@st.cache_resource` для `_get_llama_manager` — singleton, переживает reruns (закрывает blocker из STATE.md)

## Deviations from Plan

None — план выполнен точно как написан.

## Issues Encountered

None.

## User Setup Required

None — llama-server и модель скачиваются автоматически при первом запуске.

## Known Stubs

None — OllamaProvider полностью реализован. Post-processing (`sanitize_metadata`) намеренно отложен на Phase 5 (PROC-01) и документирован в docstring провайдера.

## Next Phase Readiness

- `OllamaProvider` готов к использованию в `ai_extractor.py`
- При `active_provider='ollama'` приложение автоматически запускает llama-server при старте
- Phase 5 (PROC-01): добавить вызов `sanitize_metadata` в `ai_extractor.py` после ответа OllamaProvider
- Phase 5 (PROC-02): пропуск анонимизации для `active_provider='ollama'` (ПД не покидают машину)

## Self-Check: PASSED

- providers/ollama.py: FOUND
- config.py: FOUND
- main.py: FOUND
- 04-02-SUMMARY.md: FOUND
- Commit 3278bba (Task 1): FOUND
- Commit 8109d23 (Task 2): FOUND

---
*Phase: 04-server-provider*
*Completed: 2026-03-21*
