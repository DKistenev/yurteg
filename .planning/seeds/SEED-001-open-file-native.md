---
id: SEED-001
status: dormant
planted: 2026-03-25
planted_during: v0.8.1 UI Polish
trigger_when: когда реализуется карточка документа с кнопкой «Открыть файл»
scope: Small
---

# SEED-001: Открытие файла в родном приложении (Word/Preview)

## Why This Matters

Юрист из карточки документа должен открыть оригинал прямо на компьютере — в Word для DOCX, в Preview для PDF. Без этого реестр = read-only каталог, а не рабочий инструмент. Кнопка «Открыть файл» уже в дизайне (DOC-03), но бэкенд для локального открытия нужен.

## When to Surface

**Trigger:** При реализации DOC-03 в v0.8.1 или в следующем milestone

This seed should be presented during `/gsd:new-milestone` when the milestone scope matches:
- Работа с карточкой документа
- Интеграция с десктопом / нативные возможности

## Scope Estimate

**Small** — несколько строк: `subprocess.call(['open', path])` на macOS, `os.startfile(path)` на Windows, `xdg-open` на Linux. Нужна обёртка с определением ОС и обработкой ошибки если файл удалён.

## Breadcrumbs

- `app/pages/document.py` — кнопка «Открыть файл» (сейчас вызывает download)
- `app/main.py` — route `/download/{doc_id}` (отдаёт файл через HTTP)
- `modules/database.py` — `get_contract_by_id()` возвращает `original_path`
- `modules/organizer.py` — копирует файлы, хранит путь

## Notes

Можно реализовать как часть DOC-03 в v0.8.1 — просто вместо `ui.download()` вызвать `subprocess` через `run.io_bound()`. Для NiceGUI native mode (pywebview) путь к файлу доступен напрямую.
