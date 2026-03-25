# Phase 29: AI Pipeline - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

AI-слой выдаёт реальный confidence через logprobs, GBNF-грамматика отражает актуальную схему, постпроцессор не ломает латинские аббревиатуры.

Requirements: AI-01, AI-02, AI-03

</domain>

<decisions>
## Implementation Decisions

### Confidence Architecture
- Два запроса к llama-server: первый с GBNF для структурированных данных, второй без GBNF для logprobs на ключевых полях (contract_type, counterparty, amount)
- Порог: logprobs < -2.0 на ключевых полях → помечать документ как "требует проверки"
- Хранить confidence в существующей колонке contracts.confidence — обновлять после второго запроса
- Второй запрос только для файлов где GBNF дал подозрительные null-поля — экономия на хороших документах

### GBNF Grammar
- Добавить contract_number (опциональное поле) в грамматику
- Ужесточить месяцы (01-12 вместо 00-19)
- Убрать confidence из GBNF (модель не должна его генерить)
- Грамматика передаётся через тело запроса (json_schema/grammar в OpenAI request body), не через server flag --grammar-file — это позволяет отключить грамматику для logprobs-запроса

### Постпроцессор
- Whitelist латинских аббревиатур в cyrillic_only профиле: NDA, SLA, GPS, ИНН, МРОТ, НДС, ООО, ИП, ЗАО, ОАО
- Эти аббревиатуры не должны удаляться при обработке cyrillic_only полей

### Claude's Discretion
- Формат второго запроса (промпт для logprobs) — на усмотрение
- Как именно извлекать logprobs из OpenAI-compatible response — на усмотрение
- Нужно ли обновлять SYSTEM_PROMPT при изменении GBNF — на усмотрение

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- `modules/ai_extractor.py` — основной модуль, extract_metadata(), _try_provider()
- `providers/ollama.py` — OllamaProvider.complete(), общается с llama-server
- `modules/postprocessor.py` — sanitize_metadata(), FIELD_PROFILES
- `data/contract.gbnf` — текущая GBNF грамматика
- `services/llama_server.py` — запуск llama-server, --grammar-file flag
- `config.py` — Config dataclass

### Current Architecture
- llama-server запускается с --grammar-file contract.gbnf (server-level)
- OllamaProvider вызывает /v1/chat/completions без logprobs
- Confidence = 0.0 по умолчанию (модель не генерирует reliable confidence)
- Постпроцессор: FIELD_PROFILES["cyrillic_only"] удаляет все латинские символы

### Integration Points
- Грамматику нужно перенести из server flag в request body
- OllamaProvider.complete() нужно расширить для logprobs
- postprocessor.py — добавить whitelist в cyrillic_only regex

</code_context>

<specifics>
## Specific Ideas

- Research показал: llama-server b5606 поддерживает `logprobs=True` через OpenAI-compatible API
- ВАЖНО: перед реализацией — curl-тест logprobs против работающего llama-server (MEDIUM confidence из research)
- Grammar через request body: параметр `grammar` в JSON body (не `json_schema`)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 29-ai-pipeline*
*Context gathered: 2026-03-26 via smart discuss*
