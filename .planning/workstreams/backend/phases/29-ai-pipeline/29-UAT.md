---
status: complete
phase: 29-ai-pipeline
source: 29-01-SUMMARY.md, 29-02-SUMMARY.md, 29-03-SUMMARY.md
started: 2026-03-27T15:20:00Z
updated: 2026-03-27T15:22:00Z
---

## Current Test

[testing complete]

## Tests

### 1. GBNF грамматика обновлена
expected: contract.gbnf содержит contract_number, не содержит confidence, месяцы строго 01-12
result: pass

### 2. Двухзапросный flow с logprobs
expected: OllamaProvider.get_logprobs() существует, grammar передаётся через extra_body. ai_extractor содержит _compute_confidence_from_logprobs, _has_suspicious_nulls, _load_grammar.
result: pass

### 3. Аббревиатуры сохраняются в постпроцессоре
expected: NDA, SLA, GPS, ООО, ИП и др. не удаляются cyrillic_only фильтром. protect/restore через placeholder.
result: pass

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
