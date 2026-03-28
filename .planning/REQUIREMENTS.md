# Requirements — v1.0 Hackathon-Ready Frontend

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
| AUDIT-01 | — | Pending |
| AUDIT-02 | — | Pending |
| AUDIT-03 | — | Pending |
| AUDIT-04 | — | Pending |
| AUDIT-05 | — | Pending |
| AUDIT-06 | — | Pending |
| AUDIT-07 | — | Pending |
| XSCOPE-01 | — | Pending |
| XSCOPE-02 | — | Pending |
| XSCOPE-03 | — | Pending |
| ERRES-01 | — | Pending |
| ERRES-02 | — | Pending |
| REG-01 | — | Pending |
| REG-02 | — | Pending |
| REG-03 | — | Pending |
| DOC-01 | — | Pending |
| DOC-02 | — | Pending |
| TMPL-01 | — | Pending |
| SETT-01 | — | Pending |
| ONBR-01 | — | Pending |
| VIS-01 | — | Pending |

## Future Requirements
- Responsive design (breakpoints, mobile) — deferred, desktop-only app
- Hover preview keyboard trigger — deferred, non-critical for demo
- Dark mode support — deferred

## Out of Scope
- Backend audit fixes — CalmBridge scope
- config.py / services/ / modules/ changes — CalmBridge scope
- New features not in audit or UI Polish — v1.1+
