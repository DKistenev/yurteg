# Requirements — v1.0 Hackathon-Ready

## Audit Fixes
- [ ] **AUDIT-01**: Шрифты IBM Plex Sans загружаются (add_static_files в main.py)
- [ ] **AUDIT-02**: AG Grid API обновлён до v32.2+ (checkboxSelection/headerCheckboxSelection → gridOptions)
- [ ] **AUDIT-03**: Двойные вызовы _refresh_deadline_widget удалены (registry.py:1204-1205, 1138)
- [ ] **AUDIT-04**: Settings summary cards работают (scroll-to-section) или убрать cursor-pointer
- [ ] **AUDIT-05**: Inline hardcoded colors заменены на CSS custom properties (--yt-*)
- [ ] **AUDIT-06**: Bulk actions кнопки доступны с клавиатуры (ui.button вместо ui.html)
- [ ] **AUDIT-07**: _MONTHS_RU и _format_date_ru вынесены в shared utils (удалить дубли из 3 файлов)

## Cross-Scope Integration
- [ ] **XSCOPE-01**: split_panel импортирует STATUS_LABELS из lifecycle_service (убрать _STATUS_STYLE дубль)
- [ ] **XSCOPE-02**: Footer показывает APP_VERSION из config.py вместо хардкода v0.7.1
- [ ] **XSCOPE-03**: Защитный dict(doc) cast убран из registry.py (после унификации database.py)

## Error Resilience
- [ ] **ERRES-01**: Обработка документов — loading state и error toast при падении бэкенда
- [ ] **ERRES-02**: Graceful fallback при недоступности llama-server (toast + рекомендация)

## Registry Polish
- [ ] **REG-01**: Поиск с иконкой и кнопкой очистки (prepend-icon=search, clearable)
- [ ] **REG-02**: Календарь не показывает прошедшие события в «На этой неделе»
- [ ] **REG-03**: Мини-календарь с навигацией по месяцам (кнопки < >)

## Document Card Polish
- [ ] **DOC-01**: Карточка документа с PDF/DOCX превью справа (двухколоночный layout)
- [ ] **DOC-02**: Feedback при сохранении заметки (toast «Сохранено» при blur)

## Templates & Settings Polish
- [ ] **TMPL-01**: Шаблоны — visual consistency, empty state доведение
- [ ] **SETT-01**: Настройки — summary cards scroll-to-section работает

## Onboarding Polish
- [ ] **ONBR-01**: Wizard и гид-тур работают end-to-end, визуально консистентны

## Final Visual Pass
- [ ] **VIS-01**: Финальный проход — spacing, typography, animations консистентны на всех экранах

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| AUDIT-01 | Phase 32 | Pending |
| AUDIT-02 | Phase 32 | Pending |
| AUDIT-03 | Phase 32 | Pending |
| AUDIT-04 | Phase 33 | Pending |
| AUDIT-05 | Phase 33 | Pending |
| AUDIT-06 | Phase 33 | Pending |
| AUDIT-07 | Phase 33 | Pending |
| ERRES-01 | Phase 33 | Pending |
| ERRES-02 | Phase 33 | Pending |
| REG-01 | Phase 34 | Pending |
| REG-02 | Phase 34 | Pending |
| REG-03 | Phase 34 | Pending |
| DOC-01 | Phase 34 | Pending |
| DOC-02 | Phase 34 | Pending |
| TMPL-01 | Phase 35 | Pending |
| SETT-01 | Phase 35 | Pending |
| ONBR-01 | Phase 35 | Pending |
| XSCOPE-01 | Phase 36 | Pending |
| XSCOPE-02 | Phase 36 | Pending |
| XSCOPE-03 | Phase 36 | Pending |
| VIS-01 | Phase 37 | Pending |

---

# Backend (CalmBridge scope)

## Cross-Scope (блокеры фронтенда)
- [ ] **XSCOPE-04**: APP_VERSION константа в config.py
- [ ] **XSCOPE-05**: STATUS_LABELS с 4-м элементом css_class в lifecycle_service.py
- [ ] **XSCOPE-06**: database.py get_contract_by_id/get_all_results всегда возвращают dict

## Thread Safety
- [ ] **TSAFE-01**: RLock вместо Lock в database.py
- [ ] **TSAFE-02**: Locks на все read-методы database.py (is_processed, get_all_results, get_stats)
- [ ] **TSAFE-03**: Атомарные операции в version_service.ensure_embedding
- [ ] **TSAFE-04**: Атомарные find_version_match + link_versions
- [ ] **TSAFE-05**: Lock в find_version_match вне цикла
- [ ] **TSAFE-06**: llama_server.is_running() race condition fix
- [ ] **TSAFE-07**: Атомарная запись settings.json (tempfile → os.replace)
- [ ] **TSAFE-08**: threading.Lock на save_setting read-modify-write

## Data Integrity
- [ ] **DINT-01**: contract_number: поле в ContractMetadata + миграция v10 + save_result SQL
- [ ] **DINT-02**: Деанонимизация ВСЕХ строковых полей ContractMetadata
- [ ] **DINT-03**: Флаг was_truncated при обрезке текста >30K
- [ ] **DINT-04**: redline_service дата → datetime.now(UTC)
- [ ] **DINT-05**: Telegram sync: валидация ключей item['id']/item['filename']
- [ ] **DINT-06**: Telegram sync: write → delete атомарность
- [ ] **DINT-07**: JSON corruption в settings.json — бэкап + логирование

## Config Hardening
- [ ] **CONF-01**: __post_init__() в Config — валидация всех числовых полей
- [ ] **CONF-02**: active_model property — учитывать active_provider
- [ ] **CONF-03**: telegram_chat_id: Optional[int] = None
- [ ] **CONF-04**: validation_mode через Literal с проверкой
- [ ] **CONF-05**: Bare except → except (json.JSONDecodeError, OSError) в load_settings
- [ ] **CONF-06**: settings.json chmod 0o600 на Unix

## Provider Cleanup
- [ ] **PROV-01**: timeout на всех провайдерах (120s ollama, 60s cloud)
- [ ] **PROV-02**: close() метод для HTTP-клиентов
- [ ] **PROV-03**: get_logprobs() default impl в LLMProvider base class
- [ ] **PROV-04**: API key validation — raise ValueError при пустом ключе
- [ ] **PROV-05**: verify_key() — конкретные except
- [ ] **PROV-06**: Response choices[0] bounds check
- [ ] **PROV-07**: Defensive copy messages в openrouter
- [ ] **PROV-08**: ai_disable_thinking — добавить в Config или убрать
- [ ] **PROV-09**: name property вместо class attribute

## Error Handling & Validation
- [ ] **ERRH-01**: Bare except в extractor.py → except Exception
- [ ] **ERRH-02**: GBNF grammar loading fail-loud
- [ ] **ERRH-03**: _split_sentences(None) guard
- [ ] **ERRH-04**: generate_redline_docx(None) guard
- [ ] **ERRH-05**: Negative/zero amount validation в payment_service
- [ ] **ERRH-06**: Invalid frequency validation
- [ ] **ERRH-07**: date_start > date_end validation
- [ ] **ERRH-08**: warning_days validation (>0)
- [ ] **ERRH-09**: counterparty=None guard в client_manager
- [ ] **ERRH-10**: Row unpacking bounds check
- [ ] **ERRH-11**: _parse_date short string check
- [ ] **ERRH-12**: JSON parse failure logging в version_service
- [ ] **ERRH-13**: BytesIO context manager в redline_service
- [ ] **ERRH-14**: Latin name regex — добавить дефисы в anonymizer
- [ ] **ERRH-15**: import json → module-level в version_service
- [ ] **ERRH-16**: Удалить unused has_changes в redline_service
- [ ] **ERRH-17**: db._lock → публичный интерфейс
- [ ] **ERRH-18**: O(n²) path collision → set() в client_manager

## Test Coverage
- [ ] **TEST-01**: Thread safety тесты для database.py concurrent writes
- [ ] **TEST-02**: version_service concurrent initialization
- [ ] **TEST-03**: payment_service edge cases (start>end, negative, zero, max_iter)
- [ ] **TEST-04**: Database migrations v2-v9 independent tests
- [ ] **TEST-05**: ai_extractor 8 helper functions
- [ ] **TEST-06**: ai_extractor extract_metadata error paths
- [ ] **TEST-07**: payment_service save_payments all combos
- [ ] **TEST-08**: version_service find_version_match errors + boundaries
- [ ] **TEST-09**: lifecycle_service set/clear_manual_status
- [ ] **TEST-10**: payment_service get_calendar_events
- [ ] **TEST-11**: version_service diff_versions
- [ ] **TEST-12**: postprocessor _protect/_restore_abbreviations
- [ ] **TEST-13**: ai_extractor _normalize_date boundaries
- [ ] **TEST-14**: lifecycle_service get_attention_required edge cases
- [ ] **TEST-15**: conftest.py autouse fixture to reset _model singleton

---

## Backend Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| XSCOPE-04 | Phase 38 | Pending |
| XSCOPE-05 | Phase 38 | Pending |
| XSCOPE-06 | Phase 38 | Pending |
| CONF-01 | Phase 38 | Pending |
| CONF-02 | Phase 38 | Pending |
| CONF-03 | Phase 38 | Pending |
| CONF-04 | Phase 38 | Pending |
| CONF-05 | Phase 38 | Pending |
| CONF-06 | Phase 38 | Pending |
| PROV-01 | Phase 39 | Pending |
| PROV-02 | Phase 39 | Pending |
| PROV-03 | Phase 39 | Pending |
| PROV-04 | Phase 39 | Pending |
| PROV-05 | Phase 39 | Pending |
| PROV-06 | Phase 39 | Pending |
| PROV-07 | Phase 39 | Pending |
| PROV-08 | Phase 39 | Pending |
| PROV-09 | Phase 39 | Pending |
| DINT-01 | Phase 40 | Pending |
| DINT-02 | Phase 40 | Pending |
| DINT-03 | Phase 40 | Pending |
| DINT-04 | Phase 40 | Pending |
| DINT-05 | Phase 40 | Pending |
| DINT-06 | Phase 40 | Pending |
| DINT-07 | Phase 40 | Pending |
| TSAFE-01 | Phase 41 | Pending |
| TSAFE-02 | Phase 41 | Pending |
| TSAFE-03 | Phase 41 | Pending |
| TSAFE-04 | Phase 41 | Pending |
| TSAFE-05 | Phase 41 | Pending |
| TSAFE-06 | Phase 41 | Pending |
| TSAFE-07 | Phase 41 | Pending |
| TSAFE-08 | Phase 41 | Pending |
| ERRH-01 | Phase 42 | Pending |
| ERRH-02 | Phase 42 | Pending |
| ERRH-03 | Phase 42 | Pending |
| ERRH-04 | Phase 42 | Pending |
| ERRH-05 | Phase 42 | Pending |
| ERRH-06 | Phase 42 | Pending |
| ERRH-07 | Phase 42 | Pending |
| ERRH-08 | Phase 42 | Pending |
| ERRH-09 | Phase 42 | Pending |
| ERRH-10 | Phase 42 | Pending |
| ERRH-11 | Phase 42 | Pending |
| ERRH-12 | Phase 42 | Pending |
| ERRH-13 | Phase 42 | Pending |
| ERRH-14 | Phase 42 | Pending |
| ERRH-15 | Phase 42 | Pending |
| ERRH-16 | Phase 42 | Pending |
| ERRH-17 | Phase 42 | Pending |
| ERRH-18 | Phase 42 | Pending |
| TEST-01 | Phase 43 | Pending |
| TEST-02 | Phase 43 | Pending |
| TEST-03 | Phase 43 | Pending |
| TEST-04 | Phase 43 | Pending |
| TEST-05 | Phase 43 | Pending |
| TEST-06 | Phase 43 | Pending |
| TEST-07 | Phase 43 | Pending |
| TEST-08 | Phase 43 | Pending |
| TEST-09 | Phase 43 | Pending |
| TEST-10 | Phase 43 | Pending |
| TEST-11 | Phase 43 | Pending |
| TEST-12 | Phase 43 | Pending |
| TEST-13 | Phase 43 | Pending |
| TEST-14 | Phase 43 | Pending |
| TEST-15 | Phase 43 | Pending |

**Backend Coverage:**
- Backend requirements: 67 total
- Mapped to phases: 67
- Unmapped: 0 ✓

## Future Requirements
- Responsive design (breakpoints, mobile) — deferred, desktop-only app
- Hover preview keyboard trigger — deferred, non-critical for demo
- Dark mode support — deferred
- Decimal для сумм вместо float — deferred, low risk for demo

## Out of Scope
- Frontend файлы (app/) — VioletRiver scope
- Новые фичи не из аудита — v1.1+
- WAL mode, aiosqlite, connection pool — не нужны для desktop app
- Retry logic в провайдерах — fallback chain уже есть
