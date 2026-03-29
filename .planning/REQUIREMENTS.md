# Requirements: ЮрТэг v1.2

**Defined:** 2026-03-30
**Core Value:** Юрист загружает папку с документами и за 20 минут получает готовый реестр — без ручного ввода, без обучения

## v1.2 Requirements

### Логирование и мониторинг (LOG)

- [ ] **LOG-01**: Приложение пишет логи в файл ~/.yurteg/logs/yurteg.log с ротацией (5MB × 3)
- [ ] **LOG-02**: Логи отправляются на BetterStack Logtail для удалённого мониторинга бета-тестеров
- [ ] **LOG-03**: Каждый тестер идентифицируется через machine_id в логах
- [ ] **LOG-04**: Содержимое юридических документов не попадает в удалённые логи
- [ ] **LOG-05**: Приложение не запускается дважды — file lock ~/.yurteg/app.lock с сообщением «ЮрТэг уже запущен»

### Desktop UX (DUX)

- [ ] **DUX-01**: Приложение имеет иконку «Ю» в индиго — .icns (macOS) и .ico (Windows) во всех размерах (16/32/128/256/512px)
- [ ] **DUX-02**: При запуске PyInstaller-бандла показывается splash/loading вместо пустоты (3-5 сек распаковка)
- [ ] **DUX-03**: При первом запуске без интернета — понятное сообщение «подключитесь к интернету для первой настройки» вместо краша
- [ ] **DUX-04**: Перед скачиванием моделей проверяется свободное место на диске (>1.5GB), при нехватке — предупреждение

### Безопасность и runtime (RUN)

- [ ] **RUN-01**: storage_secret генерируется через secrets.token_hex(32) при первом запуске и хранится в settings.json
- [ ] **RUN-02**: После скачивания llama-server на macOS снимается quarantine флаг (xattr -dr com.apple.quarantine)
- [ ] **RUN-03**: freeze_support() вызывается в main.py до ui.run() для корректной работы в PyInstaller-бандле
- [ ] **RUN-04**: PyInstaller .spec содержит все hidden imports (natasha, pymorphy2, sentence-transformers, pdfplumber) и data files (app/static, data/)

### Верификация существующих функций (VER)

- [ ] **VER-01**: Redline (word-level DOCX track changes) работает end-to-end — загрузка шаблона → сравнение → скачивание .docx с изменениями
- [ ] **VER-02**: Предпросмотр документа (PDF/DOCX) отображается в карточке документа
- [ ] **VER-03**: Кнопка «Гид» запускает onboarding guided tour без ошибок

## v2 Requirements

### Доставка

- **DLVR-01**: Автообновление — проверка GitHub Releases + баннер «Доступна версия X»
- **DLVR-02**: Сборка EXE для Windows через GitHub Actions
- **DLVR-03**: Code signing для macOS (Apple Developer $99/год)
- **DLVR-04**: Code signing для Windows (EV-сертификат)

### Телеметрия

- **TLMT-01**: Sentry для крэш-репортов (5K событий/мес бесплатно)
- **TLMT-02**: Posthog для анонимной аналитики (opt-in)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Автообновление (уровень 2+) | Замена файлов, Sparkle — overkill для бета |
| EULA/лицензия | Не критично для внутреннего тестирования |
| Windows EXE сборка | Фокус на macOS DMG, Windows — следующий milestone |
| Telegram-бот хостинг | Отдельный milestone после десктопа |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| LOG-01 | Phase 44 | Pending |
| LOG-02 | Phase 44 | Pending |
| LOG-03 | Phase 44 | Pending |
| LOG-04 | Phase 44 | Pending |
| LOG-05 | Phase 44 | Pending |
| DUX-01 | Phase 45 | Pending |
| DUX-02 | Phase 45 | Pending |
| DUX-03 | Phase 46 | Pending |
| DUX-04 | Phase 46 | Pending |
| RUN-01 | Phase 47 | Pending |
| RUN-02 | Phase 47 | Pending |
| RUN-03 | Phase 47 | Pending |
| RUN-04 | Phase 47 | Pending |
| VER-01 | Phase 48 | Pending |
| VER-02 | Phase 48 | Pending |
| VER-03 | Phase 48 | Pending |

**Coverage:**
- v1.2 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-30*
*Last updated: 2026-03-30 — Traceability filled after roadmap creation*
