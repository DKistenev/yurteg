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

## Cross-Scope Integration (блокеры фронтенда)
- [ ] **XSCOPE-04**: APP_VERSION константа в config.py (VioletRiver подхватит в footer)
- [ ] **XSCOPE-05**: STATUS_LABELS с 4-м элементом css_class в lifecycle_service.py
- [ ] **XSCOPE-06**: database.py get_contract_by_id/get_all_results всегда возвращают dict

## Thread Safety
- [ ] **TSAFE-01**: RLock вместо Lock в database.py (предотвращение deadlock при вложенных вызовах)
- [ ] **TSAFE-02**: Locks на все read-методы database.py (is_processed, get_all_results, get_stats)
- [ ] **TSAFE-03**: Атомарные операции в version_service.ensure_embedding (TOCTOU fix)
- [ ] **TSAFE-04**: Атомарные find_version_match + link_versions (единая транзакция)
- [ ] **TSAFE-05**: Lock в version_service.find_version_match вне цикла (не внутри)
- [ ] **TSAFE-06**: Process state race condition fix в llama_server.is_running()
- [ ] **TSAFE-07**: Атомарная запись settings.json (tempfile → os.replace)
- [ ] **TSAFE-08**: threading.Lock на save_setting read-modify-write цикл

## Data Integrity
- [ ] **DINT-01**: contract_number: поле в ContractMetadata + миграция v10 + save_result SQL
- [ ] **DINT-02**: Деанонимизация ВСЕХ строковых полей ContractMetadata, не только 4
- [ ] **DINT-03**: Флаг was_truncated при обрезке текста >30K — передача через pipeline
- [ ] **DINT-04**: Hardcoded дата 2026-01-01 в redline_service → datetime.now(UTC)
- [ ] **DINT-05**: Telegram sync: KeyError на item['id']/item['filename'] — валидация ключей
- [ ] **DINT-06**: Telegram sync: write → delete race — атомарность
- [ ] **DINT-07**: JSON corruption в settings.json — бэкап + логирование

## Config Hardening
- [ ] **CONF-01**: __post_init__() в Config — валидация: порт, воркеры, температура, токены, thresholds, file_size
- [ ] **CONF-02**: active_model property — учитывать active_provider, не хардкод "glm-4.7"
- [ ] **CONF-03**: telegram_chat_id: Optional[int] = None вместо int = 0
- [ ] **CONF-04**: validation_mode через Literal["off","selective","full"] с проверкой
- [ ] **CONF-05**: Bare except → except (json.JSONDecodeError, OSError) в load_settings
- [ ] **CONF-06**: Non-atomic write fix (tempfile + os.replace) — см. TSAFE-07
- [ ] **CONF-07**: settings.json chmod 0o600 на Unix

## Provider Cleanup
- [ ] **PROV-01**: timeout=httpx.Timeout(read=120) на всех провайдерах (120s для ollama, 60s для cloud)
- [ ] **PROV-02**: close() метод + context manager для HTTP-клиентов
- [ ] **PROV-03**: get_logprobs() default impl в LLMProvider base class (return {})
- [ ] **PROV-04**: API key validation — raise ValueError при пустом ключе (zai, openrouter)
- [ ] **PROV-05**: verify_key() — конкретные except (AuthenticationError, APIConnectionError)
- [ ] **PROV-06**: Response choices[0] bounds check перед доступом
- [ ] **PROV-07**: Defensive copy messages в openrouter._merge_system_into_user()
- [ ] **PROV-08**: ai_disable_thinking — добавить в Config или убрать из zai.py
- [ ] **PROV-09**: name property в реализациях вместо class attribute

## Error Handling & Validation
- [ ] **ERRH-01**: Bare except в extractor.py → except Exception
- [ ] **ERRH-02**: GBNF grammar loading fail-loud (raise FileNotFoundError, не None)
- [ ] **ERRH-03**: _split_sentences(None) guard в review_service
- [ ] **ERRH-04**: generate_redline_docx(None, None) guard в redline_service
- [ ] **ERRH-05**: Negative/zero amount validation в payment_service.unroll_payments
- [ ] **ERRH-06**: Invalid frequency validation в payment_service (typo → ValueError)
- [ ] **ERRH-07**: date_start > date_end validation в payment_service.save_payments
- [ ] **ERRH-08**: warning_days validation (>0) в lifecycle_service
- [ ] **ERRH-09**: counterparty=None guard в client_manager.find_client_by_counterparty
- [ ] **ERRH-10**: Row unpacking bounds check в review_service + lifecycle_service
- [ ] **ERRH-11**: _parse_date short string check в payment_service
- [ ] **ERRH-12**: JSON parse failure logging в version_service (не молча set())
- [ ] **ERRH-13**: BytesIO context manager в redline_service
- [ ] **ERRH-14**: Latin name regex — добавить дефисы (Mary-Jane) в anonymizer
- [ ] **ERRH-15**: import json → module-level в version_service
- [ ] **ERRH-16**: Удалить unused has_changes в redline_service
- [ ] **ERRH-17**: db._lock → публичный интерфейс или документация в review_service
- [ ] **ERRH-18**: O(n²) path collision → set() в client_manager

## Test Coverage
- [ ] **TEST-01**: Thread safety тесты для database.py save_result concurrent writes
- [ ] **TEST-02**: version_service get_embedding_model concurrent initialization
- [ ] **TEST-03**: payment_service edge cases (start>end, negative, zero, max_iter)
- [ ] **TEST-04**: Database migrations v2-v9 independent tests
- [ ] **TEST-05**: ai_extractor 8 helper functions (_translate_ru_months, _safe_float, etc.)
- [ ] **TEST-06**: ai_extractor extract_metadata error paths (truncation, empty, provider fail)
- [ ] **TEST-07**: payment_service save_payments all parameter combos
- [ ] **TEST-08**: version_service find_version_match error cases + boundaries
- [ ] **TEST-09**: lifecycle_service set_manual_status + clear_manual_status
- [ ] **TEST-10**: payment_service get_calendar_events filtering + formatting
- [ ] **TEST-11**: version_service diff_versions all field comparisons
- [ ] **TEST-12**: postprocessor _protect/_restore_abbreviations edge cases
- [ ] **TEST-13**: ai_extractor _normalize_date boundary cases (year range, malformed)
- [ ] **TEST-14**: lifecycle_service get_attention_required edge cases (empty, manual_status)
- [ ] **TEST-15**: conftest.py autouse fixture to reset version_service._model singleton

## Future Requirements
- Responsive design (breakpoints, mobile) — deferred, desktop-only app
- Hover preview keyboard trigger — deferred, non-critical for demo
- Dark mode support — deferred
- Decimal для сумм вместо float — deferred, low risk for demo

## Out of Scope
- Frontend файлы (app/) — VioletRiver scope
- Новые фичи не из аудита — v1.1+
- WAL mode для SQLite — не нужен для single-writer desktop app
- aiosqlite — добавляет сложности без пользы при текущей архитектуре
- Connection pool — SQLite не нуждается
- Retry logic в провайдерах — fallback chain уже есть
