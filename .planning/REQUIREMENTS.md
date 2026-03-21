# Requirements: ЮрТэг

**Defined:** 2026-03-21
**Core Value:** Юрист загружает папку с документами и за 20 минут получает готовый реестр — без ручного ввода, без обучения, без «проекта внедрения»

## v0.5 Requirements

### Сервер

- [ ] **SRVR-01**: llama-server запускается как локальный бэкенд для модели
- [ ] **SRVR-02**: GBNF грамматика ограничивает вывод кириллицей
- [ ] **SRVR-03**: llama-server стартует автоматически при открытии приложения
- [ ] **SRVR-04**: GGUF модель скачивается с HuggingFace при первом запуске

### Провайдер

- [ ] **PROV-01**: OllamaProvider реализован (вместо stub) для работы с llama-server
- [ ] **PROV-02**: Локальная модель = провайдер по умолчанию в конфиге
- [ ] **PROV-03**: Временный переключатель в UI для переключения на облачный провайдер

### Обработка

- [ ] **PROC-01**: Post-processing ответов модели ("None" → null, санитайзер)
- [ ] **PROC-02**: Анонимизация пропускается для локального провайдера

## Future Requirements

### Доставка

- **DLVR-01**: DMG-сборка с llama-server + GGUF внутри
- **DLVR-02**: .exe-сборка для Windows

### Качество модели

- **QUAL-01**: Автоматический fallback на облачный провайдер при низком качестве
- **QUAL-02**: Логирование уверенности модели для мониторинга

## Out of Scope

| Feature | Reason |
|---------|--------|
| DMG/EXE бандлинг | Отложен — сначала интеграция, потом доставка |
| Автоматический fallback на облако | Не нужен сейчас, есть ручной переключатель |
| Дообучение модели | Модель v3 ORPO уже готова (85% чистых, 0 code-switching) |
| Ollama как runtime | llama-server выбран вместо Ollama (GBNF, llamafile) |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SRVR-01 | Phase 4 | Pending |
| SRVR-02 | Phase 4 | Pending |
| SRVR-03 | Phase 4 | Pending |
| SRVR-04 | Phase 4 | Pending |
| PROV-01 | Phase 4 | Pending |
| PROV-02 | Phase 4 | Pending |
| PROV-03 | Phase 5 | Pending |
| PROC-01 | Phase 5 | Pending |
| PROC-02 | Phase 5 | Pending |

**Coverage:**
- v0.5 requirements: 9 total
- Mapped to phases: 9
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-21*
*Last updated: 2026-03-21 — traceability filled after roadmap creation*
