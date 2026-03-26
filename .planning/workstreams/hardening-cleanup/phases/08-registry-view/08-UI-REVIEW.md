# Phase 08 — UI Review

**Audited:** 2026-03-22
**Baseline:** Abstract 6-pillar standards (no UI-SPEC for this phase)
**Screenshots:** Not captured (playwright not available; dev server detected on port 8080 but screenshot tool failed)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Russian-first, contextual CTAs throughout; two context-menu items expose placeholder message to users |
| 2. Visuals | 3/4 | Clear Linear/Notion aesthetic with good hierarchy; icon-only toggle buttons lack visible labels |
| 3. Color | 4/4 | Consistent indigo-600 accent, semantic status palette, Tailwind tokens used correctly |
| 4. Typography | 4/4 | 5 sizes used but scale is purposeful (xs/sm/base/lg/xl); 3 weights all semantically justified |
| 5. Spacing | 4/4 | Tailwind scale throughout, no arbitrary px/rem values, consistent spacing rhythm |
| 6. Experience Design | 3/4 | Loading progress bar present, empty state implemented, error recovery silent on failed fuzzy-search empty |

**Overall: 21/24**

---

## Top 3 Priority Fixes

1. **Placeholder notify for "Скачать оригинал" and "Переобработать"** — юрист кликает, ожидает действия, получает технический текст "Функция доступна в следующей версии" — замените на информативный текст с объяснением срока или просто скройте пункты меню до реализации в Phase 10. Файл: `app/pages/registry.py:274-276`.

2. **Нет empty-state при пустом поиске** — если поиск вернул 0 строк (не из-за пустой БД, а из-за фильтра), AG Grid показывает пустую таблицу с плавающими заголовками без пояснения. Добавьте overlay "Ничего не найдено. Попробуйте другой запрос" + кнопку сброса — это явно описано в CONTEXT.md D-specifics, но не реализовано. Файл: `app/pages/registry.py:_init()`.

3. **Кнопки переключения вида (≡ / ⊞) не имеют видимых текстовых меток** — только `title` атрибут (tooltip при hover). Пользователь без hover не понимает назначение иконок ≡ и ⊞. Добавьте короткий текст рядом с иконкой ("Список" / "Календарь") или aria-label для доступности. Файл: `app/pages/registry.py:125-128`.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

Сильные стороны:
- Поисковый placeholder "Поиск по реестру..." — контекстный и понятный.
- Сегменты "Все / Истекают ⚠ / Требуют внимания" — профессиональный юридический язык.
- Empty state "Загрузите первые документы" с буллетами "· Извлечёт метаданные / · Разложит по папкам / · Проверит сроки" — конкретный и ценностно-ориентированный.
- CTA "Выбрать папку" — точный глагол.
- Диалог удаления: "Это действие необратимо. Файл в исходной папке останется." — отличная copy, снимает тревогу пользователя.
- Статус-бейджи: "✔ Действует / ⚠ Скоро истекает / ✗ Истёк" — иконки усиливают смысл.

Проблемы:
- `app/pages/registry.py:274` — `ui.notify("Функция доступна в следующей версии", type="info")` при клике "Скачать оригинал". Технический placeholder-текст в производственном потоке юриста.
- `app/pages/registry.py:276` — то же для "Переобработать".
- `app/pages/registry.py:331` — диалог удаления реально показывает "Функция удаления доступна в следующей версии" после показа пугающего "Удалить документ?". Создаёт ложное ожидание и разочарование.

### Pillar 2: Visuals (3/4)

Сильные стороны:
- Структура header: лого слева → навигация по центру → действия справа — классический и понятный layout.
- Прогрессивные row-анимации (`animation-delay` для первых 9 строк) — полированная деталь.
- Page fade-in через `.nicegui-content` — плавный переход.
- Статус-бейджи с цветным фоном и иконкой — читаемы без текста.
- Actions hover opacity transition 150ms — соответствует дизайн-требованию "плавно, не скачком".
- Hover expand-icon с изменением цвета slate-400 → slate-600.
- Empty state с SVG иконкой папки, заголовком, описанием и CTA — полная визуальная иерархия.
- Иконка ⋯ (U+22EF) как indicator контекстного меню — нестандартный символ, не везде хорошо рендерится; рассмотрите `•••` или три точки `...`.

Проблемы:
- `app/pages/registry.py:125-128` — кнопки переключения вида ≡ и ⊞ (list/calendar toggle) имеют только `title` атрибут и непонятны без hover. Символ ⊞ нестандартный и неоднозначный.
- В навигации `app/components/header.py:41` — `⚙` (шестерёнка) как текстовый nav link без label рядом — не интуитивно для нового пользователя.
- Раскрытие версий (▶/▼) работает через клик на отдельный столбец шириной 40px — мелкая цель нажатия.

### Pillar 3: Color (4/4)

Акцентный цвет: indigo-600 (`#4f46e5`) используется точечно:
- Активный сегмент кнопок (`bg-indigo-600`)
- CTA кнопка "Выбрать папку" в empty state (`bg-indigo-600`)
- Кнопка "Добавить" в диалоге клиента (`color=primary`)
- Calendar tooltip ссылка "Открыть →"

Семантическая палитра статусов реализована через Tailwind @layer components:
- `status-active` → green-50/green-700
- `status-expiring` → yellow-50/yellow-700
- `status-expired` → red-50/red-700
- `status-unknown`, `status-terminated` → slate-100/slate-500 (нейтральный)
- `status-extended` → blue-50/blue-700
- `status-negotiation` → purple-50/purple-700
- `status-suspended` → orange-50/orange-700

Жёсткие hex-цвета только там, где необходимо (SVG stroke, FullCalendar event color, calendar tooltip inline styles) — оправданно. Нет dynamic Tailwind классов — литеральные строки используются правильно.

### Pillar 4: Typography (4/4)

Шрифт: IBM Plex Sans 400/600, загружается первым через preconnect — правильный приоритет.

Размеры в реестре (5 уровней — допустимо для сложного UI):
- `text-xs` — метка файла в прогрессе, FC типы событий
- `text-sm` — основной текст UI: кнопки, placeholder, hint-буллеты, nav links
- `text-base` — лого "ЮрТэг"
- `text-lg` — диалоговые заголовки
- `text-xl` — empty state heading "Загрузите первые документы"

Веса (3 уровня — все обоснованы):
- `font-normal` — body copy, подписи
- `font-medium` — сегментные кнопки, диалог клиента
- `font-semibold` — лого, delete dialog heading, empty state heading

AG Grid колонки не переопределяют шрифт — наследуют IBM Plex Sans через `* { font-family: ... }`.
Статус-бейджи используют `text-xs font-medium` — читаемо и аккуратно.

### Pillar 5: Spacing (4/4)

Последовательное использование Tailwind scale:
- Header: `px-6 py-0 h-12 gap-8` — фиксированная высота, чёткие отступы
- Search row: `px-6 pt-4 pb-2 gap-4` — стандартные шаги шкалы
- Сегменты: `gap-1 p-1` внутри пилюли, кнопки `px-4 py-1.5` — компактно и последовательно
- Empty state: `py-16 gap-4 mt-2 gap-1` — адекватные отступы для prominent state
- Диалоги: `gap-2 mt-4` — согласованы с остальным UI

Нет произвольных `[Npx]` или `[Nrem]` значений во всех аудируемых файлах.

Единственная нестандартность: `py-1.5` и `pb-0.5` в `_nav_link` — это корректные Tailwind значения (1.5 = 6px, 0.5 = 2px), не произвольные.

### Pillar 6: Experience Design (3/4)

Покрытие состояний:

| Состояние | Реализовано | Заметки |
|-----------|-------------|---------|
| Loading (пайплайн) | Да | `linear_progress` + file_label + count_label в `progress_section` |
| Empty (пустая БД) | Да | `_render_empty_state()` с CTA, скрывает grid |
| Empty (фильтр/поиск) | Нет | Grid показывает пустую таблицу без сообщения |
| Error (load_version_children) | Частично | `logger.warning` — пользователь не оповещается |
| Destructive confirm | Да | Диалог перед удалением |
| Disabled (processing) | Да | `state.processing` блокирует upload_btn |
| Success notify | Да | `ui.notify(type="positive")` после смены статуса |
| Placeholder actions | Плохо | notify с "следующей версии" — вводит в заблуждение |

Ключевая проблема: поиск, вернувший 0 строк (AG Grid с пустым rowData), не показывает никакого feedback — плавающие заголовки столбцов над пустотой. Это мешает понять: документы не найдены или данные не загрузились.

Положительно: debounce 300ms на поиске — правильный баланс отзывчивости и производительности. Lazy version loading избегает N+1 запросов. Confirmation dialog перед удалением. Tour onboarding после первой обработки.

---

## Files Audited

- `app/components/registry_table.py` — data layer, AG Grid component, COLUMN_DEFS, status renderer
- `app/pages/registry.py` — registry page build(), search/segments/actions/version UI
- `app/components/header.py` — persistent header, client dropdown, nav links
- `app/main.py` — CSS injection order, STATUS_CSS, ACTIONS_CSS, animation CSS, FullCalendar
- `.planning/phases/08-registry-view/08-CONTEXT.md` — design decisions
- `.planning/phases/08-registry-view/08-01-SUMMARY.md` through `08-03-SUMMARY.md` — implementation record
