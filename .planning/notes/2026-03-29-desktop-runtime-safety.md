---
date: "2026-03-29 03:28"
promoted: false
---

Критичные вещи для десктоп-рантайма:

ЛОГИРОВАНИЕ В ФАЙЛ: Сейчас логи в stdout — в десктопе не видно. Добавить RotatingFileHandler в ~/.yurteg/logs/yurteg.log, ротация 5MB × 3 файла. Когда юрист скажет "не работает" — попросить скинуть лог. Настраивается в main.py при старте (logging.handlers.RotatingFileHandler).

ОДНОКРАТНЫЙ ЗАПУСК: Два клика по иконке = два экземпляра = два llama-server на порту 8080 = крэш. Нужен file lock ~/.yurteg/app.lock при старте. Если lock занят — показать "ЮрТэг уже запущен" и выйти. Реализация: fcntl.flock (Unix) или msvcrt.locking (Windows).
