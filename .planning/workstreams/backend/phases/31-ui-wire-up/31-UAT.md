---
status: complete
phase: 31-ui-wire-up
source: 31-01-SUMMARY.md, 31-02-SUMMARY.md
started: 2026-03-27T15:15:00Z
updated: 2026-03-27T15:20:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Закрыть приложение если запущено. Запустить `PYTHONPATH=. python app/main.py`. Приложение открывается без ошибок, реестр загружается.
result: pass

### 2. Открыть файл из карточки документа
expected: Открыть любой документ в реестре. В action bar кнопка «Открыть файл» (иконка open_in_new). subprocess.Popen(["open"]) на macOS.
result: pass

### 3. Сохранить как шаблон
expected: Открыть документ. Кнопка «Сохранить как шаблон» (bookmark). mark_contract_as_template() через run.io_bound(). Кнопка disable на время запроса.
result: pass

### 4. Виджет дедлайнов в реестре
expected: На странице реестра под строкой статистики — amber-блок с дедлайнами. Блок раскрывается/сворачивается по клику. Клик на строку алерта переходит на карточку документа.
result: pass

### 5. Bulk delete обновляет дедлайны
expected: Удалить документы через массовое действие. _delete_bulk вызывает _refresh_deadline_widget — удалённые документы пропадают из виджета.
result: pass

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
