---
phase: 29-ai-pipeline
plan: "02"
subsystem: ai-pipeline
tags: [logprobs, confidence, grammar, ollama, two-request-flow]
dependency_graph:
  requires: [29-01]
  provides: [logprobs-confidence, grammar-in-body]
  affects: [providers/ollama.py, modules/ai_extractor.py]
tech_stack:
  added: []
  patterns: [two-request-flow, grammar-via-extra-body, logprobs-normalization]
key_files:
  created: []
  modified:
    - providers/ollama.py
    - modules/ai_extractor.py
decisions:
  - "grammar передаётся через extra_body в complete(), не через server flag"
  - "get_logprobs() делает отдельный запрос без grammar с logprobs=True"
  - "второй запрос только при suspicious nulls в ключевых полях (экономия)"
  - "нормализация logprobs: mean_lp диапазон [-4, 0] → confidence [0.0, 1.0]"
  - "защита от нечисловых значений в lp.get() — тесты с MagicMock не ломаются"
metrics:
  duration: "9m 11s"
  completed: "2026-03-26"
  tasks_completed: 2
  files_modified: 2
---

# Phase 29 Plan 02: Logprobs Confidence — Summary

**One-liner:** Двухзапросный flow к llama-server — grammar в первом запросе, logprobs во втором, confidence нормализуется из mean logprob по ключевым полям.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 0 | Curl-тест logprobs (авто-проверка) | — | — |
| 1 | Grammar и get_logprobs в OllamaProvider | e5702cd | providers/ollama.py |
| 2 | Двухзапросный flow и confidence в ai_extractor | 0360d66 | modules/ai_extractor.py |

## What Was Built

**Task 0 (curl-тест):** llama-server b5606 работал. Оба теста прошли:
- Grammar через request body: `{"test": "ok"}` — ответ точно по схеме
- Logprobs: `choices[0].logprobs.content` с отрицательными числами — работает

**Task 1 — OllamaProvider:**
- `complete()` теперь принимает `grammar=` в kwargs и передаёт через `extra_body` (llama-server extension)
- `get_logprobs()` делает второй запрос с `logprobs=True, top_logprobs=1`, возвращает `{"_min": float, "_mean": float}`
- Если get_logprobs не удался — возвращает `{}`

**Task 2 — ai_extractor.py:**
- `_load_grammar()` загружает `data/contract.gbnf`
- `_has_suspicious_nulls()` — проверяет contract_type/counterparty/amount на None
- `_compute_confidence_from_logprobs()` — нормализует mean logprob из [-4, 0] в [0.0, 1.0]
- `_try_provider()` расширен `**kwargs` — передаёт grammar= в complete()
- `extract_metadata()`: первый запрос с grammar (Ollama), второй только при suspicious nulls

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Защита от MagicMock в _compute_confidence_from_logprobs**
- **Found during:** Task 2, прогон тестов
- **Issue:** `test_provider_route_called` использует MagicMock — `provider.get_logprobs()` возвращает MagicMock, `lp.get("_mean")` тоже MagicMock, `max(0.0, min(1.0, MagicMock + 4.0))` → `TypeError`
- **Fix:** Проверка `isinstance(lp, dict)` и `isinstance(mean_lp, (int, float))` перед нормализацией
- **Files modified:** modules/ai_extractor.py
- **Commit:** 0360d66

## Known Stubs

None — confidence реально вычисляется из logprobs, не захардкожен.

## Self-Check

- [x] providers/ollama.py существует и содержит get_logprobs, extra_body
- [x] modules/ai_extractor.py содержит _load_grammar, _has_suspicious_nulls, _compute_confidence_from_logprobs
- [x] Коммиты e5702cd и 0360d66 существуют
- [x] 138 тестов прошли, 0 упало
