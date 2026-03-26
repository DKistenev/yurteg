---
phase: 09-document-detail-card
verified: 2026-03-22T09:00:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
---

# Phase 9: Document Detail Card — Verification Report

**Phase Goal:** Карточка документа содержит всю информацию и действия — юрист может просмотреть метаданные, запустить AI-ревью, посмотреть версии и оставить заметку, не возвращаясь в реестр
**Verified:** 2026-03-22T09:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Юрист видит карточку документа с метаданными при клике по строке реестра | ✓ VERIFIED | `async def build(doc_id)` в `app/pages/document.py:113`, `_render_metadata` рендерит 7 полей через `ui.grid(columns=2)` |
| 2 | Кнопка «Назад к реестру» возвращает на главную страницу | ✓ VERIFIED | `ui.navigate.to("/")` в `document.py:152` — кнопка «← Назад к реестру» в заголовке |
| 3 | Prev/next переключают документы без возврата в реестр | ✓ VERIFIED | `state.filtered_doc_ids` читается в `document.py:160`, кнопки ◀/▶ делают `navigate.to(f"/document/{pid}")` с захватом дефолт-аргументов |
| 4 | Заметка юриста автосохраняется при blur | ✓ VERIFIED | `comment_area.on("blur", _save_comment)` в `document.py:266`; `_save_comment` вызывает `db.update_review` с `file_hash` |
| 5 | Статус документа отображается с бейджем и может быть изменён вручную | ✓ VERIFIED | `STATUS_LABELS` CSS-бейдж + `set_manual_status`/`clear_manual_status` через `run.io_bound` |
| 6 | Юрист нажимает «Проверить по шаблону» и видит список отступлений с цветовыми метками | ✓ VERIFIED | `_run_review()` → `match_template` → `review_against_template` → `_render_deviations` с inline hex-цветами |
| 7 | Если нет шаблонов — сообщение с ссылкой на раздел Шаблоны | ✓ VERIFIED | `document.py:285-291`: `ui.label('Нет шаблонов.')` + `ui.link('Добавьте в разделе Шаблоны', '/templates')` |
| 8 | Секция «Версии» сворачиваема, показывает список версий с номером и датой | ✓ VERIFIED | `ui.expansion('Версии', icon='history', value=False)` в `document.py:328`; версии рендерятся с `v{v.version_number}` и `v.created_at` |
| 9 | Кнопка «Скачать redline» скачивает .docx через FastAPI route | ✓ VERIFIED | `ui.link('Скачать redline', f'/download/redline/{doc_id}/{v.contract_id}')` + FastAPI route `download_redline` в `app/main.py:127` |

**Score:** 9/9 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `modules/database.py` | `get_contract_by_id` method | ✓ VERIFIED | Строка 329: `def get_contract_by_id(self, contract_id: int) -> dict | None` с JSON-десериализацией `special_conditions`, `parties`, `validation_warnings` |
| `app/state.py` | `filtered_doc_ids` field in AppState | ✓ VERIFIED | Строка 37: `filtered_doc_ids: list = field(default_factory=list)` |
| `app/components/registry_table.py` | Syncs `filtered_doc_ids` on data load | ✓ VERIFIED | Строки 375-376: `state.filtered_doc_ids = [r['id'] for r in rows if not r.get('is_child')]` |
| `app/pages/document.py` | Full document card page | ✓ VERIFIED | 364 строки (min 120); содержит header, metadata grid, status, notes, AI review, version history |
| `app/main.py` | FastAPI route for redline download | ✓ VERIFIED | `@app.get('/download/redline/{contract_id}/{other_id}')` с `FastAPIResponse` |
| `tests/test_document_card.py` | Tests for data layer | ✓ VERIFIED | 66 строк (min 40); 3 теста: `test_get_contract_by_id`, `test_get_contract_by_id_none`, `test_prevnext_logic` — все проходят |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/pages/document.py` | `modules/database.py` | `run.io_bound(db.get_contract_by_id, int(doc_id))` | ✓ WIRED | Строка 128 — вызов через run.io_bound |
| `app/pages/document.py` | `services/lifecycle_service.py` | `set_manual_status` / `clear_manual_status` | ✓ WIRED | Строки 205, 235 — оба через `run.io_bound` |
| `app/components/registry_table.py` | `app/state.py` | `state.filtered_doc_ids = [r['id'] for r in rows]` | ✓ WIRED | Строки 375-376 — синхронизируется при каждой загрузке данных |
| `app/pages/document.py` | `services/review_service.py` | `run.io_bound(match_template, ...)` + `run.io_bound(review_against_template, ...)` | ✓ WIRED | Строки 279, 320 |
| `app/pages/document.py` | `services/version_service.py` | `run.io_bound(get_version_group, ...)` + `run.io_bound(diff_versions, ...)` | ✓ WIRED | Строки 332, 355 |
| `app/main.py` | `services/version_service.py` | FastAPI route calling `generate_redline_docx` | ✓ WIRED | Строка 141: `await run.io_bound(_gen_redline, text_old, text_new, title)` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DOC-01 | 09-01-PLAN | Full-page карточка документа с кнопкой «← Назад к реестру» | ✓ SATISFIED | `build()` рендерит полностраничную карточку; кнопка «← Назад к реестру» в header |
| DOC-02 | 09-01-PLAN | Метаданные документа отображаются в CSS grid-layout | ✓ SATISFIED | `ui.grid(columns=2)` с 7 полями + особые условия списком |
| DOC-03 | 09-01-PLAN | Навигация «Предыдущий / Следующий» без возврата в реестр | ✓ SATISFIED | ◀/▶ кнопки, disabled на краях, navigate через URL |
| DOC-04 | 09-02-PLAN | AI-ревью по шаблону (кнопка в карточке) | ✓ SATISFIED | `ui.expansion('Ревью')` + кнопка «Проверить по шаблону» + автоподбор + fallback dropdown + no-templates сообщение |
| DOC-05 | 09-02-PLAN | История версий в сворачиваемой секции | ✓ SATISFIED | `ui.expansion('Версии', value=False)` + список версий + «Сравнить» + «Скачать redline» |
| DOC-06 | 09-01-PLAN | Пометки юриста (ручные заметки к документу) | ✓ SATISFIED | `ui.textarea` с `on('blur', _save_comment)` → `db.update_review(file_hash, ...)` |

Все 6 требований (DOC-01 — DOC-06) заявлены в планах и подтверждены в коде. Orphaned requirements отсутствуют — REQUIREMENTS.md назначает DOC-01..06 на Phase 9 и все они покрыты.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | — |

Подозрительные `return null`/`return []` и TODO-комментарии не обнаружены. Placeholder-комментарии Plan 01 (`# ── AI Review section (Plan 02) ──`) заменены реальной реализацией в Plan 02. Единственный pre-existing провал теста — `test_ollama_stub` требует запущенного Ollama-сервера (сетевая зависимость, вне скоупа фазы).

---

### Human Verification Required

#### 1. Визуальная проверка карточки документа

**Test:** Запустить `python app/main.py`, открыть реестр, кликнуть по любой строке документа.
**Expected:** Открывается полностраничная карточка с заголовком (← Назад, тип документа, ◀ ▶), 2-column grid метаданных, статус-бейдж, textarea для заметок, секции «Ревью» и «Версии».
**Why human:** Визуальный layout, стили CSS и UX-поведение нельзя верифицировать автоматически.

#### 2. Автосохранение заметки

**Test:** Ввести текст в поле «Пометки юриста», кликнуть за его пределами, перезагрузить страницу.
**Expected:** Текст сохранился и отображается при повторном открытии карточки.
**Why human:** Требует browser interaction для триггера blur-события.

#### 3. AI-ревью при наличии шаблонов

**Test:** При наличии хотя бы одного шаблона в базе — нажать «Проверить по шаблону».
**Expected:** Появляется spinner, затем список отступлений с цветными полосками (зелёные/красные/жёлтые).
**Why human:** Требует реальных шаблонов в БД и проверки визуального рендеринга отступлений.

---

## Gaps Summary

Gaps отсутствуют. Все 9 observable truths верифицированы. Все 6 артефактов существуют, содержательны и подключены. Все 6 ключевых связей (key links) активны. Все требования DOC-01..DOC-06 покрыты. Тест-сьют: 246 passed, 1 pre-existing failure (Ollama network — вне скоупа).

---

_Verified: 2026-03-22T09:00:00Z_
_Verifier: Claude (gsd-verifier)_
