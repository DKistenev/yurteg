---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Desktop Build
status: defining
stopped_at: —
last_updated: "2026-03-30T12:00:00Z"
last_activity: 2026-03-30 — Milestone v1.2 started
progress:
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-30)

**Core value:** Юрист загружает папку с документами и за 20 минут получает готовый реестр — без ручного ввода, без обучения
**Current focus:** v1.2 Desktop Build — подготовка к сборке DMG

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-30 — Milestone v1.2 started

Progress: [░░░░░░░░░░] 0%

## Accumulated Context

### Decisions

- v1.1 Bug Sweep завершён (PR #3, commit 1243a89)
- BetterStack Logtail выбран для удалённого логирования бета-тестов
- Автообновление: уровень 1 (баннер с ссылкой на GitHub Releases), уровень 2+ отложен
- runtime_paths.py для frozen-safe ресурсов уже частично реализован
- onedir вместо onefile (PyInstaller) — иначе +8-15 сек к каждому запуску
- Модели НЕ бандлим — GGUF + sentence-transformers скачиваются при первом запуске

### Notes Reference

6 заметок из ресёрча в .planning/notes/:
- desktop-build-plan — PyInstaller, CI/CD, установщики, подписание, Sentry
- pre-build-checklist — иконка, splash, offline, диск, EULA
- desktop-runtime-safety — логирование, single instance lock
- remote-logging-betterstack — BetterStack Logtail для бета-тестов
- telegram-bot-hosting — Beget VPS деплой
- build-research-findings — 16 технических находок

### Blockers/Concerns

- Нет (чистый старт)

### Pending Todos

- Нет

## Session Continuity

Last session: 2026-03-30
Stopped at: Milestone v1.2 initialized, defining requirements
Resume file: .planning/PROJECT.md
