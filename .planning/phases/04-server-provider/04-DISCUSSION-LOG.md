# Phase 4: Сервер и провайдер - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-21
**Phase:** 04-server-provider
**Areas discussed:** Запуск сервера, Скачивание модели, GBNF грамматика, Конфиг по умолчанию

---

## Запуск сервера

| Option | Description | Selected |
|--------|-------------|----------|
| brew + автопроверка | Проверка наличия в PATH, просьба установить | |
| Скачать бинарник | Приложение само скачивает с GitHub releases | ✓ |
| llamafile | Сервер+модель в одном файле | |

**User's choice:** Скачивать автоматически с GitHub releases
**Notes:** Пользователь уточнил что в продакшене (DMG) llama-server будет встроен в пакет. Сейчас скачивание — временное решение для этапа разработки.

| Option | Description | Selected |
|--------|-------------|----------|
| С приложением | atexit handler при закрытии Streamlit | ✓ |
| Работает в фоне | Сервер остаётся после закрытия UI | |

**User's choice:** С приложением (atexit handler)

---

## Скачивание модели

| Option | Description | Selected |
|--------|-------------|----------|
| ~/.yurteg/ | В домашней папке пользователя | ✓ |
| Рядом с приложением | В подпапке models/ | |

**User's choice:** ~/.yurteg/

| Option | Description | Selected |
|--------|-------------|----------|
| Прогресс-бар | Streamlit progress bar с процентами | ✓ |
| Спиннер | Просто «Загрузка модели...» | |

**User's choice:** Прогресс-бар

---

## GBNF грамматика

| Option | Description | Selected |
|--------|-------------|----------|
| Кириллица + латиница | Оба алфавита + цифры | |
| Только кириллица | Строго кириллица | |
| JSON-схема | Только структура JSON | |
| JSON-схема + post-processing | GBNF для JSON + посимвольная чистка по полям | ✓ |

**User's choice:** JSON-схема GBNF + post-processing по полям с профилями допустимых символов
**Notes:** Пользователь уточнил что для части полей (contract_type, special_conditions) латиница недопустима, для части (counterparty, subject) — допустима. Нужна гибкая система профилей по полям. Enum-поля (payment_frequency, payment_direction) — строго допустимые значения.

---

## Конфиг по умолчанию

| Option | Description | Selected |
|--------|-------------|----------|
| Просто меняем | active_provider = 'ollama' в config.py | ✓ |
| Миграция | Спросить пользователя при первом запуске | |

**User's choice:** Просто меняем дефолт

---

## Claude's Discretion

- Конкретная реализация subprocess менеджера
- Порт llama-server
- Обработка конфликтов портов
- Конкретный синтаксис GBNF грамматики
- Стратегия retry

## Deferred Ideas

- DMG/EXE бандлинг — отдельная веха
- Автоматический fallback при низком качестве — v2+
