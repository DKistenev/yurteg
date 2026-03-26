# Phase 5: Пайплайн с локальной моделью - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-21
**Phase:** 05-pipeline-local-llm
**Areas discussed:** Пропуск анонимизации, UI-переключатель

---

## Пропуск анонимизации

| Option | Description | Selected |
|--------|-------------|----------|
| Полный пропуск | Не вызывать anonymize() вообще | ✓ |
| Только маскирование | NER работает, маски не применяются | |

**User's choice:** Полный пропуск

| Option | Description | Selected |
|--------|-------------|----------|
| По config | config.active_provider == "ollama" | ✓ |
| По провайдеру | provider.name == "ollama" | |

**User's choice:** По config

---

## UI-переключатель

| Option | Description | Selected |
|--------|-------------|----------|
| Sidebar внизу | Рядом с «Статус API + версия» | |
| В настройках | В expander «Настройки» | ✓ |

**User's choice:** В expander «Настройки» в sidebar

| Option | Description | Selected |
|--------|-------------|----------|
| Только сессию | Сбрасывается при перезапуске | |
| Сохраняется | Записывается в config файл | ✓ |

**User's choice:** Сохраняется в config

---

## Claude's Discretion

- Config persistence механизм
- AnonymizedText обёртка без вызова anonymize
- Размещение внутри expander
- Перезагрузка llama-server при обратном переключении

## Deferred Ideas

None
