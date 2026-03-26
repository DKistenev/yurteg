---
phase: 30-redline-vectors
plan: 02
subsystem: services
tags: [vectors, embeddings, templates, review]
dependency_graph:
  requires: [30-01]
  provides: [VEC-02, VEC-03, VEC-04]
  affects: [services/review_service.py, services/version_service.py]
tech_stack:
  added: []
  patterns: [embedding-cache, full-text-templates]
key_files:
  modified:
    - services/review_service.py
    - services/version_service.py
decisions:
  - "full_text приоритетнее subject при пометке шаблона (content = full_text or subject or filename)"
  - "Embedding сохраняется сразу при mark_contract_as_template через INSERT OR REPLACE"
  - "match_template загружает cached_vectors из template_embeddings — нет повторного compute_embedding"
  - "TEMPLATE_MATCH_THRESHOLD поднят 0.60 → 0.70 (меньше ложных подборов)"
  - "compute_embedding убирает срез [:8000] — модель MiniLM усекает до max_seq_length сама"
metrics:
  duration_minutes: 12
  completed_date: "2026-03-26T19:30:10Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 30 Plan 02: Vector Layer Fix Summary

**One-liner:** Исправлен баг сохранения шаблонов (full_text вместо subject) + кэш embeddings в template_embeddings + порог 0.70.

## What Was Built

### Task 1: mark_contract_as_template + кэшированный match_template

`mark_contract_as_template` в `review_service.py` раньше сохранял только поле `subject` (3–10 слов) как контент шаблона. Исправлен SELECT — теперь достаёт `full_text` из contracts. После `add_template` сразу вычисляет embedding и сохраняет через `INSERT OR REPLACE INTO template_embeddings`.

`match_template` теперь перед циклом загружает все кэшированные embeddings из `template_embeddings`. Для каждого шаблона: если есть в кэше — берёт оттуда, иначе вычисляет на лету. Модель при изменении версии автоматически игнорирует старые кэши (`model_version` check).

### Task 2: compute_embedding + порог

Убран срез `[:8000]` из `compute_embedding` — MiniLM-L12-v2 сам усекает до `max_seq_length` (128 токенов). `TEMPLATE_MATCH_THRESHOLD` поднят с 0.60 до 0.70.

## Verification

```
OK: threshold=0.7, no truncation in compute_embedding
25 passed in 1.08s (test_postprocessor, test_migrations, test_versioning)
```

## Deviations from Plan

None — план выполнен точно как написан.

## Known Stubs

None.

## Self-Check: PASSED

- `services/review_service.py` — существует, изменён (commit c6602c4)
- `services/version_service.py` — существует, изменён (commit 1ce62c1)
- Оба коммита присутствуют в git log
