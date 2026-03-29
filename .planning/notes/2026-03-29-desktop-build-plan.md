---
date: "2026-03-29 03:20"
promoted: false
---

Сборка десктоп-версий (milestone v1.1):

СБОРЩИК: PyInstaller + UPX (сжатие ~30-40%). NiceGUI + PyInstaller задокументированы в официальном репо. Размер ~300-500MB без моделей.

CI/CD: GitHub Actions — один .github/workflows/build.yml. На каждый тег vX.Y собирает .dmg (macOS runner) и .exe (Windows runner). Единственный способ собрать Windows без Windows-ноута. Бесплатно 2000 мин/мес.

УСТАНОВЩИК macOS: create-dmg — CLI, красивый .dmg с фоном и стрелкой "перетащи в Applications".

УСТАНОВЩИК Windows: Inno Setup — бесплатный, стандартный wizard "Далее → Установить".

ПОДПИСАНИЕ macOS: Apple Developer Account $99/год. Без него — "неизвестный разработчик". codesign → notarytool → staple. Через GitHub Actions секреты.

ПОДПИСАНИЕ Windows: Code Signing Certificate $70-300/год. Без него SmartScreen блокирует.

АВТООБНОВЛЕНИЕ: Простая проверка через GitHub Releases API + httpx при старте. Сравнить APP_VERSION → показать "Доступна версия X". Полный автоапдейт (скачать → заменить → перезапуск) — v2.

КРЭШ-РЕПОРТЫ: Sentry (бесплатно 5K событий/мес). Один pip install, одна строка в main.py. Без этого "не работает" от юриста = тупик.

АНАЛИТИКА: Posthog (опционально, только с opt-in). Анонимная телеметрия — сколько документов, какой провайдер, где застрял. Для CustDev на реальных данных.

МОДЕЛИ: НЕ бандлим. GGUF (~1GB) и sentence-transformers (~90MB) скачиваются при первом запуске. Уже есть LlamaServerManager + прогресс-бар в онбординге.

ОБРАТНАЯ СОВМЕСТИМОСТЬ:
- macOS 12+ (Monterey) — работает. macOS 11 (Big Sur) — вероятно. macOS 10.15 и ниже — нет.
- Windows 10 (1809+) — работает. Windows 7/8 — нет (Python 3.10+ не поддерживает).

РИСКИ:
- llama-server на Windows без GPU — медленно (~30 сек/документ). Fallback на облако.
- PyInstaller .exe ложно детектится антивирусами. EV-сертификат решает.
- Кириллические пути на Windows — тестировать. Pathlib покрывает, но нужна проверка.
- Первый запуск: скачивание 1GB+ при медленном интернете. Хороший прогресс-бар обязателен.
