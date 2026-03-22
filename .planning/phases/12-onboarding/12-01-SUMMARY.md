---
phase: 12-onboarding
plan: 01
subsystem: ui
tags: [nicegui, onboarding, splash, wizard, llama-server, tailwind]

requires:
  - phase: 11-settings-templates
    provides: load_settings/save_setting в config.py
  - phase: 04-server-provider
    provides: LlamaServerManager.ensure_model с on_progress callback

provides:
  - Splash screen full-page onboarding component (app/components/onboarding/splash.py)
  - Splash gate в app/main.py (early return при first_run_completed == false)
  - 2-шаговый wizard: приветствие + Telegram-токен

affects:
  - 12-02 (empty state + guided tour)

tech-stack:
  added: []
  patterns:
    - "Splash gate: load_settings() inside root(), early return перед header+sub_pages"
    - "Thread-safe progress: loop.call_soon_threadsafe для UI updates из thread pool"
    - "Wizard step transition: wizard_area.clear() + re-render (instant, no animation)"
    - "ui.timer(0, coro, once=True) для запуска async задачи сразу после рендера"

key-files:
  created:
    - app/components/onboarding/__init__.py
    - app/components/onboarding/splash.py
  modified:
    - app/main.py

key-decisions:
  - "render_splash() рендерится как full-page component, не ui.dialog — чистый layout без overlay"
  - "load_settings() вызывается внутри root(), не на уровне модуля — safe для NiceGUI per-connection"
  - "_start_llama в app.on_startup остаётся без изменений — ensure_model идемпотентен; двойной запуск безопасен"
  - "Пропустить доступен немедленно — не ждёт завершения загрузки модели (Pitfall 5 guard)"

patterns-established:
  - "Splash gate: if not settings.get('first_run_completed'): render_splash(); return"
  - "Progress wiring: on_progress(fraction, msg) через loop.call_soon_threadsafe(bar.set_value, fraction)"

requirements-completed: [ONBR-01, ONBR-03, ONBR-04]

duration: 2min
completed: 2026-03-22
---

# Phase 12 Plan 01: Splash Screen + Wizard Summary

**Full-page onboarding splash с прогресс-баром загрузки GGUF модели и 2-шаговым wizard (приветствие + Telegram) — splash gate в main.py делает early return при первом запуске**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-22T10:56:15Z
- **Completed:** 2026-03-22T10:58:07Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `render_splash()` с логотипом, приветствием, 3 capability bullets, прогресс-баром и wizard — все CSS-классы и копия из UI-SPEC
- Thread-safe обновление прогресс-бара через `loop.call_soon_threadsafe` — модель качается в thread pool без блокировки event loop
- Splash gate в `root()`: `load_settings()` → проверка `first_run_completed` → early return при false

## Task Commits

1. **Task 1: Splash screen + wizard component** — `9f03e9e` (feat)
2. **Task 2: Splash gate в main.py** — `6487097` (feat)

## Files Created/Modified

- `app/components/onboarding/__init__.py` — package init (пустой)
- `app/components/onboarding/splash.py` — render_splash(): логотип, bullets, прогресс, wizard step 1+2
- `app/main.py` — splash gate: load_settings() + early return в root()

## Decisions Made

- `load_settings()` вызывается внутри `root()`, не на уровне модуля — безопасно для per-connection NiceGUI
- `_start_llama` в `app.on_startup` не изменяется — `ensure_model` идемпотентен, двойной вызов безопасен
- Кнопка «Пропустить» работает немедленно, не ждёт загрузки модели (Pitfall 5 guard из плана)
- Splash рендерится как full-page component, не `ui.dialog` — чище layout, нет overlay

## Deviations from Plan

None — план выполнен точно по спецификации.

## Issues Encountered

None.

## Known Stubs

None — все элементы UI подключены к реальным данным (config.py, llama_server.py).

## Next Phase Readiness

- Splash screen готов; plan 12-02 может реализовывать empty state реестра и guided tour
- `first_run_completed` флаг устанавливается корректно — tour trigger в 12-02 будет проверять его наличие

---
*Phase: 12-onboarding*
*Completed: 2026-03-22*

## Self-Check: PASSED

- `app/components/onboarding/__init__.py` — FOUND
- `app/components/onboarding/splash.py` — FOUND
- `app/main.py` (modified) — FOUND
- commit `9f03e9e` — FOUND
- commit `6487097` — FOUND
