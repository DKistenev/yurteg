---
phase: 09-document-detail-card
plan: 02
subsystem: ui
tags: [nicegui, fastapi, review_service, version_service, diff, redline]

requires:
  - phase: 09-01
    provides: document card header, metadata, status, lawyer notes, get_contract_by_id
  - phase: 02-document-lifecycle
    provides: review_service, version_service, generate_redline_docx, diff_versions

provides:
  - AI review section with auto template matching and deviation display (DOC-04)
  - Version history section with collapsible list, compare and redline download (DOC-05)
  - FastAPI /download/redline/{id}/{other_id} route serving .docx bytes

affects:
  - phase 10 (full-page layout)
  - phase 12 (design polish)

tech-stack:
  added: []
  patterns:
    - "ui.expansion for collapsible sections (Quasar QExpansionItem)"
    - "inline style hex colors for diff rendering — not dynamic Tailwind classes"
    - "FastAPI @app.get route for file downloads instead of ui.download"
    - "_dict_to_metadata helper converts contract dict to ContractMetadata"

key-files:
  created: []
  modified:
    - app/pages/document.py
    - app/main.py

key-decisions:
  - "Redline route uses ClientManager('Основной реестр') as default client — redline is always requested from document card context"
  - "subject field used as proxy text in generate_redline_docx — full text not stored in DB (existing decision from Phase 2)"
  - "Deviation rendering uses inline style hex colors, not dynamic Tailwind f-strings (Pitfall 4)"

requirements-completed: [DOC-04, DOC-05]

duration: <1min
completed: 2026-03-22
---

# Phase 9 Plan 02: AI Review and Version History Summary

**NiceGUI document card completed with AI review via match_template + review_against_template, collapsible version history with diff table, and FastAPI redline .docx download route.**

## Performance

- **Duration:** <1 min
- **Started:** 2026-03-22T08:40:52Z
- **Completed:** 2026-03-22T08:41:10Z
- **Tasks:** 1 auto + 1 checkpoint (auto-approved)
- **Files modified:** 2

## Accomplishments

- AI review section: кнопка «Проверить по шаблону» → автоподбор шаблона через match_template → список отступлений с цветовыми полосками; fallback dropdown если автоподбор не нашёл; сообщение с ссылкой если шаблонов нет совсем (DOC-04)
- Version history section: сворачиваемая секция «Версии» показывает список версий с номером, методом привязки и датой; кнопка «Сравнить» рендерит таблицу изменённых полей; ссылка «Скачать redline» → FastAPI route (DOC-05)
- FastAPI route `/download/redline/{contract_id}/{other_id}` — загружает оба контракта через run.io_bound, генерирует .docx с w:ins/w:del, отдаёт с правильным Content-Disposition

## Task Commits

1. **Task 1: AI review and version history sections + redline download route** - `ebb3e9f` (feat)
2. **Task 2: checkpoint auto-approved** - (no commit, visual verification)

## Files Created/Modified

- `app/pages/document.py` — добавлены helper-функции _dict_to_metadata, _render_deviations, _render_diff_table; реализованы секции Ревью и Версии внутри build()
- `app/main.py` — добавлен FastAPI route download_redline с импортом FastAPIResponse

## Decisions Made

- Redline route использует `ClientManager("Основной реестр")` как дефолтный клиент — redline всегда вызывается из контекста карточки документа
- `subject` используется как proxy-текст для generate_redline_docx (полного текста в БД нет, решение из Phase 2)
- Inline style для hex-цветов отступлений — не динамические Tailwind-классы (Pitfall 4 из RESEARCH)

## Deviations from Plan

None — план выполнен точно как написан.

## Issues Encountered

None.

## Known Stubs

None — все секции полностью реализованы и подключены к сервисному слою. Redline и diff используют subject как proxy-текст, но это задокументированное решение (STATE.md), не stub.

## Next Phase Readiness

- Карточка документа полностью реализована (все 6 требований DOC-01 — DOC-06)
- Phase 9 завершена, готово к Phase 10 (full-page layout, keyboard shortcuts, scroll restore)

---
*Phase: 09-document-detail-card*
*Completed: 2026-03-22*
