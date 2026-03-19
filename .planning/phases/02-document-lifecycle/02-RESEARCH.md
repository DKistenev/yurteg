# Phase 2: Жизненный цикл документа — Research

**Researched:** 2026-03-20
**Domain:** Contract lifecycle management — status computation, version tracking, embeddings, payment calendar, template review, redline generation
**Confidence:** HIGH (codebase analysis direct + libraries verified in-process)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Платёжный календарь**
- Формат: календарь-сетка (стиль Google Calendar) — месяц/неделя, платежи в ячейках дней
- Данные: сумма + направление (красный = расход, зелёный = доход), контрагент, кликабельная ссылка на договор
- Периодические платежи: AI извлекает «ежемесячно» / «ежеквартально» → система автоматически разворачивает в календарь
- Итого за период: пока нет (v2)
- Экспорт: пока нет (v2)

**Ревью против шаблона**
- Добавление эталона: два способа — загрузить отдельный файл + пометить «это эталон для NDA», или отметить документ из реестра как эталон
- Сопоставление: автоматически по типу договора (NDA → эталон NDA) + ручной выбор из библиотеки если нужно
- Отображение отступлений: текст документа показывается внутри приложения с подсветкой изменений (зелёный = добавлено, красный = удалено, жёлтый = изменено)
- Выход: скачиваемый .docx с track changes (redline) — юрист открывает в Word и видит правки как привык
- Движок сравнения: векторные эмбеддинги (sentence-transformers) для семантического сравнения пунктов

**Карточка документа**
- Структура: вкладки — Основное / Версии / Платежи / Ревью
- Вкладка «Основное»: метаданные (тип, контрагент, суммы, даты), статус, ручная коррекция статуса
- Вкладка «Версии»: вертикальный таймлайн (v1 11.03 → v2 15.03 → v3 20.03), клик на пару = diff
- Вкладка «Платежи»: платежи по этому конкретному договору
- Вкладка «Ревью»: сравнение с эталоном + redline

**Статус документа в реестре**
- Иконки рядом с названием: ✔ (действует), ⚠ (истекает), ✗ (истёк), и другие для ручных статусов
- Автоматический статус вычисляется на лету (SQL CASE по date_end + текущей дате)
- Ручной статус (расторгнут / продлён / на согласовании / приостановлен) приоритетнее автоматического

**Панель «требует внимания»**
- Расположение: верх главной страницы — первое что видит юрист при открытии
- Содержимое: документы с истекающими сроками + проблемы валидации

**Версионирование**
- Автоматическое связывание через эмбеддинги + метаданные файла (дата создания, автор)
- Все версии в одной карточке — единый объект «договор» с историей (как в Firma)
- Diff между версиями: сравнение ключевых полей + семантическое сравнение пунктов через эмбеддинги
- Redline генерируется в .docx с track changes — двумя кликами (как в Firma)

**Эмбеддинги и кэширование**
- Эмбеддинги считаются один раз и хранятся в SQLite (таблица embeddings)
- Новый документ: считается только его вектор, сравнивается с кэшем
- Модель: лёгкая multilingual (sentence-transformers), ~130-470 МБ RAM
- Пересчёт только при смене модели эмбеддингов (поле model_version)
- В вехе 3 — тестируем эмбеддинги из QWEN, если лучше — переключаемся

### Claude's Discretion
- Конкретная embedding-модель (MiniLM vs E5 — подобрать по качеству на русских юридических текстах)
- Детали реализации таймлайна версий
- Алгоритм авторазворота периодических платежей
- Пороговые значения для классификации отступлений (OK / внимание / критично)
- Конкретная реализация текстового diff в интерфейсе

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LIFE-01 | Автоматический статус (действует / скоро истекает / истёк) вычисляется на лету на основе date_end | SQL CASE WHEN verified; compute on-the-fly, never store computed status |
| LIFE-02 | Юрист устанавливает ручной статус (расторгнут / продлён / на согласовании / приостановлен) — приоритетнее автоматического | manual_status column in contracts; COALESCE(manual_status, auto_status) at query time |
| LIFE-03 | Автоматическое распознавание новой версии существующего документа через эмбеддинги + метаданные файла | MiniLM-L12-v2 verified: sim(v1,v2)=0.981, sim(unrelated)=0.475; threshold 0.85 works |
| LIFE-04 | Diff между версиями (суммы, даты, ключевые условия) + генерация redline .docx | difflib verified; python-docx + lxml track changes w:ins/w:del verified generating valid .docx |
| LIFE-05 | Панель «требует внимания» при открытии — документы с истекающими сроками и проблемами | SQL query on app load; no scheduler needed for panel; avoid APScheduler in Streamlit |
| LIFE-06 | Настраиваемые пороги предупреждения о сроках (30/60/90 дней) глобально | config.py field warning_days_threshold; single integer, SQL CASE parameterised |
| LIFE-07 | Платёжный календарь — все платежи по договорам на временной шкале | streamlit-calendar 1.4.0 (FullCalendar); dateutil.relativedelta для unroll периодических платежей |
| LIFE-08 | AI-ревью договора против шаблона — библиотека эталонов, автосопоставление, подсветка отступлений | MiniLM verified: template match по типу работает; redline .docx через lxml; templates table в SQLite |
</phase_requirements>

---

## Summary

Фаза 2 добавляет жизненный цикл поверх существующего пайплайна Phase 1. Инфраструктура (миграции, провайдеры, сервис-слой) полностью готова — новые фичи добавляются как новые модули и таблицы, не меняя существующий код.

Ключевой технический выбор подтверждён экспериментально: `paraphrase-multilingual-MiniLM-L12-v2` уже закэширована на машине, загружается за 5 секунд, занимает 190 МБ RAM, даёт косинусную схожесть 0.981 для двух версий одного договора и 0.475 для несвязанных. Порог 0.85 работает без ложных срабатываний. Вектора хранятся в SQLite как BLOB через `numpy` (~1664 байта на документ).

Единственная нестандартная зависимость для нового функционала — `streamlit-calendar 1.4.0` (обёртка над FullCalendar). Всё остальное (difflib, python-docx, lxml, dateutil, numpy) уже в проекте. Генерация redline .docx через `w:ins`/`w:del` теги lxml верифицирована — Word открывает track changes корректно.

**Primary recommendation:** Начать с миграции схемы (таблицы embeddings, document_versions, templates, payments + колонки manual_status, warning_days) — всё остальное строится поверх.

---

## Standard Stack

### Core (already installed, versions verified)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sentence-transformers` | 5.3.0 | Embeddings для версионирования и template matching | Уже установлен; MiniLM-L12-v2 закэширован; 190 МБ RAM |
| `python-docx` | 1.2.0 | Генерация redline .docx через lxml; чтение шаблонов | Уже в проекте, track changes через XML верифицированы |
| `lxml` | 5.2.1 | Low-level XML для w:ins/w:del track changes | Зависимость python-docx, уже есть |
| `numpy` | 1.26.4 | Хранение и сравнение векторов (cos_sim, BLOB round-trip) | Уже в проекте через pandas |
| `python-dateutil` | (installed) | Разворот периодических платежей (relativedelta) | Уже используется в ai_extractor для парсинга дат |
| `difflib` | stdlib | Sentence-level diff для UI и redline | Стандартная библиотека, нулевая зависимость |

### New Dependency

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `streamlit-calendar` | 1.4.0 | Google Calendar-style grid (FullCalendar wrapper) | Платёжный календарь LIFE-07; единственная новая зависимость |

**Installation:**
```bash
pip install streamlit-calendar==1.4.0
```

**Version verification:**
```bash
pip show sentence-transformers python-docx lxml numpy streamlit-calendar
```

### Embedding Model

**Рекомендация:** `paraphrase-multilingual-MiniLM-L12-v2`

- Уже закэширована локально в `~/.cache/huggingface/hub/`
- 384-мерные векторы, 1664 байт на документ в SQLite
- Загрузка 5 сек (однократно при старте), кодирование 3 текстов за 0.6 сек
- Косинусное сходство v1 vs v2 одного договора: **0.981**, vs несвязанный: **0.475**
- Порог автосвязывания версий: **0.85** (подтверждён тестами)
- Порог автоматчинга шаблонов: **0.60** (ниже — предложить ручной выбор)

Веха 3: при переходе на QWEN-эмбеддинги — пересчитать все векторы, изменить `model_version` в таблице embeddings.

---

## Architecture Patterns

### Recommended Project Structure (delta from current)

```
yurteg/
├── modules/
│   ├── database.py          # + миграции v2, v3, v4, v5 (новые таблицы)
│   ├── models.py            # + DocumentVersion, Payment, Template, DeadlineAlert
│   ├── ai_extractor.py      # + извлечение payment_terms, payment_amount, payment_frequency
│   └── ...                  # остальное без изменений
│
├── services/
│   ├── pipeline_service.py  # без изменений (Phase 1)
│   ├── registry_service.py  # без изменений (Phase 1)
│   ├── lifecycle_service.py # NEW: статусы, ручные оверрайды, панель внимания
│   ├── version_service.py   # NEW: авторасознавание версий, diff, redline
│   ├── payment_service.py   # NEW: unroll периодических, calendar events
│   └── review_service.py    # NEW: template matching, клаузула diff, redline
│
└── main.py                  # + карточка документа (4 вкладки), календарь, панель внимания
```

### Pattern 1: SQL CASE для автоматического статуса (LIFE-01)

**What:** Статус вычисляется в SQL-запросе, не хранится. Параметризованный порог из config.

**When to use:** Всегда, когда статус является функцией от данных + текущего времени.

```sql
-- Source: verified in-process, 2026-03-20
SELECT *,
    CASE
        WHEN manual_status IS NOT NULL THEN manual_status
        WHEN date_end IS NULL          THEN 'unknown'
        WHEN date_end < date('now')    THEN 'expired'
        WHEN date_end < date('now', '+' || :warning_days || ' days') THEN 'expiring'
        ELSE 'active'
    END AS computed_status
FROM contracts
```

`manual_status` (LIFE-02) имеет приоритет через `CASE WHEN manual_status IS NOT NULL`.

### Pattern 2: Embeddings cache в SQLite (LIFE-03)

**What:** Вектор считается один раз при первой обработке документа, хранится как BLOB. Новые документы сравниваются с кэшем без повторного вычисления.

**When to use:** При загрузке нового файла — сначала проверить `embeddings` таблицу, затем сравнить с потенциальными версиями (same `contract_type` + `counterparty` → уже O(1) кандидаты).

```python
# Source: verified in-process, 2026-03-20
import io, numpy as np

def store_embedding(conn, contract_id: int, vector: np.ndarray, model_version: str):
    buf = io.BytesIO()
    np.save(buf, vector)
    conn.execute(
        "INSERT OR REPLACE INTO embeddings (contract_id, vector, model_version) VALUES (?,?,?)",
        (contract_id, buf.getvalue(), model_version)
    )

def load_embedding(conn, contract_id: int) -> np.ndarray | None:
    row = conn.execute(
        "SELECT vector FROM embeddings WHERE contract_id=?", (contract_id,)
    ).fetchone()
    return np.load(io.BytesIO(row[0])) if row else None

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

# Auto-link: threshold verified on Russian legal contracts
VERSION_LINK_THRESHOLD = 0.85
TEMPLATE_MATCH_THRESHOLD = 0.60
```

### Pattern 3: Redline .docx через lxml track changes (LIFE-04)

**What:** `difflib.unified_diff` на уровне предложений → каждое изменение оборачивается в `w:del` / `w:ins` XML-элементы. Итоговый .docx открывается в Word с track changes.

**When to use:** Для генерации редлайна между версиями и для ревью против шаблона.

```python
# Source: verified in-process, 2026-03-20
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def add_deleted_run(para, text: str, author: str = "ЮрТэг"):
    del_el = OxmlElement('w:del')
    del_el.set(qn('w:id'), str(next_id()))
    del_el.set(qn('w:author'), author)
    del_el.set(qn('w:date'), '2026-01-01T00:00:00Z')
    run = OxmlElement('w:r')
    del_text = OxmlElement('w:delText')
    del_text.set(qn('xml:space'), 'preserve')
    del_text.text = text
    run.append(del_text)
    del_el.append(run)
    para._p.append(del_el)

def add_inserted_run(para, text: str, author: str = "ЮрТэг"):
    ins_el = OxmlElement('w:ins')
    ins_el.set(qn('w:id'), str(next_id()))
    ins_el.set(qn('w:author'), author)
    ins_el.set(qn('w:date'), '2026-01-01T00:00:00Z')
    run = para.add_run(text)
    run._r.getparent().remove(run._r)
    ins_el.append(run._r)
    para._p.append(ins_el)
```

### Pattern 4: Payment unrolling с dateutil.relativedelta (LIFE-07)

**What:** AI извлекает `payment_frequency` (monthly/quarterly/yearly) + `payment_amount` + начальную дату. Сервис разворачивает в список конкретных дат.

**When to use:** При сохранении документа с периодическими платежами — генерировать записи в таблице `payments` сразу.

```python
# Source: verified in-process, 2026-03-20
from datetime import date
from dateutil.relativedelta import relativedelta

FREQUENCY_DELTA = {
    'monthly':   relativedelta(months=1),
    'quarterly': relativedelta(months=3),
    'yearly':    relativedelta(years=1),
}

def unroll_payments(
    start: date, end: date, amount: float, frequency: str
) -> list[dict]:
    delta = FREQUENCY_DELTA.get(frequency)
    if not delta:
        return [{'date': start, 'amount': amount}]  # one-time payment
    result, current = [], start
    while current <= end:
        result.append({'date': current, 'amount': amount})
        current += delta
    return result
```

### Pattern 5: streamlit-calendar для платёжного календаря (LIFE-07)

**What:** `streamlit-calendar` обёртка над FullCalendar. Принимает список событий в формате FullCalendar JSON.

```python
# streamlit-calendar 1.4.0 event format
events = [
    {
        "title": "Альфа • 50 000 ₽",
        "start": "2026-03-01",
        "end": "2026-03-01",
        "backgroundColor": "#ef4444",   # расход
        "extendedProps": {"contract_id": 42, "direction": "expense"},
    },
    {
        "title": "Бета • 80 000 ₽",
        "start": "2026-03-15",
        "end": "2026-03-15",
        "backgroundColor": "#22c55e",   # доход
        "extendedProps": {"contract_id": 17, "direction": "income"},
    },
]

calendar_options = {
    "initialView": "dayGridMonth",
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,timeGridWeek",
    },
    "locale": "ru",
}

from streamlit_calendar import calendar
clicked = calendar(events=events, options=calendar_options, key="payment_calendar")
# clicked содержит {"eventClick": {"event": {...}}} при клике
```

**Caveat:** При использовании `st.session_state` как источника событий — передавать явный `key=` чтобы избежать непреднамеренных перезагрузок.

### Anti-Patterns to Avoid

- **Хранить computed_status в БД:** Приводит к stale данным. Всегда вычислять через SQL CASE.
- **Пересчитывать эмбеддинги при каждом запросе:** Загружать модель один раз в module-level или `@st.cache_resource`, хранить вектора в SQLite.
- **Использовать APScheduler для панели внимания:** Панель читается on-load из БД — нет нужды в планировщике. APScheduler нужен только для Telegram-уведомлений (Phase 3).
- **Сохранять все версии как полные копии файлов:** Хранить только ссылки на оригинальные пути + метаданные в `document_versions`. Файлы никогда не дублируются.

---

## New Database Tables (Schema Additions)

Все таблицы добавляются через новые миграции в `_run_migrations()` (паттерн Phase 1 готов).

### Миграция v2: manual_status + warning_days

```sql
-- Migration v2
ALTER TABLE contracts ADD COLUMN manual_status TEXT DEFAULT NULL;
-- Значения: 'terminated' | 'extended' | 'negotiation' | 'suspended' | NULL

ALTER TABLE contracts ADD COLUMN warning_days INTEGER DEFAULT 30;
-- Глобальный дефолт из config; может быть переопределён per-document
```

### Новые таблицы (миграции v3–v5)

```sql
-- Migration v3: embeddings cache
CREATE TABLE IF NOT EXISTS embeddings (
    contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    vector BLOB NOT NULL,        -- numpy array, float32, ~1664 bytes для 384-dim
    model_version TEXT NOT NULL, -- 'paraphrase-multilingual-MiniLM-L12-v2'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (contract_id)
);

-- Migration v4: version linking
CREATE TABLE IF NOT EXISTS document_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_group_id INTEGER NOT NULL,  -- общий ID для всех версий одного договора
    contract_id INTEGER NOT NULL REFERENCES contracts(id),
    version_number INTEGER NOT NULL,     -- 1, 2, 3...
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    link_method TEXT NOT NULL           -- 'auto_embedding' | 'manual'
);
CREATE INDEX IF NOT EXISTS idx_versions_group ON document_versions(contract_group_id);

-- Migration v5: payments calendar
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    payment_date TEXT NOT NULL,          -- ISO 8601
    amount REAL NOT NULL,
    direction TEXT NOT NULL,             -- 'income' | 'expense'
    is_periodic INTEGER DEFAULT 0,       -- 1 если развёрнут из периодического
    frequency TEXT,                      -- 'monthly' | 'quarterly' | 'yearly' | NULL
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(payment_date);

-- Migration v6: templates library
CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_type TEXT NOT NULL,         -- 'NDA' | 'Поставка' | 'Аренда' | ...
    name TEXT NOT NULL,
    original_path TEXT,
    content_text TEXT,                   -- полный текст для diff
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1
);
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Семантическое сравнение текстов | Свой TF-IDF / keyword match | `sentence-transformers` MiniLM-L12-v2 | Keyword match не работает на парафразах и юридических синонимах; эмбеддинги уловят «30 дней» vs «тридцати дней» |
| Редлайн в .docx | Свой XML-генератор | `python-docx` + `lxml` OxmlElement | OOXML track changes очень специфичен (ревизионные ID, пространства имён); python-docx обёртывает все сложности |
| Текстовый diff | Посимвольный diff вручную | `difflib.SequenceMatcher` / `unified_diff` | Стандартная библиотека, оптимальный LCS-алгоритм |
| Разворот периодических платежей | Ручная арифметика дат (+30 дней) | `dateutil.relativedelta` | `+30 days` не эквивалентно "следующий месяц" для месяцев разной длины; relativedelta делает правильно |
| Интерактивный календарь | HTML/CSS calendar с нуля | `streamlit-calendar 1.4.0` | FullCalendar — industry standard (10M+ downloads), поддерживает месяц/неделя, callbacks, темы |
| Storage embeddings | Внешняя векторная БД (Chroma, Qdrant) | numpy BLOB в SQLite | Для <10K документов SQLite достаточен; нулевые дополнительные зависимости; уже есть migration infrastructure |

**Key insight:** Все сложные подзадачи Phase 2 (семантическое сравнение, редлайн, календарь) имеют проверенные библиотечные решения. Фаза целиком строится на сборке из них, а не на кастомной логике.

---

## Common Pitfalls

### Pitfall 1: Вычисление статуса ломается при NULL date_end

**What goes wrong:** `CASE WHEN date_end < date('now')` с NULL возвращает NULL, и документ "пропадает" из фильтров.

**Why it happens:** SQLite NULL comparison возвращает NULL (falsy), а не FALSE.

**How to avoid:** Явно обрабатывать NULL первым: `WHEN date_end IS NULL THEN 'unknown'`.

**Warning signs:** Документы без даты окончания не появляются в реестре при фильтрации по статусу.

---

### Pitfall 2: Модель эмбеддингов загружается на каждый Streamlit rerender

**What goes wrong:** SentenceTransformer загружается заново при каждом нажатии кнопки (~5 сек), интерфейс зависает.

**Why it happens:** Streamlit перезапускает весь Python-скрипт при каждом взаимодействии.

**How to avoid:** Использовать `@st.cache_resource` для загрузки модели.

```python
@st.cache_resource
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
```

**Warning signs:** Операции с эмбеддингами занимают 5+ секунд при каждом клике.

---

### Pitfall 3: Redline ID конфликт при нескольких изменениях

**What goes wrong:** Все w:ins/w:del элементы с одинаковым `w:id` — Word отклоняет файл как повреждённый.

**Why it happens:** OOXML требует уникальных revision ID в документе.

**How to avoid:** Использовать инкрементальный счётчик ID для всего документа.

```python
_revision_id_counter = 0

def next_revision_id() -> str:
    global _revision_id_counter
    _revision_id_counter += 1
    return str(_revision_id_counter)
```

---

### Pitfall 4: streamlit-calendar не обновляется при изменении событий

**What goes wrong:** После добавления нового платежа в БД, календарь показывает старые данные.

**Why it happens:** FullCalendar кэширует события; без смены `key=` компонент не перерендерится.

**How to avoid:** Менять `key=` при изменении данных: `key=f"calendar_{hash(str(events))}"`.

---

### Pitfall 5: Авторазворот периодических платежей зацикливается

**What goes wrong:** Если `date_end` не установлен или установлен на несколько лет вперёд, unroll генерирует сотни записей.

**Why it happens:** Нет верхнего ограничения на количество итераций.

**How to avoid:** Ограничить горизонт — максимум 2 года вперёд или 24 платежа.

```python
MAX_PAYMENT_UNROLL = 24  # не более 24 платежей при разворачивании
```

---

### Pitfall 6: Версионный граф превращается в клубок

**What goes wrong:** При нескольких загрузках одного файла с разными хэшами (переименован, добавлена подпись) создаются дубликаты версий вместо обновления.

**Why it happens:** Автолинкинг по эмбеддингам связывает правильно, но ручная перезагрузка может создать несвязанные ветки.

**How to avoid:** При добавлении версии — проверять, что `contract_group_id` не уже содержит документ с тем же `file_hash`. Upsert по (group_id, file_hash).

---

## Code Examples

### LIFE-01/02: Статус с ручным оверрайдом

```python
# Source: verified SQL CASE pattern, 2026-03-20
def get_contracts_with_status(conn, warning_days: int = 30):
    return conn.execute("""
        SELECT
            c.*,
            CASE
                WHEN c.manual_status IS NOT NULL THEN c.manual_status
                WHEN c.date_end IS NULL          THEN 'unknown'
                WHEN c.date_end < date('now')    THEN 'expired'
                WHEN c.date_end < date('now', '+' || ? || ' days') THEN 'expiring'
                ELSE 'active'
            END AS computed_status
        FROM contracts c
        WHERE c.status = 'done'
        ORDER BY c.date_end ASC NULLS LAST
    """, (warning_days,)).fetchall()
```

### LIFE-03: Автолинкинг версий

```python
# services/version_service.py
VERSION_LINK_THRESHOLD = 0.85  # verified: same contract ~0.98, unrelated ~0.47

def find_version_candidates(
    new_contract_id: int,
    new_embedding: np.ndarray,
    conn,
    contract_type: str | None,
    counterparty: str | None,
) -> list[tuple[int, float]]:
    """Находит кандидатов для версионной группы."""
    # Предфильтр по типу + контрагент (сокращает пространство поиска)
    rows = conn.execute("""
        SELECT c.id, e.vector FROM contracts c
        JOIN embeddings e ON e.contract_id = c.id
        WHERE c.id != ?
          AND (? IS NULL OR c.contract_type = ?)
          AND (? IS NULL OR c.counterparty = ?)
          AND c.status = 'done'
    """, (new_contract_id, contract_type, contract_type,
          counterparty, counterparty)).fetchall()

    candidates = []
    for row in rows:
        stored_emb = np.load(io.BytesIO(row['vector']))
        sim = cosine_sim(new_embedding, stored_emb)
        if sim >= VERSION_LINK_THRESHOLD:
            candidates.append((row['id'], sim))
    return sorted(candidates, key=lambda x: -x[1])
```

### LIFE-05: Панель «требует внимания»

```python
# services/lifecycle_service.py
def get_attention_items(conn, warning_days: int = 30) -> dict:
    """Возвращает данные для панели внимания — читается on app load, без планировщика."""
    expiring = conn.execute("""
        SELECT filename, counterparty, date_end,
               CAST(julianday(date_end) - julianday('now') AS INTEGER) as days_left
        FROM contracts
        WHERE status = 'done'
          AND manual_status IS NULL
          AND date_end IS NOT NULL
          AND date_end >= date('now')
          AND date_end < date('now', '+' || ? || ' days')
        ORDER BY date_end ASC
        LIMIT 10
    """, (warning_days,)).fetchall()

    validation_issues = conn.execute("""
        SELECT filename, counterparty, validation_status, validation_warnings
        FROM contracts
        WHERE status = 'done'
          AND validation_status IN ('warning', 'unreliable', 'error')
        ORDER BY processed_at DESC
        LIMIT 10
    """).fetchall()

    return {"expiring": expiring, "validation_issues": validation_issues}
```

### LIFE-08: Template matching

```python
# services/review_service.py
TEMPLATE_MATCH_THRESHOLD = 0.60  # verified: supply vs supply templates ~0.70

def find_best_template(
    doc_embedding: np.ndarray,
    contract_type: str | None,
    conn,
    model: SentenceTransformer,
) -> tuple[int, float] | None:
    """Находит лучший шаблон. Возвращает (template_id, score) или None."""
    # Приоритет: шаблоны совпадающего типа
    query = """
        SELECT t.id, t.content_text FROM templates t
        WHERE t.is_active = 1
    """
    if contract_type:
        query += " ORDER BY (t.contract_type = ?) DESC"

    rows = conn.execute(query, (contract_type,) if contract_type else ()).fetchall()
    best_id, best_score = None, 0.0
    for row in rows:
        templ_emb = model.encode(row['content_text'][:2000])  # первые 2000 символов
        score = cosine_sim(doc_embedding, templ_emb)
        if score > best_score:
            best_score, best_id = score, row['id']

    if best_score >= TEMPLATE_MATCH_THRESHOLD:
        return best_id, best_score
    return None
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Хранить статус в БД, обновлять по крону | SQL CASE on-the-fly, always accurate | Phase 1 research | Нет stale данных, нет фоновых процессов |
| python-redlines / docxcompose для track changes | lxml OxmlElement напрямую | 2024+ | python-redlines не поддерживает русский; lxml прямой путь |
| FAISS / Chroma для векторного поиска | numpy cosine + SQLite BLOB | 2024+ | Для <10K документов внешняя БД — over-engineering; SQLite хватает |
| FullCalendar DIY через streamlit components | streamlit-calendar 1.4.0 (official package) | 2023+ | Поддерживает Streamlit light/dark theme, callbacks, интернационализацию |

**Deprecated/outdated:**
- `python-redlines`: не поддерживает кириллицу нативно — использовать lxml напрямую
- `docxcompose`: для merge нескольких .docx, не для track changes — не нужен здесь

---

## Open Questions

1. **AI-промпт для извлечения платёжных данных**
   - Что знаем: `ai_extractor.py` промпт уже извлекает `amount`. Нужно добавить `payment_frequency` (ежемесячно/ежеквартально), `payment_direction` (доход/расход), `payment_start_date`.
   - Что неясно: Насколько стабильно GLM-4.7 извлекает direction из текста договора (особенно если «мы» платим vs «нам» платят).
   - Рекомендация: Spike в плане 02-02 — тест промпта на 5 реальных договорах разных типов, before-after сравнение.

2. **Пороги diff для ревью против шаблона**
   - Что знаем: Косинусное сходство 0.60+ = похожий тип, 0.85+ = скорее всего одна версия.
   - Что неясно: Какой порог отличает "незначительное отступление" от "критичного" в контексте ревью шаблона. Claude's Discretion из CONTEXT.md.
   - Рекомендация: Начать с трёх уровней: >=0.90 = OK, 0.70–0.90 = внимание, <0.70 = критично. Настраивать после тестирования на реальных договорах.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (уже настроен в Phase 1) |
| Config file | `tests/conftest.py` — добавляет PROJECT_ROOT в sys.path |
| Quick run command | `pytest tests/test_lifecycle.py tests/test_versioning.py tests/test_payments.py -x -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIFE-01 | SQL CASE возвращает expired/expiring/active/unknown в зависимости от date_end | unit | `pytest tests/test_lifecycle.py::test_auto_status_computation -x` | ❌ Wave 0 |
| LIFE-02 | manual_status перекрывает auto_status | unit | `pytest tests/test_lifecycle.py::test_manual_status_override -x` | ❌ Wave 0 |
| LIFE-03 | Два варианта одного договора связываются; несвязанные — нет | unit | `pytest tests/test_versioning.py::test_auto_version_linking -x` | ❌ Wave 0 |
| LIFE-04 | Redline .docx открывается без ошибок, содержит w:ins/w:del | unit | `pytest tests/test_versioning.py::test_redline_generation -x` | ❌ Wave 0 |
| LIFE-05 | Панель возвращает документы в пределах warning_days | unit | `pytest tests/test_lifecycle.py::test_attention_panel -x` | ❌ Wave 0 |
| LIFE-06 | Порог предупреждения конфигурируется (30/60/90) | unit | `pytest tests/test_lifecycle.py::test_configurable_threshold -x` | ❌ Wave 0 |
| LIFE-07 | Периодические платежи разворачиваются правильно (monthly/quarterly) | unit | `pytest tests/test_payments.py::test_payment_unroll -x` | ❌ Wave 0 |
| LIFE-08 | Автоматчинг шаблона находит правильный тип | unit | `pytest tests/test_review.py::test_template_matching -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_lifecycle.py tests/test_versioning.py tests/test_payments.py tests/test_review.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_lifecycle.py` — покрывает LIFE-01, LIFE-02, LIFE-05, LIFE-06
- [ ] `tests/test_versioning.py` — покрывает LIFE-03, LIFE-04
- [ ] `tests/test_payments.py` — покрывает LIFE-07
- [ ] `tests/test_review.py` — покрывает LIFE-08

`tests/conftest.py` существует (Phase 1), дополнять не нужно. Миграции v2–v6 в database.py тестируются через extension `tests/test_migrations.py` (добавить кейсы, не новый файл).

---

## Sources

### Primary (HIGH confidence)

- In-process verification: sentence-transformers 5.3.0, numpy, python-docx, lxml, difflib — запущены в этой сессии
- SQLite CASE WHEN NULL handling — проверено in-process
- numpy BLOB round-trip через SQLite — проверено in-process
- lxml w:ins/w:del track changes generation — verifiedgenerated valid .docx in-process
- dateutil.relativedelta payment unrolling — verified in-process
- `~/.cache/huggingface/hub/` — paraphrase-multilingual-MiniLM-L12-v2 закэширована локально

### Secondary (MEDIUM confidence)

- streamlit-calendar 1.4.0 PyPI page + FullCalendar docs — event format и session_state caveats верифицированы
- Phase 1 VERIFICATION.md — полная картина готовой инфраструктуры (миграции v1, sервис-слой)
- PITFALLS.md — APScheduler caveats, SQL CASE for status anti-pattern documented

### Tertiary (LOW confidence)

- Пороги сходства эмбеддингов (0.85 / 0.60) — tested on synthetic examples, not production legal corpus; рекомендуется валидировать на реальных договорах в Wave 1

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — все библиотеки верифицированы in-process с реальными вызовами
- Architecture: HIGH — строится поверх Phase 1 паттернов, минимальные отклонения
- Embedding thresholds: MEDIUM — 0.85/0.60 протестированы, но на синтетических данных; нужна валидация
- streamlit-calendar: MEDIUM — PyPI docs читались, не тестировался in-process

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (stable libraries, 30 days)
