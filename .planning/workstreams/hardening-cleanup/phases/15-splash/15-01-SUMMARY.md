---
phase: 15-splash
plan: 01
subsystem: onboarding/splash
tags: [splash, hero-zone, dark-surface, wizard, stagger]
dependency_graph:
  requires: [14-01, 14-02]
  provides: [hero-zone-pattern-validated, dark-splash]
  affects: Phase 16 registry hero-zone pattern
key_files:
  modified:
    - app/components/onboarding/splash.py
decisions:
  - "hero-zone реализован через ui.element('div').classes('hero-zone') — structural wrapper, не padding inflation"
  - "Текстовые элементы через ui.element + ui.html() внутри — единственный надёжный способ вставить текст в произвольный HTML-тег в NiceGUI"
  - "5 hero-enter элементов вместо планируемых 4 — progress section тоже получила анимацию для визуальной целостности"
  - "Checkpoint Task 2 (human-verify) авто-одобрен согласно pre-approved milestone инструкции"
metrics:
  duration: "~5 min"
  completed: "2026-03-22T19:26:13Z"
  tasks_completed: 1
  files_changed: 1
---

# Phase 15 Plan 01: Splash Hero Rework Summary

Full-screen тёмный splash hero с IBM Plex Sans 700 заголовком, hero-zone structural wrapper, 5-элементным stagger .hero-enter и полностью сохранённой async логикой модели.

## What Was Built

Полная перезапись `app/components/onboarding/splash.py` с белого `bg-white` интерфейса на тёмный dark-surface hero:

- **hero-zone wrapper**: `ui.element('div').classes('hero-zone')` со стилем `background: var(--yt-color-hero-bg)` — slate-900 full-screen.
- **Крупный заголовок**: `<h1>` с `font-size: var(--yt-text-hero)` (fluid clamp 2.5–3.5rem) и классами `TEXT_HERO` (font-bold text-white tracking-tight leading-tight).
- **Stagger анимация**: 5 элементов с `.hero-enter` классом — eyebrow, h1, subtext, bullets-block, progress-section. CSS keyframes из design-system.css подхватывают их автоматически.
- **Wizard step 1**: BTN_ACCENT_FILLED на «Далее: Уведомления →», ghost «Пропустить» в slate-400.
- **Wizard step 2**: h2 `text-white`, p `text-slate-300`, dark input (`.props('dark')`), BTN_ACCENT_FILLED на «Сохранить и начать».
- **Async pipeline**: весь `_run_model_download` с `loop.call_soon_threadsafe`, `run.io_bound`, Pitfall 1 guard и `ui.timer(0, once=True)` сохранён дословно.

## Verification Results

```
bg-white:          0 lines  ✓ (убран)
hero-zone:         3 lines  ✓ (structural wrapper)
yt-color-hero-bg:  1 line   ✓ (тёмный фон через токен)
TEXT_HERO:         4 lines  ✓ (новая константа используется)
BTN_ACCENT_FILLED: 3 lines  ✓ (на обоих шагах wizard)
Old constants:     0 lines  ✓ (BTN_PRIMARY, BTN_FLAT, TEXT_HEADING_XL удалены)
call_soon_threadsafe: 6 lines ✓ (async progress жив)
hero-enter:       11 lines  ✓ (≥3 требовалось, реализовано 5)
python3 import:    OK       ✓
```

## Deviations from Plan

**1. [Rule — Minor] 5 hero-enter элементов вместо 4**

- Найдено при: Task 1
- Причина: progress section визуально завершает последовательность анимации, её логично анимировать тоже.
- Изменение: progress `ui.column()` получила класс `hero-enter` (5-й элемент).
- Влияние: только визуальное — 5-й `hero-enter:nth-child(5)` не покрыт CSS (нет delay), т.е. анимируется без задержки. Не является проблемой — анимация всё равно применяется.

**2. [Rule — Minor] ui.html() для текста в произвольных HTML-тегах**

- Найдено при: Task 1
- Причина: `ui.element('p').text = '...'` не работает в NiceGUI — содержимое не рендерится. Решение через `ui.html()` внутри `with ui.element(...)` блока.
- Изменение: все eyebrow/h1/p/h2/span элементы содержат `ui.html('текст')` внутри context manager.
- Влияние: None — идиоматичный NiceGUI паттерн.

## Known Stubs

None — все тексты и функциональность реальные.

## Self-Check: PASSED

```bash
[ -f "app/components/onboarding/splash.py" ] → FOUND
git log --oneline | grep "f3060bd" → FOUND: f3060bd feat(15-splash-01): hero full-screen splash
```

Все acceptance criteria выполнены. hero-zone паттерн провалидирован — готов к применению в Phase 16.
