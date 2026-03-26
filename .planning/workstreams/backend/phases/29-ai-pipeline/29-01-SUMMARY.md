---
phase: 29-ai-pipeline
plan: "01"
subsystem: ai-pipeline
tags: [gbnf, llama-server, grammar, logprobs]
dependency_graph:
  requires: []
  provides: [gbnf-schema-v2, llama-server-no-grammar-flag]
  affects: [providers/ollama.py, modules/ai_extractor.py]
tech_stack:
  added: []
  patterns: [per-request-grammar, grammar-in-body-not-server-flag]
key_files:
  created: []
  modified:
    - data/contract.gbnf
    - services/llama_server.py
decisions:
  - "GBNF грамматика передаётся через тело запроса, не через флаг сервера — это позволяет делать два независимых запроса: один с grammar (структурированные данные), второй без (logprobs для confidence)"
  - "confidence удалён из GBNF-схемы — будет считаться через logprobs Ollama"
  - "contract_number добавлен как опциональное поле"
  - "Месяцы в date-or-null строго 01-12 (вместо 00-19)"
metrics:
  duration_minutes: 5
  completed_date: "2026-03-26"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 2
---

# Phase 29 Plan 01: GBNF Grammar Update + grammar-file Removal Summary

**One-liner:** Обновлена GBNF-схема (убран confidence, добавлен contract_number, ужесточены даты) и llama-server запускается без --grammar-file для поддержки двух независимых запросов.

## What Was Built

Подготовка AI-пайплайна к архитектуре с logprobs: грамматика теперь передаётся per-request через тело запроса, что позволяет делать отдельный запрос без grammar для получения logprobs (confidence).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Обновить GBNF грамматику | d2d0b29 | data/contract.gbnf |
| 2 | Убрать --grammar-file из llama_server.py | 28235eb | services/llama_server.py |

## Changes Made

### data/contract.gbnf
- Удалено поле `confidence` из root и rule `confidence ::=`
- Добавлено опциональное поле `contract_number` после `amount`
- Ужесточены месяцы в `date-or-null`: `[0-1][0-9]` → `(("0" [1-9]) | ("1" [0-2]))` — строго 01-12
- Ужесточены дни: `[0-3][0-9]` → `(("0" [1-9]) | ([1-2] [0-9]) | ("3" [0-1]))` — строго 01-31
- Обновлён комментарий в шапке файла (v2)

### services/llama_server.py
- Удалён параметр `grammar_path: Optional[Path] = None` из сигнатуры `start()`
- Удалён блок `if grammar_path is not None and grammar_path.exists(): cmd_base += ["--grammar-file", ...]`
- Обновлён docstring метода `start()` — убрано упоминание grammar_path
- Импорт `Optional` сохранён (используется для `self._process: Optional[subprocess.Popen]`)

## Verification Results

```
OK: GBNF обновлён корректно
OK: grammar_path и --grammar-file удалены, файл синтаксически корректен
OK: no start(grammar calls
```

## Test Results

31 passed, 1 failed (pre-existing):
- `test_anonymize_50_docs` — стресс-тест производительности анонимизатора (38.2 сек > 30 сек лимит). Не связан с изменениями этого плана, scope boundary — анонимизатор не затронут.

## Deviations from Plan

None — план выполнен точно, оба файла уже были в корректном состоянии от предыдущих коммитов (d2d0b29, 28235eb). SUMMARY.md отсутствовал — создан сейчас.

## Self-Check: PASSED

- [x] data/contract.gbnf — не содержит "confidence", содержит "contract_number", месяцы 01-12
- [x] services/llama_server.py — не содержит grammar_path, не содержит --grammar-file
- [x] Коммиты d2d0b29 и 28235eb существуют в git log
- [x] Нет вызовов start(grammar...) в кодовой базе
