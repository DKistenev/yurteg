# ЮрТэг — Claude-specific notes

Сначала читай `AGENTS.md`: там канонический workflow, правила веток, GitHub-процесс и координация с другими агентами.

Этот файл держит только детали, полезные именно для Claude Code и GSD-инструментов.

## Claude / GSD

- GSD-артефакты в `.planning/` считаются частью проекта и могут быть tracked.
- Локальный runtime Claude не должен попадать в git: особенно `.claude/worktrees/` и `settings.local.json`.
- Если Claude работает через субагентов, общие repo-правила из `AGENTS.md` всё равно обязательны.

## Tooling caveats

- MCP серверы не всегда наследуются субагентами GSD автоматически.
- Для инъекции skill-путей в GSD использовать `agent_skills` в `.planning/config.json`, а не хардкодить это по месту.
- Если `agent-mcp` недоступен, это нужно явно зафиксировать в рабочем сообщении или PR, а не молча обходить.

## UI / NiceGUI reminders

- Quasar props вроде `flat`, `outline`, `unelevated` могут перебивать Tailwind.
- `.nicegui-content` часто требует `align-items: stretch`, иначе дети сжимаются.
- `AG Grid` лучше настраивать через `autoSizeStrategy`, а не таймером через `sizeColumnsToFit()`.
- Для русских дат не полагаться на `strftime("%d %b")`.

## Claude-local helpers

- UI-тестовый раннер: `.claude/skills/webapp-testing/scripts/with_server.py`
- Полезный NiceGUI справочник: `.claude/skills/nicegui-layout-debugging/SKILL.md`
