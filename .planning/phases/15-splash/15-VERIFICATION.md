---
phase: 15-splash
verified: 2026-03-22T20:15:00Z
status: human_needed
score: 6/7 truths verified
human_verification:
  - test: "Визуальный осмотр splash screen"
    expected: "Весь экран тёмный slate-900, крупный белый bold заголовок, filled indigo кнопка «Далее: Уведомления →», ghost «Пропустить», прогресс-бар в тёмном стиле, переход на шаг 2 работает, из шага 2 — переход в реестр"
    why_human: "CSS-классы и inline-стили нельзя проверить без рендера WebKit. Тёмный фон, типографика и wizard-флоу требуют визуальной проверки в native-окне приложения"
---

# Phase 15: Splash Verification Report

**Phase Goal:** Первое впечатление = продукт, не wireframe. Валидация hero-zone structural wrapper паттерна перед registry
**Verified:** 2026-03-22T20:15:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Splash занимает весь экран с тёмным slate-900 фоном — белого bg-white нет | ✓ VERIFIED | `grep "bg-white" splash.py` → 0 строк; `background: var(--yt-color-hero-bg)` в inline style строка 37; токен `--yt-color-hero-bg: var(--yt-p-slate-900)` = #0f172a в tokens.css:37; `min-height: 100vh` на wrapper |
| 2 | Крупный заголовок IBM Plex Sans 700 text-4xl+ (TEXT_HERO) читается на тёмном фоне | ✓ VERIFIED | `TEXT_HERO = "font-bold text-white tracking-tight leading-tight"` в styles.py:56; `font-size: var(--yt-text-hero)` = clamp(2.5rem, 5vw, 3.5rem) на h1; IBM Plex Sans загружается глобально в main.py:91-96 |
| 3 | Hero-zone реализован как `ui.element('div').classes('hero-zone')` — structural wrapper, не padding inflation | ✓ VERIFIED | splash.py:36 — `ui.element('div').classes('hero-zone').style(...)` — явный wrapper; не padding на существующем column контейнере |
| 4 | Прогресс-бар модели (940 МБ GGUF) работает и обновляется через call_soon_threadsafe | ✓ VERIFIED | `call_soon_threadsafe` — 6 вхождений в splash.py; `run.io_bound` — 3 вхождения; `ensure_model`, `ensure_server_binary`, `start` сохранены; `ui.timer(0, _run_model_download, once=True)` на строке 188 |
| 5 | Wizard step 1 → step 2 переход работает без регрессий | ✓ VERIFIED | `_show_step_2()` сохранена (строки 98-130); `wizard_area.clear()` + rebuild паттерн; BTN_ACCENT_FILLED на «Далее: Уведомления →» (строка 139); `_finish()` и `_save_and_finish()` полностью сохранены |
| 6 | Шаг 2 (Telegram): сохранение токена и «Пропустить» функционируют | ✓ VERIFIED | `save_setting('bot_token', ...)` в строке 95; `save_setting('first_run_completed', True)` в строке 89; `ui.navigate.to('/')` в строке 90; `_on_save_click` с `btn.disable()/enable()` guard |
| 7 | (Stretch) Элементы hero появляются с stagger через .hero-enter CSS класс | ✓ VERIFIED | 11 вхождений `hero-enter` в splash.py — 5 элементов получили класс (eyebrow, h1, subtext, bullets-div, progress column); `@keyframes hero-slide-up` + `.hero-enter` + `:nth-child(1-4)` delays определены в design-system.css:182-194; CSS загружается в main.py:105 |

**Score:** 7/7 truths verified (автоматически)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/components/onboarding/splash.py` | Full-screen hero splash с 2-step wizard | ✓ VERIFIED | 188 строк (min_lines: 100 — выполнено); содержит `hero-zone`, `TEXT_HERO`, `BTN_ACCENT_FILLED`, `hero-enter`; python import OK |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `splash.py render_splash()` | `app/main.py root()` | early return gate | ✓ WIRED | main.py:148-151 — `if not app_settings.get("first_run_completed"): render_splash(); return` |
| `ui.element div hero-zone` | `design-system.css .hero-zone` | CSS class hook | ⚠️ PARTIAL | Класс `hero-zone` присутствует на div (splash.py:36), но CSS-правило `.hero-zone {}` не определено ни в design-system.css, ни в tokens.css. Визуальный эффект достигается через inline `.style(...)`. Класс работает как семантический маркер без CSS-backing — патерн задокументирован в ARCHITECTURE.md, но CSS-правило отсутствует |
| `BTN_ACCENT_FILLED` | `app/styles.py` | import | ✓ WIRED | splash.py:18 — `from app.styles import TEXT_HERO, TEXT_HERO_SUB, TEXT_EYEBROW, BTN_ACCENT_FILLED`; используется на строках 120, 139 |

**Замечание по hero-zone CSS:** PLAN ожидал ссылку `div.hero-zone → design-system.css .hero-zone`. CSS-правило отсутствует — layout задан inline. Это не мешает работе (стили применяются), но ломает обещанный «semantic CSS class hook» паттерн. ARCHITECTURE.md описывает `.hero-zone` как класс, который "owns its background, padding, and border" через CSS — на практике всё в inline style. Для Phase 16 это создаёт неконсистентность: следующая фаза может унаследовать паттерн без CSS-backing.

---

### Data-Flow Trace (Level 4)

*Не применимо* — splash.py не рендерит динамические данные из БД. Единственный динамический источник — прогресс модели, который обновляется через `call_soon_threadsafe` callback (проверен в Level 1-3).

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Python import без ошибок | `python3 -c "from app.components.onboarding.splash import render_splash; print('OK')"` | OK | ✓ PASS |
| hero-zone wrapper присутствует | `grep -c "hero-zone" splash.py` | 3 (включая комментарий и класс) | ✓ PASS |
| Белый фон отсутствует | `grep -c "bg-white" splash.py` | 0 | ✓ PASS |
| Старые константы удалены | `grep -c "TEXT_HEADING_XL\|BTN_PRIMARY\b\|BTN_FLAT\b" splash.py` | 0 | ✓ PASS |
| call_soon_threadsafe сохранён | `grep -c "call_soon_threadsafe" splash.py` | 6 | ✓ PASS |
| hero-enter stagger | `grep -c "hero-enter" splash.py` | 11 | ✓ PASS |
| Визуальный рендер в native-окне | Требует запуска приложения | — | ? SKIP — нужна ручная проверка |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SPLS-01 | 15-01-PLAN.md | Hero-секция на весь экран с крупной типографикой и визуальной уверенностью | ✓ SATISFIED | `min-height: 100vh`, `font-size: var(--yt-text-hero)` = clamp(2.5rem..3.5rem), TEXT_HERO = font-bold text-white |
| SPLS-02 | 15-01-PLAN.md | Dark accent surface для hero-зоны | ✓ SATISFIED | `background: var(--yt-color-hero-bg)` = #0f172a (slate-900) |
| SPLS-03 | 15-01-PLAN.md | Staggered entrance анимация элементов (stretch) | ✓ SATISFIED | 5 элементов с `.hero-enter`; keyframes и nth-child delays в design-system.css |

**Все 3 requirement ID из PLAN frontmatter покрыты.**

**Orphaned requirements:** В REQUIREMENTS.md трассировка: SPLS-01, SPLS-02, SPLS-03 → Phase 15, статус Complete. Других ID для Phase 15 не объявлено. Нет orphaned requirements.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/static/design-system.css` | — | Класс `.hero-zone` использован в splash.py, но CSS-правило не определено в CSS-файлах | ℹ️ Info | Layout работает через inline style — визуально корректно. Но паттерн "semantic CSS class hook" задокументирован в ARCHITECTURE.md как стандарт, а реализация его не соблюдает. Phase 16 унаследует паттерн без CSS-backing |

Нет placeholder/TODO/stub паттернов. Нет пустых return null. Нет хардкодированных пустых данных.

---

### Human Verification Required

#### 1. Визуальный осмотр splash screen

**Test:** Удалить или выставить `first_run_completed = false` в `~/.yurteg/settings.json`, запустить `python3 main.py`, дождаться открытия native-окна.

**Expected:**
- Весь экран тёмный (slate-900 #0f172a) — без белых областей
- Заголовок «Ваш архив договоров — под контролем» крупный, белый, bold — ощущается как продукт
- Eyebrow «ЮрТэг» мелкий uppercase, серый
- 3 capability bullet-а с indigo галочками на тёмном фоне
- Прогресс-бар стартует (0%) и заполняется, или сразу 100% если модель уже скачана
- Кнопка «Далее: Уведомления →» — filled indigo (не flat/ghost)
- «Пропустить» — ghost/text стиль, приглушённый slate-400
- Клик «Далее» → плавный переход на шаг 2 (Telegram) в том же тёмном фоне
- Шаг 2: h2 «Уведомления» белый, описание серое, input dark-styled
- «Пропустить» и «Сохранить и начать» работают → переход в реестр (/)
- Stagger-анимация: элементы появляются с задержкой 0/100/200/300ms

**Why human:** NiceGUI рендерит CSS в WebKit webview. Inline styles и Tailwind классы нельзя проверить без реального рендера. Цвет фона, типографика, wizard-флоу и stagger-анимация требуют визуального подтверждения.

---

### Gaps Summary

Автоматические проверки прошли полностью. Единственное замечание — отсутствие CSS-правила `.hero-zone {}` в design-system.css при использовании класса как semantic hook. Это не блокирует цель фазы (visual rework достигнут через inline style), но создаёт потенциальную несогласованность для Phase 16. Рекомендация: при создании Phase 16 добавить `.hero-zone { ... }` в design-system.css с background и min-height токенами.

Статус: **human_needed** — все автоматические проверки прошли, финальное подтверждение требует визуального осмотра в native-приложении.

---

_Verified: 2026-03-22T20:15:00Z_
_Verifier: Claude (gsd-verifier)_
