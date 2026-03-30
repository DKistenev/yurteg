# Roadmap: ЮрТэг

## Milestones

- ✅ **v0.4–v0.9** - Phases 1–31 (shipped 2026-03-27)
- ✅ **v1.0 Hackathon-Ready** - Phases 32–43 (shipped 2026-03-29)
- ✅ **v1.1 Bug Sweep** - Phase 43.1 (shipped 2026-03-29)
- ✅ **v1.2 Desktop Build** - Phases 44–48 (shipped 2026-03-30)
- 🚧 **v1.3 Desktop Distribution** - Phases 49–52 (in progress)

## Phases

<details>
<summary>✅ v0.4–v1.2 (Phases 1–48) - SHIPPED 2026-03-30</summary>

Earlier milestones shipped in phases 1–48. See MILESTONES.md for full history.

</details>

### 🚧 v1.3 Desktop Distribution (In Progress)

**Milestone Goal:** Собрать macOS DMG через PyInstaller + GitHub Actions и раздать тестерам через GitHub Releases.

#### Phase 49: PyInstaller Spec + Bundling
**Goal**: Приложение собирается в корректный .app бандл с llama-server внутри
**Depends on**: Phase 48
**Requirements**: BUILD-01, BUILD-02, BUILD-03, BUILD-04
**Success Criteria** (what must be TRUE):
  1. `pyinstaller yurteg.spec` завершается без ошибок на машине разработчика
  2. .app бандл запускается на чистой macOS без установленного Python
  3. Размер бандла не содержит CUDA/distributed слоёв torch (нет папок cuda/distributed в dist/)
  4. llama-server бинарник присутствует внутри .app/Contents/MacOS/ с правами +x
**Plans**: 1 plan
Plans:
- [x] 49-01-PLAN.md — Rewrite spec to onedir + COLLECT + BUNDLE, add NiceGUI/pywebview, torch excludes, llama-server

#### Phase 50: Runtime Path Integration
**Goal**: Приложение использует бандленный llama-server вместо скачивания
**Depends on**: Phase 49
**Requirements**: BUILD-05, BUILD-06
**Success Criteria** (what must be TRUE):
  1. При запуске из .app бандла llama-server стартует без скачивания с GitHub
  2. При запуске из исходников (python main.py) поведение не изменилось — llama-server скачивается как раньше
  3. Приложение полностью запускается из собранного .app: реестр открывается, документ обрабатывается
**Plans**: 1 plan
Plans:
- [ ] 49-01-PLAN.md — Rewrite spec to onedir + COLLECT + BUNDLE, add NiceGUI/pywebview, torch excludes, llama-server

#### Phase 51: GitHub Actions CI/CD
**Goal**: Push тега автоматически создаёт DMG и публикует его в GitHub Releases
**Depends on**: Phase 50
**Requirements**: CICD-01, CICD-02, CICD-03, CICD-04, CICD-05
**Success Criteria** (what must be TRUE):
  1. `git push origin v1.3.0` запускает workflow и через ~15 минут в GitHub Releases появляется YurTag-1.3.0.dmg
  2. DMG содержит drag-to-Applications интерфейс с иконкой приложения
  3. CI workflow использует pip cache — повторные запуски проходят быстрее первого
  4. Файл в релизе называется YurTag-{version}.dmg (версия из тега)
**Plans**: 1 plan
Plans:
- [ ] 49-01-PLAN.md — Rewrite spec to onedir + COLLECT + BUNDLE, add NiceGUI/pywebview, torch excludes, llama-server
**UI hint**: no

#### Phase 52: Docs + DMG Polish
**Goal**: Тестер может скачать DMG, установить и запустить приложение без вопросов
**Depends on**: Phase 51
**Requirements**: DOCS-01, DOCS-02, DOCS-03
**Success Criteria** (what must be TRUE):
  1. INSTALL.md объясняет обход Gatekeeper через UI (Settings → Privacy → Open Anyway) и через терминал
  2. DMG окно при открытии показывает фоновую картинку с брендингом ЮрТэг
  3. GitHub Release содержит заполненные release notes по шаблону
**Plans**: 1 plan
Plans:
- [ ] 49-01-PLAN.md — Rewrite spec to onedir + COLLECT + BUNDLE, add NiceGUI/pywebview, torch excludes, llama-server

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 49. PyInstaller Spec + Bundling | v1.3 | 1/1 | Complete   | 2026-03-30 |
| 50. Runtime Path Integration | v1.3 | 0/? | Not started | - |
| 51. GitHub Actions CI/CD | v1.3 | 0/? | Not started | - |
| 52. Docs + DMG Polish | v1.3 | 0/? | Not started | - |
