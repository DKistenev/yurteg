# Roadmap: ЮрТэг

## Milestones

- ✅ **v0.4 Архитектура и функционал** — Phases 1-3 (shipped 2026-03-20)
- ◆ **v0.5 Локальная LLM** — Phases 4-5 (current)
- 📋 **v0.6 UI-редизайн** — planned

## Phases

<details>
<summary>✅ v0.4 Архитектура и функционал (Phases 1-3) — SHIPPED 2026-03-20</summary>

- [x] Phase 1: Инфраструктура (4 plans) — completed 2026-03-19
- [x] Phase 2: Жизненный цикл документа (8 plans) — completed 2026-03-19
- [x] Phase 3: Интеграции и мультидоступ (12 plans) — completed 2026-03-20

Phase 4 (On-Premise и безопасность) — deferred, не актуально для текущей модели доставки (DMG/EXE).

Full details: `.planning/milestones/v0.4-ROADMAP.md`

</details>

### v0.5 Локальная LLM

- [x] **Phase 4: Сервер и провайдер** — llama-server запускается и подключён как дефолтный AI-провайдер (completed 2026-03-21)
- [x] **Phase 5: Пайплайн с локальной моделью** — документы обрабатываются end-to-end через локальную LLM (completed 2026-03-21)
- [x] **Phase 6: Проводка ai_extractor через провайдер** — рефакторинг extract_metadata для маршрутизации через provider.complete() (gap closure) (completed 2026-03-21)

## Phase Details

### Phase 4: Сервер и провайдер
**Goal**: Локальная QWEN 1.5B стартует вместе с приложением и принимает запросы через реализованный провайдер
**Depends on**: Phase 3 (provider abstraction существует — OllamaProvider stub в ai_extractor.py)
**Requirements**: SRVR-01, SRVR-02, SRVR-03, SRVR-04, PROV-01, PROV-02
**Success Criteria** (что должно быть TRUE для пользователя):
  1. Пользователь открывает приложение — llama-server стартует автоматически в фоне без ручных действий
  2. При первом запуске GGUF модель (~940MB) скачивается с HuggingFace и кэшируется локально
  3. Конфиг приложения указывает `provider: local` по умолчанию — облачный провайдер не задействован без явного переключения
  4. GBNF грамматика ограничивает вывод модели кириллицей — в ответах нет латинских символов в JSON-значениях
**Plans:** 2/2 plans complete

Plans:
- [x] 04-01-PLAN.md — Серверный менеджер (скачивание + запуск llama-server) и GBNF грамматика + post-processing
- [x] 04-02-PLAN.md — OllamaProvider (реализация stub), дефолт конфига и автозапуск в main.py

### Phase 5: Пайплайн с локальной моделью
**Goal**: Обработка документов работает end-to-end через локальную LLM — с правильным post-processing ответов и без лишней анонимизации
**Depends on**: Phase 4
**Requirements**: PROV-03, PROC-01, PROC-02
**Success Criteria** (что должно быть TRUE для пользователя):
  1. Документ обработан локальной моделью — метаданные в реестре без мусора: нет строк "None", null-поля корректны
  2. При обработке локальным провайдером шаг анонимизации пропускается — скорость обработки выше, ПД не маскируются без нужды
  3. Пользователь переключается на облачный провайдер через UI-переключатель — следующие документы идут через ZAI/OpenRouter без перезапуска
**Plans:** 1/1 plans complete

Plans:
- [x] 05-01-PLAN.md — Pipeline integration + UI-переключатель провайдера

### Phase 6: Проводка ai_extractor через провайдер
**Goal**: extract_metadata маршрутизирует запросы через provider.complete() вместо legacy _try_model, sanitize_metadata корректно вызывается и применяется
**Depends on**: Phase 5
**Requirements**: SRVR-01, SRVR-02, PROV-01, PROC-01
**Gap Closure:** Closes integration gaps from v0.5 audit
**Success Criteria** (что должно быть TRUE для пользователя):
  1. Документ обработан через OllamaProvider.complete() — запрос идёт на localhost:8080, не на ZAI/OpenRouter
  2. GBNF грамматика применяется — вывод модели ограничен JSON-схемой
  3. sanitize_metadata получает dict, возвращает dict, результат используется — метаданные чистые
**Plans:** 1/1 plans complete

Plans:
- [x] 06-01-PLAN.md — Provider routing fix + sanitize_metadata wiring

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Инфраструктура | v0.4 | 4/4 | Complete | 2026-03-19 |
| 2. Жизненный цикл | v0.4 | 8/8 | Complete | 2026-03-19 |
| 3. Интеграции | v0.4 | 12/12 | Complete | 2026-03-20 |
| 4. Сервер и провайдер | v0.5 | 2/2 | Complete   | 2026-03-21 |
| 5. Пайплайн с локальной LLM | v0.5 | 1/1 | Complete   | 2026-03-21 |
| 6. Проводка ai_extractor | v0.5 | 1/1 | Complete   | 2026-03-21 |
