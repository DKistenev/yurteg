# Requirements: ЮрТэг v1.3

**Defined:** 2026-03-30
**Core Value:** Юрист загружает папку с документами и за 20 минут получает готовый реестр с метаданными

## v1.3 Requirements

### Сборка (Build)

- [x] **BUILD-01**: PyInstaller spec переключён на onedir mode с COLLECT + BUNDLE для быстрого запуска
- [x] **BUILD-02**: NiceGUI static files и pywebview включены в spec (collect_data_files + collect_submodules)
- [x] **BUILD-03**: torch.cuda и torch.distributed исключены из бандла для уменьшения размера
- [x] **BUILD-04**: llama-server бинарник бандлится в .app через binaries в spec
- [x] **BUILD-05**: llama_server.py проверяет бандленный бинарник (sys._MEIPASS) перед скачиванием
- [x] **BUILD-06**: Локальная сборка .app проходит успешно и приложение запускается

### CI/CD

- [ ] **CICD-01**: GitHub Actions workflow срабатывает на push тега v*
- [ ] **CICD-02**: CI собирает .app через PyInstaller на macos-14 runner
- [ ] **CICD-03**: CI создаёт DMG через create-dmg с drag-to-Applications
- [ ] **CICD-04**: DMG загружается как asset в GitHub Release с версией в имени (YurTag-1.3.0.dmg)
- [ ] **CICD-05**: pip cache настроен для экономии CI минут

### Документация (Docs)

- [ ] **DOCS-01**: INSTALL.md с инструкцией установки и обхода Gatekeeper (GUI + терминал)
- [ ] **DOCS-02**: DMG имеет фоновую картинку с брендингом ЮрТэг
- [ ] **DOCS-03**: Release notes template для описания изменений

## Future Requirements

### Windows

- **WIN-01**: GitHub Actions workflow для Windows EXE сборки
- **WIN-02**: NSIS или MSI установщик

### Distribution

- **DIST-01**: Auto-update механизм (Sparkle или аналог)
- **DIST-02**: Apple Developer ID + Notarization

## Out of Scope

| Feature | Reason |
|---------|--------|
| Apple Developer ID + Notarization | $99/год, избыточно для бета-тестирования |
| Auto-update (Sparkle) | Требует codesigning, сложная интеграция |
| Windows EXE | Отдельный milestone |
| Homebrew Cask | Требует нотаризации и публичного репозитория |
| Custom .pkg installer | Сложнее DMG, нет дополнительной ценности |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BUILD-01 | Phase 49 | Complete |
| BUILD-02 | Phase 49 | Complete |
| BUILD-03 | Phase 49 | Complete |
| BUILD-04 | Phase 49 | Complete |
| BUILD-05 | Phase 50 | Complete |
| BUILD-06 | Phase 50 | Complete |
| CICD-01 | Phase 51 | Pending |
| CICD-02 | Phase 51 | Pending |
| CICD-03 | Phase 51 | Pending |
| CICD-04 | Phase 51 | Pending |
| CICD-05 | Phase 51 | Pending |
| DOCS-01 | Phase 52 | Pending |
| DOCS-02 | Phase 52 | Pending |
| DOCS-03 | Phase 52 | Pending |

**Coverage:**
- v1.3 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-30*
*Last updated: 2026-03-30 — traceability mapped to phases 49–52*
