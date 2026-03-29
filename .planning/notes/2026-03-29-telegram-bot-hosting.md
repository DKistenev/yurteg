---
date: "2026-03-29 03:45"
promoted: false
---

Telegram-бот: хостинг на Beget VPS

СЕРВЕР: Beget VPS (уже есть, ранее использовался для Open WebUI). Python + long-running процессы работают.

БОТ: bot_server/ — FastAPI сервер. Эндпоинты: /api/bind, /api/queue, /api/files, /api/notify, /api/deadlines. Лёгкий, минимальные ресурсы (~50-80MB RAM).

ДЕПЛОЙ: systemd unit для автостарта + автоперезапуска. Nginx как reverse proxy. SSL через Let's Encrypt (бесплатно).

СВЯЗЬ С ДЕСКТОПОМ: Приложение → HTTPS запросы на VPS. Настраивается в config.py telegram_server_url. Уже реализовано в services/telegram_sync.py.

ЧТО ДЕЛАЕТ БОТ:
- Принимает документы от юриста через Telegram → кладёт в очередь
- Десктоп при запуске забирает очередь → обрабатывает локально
- Ежедневный дайджест дедлайнов (cron на VPS)
- Уведомления о результатах обработки

НА VPS ТАКЖЕ:
- Лендинг/сайт ЮрТэг (статика через Nginx)
- API для лицензий (можно добавить в bot_server)
