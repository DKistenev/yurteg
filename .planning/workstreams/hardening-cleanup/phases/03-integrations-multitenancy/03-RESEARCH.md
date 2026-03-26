# Phase 3: Интеграции и мультидоступ — Research

**Researched:** 2026-03-20
**Domain:** Telegram Bot API, APScheduler, multi-client SQLite, webhook server
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Telegram-бот — архитектура**
- Единый бот @YurTagBot на сервере (webhook), не отдельный бот на каждого юриста
- Бот как «почтовый ящик»: принимает файл → сохраняет в очередь на сервере → приложение юриста забирает файлы при запуске и обрабатывает локально
- Данные остаются локальными — сервер хранит только очередь файлов и минимальные метаданные для уведомлений
- Доступ: привязка по chat_id, один владелец на аккаунт (v1)

**Telegram-бот — онбординг**
- Привязка через /start: юрист пишет /start боту → бот выдаёт одноразовый код → юрист вводит код в приложении → привязка готова
- Не нужно искать chat_id вручную, не нужно создавать бота в BotFather

**Telegram-бот — ответы**
- После обработки файла бот отправляет краткую карточку: «✅ Договор аренды с ООО Рога, 150 000 ₽, до 31.12.2026»

**Уведомления о сроках — Telegram**
- Сервер бота проверяет сроки по cron и отправляет уведомления
- Расписание настраивается юристом: ежедневный дайджест / при наступлении порога / оба / выключить
- Данные на сервере для проверки сроков: date_end, название документа, контрагент, статус. Никаких текстов, никаких сумм

**Уведомления внутри приложения**
- st.toast при запуске: «⚠️ 3 документа истекают на этой неделе»

**Мультиклиентский режим**
- Опциональный, отдельная БД на клиента (client_roga.db, client_kopyta.db)
- Переключение: selectbox в сайдбаре
- Создание: кнопка «Новый клиент» → ввод названия
- Автопривязка по контрагенту

### Claude's Discretion
- Конкретный стек серверной части бота (python-telegram-bot vs aiogram, FastAPI vs Flask)
- Формат очереди файлов на сервере (SQLite vs Redis vs файловая система)
- Протокол sync метаданных (REST API vs простые HTTP-запросы)
- Реализация одноразовых кодов привязки
- Fuzzy matching названий клиентов при автопривязке
- Схема хранения настроек уведомлений

### Deferred Ideas (OUT OF SCOPE)
- **Google Drive автообработка (INTG-03)** — отложена в v2
- **PROF-02: Совместный доступ нескольких юристов** — отложено в v2
- **Яндекс.Диск (INTG-07)** — v2
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INTG-01 | Telegram-бот принимает документы (PDF/DOCX) — кинул файл в чат, через минуту он в реестре | python-telegram-bot webhook + file_queue таблица на сервере + REST API синхронизации в приложении |
| INTG-02 | Telegram-бот отправляет уведомления о приближающихся сроках | APScheduler CronTrigger на сервере + таблица deadline_sync с метаданными + bot.send_message() |
| INTG-03 | Google Drive — DEFERRED | Не реализуется в этой фазе |
| INTG-04 | Уведомления внутри приложения при запуске | st.toast() в main.py + вызов get_attention_required() из lifecycle_service (уже готов) |
| PROF-01 | Один юрист ведёт несколько клиентов — изолированные реестры | Отдельный .db файл на клиента, ClientManager класс, selectbox в сайдбаре |
| PROF-02 | Совместный доступ нескольких юристов — DEFERRED | Не реализуется в этой фазе |
</phase_requirements>

---

## Summary

Фаза состоит из двух независимых частей: **(A) Telegram-интеграция** (INTG-01, INTG-02) и **(B) Мультиклиентский режим** (PROF-01). Обе части не зависят друг от друга и могут реализовываться параллельно в рамках разных задач.

**Часть A — Telegram** требует серверный компонент (отдельный Python-процесс с ботом), который живёт на хостинге (Railway/Fly.io), принимает файлы через webhook, хранит их в очереди, и уведомляет о сроках по cron. Локальное приложение при запуске обращается к серверу по REST API и забирает файлы из очереди. Выбранный стек: **python-telegram-bot 22.x** (наиболее зрелая и документированная библиотека для Python) + **FastAPI** (асинхронный, идеально подходит для webhook-сервера) + **APScheduler 3.x** (BackgroundScheduler для cron на том же процессе сервера).

**Часть B — Мультиклиент** реализуется полностью в локальном приложении: `ClientManager` класс, который управляет набором `*.db` файлов, и обновлённый `main.py` с selectbox клиентов. Нет сервера, нет сложной синхронизации.

**Primary recommendation:** python-telegram-bot 22.7 + FastAPI 0.135 + APScheduler 3.11 + SQLite для очереди на сервере; rapidfuzz 3.14 для fuzzy-матчинга клиентов.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-telegram-bot | 22.7 | Telegram Bot API — приём файлов, отправка сообщений, webhook | Самая зрелая Python-библиотека для Telegram, встроенный webhook через Application.run_webhook(), активно поддерживается |
| FastAPI | 0.135.1 | HTTP-сервер для webhook и REST API синхронизации | Асинхронный, автодокументация OpenAPI, минимум кода для эндпоинтов |
| uvicorn | 0.42.0 | ASGI-сервер для запуска FastAPI | Стандарт для FastAPI в продакшене |
| APScheduler | 3.11.2 | Cron-задача проверки сроков на сервере | BackgroundScheduler работает в том же процессе без лишних зависимостей, CronTrigger для дайджестов |
| rapidfuzz | 3.14.3 | Fuzzy matching названий клиентов (ООО «Рога» vs ООО "Рога") | Быстрее thefuzz в 10-100x, нет зависимости от python-Levenshtein, активно поддерживается |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | 0.28.1 | HTTP-клиент для синхронизации локального приложения с сервером | Уже в транзитивных зависимостях, async-поддержка |
| python-dotenv | 1.0.0 | Env-переменные для TELEGRAM_BOT_TOKEN, SERVER_URL | Уже в requirements.txt |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| python-telegram-bot | aiogram 3.x | aiogram полностью async, но требует async-рефакторинга всего кода; python-telegram-bot v20+ тоже async, проще интеграция |
| FastAPI | Flask 3.1 | Flask проще, но синхронный — блокирует при получении файлов; FastAPI нативно async |
| APScheduler | celery + redis | Celery избыточен для одного cron-задания без очереди задач |
| rapidfuzz | thefuzz | thefuzz медленнее, rapidfuzz — drop-in replacement с тем же API |
| SQLite очередь | Redis | Redis требует отдельный сервис; SQLite достаточен для MVP, легко бэкапить |

**Installation (серверная часть):**
```bash
pip install "python-telegram-bot>=22.7" "fastapi>=0.135" "uvicorn>=0.42" "apscheduler>=3.11" "httpx>=0.28"
```

**Installation (локальная часть):**
```bash
pip install "rapidfuzz>=3.14" "httpx>=0.28"
```

---

## Architecture Patterns

### Структура серверного компонента
```
bot_server/
├── main.py              # FastAPI app + lifespan (запуск бота и планировщика)
├── bot.py               # python-telegram-bot Application, handlers
├── scheduler.py         # APScheduler setup, cron-задача проверки сроков
├── database.py          # SQLite: file_queue, bindings, deadline_sync, notification_settings
├── config.py            # BOT_TOKEN, SERVER_URL, DB_PATH из env
└── requirements.txt     # отдельный от основного приложения
```

### Структура изменений в локальном приложении
```
yurteg/
├── services/
│   ├── client_manager.py      # НОВЫЙ: управление клиентами (db per client)
│   ├── telegram_sync.py       # НОВЫЙ: синхронизация с сервером (fetch queue, push deadlines)
│   └── ...existing services
├── modules/
│   └── database.py            # ИЗМЕНЕНИЕ: миграции v6 (clients, telegram_bindings, notification_settings)
├── config.py                  # ИЗМЕНЕНИЕ: telegram_server_url, client_mode поля
└── main.py                    # ИЗМЕНЕНИЕ: selectbox клиентов, TG-привязка, st.toast
```

### Pattern 1: Webhook-сервер с python-telegram-bot + FastAPI

**What:** python-telegram-bot Application запускается внутри FastAPI lifespan, webhook регистрируется при старте.

**When to use:** Единственный правильный подход для production-бота — polling не подходит для хостинга без постоянного соединения.

**Example:**
```python
# bot_server/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application
import uvicorn

app_bot: Application = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global app_bot
    app_bot = Application.builder().token(BOT_TOKEN).build()
    app_bot.add_handler(...)
    await app_bot.initialize()
    await app_bot.bot.set_webhook(url=f"{SERVER_URL}/telegram/webhook")
    await app_bot.start()
    yield
    # Shutdown
    await app_bot.stop()
    await app_bot.shutdown()

app = FastAPI(lifespan=lifespan)

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, app_bot.bot)
    await app_bot.process_update(update)
    return {"ok": True}
```

### Pattern 2: Приём файла ботом → сохранение в очередь

**What:** Handler перехватывает Document, скачивает файл через Telegram API, сохраняет в локальную папку на сервере, добавляет запись в таблицу `file_queue`.

**Example:**
```python
# bot_server/bot.py
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    chat_id = update.effective_chat.id

    # Проверяем привязку
    binding = db.get_binding(chat_id)
    if not binding:
        await update.message.reply_text("Сначала привяжите аккаунт — введите /start")
        return

    # Скачиваем файл
    file = await context.bot.get_file(doc.file_id)
    dest = QUEUE_DIR / f"{chat_id}_{doc.file_unique_id}_{doc.file_name}"
    await file.download_to_drive(dest)

    # Добавляем в очередь
    db.enqueue_file(
        chat_id=chat_id,
        file_path=str(dest),
        filename=doc.file_name,
        mime_type=doc.mime_type,
    )
    await update.message.reply_text("📥 Получил! Обработаю при следующем запуске приложения.")
```

### Pattern 3: Одноразовый код привязки

**What:** /start генерирует 6-значный код, хранится в `pending_bindings` таблице с TTL 15 минут. Локальное приложение отправляет код на сервер → сервер возвращает chat_id → приложение сохраняет chat_id + server_url в своём config.

**Example:**
```python
# bot_server/bot.py
import secrets, string

async def handle_start(update: Update, context):
    chat_id = update.effective_chat.id
    code = ''.join(secrets.choice(string.digits) for _ in range(6))
    db.save_pending_binding(chat_id=chat_id, code=code, ttl_minutes=15)
    await update.message.reply_text(
        f"Ваш код привязки: *{code}*\n\nВведите его в приложении ЮрТэг → Настройки → Telegram.\nКод действует 15 минут.",
        parse_mode="Markdown"
    )

# bot_server/main.py REST endpoint
@app.post("/api/bind")
async def bind_account(code: str):
    binding = db.consume_pending_binding(code)  # удаляет запись
    if not binding:
        raise HTTPException(status_code=404, detail="Код не найден или истёк")
    db.save_binding(chat_id=binding.chat_id)
    return {"chat_id": binding.chat_id, "ok": True}
```

### Pattern 4: APScheduler для дайджеста сроков

**What:** BackgroundScheduler в том же процессе, CronTrigger на 09:00 каждый день. Задача берёт все записи из `deadline_sync`, фильтрует по порогу пользователя, отправляет сообщение.

**Example:**
```python
# bot_server/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

async def send_deadline_digest():
    for binding in db.get_all_bindings():
        settings = db.get_notification_settings(binding.chat_id)
        if not settings.digest_enabled:
            continue
        alerts = db.get_alerts_for_user(
            chat_id=binding.chat_id,
            warning_days=settings.warning_days
        )
        if alerts:
            text = format_digest(alerts)
            await bot.send_message(chat_id=binding.chat_id, text=text)

# Запуск в lifespan
scheduler.add_job(send_deadline_digest, CronTrigger(hour=9, minute=0))
scheduler.start()
```

### Pattern 5: Мультиклиентский режим — ClientManager

**What:** ClientManager хранит список клиентов в `clients.json` (или отдельной meta.db). Активный клиент определяет, какой `*.db` файл открывается. Database класс получает путь при инициализации — нет глобального состояния.

**Example:**
```python
# services/client_manager.py
import json
from pathlib import Path
from modules.database import Database

class ClientManager:
    META_FILE = Path.home() / ".yurteg" / "clients.json"

    def __init__(self):
        self.META_FILE.parent.mkdir(exist_ok=True)
        self._clients: dict[str, Path] = self._load()

    def _load(self) -> dict[str, Path]:
        if self.META_FILE.exists():
            data = json.loads(self.META_FILE.read_text(encoding="utf-8"))
            return {name: Path(p) for name, p in data.items()}
        return {"Основной реестр": Path.home() / ".yurteg" / "yurteg.db"}

    def _save(self):
        data = {name: str(p) for name, p in self._clients.items()}
        self.META_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_clients(self) -> list[str]:
        return list(self._clients.keys())

    def get_db(self, name: str) -> Database:
        return Database(self._clients[name])

    def add_client(self, name: str) -> None:
        slug = name.lower().replace(" ", "_").replace('"', '').replace("'", "")
        path = Path.home() / ".yurteg" / f"client_{slug}.db"
        self._clients[name] = path
        self._save()

    def find_client_by_counterparty(self, counterparty: str, threshold: int = 85) -> str | None:
        """Fuzzy-матчинг контрагента по именам клиентов."""
        from rapidfuzz import process, fuzz
        result = process.extractOne(
            counterparty,
            self._clients.keys(),
            scorer=fuzz.token_sort_ratio,
            score_cutoff=threshold
        )
        return result[0] if result else None
```

### Pattern 6: Синхронизация дедлайнов с сервером

**What:** При запуске приложения `telegram_sync.py` вызывает два метода: 1) `fetch_queue()` — забирает файлы из очереди сервера, 2) `push_deadlines()` — отправляет на сервер минимальные метаданные (date_end, filename, counterparty, status) для cron-уведомлений. Всё через простой REST.

**Example:**
```python
# services/telegram_sync.py
import httpx
from pathlib import Path

class TelegramSync:
    def __init__(self, server_url: str, chat_id: int):
        self.base = server_url.rstrip("/")
        self.chat_id = chat_id

    def fetch_queue(self) -> list[Path]:
        """Забирает файлы из очереди на сервере, возвращает локальные пути."""
        r = httpx.get(f"{self.base}/api/queue/{self.chat_id}", timeout=10)
        r.raise_for_status()
        paths = []
        for item in r.json()["files"]:
            dest = TEMP_DIR / item["filename"]
            file_bytes = httpx.get(f"{self.base}/api/files/{item['id']}").content
            dest.write_bytes(file_bytes)
            httpx.delete(f"{self.base}/api/queue/{item['id']}")  # подтверждение
            paths.append(dest)
        return paths

    def push_deadlines(self, alerts: list[dict]) -> None:
        """Отправляет минимальные метаданные для уведомлений."""
        httpx.post(
            f"{self.base}/api/deadlines/{self.chat_id}",
            json={"alerts": alerts},
            timeout=10
        )
```

### Anti-Patterns to Avoid

- **APScheduler + Streamlit threading:** Не запускать BackgroundScheduler внутри Streamlit-приложения. Streamlit перезапускает скрипт при каждом взаимодействии — планировщик создаётся заново, потоки накапливаются. Решение: cron живёт только на сервере бота.
- **Глобальный db-объект:** Не хранить единственный `Database` объект в `st.session_state` и передавать между клиентами. При переключении клиента нужен новый объект с новым путём к файлу.
- **Telegram polling в production:** `application.run_polling()` блокирует процесс и несовместим с FastAPI. Только webhook.
- **Хранение всего текста договора на сервере:** Только минимальные поля (date_end, filename, counterparty, status). Конфиденциальность — ключевое требование.
- **Синхронный httpx в async контексте:** Внутри FastAPI-handlers использовать `httpx.AsyncClient`, не синхронный `httpx.get()`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Telegram API | Собственный HTTP-клиент к api.telegram.org | python-telegram-bot | Обработка ошибок, rate limits, retry, типизированные объекты Update |
| Cron-задачи | `while True: sleep(3600)` | APScheduler CronTrigger | Надёжный запуск, пропуск если сервер был выключен, поддержка временных зон |
| Fuzzy matching | SequenceMatcher из difflib | rapidfuzz | difflib не обрабатывает перестановку слов («ООО Рога» vs «Рога ООО»), rapidfuzz в 100x быстрее |
| Одноразовые коды | UUID | secrets.choice(digits) 6-значный | UUID длинный, 6 цифр — привычно для пользователей (как SMS-код) |
| ASGI-сервер | Встроенный Flask dev-сервер | uvicorn | Flask dev-сервер однопоточный, не переживёт webhook при высокой нагрузке |

---

## Common Pitfalls

### Pitfall 1: st.toast вызывается при каждом rerun

**What goes wrong:** `st.toast()` показывается снова при каждом пересчёте страницы (нажатие кнопки, изменение selectbox).
**Why it happens:** Streamlit выполняет весь скрипт при каждом взаимодействии.
**How to avoid:** Показывать toast только при первом запуске сессии. Использовать `st.session_state` флаг:
```python
if not st.session_state.get("startup_toast_shown"):
    alerts = get_attention_required(db, config.warning_days_threshold)
    if alerts:
        st.toast(f"⚠️ {len(alerts)} документов истекают скоро", icon="⚠️")
    st.session_state["startup_toast_shown"] = True
```
**Warning signs:** Toast появляется после каждого клика.

### Pitfall 2: python-telegram-bot v13 vs v20+ несовместимость

**What goes wrong:** Документация/примеры из Google для python-telegram-bot v13 (sync API) не работают с v20+ (async API).
**Why it happens:** В v20 вся библиотека переписана на asyncio, все handlers async, другой способ запуска.
**How to avoid:** Использовать только официальную документацию v20+. Все handlers: `async def handler(update, context)`. Запуск: `Application.builder()`, не `Updater`.
**Warning signs:** `TypeError: object bool can't be used in 'await' expression`.

### Pitfall 3: SQLite параллельный доступ из двух процессов

**What goes wrong:** Серверный процесс бота и CLI-утилита (или тесты) одновременно пишут в одну SQLite — `database is locked`.
**Why it happens:** SQLite поддерживает только один writer одновременно, WAL-режим снимает проблему для reads, но не для concurrent writes.
**How to avoid:** Сервер бота имеет **собственную** SQLite (только очередь и метаданные). Локальное приложение имеет свои `*.db` файлы. Никогда один и тот же файл из двух процессов одновременно.
**Warning signs:** `sqlite3.OperationalError: database is locked` в логах.

### Pitfall 4: Webhook URL недоступен — бот молчит

**What goes wrong:** Telegram не может достучаться до webhook, сообщения не обрабатываются, никаких ошибок в логах приложения.
**Why it happens:** Telegram требует публичный HTTPS URL. localhost не работает. SSL-сертификат должен быть валидным.
**How to avoid:** При разработке использовать ngrok для туннелирования. В production — Railway/Fly.io с автоматическим SSL. Проверять статус webhook: `bot.get_webhook_info()`.
**Warning signs:** Команды боту не приводят ни к чему.

### Pitfall 5: Переключение клиента не обновляет весь UI

**What goes wrong:** Пользователь выбрал другого клиента в selectbox, но реестр показывает данные предыдущего.
**Why it happens:** Streamlit кеширует результаты `@st.cache_data` по аргументам — если функция не принимает `client_name` как аргумент, кеш не инвалидируется.
**How to avoid:** Передавать `client_name` как параметр во все кешированные функции. Или использовать `st.cache_data(ttl=0)` для данных реестра.
**Warning signs:** Данные не меняются при переключении клиента.

### Pitfall 6: APScheduler в asyncio контексте

**What goes wrong:** `BackgroundScheduler` (sync) не работает с async функциями (отправка через бота). `AsyncIOScheduler` нужен для async-задач.
**Why it happens:** python-telegram-bot v20+ использует asyncio event loop; sync scheduler не может вызывать async функции.
**How to avoid:** Использовать `AsyncIOScheduler` вместо `BackgroundScheduler`:
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
scheduler = AsyncIOScheduler()
```

---

## Code Examples

### Таблицы серверной SQLite
```sql
-- file_queue: очередь файлов
CREATE TABLE IF NOT EXISTS file_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    mime_type TEXT,
    enqueued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fetched INTEGER DEFAULT 0  -- 0=ожидает, 1=забрано
);

-- bindings: привязка chat_id
CREATE TABLE IF NOT EXISTS bindings (
    chat_id INTEGER PRIMARY KEY,
    bound_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- pending_bindings: одноразовые коды
CREATE TABLE IF NOT EXISTS pending_bindings (
    code TEXT PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    expires_at TIMESTAMP NOT NULL
);

-- deadline_sync: минимальные метаданные для уведомлений
CREATE TABLE IF NOT EXISTS deadline_sync (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    contract_ref TEXT NOT NULL,   -- filename (без полного текста)
    counterparty TEXT,
    date_end TEXT,                -- YYYY-MM-DD
    status TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- notification_settings: настройки уведомлений пользователя
CREATE TABLE IF NOT EXISTS notification_settings (
    chat_id INTEGER PRIMARY KEY,
    digest_enabled INTEGER DEFAULT 1,
    threshold_enabled INTEGER DEFAULT 1,
    warning_days INTEGER DEFAULT 30,
    digest_hour INTEGER DEFAULT 9
);
```

### Миграция v6 в локальном modules/database.py
```python
def _migrate_v6_telegram(conn: sqlite3.Connection) -> None:
    """v6: Добавить таблицы telegram_bindings и notification_settings."""
    if _is_migration_applied(conn, 6):
        return
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS telegram_bindings (
            chat_id INTEGER PRIMARY KEY,
            server_url TEXT NOT NULL,
            bound_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS notification_settings (
            id INTEGER PRIMARY KEY,
            warning_days INTEGER DEFAULT 30,
            digest_enabled INTEGER DEFAULT 1,
            threshold_enabled INTEGER DEFAULT 1
        );
    """)
    conn.commit()
    _mark_migration_applied(conn, 6)
```

### rapidfuzz для автопривязки клиентов
```python
from rapidfuzz import process, fuzz

def find_client_by_counterparty(
    counterparty: str,
    client_names: list[str],
    threshold: int = 80
) -> str | None:
    """Возвращает имя клиента если counterparty похож на него.

    token_sort_ratio обрабатывает порядок слов:
    'ООО Рога и Копыта' ≈ 'Рога и Копыта ООО' → 100
    """
    if not client_names:
        return None
    result = process.extractOne(
        counterparty,
        client_names,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=threshold,
    )
    return result[0] if result else None
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| python-telegram-bot v13 sync | v20+ fully async (asyncio) | 2023, v20.0 | Весь API async, несовместим с v13 |
| Polling (run_polling) | Webhook (run_webhook / set_webhook) | Всегда рекомендовалось | polling нельзя использовать с FastAPI |
| BackgroundScheduler | AsyncIOScheduler для async задач | APScheduler 3.x | Нужен AsyncIO планировщик для async функций |
| thefuzz | rapidfuzz | 2021+ | rapidfuzz — drop-in replacement, в 100x быстрее |

**Deprecated/outdated:**
- `Updater` класс из python-telegram-bot v13: заменён на `Application.builder()` в v20+
- `run_polling()` внутри FastAPI: блокирует event loop, не работает
- `BackgroundScheduler` для async telegram функций: не поддерживает await

---

## Open Questions

1. **Хостинг серверного компонента**
   - What we know: нужен публичный HTTPS сервер для webhook
   - What's unclear: Railway vs Fly.io vs Render — у каждого свои ограничения бесплатного плана
   - Recommendation: Railway — бесплатный план достаточен для MVP, простой деплой из GitHub, автоматический SSL. Решение принять при задаче 03-02.

2. **Хранение очереди файлов на сервере**
   - What we know: файлы нужно где-то хранить до того как приложение их заберёт
   - What's unclear: Railway предоставляет ephemeral filesystem — файлы теряются при рестарте
   - Recommendation: Хранить в SQLite как BLOB для файлов до 50MB. Или использовать Railway Volume (persistent disk). Рассмотреть при планировании 03-02.

3. **Порог fuzzy-матчинга клиентов**
   - What we know: rapidfuzz token_sort_ratio дает 80-85% порог как стандарт
   - What's unclear: 80% может давать ложные срабатывания при коротких именах («ИП Иванов» ≈ «ИП Иванова»)
   - Recommendation: Начать с 85%, предоставить юристу возможность корректировки в сводке.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (из pytest.ini в корне проекта) |
| Config file | `yurteg/pytest.ini` |
| Quick run command | `cd yurteg && pytest tests/ -x -q -m "not slow"` |
| Full suite command | `cd yurteg && pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTG-04 | st.toast показывается только при первом запуске сессии | unit | `pytest tests/test_integrations.py::test_startup_toast_once -x` | ❌ Wave 0 |
| INTG-01 | file_queue: enqueue/fetch/confirm работают корректно | unit | `pytest tests/test_integrations.py::test_file_queue_lifecycle -x` | ❌ Wave 0 |
| INTG-02 | get_alerts_for_user возвращает договоры с date_end < threshold | unit | `pytest tests/test_integrations.py::test_deadline_alerts -x` | ❌ Wave 0 |
| PROF-01 | ClientManager: add_client создаёт db-файл, get_db возвращает правильный | unit | `pytest tests/test_client_manager.py::test_add_and_get_client -x` | ❌ Wave 0 |
| PROF-01 | find_client_by_counterparty: fuzzy match ООО «Рога» vs «Рога ООО» | unit | `pytest tests/test_client_manager.py::test_fuzzy_match -x` | ❌ Wave 0 |
| PROF-01 | Переключение клиента меняет активную db | unit | `pytest tests/test_client_manager.py::test_switch_client -x` | ❌ Wave 0 |
| INTG-01 | pending_binding: код действует 15 минут, истёкший отклоняется | unit | `pytest tests/test_integrations.py::test_binding_code_expiry -x` | ❌ Wave 0 |
| INTG-02 | push_deadlines сериализует только date_end/filename/counterparty/status | unit | `pytest tests/test_integrations.py::test_push_deadlines_minimal_data -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_integrations.py tests/test_client_manager.py -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_integrations.py` — покрывает INTG-01, INTG-02, INTG-04
- [ ] `tests/test_client_manager.py` — покрывает PROF-01
- [ ] `bot_server/database.py` — серверная SQLite с таблицами очереди (нужна для тестов)

---

## Sources

### Primary (HIGH confidence)
- Verified via `pip index versions`: python-telegram-bot 22.7, aiogram 3.26.0, apscheduler 3.11.2, fastapi 0.135.1, uvicorn 0.42.0, rapidfuzz 3.14.3, httpx 0.28.1
- Существующий код `services/pipeline_service.py` — подтверждает отсутствие Streamlit-импорта (готов к вызову из бота)
- Существующий код `services/lifecycle_service.py` — `get_attention_required()` готов для данных уведомлений
- Существующий код `modules/database.py` — паттерн миграций v1–v5, готов для v6

### Secondary (MEDIUM confidence)
- python-telegram-bot v20+ async API — известно по training data, подтверждено версией 22.7 в индексе PyPI
- APScheduler AsyncIOScheduler — стандартная рекомендация для async-контекста, подтверждено документацией библиотеки
- rapidfuzz token_sort_ratio порог 80-85% — стандартная рекомендация для нечёткого сравнения названий компаний

### Tertiary (LOW confidence)
- Railway как рекомендация хостинга для webhook — популярный выбор в 2025-2026, но не верифицирован официально
- Ограничения бесплатного плана Railway — могут изменяться

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — версии верифицированы через pip index versions
- Architecture: HIGH — основана на существующем коде проекта (pipeline_service, lifecycle_service, database migrations pattern)
- Pitfalls: HIGH — python-telegram-bot v13/v20 несовместимость и APScheduler/asyncio — известные задокументированные проблемы
- Hosting: LOW — Railway/Fly.io выбор требует проверки актуальных тарифов

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (стабильный стек, 30 дней)
