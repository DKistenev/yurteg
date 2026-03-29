# ЮрТэг

ЮрТэг — desktop-приложение на NiceGUI для AI-обработки юридических документов и связанных архивов.

## Установка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Или через conda:

```bash
conda create -n yurteg python=3.12 -y
conda activate yurteg
pip install -r requirements.txt
```

## Запуск

```bash
# Основное приложение
PYTHONPATH=. python app/main.py

# Telegram-бот
python -m bot_server.main
```

## Тесты

```bash
pytest
pytest -m "not slow"
```

## Что в репозитории

- `app/` — NiceGUI UI
- `modules/` — пайплайн обработки документов
- `services/` — бизнес-логика
- `providers/` — LLM-провайдеры
- `tests/` — pytest
- `.planning/` — project planning артефакты, они остаются tracked

## Совместная работа

- Не коммитим напрямую в `main`
- Работаем из коротких веток и мержим через PR
- Локальные agent/tool runtime-файлы, логи и временные скриншоты не должны попадать в git

Подробные правила:

- общий workflow для людей и AI-агентов: `AGENTS.md`
- Claude-specific заметки: `CLAUDE.md`
