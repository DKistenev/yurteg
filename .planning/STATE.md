---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: Desktop Distribution
status: verifying
stopped_at: Completed 52-01-PLAN.md
last_updated: "2026-03-31T00:13:30.481Z"
last_activity: 2026-03-31
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 4
  completed_plans: 4
  percent: 90
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-30)

**Core value:** Юрист загружает папку с документами и за 20 минут получает готовый реестр с метаданными
**Current focus:** Phase 52 — Docs + DMG Polish

## Current Position

Phase: 52 (Docs + DMG Polish) — EXECUTING
Plan: 1 of 1
Status: Phase complete — ready for verification
Last activity: 2026-03-31

Progress: [████████████████████░░] 90% (48/52 phases complete)

## Performance Metrics

**Velocity:**

- Total plans completed: ~80+ across v1.2 and prior
- Average duration: ~15 min/plan (estimate)
- Total execution time: cumulative across milestones

**Recent Trend:**

- Trend: Stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

- v1.2: PyInstaller уже используется, hidden imports уже в spec
- v1.2: llama-server скачивается через GitHub Releases (~30-40 MB), модель — HuggingFace (~1 GB)
- v1.3: onedir mode вместо onefile — быстрее запуск
- v1.3: torch.cuda/torch.distributed исключаются — sentence-transformers тянет ~2 GB без них
- [Phase 49]: onedir mode via COLLECT+BUNDLE for fast .app startup
- [Phase 49]: PyInstaller 6.x: binaries in Contents/Frameworks/, not Contents/MacOS/
- [Phase 49]: Only torch.cuda/distributed excluded; _inductor/_dynamo deferred to Phase 50
- [Phase 50]: Lazy import of get_bundle_root inside _get_bundled_binary for frozen-only code path
- [Phase 51]: macos-15 runner instead of deprecated macos-14 (ARM64)
- [Phase 51]: find-based llama-server location after unzip for archive structure resilience
- [Phase 52]: Static release notes template -- manual edit before tag, appropriate for team of 3
- [Phase 52]: No right-click Gatekeeper bypass -- removed in macOS Sequoia 15.0+

### Pending Todos

None.

### Blockers/Concerns

- Open PRs #4 и #5 (cleanup) — не блокируют, но стоит смержить до сборки
- llama-server бинарник нужно скачать в CI перед PyInstaller (или вендорить в репо)

## Session Continuity

Last session: 2026-03-31T00:13:30.478Z
Stopped at: Completed 52-01-PLAN.md
Resume file: None
