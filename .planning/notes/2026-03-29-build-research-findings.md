---
date: "2026-03-29 03:35"
promoted: false
---

Ресёрч: критичные технические находки перед сборкой

КРИТИЧНО (без этого не запустится):
1. macOS quarantine — скачанный llama-server блокируется Gatekeeper. Нужен xattr -dr com.apple.quarantine после загрузки в ensure_server_binary()
2. Windows WebView2 — на Win10 корпоративных может отсутствовать. Включить Evergreen Standalone Installer в Inno Setup
3. Hidden imports — natasha/pymorphy2, sentence-transformers, pdfplumber динамически грузят модули. Нужен явный список в .spec файле
4. NiceGUI static — __file__ в frozen app не работает, нужен sys._MEIPASS для путей
5. freeze_support() — обязателен в main.py до ui.run(), иначе torch зациклит приложение

ВЫСОКИЕ:
6. onedir вместо onefile — иначе +8-15 сек к каждому запуску (распаковка)
7. Кириллические TEMP на Windows — C:\Users\Иванов\ сломает часть библиотек. Переключать TEMP на ASCII-путь
8. HF_HUB_OFFLINE — sentence-transformers лезет в интернет при каждом запуске. Ставить TRANSFORMERS_OFFLINE=1 после первой загрузки
9. App Nap на macOS — свернул окно → llama-server заморожен. Запускать через caffeinate -i
10. Hardened Runtime entitlements — нотаризация блокирует дочерние процессы. Нужны entitlements для llama-server

БЕЗОПАСНОСТЬ:
11. storage_secret захардкожен — генерировать secrets.token_hex(32) при первом запуске, хранить в settings.json
12. SQLite без шифрования — минимум: предупреждение "включите FileVault/BitLocker". Максимум: SQLCipher

UX:
13. Онбординг — показывать суммарный объём ДО скачивания (~1.1GB), разбить на этапы, объяснить зачем
14. Антивирусы Windows — PyInstaller + скачивание файлов = паттерн малвари. EV-сертификат решает
15. macOS TCC права доступа — сохранённый путь к папке может быть недоступен при следующем запуске без picker
16. Обновления — прямая ссылка на .dmg/.exe + краткий changelog, не ссылка на репозиторий
