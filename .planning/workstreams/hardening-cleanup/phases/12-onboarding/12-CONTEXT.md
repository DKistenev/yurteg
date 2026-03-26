# Phase 12: Onboarding - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Первый контакт юриста с приложением: splash screen с прогрессом загрузки модели и setup wizard, empty state реестра при пустой базе, guided tour после первой обработки. Каждый элемент показывается один раз.

</domain>

<decisions>
## Implementation Decisions

### Splash screen
- **D-01:** Тон — дружелюбное приветствие (не холодный инструмент, не flashy стартап)
- **D-02:** Композиция: логотип ЮрТэг наверху → «Добро пожаловать!» → 3 пункта возможностей → прогресс-бар загрузки модели → wizard под прогрессом
- **D-03:** 3 пункта описания (ONBR-04): «Загрузите папку → получите реестр», «Автосортировка по папкам», «Контроль сроков и предупреждения»
- **D-04:** Прогресс-бар модели: «Загрузка модели (580/940 МБ)» с процентом
- **D-05:** Splash показывается ТОЛЬКО при первом запуске (флаг в `~/.yurteg/settings.json`)

### Setup wizard
- **D-06:** 2 шага, не больше:
  - Шаг 1: Приветствие + 3 пункта возможностей (совмещён с ONBR-04)
  - Шаг 2: Telegram — привязка бота для уведомлений
- **D-07:** Каждый шаг имеет кнопку «Пропустить» и «Далее»/«Готово»
- **D-08:** Wizard показывается ПОД прогресс-баром загрузки модели — юрист настраивает пока модель качается
- **D-09:** После завершения загрузки модели + wizard → splash закрывается → открывается реестр

### Empty state реестра
- **D-10:** Центрированный CTA + подсказки (не просто кнопка)
- **D-11:** Иконка папки 📁 → «Загрузите первые документы» → кнопка «Выбрать папку» → 3 подсказки: «Извлечёт метаданные», «Разложит по папкам», «Проверит сроки»
- **D-12:** Таблица реестра скрыта при пустой базе — вместо неё empty state
- **D-13:** После загрузки первых документов — empty state исчезает навсегда, показывается таблица

### Guided tour
- **D-14:** Запускается ПОСЛЕ первой обработки (когда данные есть в реестре, есть что показывать)
- **D-15:** 3 шага с подсветкой элементов:
  - Шаг 1: Реестр — «Это ваш реестр документов. Кликните на строку для подробностей»
  - Шаг 2: Фильтры — «Используйте фильтры для поиска. Истекающие документы выделены цветом»
  - Шаг 3: Загрузка — «Нажмите + Загрузить для обработки новых документов»
- **D-16:** Подсветка — затемнение фона + выделение целевого элемента (spotlight pattern)
- **D-17:** Каждый шаг — кнопка «Далее» и «Пропустить тур»
- **D-18:** Tour показывается один раз (отдельный флаг `tour_completed` в settings.json)

### Флаги первого запуска
- **D-19:** В `~/.yurteg/settings.json` три флага:
  - `first_run_completed: true` — splash + wizard пройдены
  - `tour_completed: true` — guided tour пройден
  - (проверяются при запуске и после первой обработки)

### Claude's Discretion
- Exact CSS для spotlight overlay (z-index, opacity, transition)
- Tooltip positioning для шагов тура
- Анимация перехода между шагами wizard
- Размер и отступы splash screen

</decisions>

<specifics>
## Specific Ideas

- Splash должен ощущаться как «мы рады что вы здесь» — не как «подождите загрузку»
- Wizard шаги — не модалки, а секции внутри splash screen. Smooth scroll или fade-transition
- Guided tour — как в Notion при первом использовании: лёгкий overlay, не блокирующий popup
- Empty state — спокойный, не агрессивный. Подсказки серым цветом, кнопка — акцентная
- Все тексты на русском, без англицизмов

</specifics>

<canonical_refs>
## Canonical References

### Phase artifacts
- `app/main.py` — on_startup hook (где проверять first_run флаг)
- `app/pages/registry.py` — где добавить empty state и tour trigger
- `app/components/header.py` — элементы для подсветки в туре
- `config.py` — `load_settings()` / `save_setting()` для флагов

### Design skills
- `/onboard` — first-run experience, empty states, guided tour patterns
- `/clarify` — wizard copy, CTA labels, tour step text

### Pitfalls
- `.planning/research/PITFALLS.md` §Pitfall 2 — run.io_bound для загрузки модели в splash
- `.planning/research/PITFALLS.md` §Pitfall 3 — llama-server lifecycle (splash запускает загрузку)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `config.load_settings()` / `config.save_setting()` — persistence для флагов first_run, tour_completed
- `app/components/process.py` — `pick_folder()` для кнопки в empty state (reuse)
- `_start_llama()` в `app/main.py` — текущая логика загрузки модели, нужно интегрировать с splash прогрессом
- `app/components/registry_table.py` — `load_table_data()` для проверки наличия данных (empty state trigger)

### Established Patterns
- `run.io_bound()` для блокирующих операций
- `ui.notify()` для toast-уведомлений
- `get_state()` для AppState
- `ui.navigate.to()` для SPA-навигации

### Integration Points
- `app/main.py` — splash screen рендерится ДО `ui.sub_pages` при `first_run_completed == false`
- `app/pages/registry.py` — empty state вместо таблицы при пустой базе; tour trigger после первой обработки
- `config.py` — два новых ключа в settings.json

</code_context>

<deferred>
## Deferred Ideas

- Видео-tutorial или help section — v2+
- Contextual tooltips при первом использовании каждой функции — v2+
- Кнопка «Повторить тур» в настройках — можно добавить, но не в scope ONBR requirements

</deferred>

---

*Phase: 12-onboarding*
*Context gathered: 2026-03-22*
