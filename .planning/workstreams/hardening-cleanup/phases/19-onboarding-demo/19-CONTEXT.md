# Phase 19: Onboarding + Demo Data - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning
**Mode:** Pre-discussed via user feedback

<domain>
## Phase Boundary

Add guided tour for first-time users, button to re-trigger tour, demo data loading for testing without native mode, template demo card in empty state, and web mode file picker fallback.

</domain>

<decisions>
## Implementation Decisions

### Guided Tour (ONBR-01)
- Spotlight overlay on key elements: header upload button, nav tabs, filter bar, calendar toggle
- Each step: dark overlay with spotlight hole, card with title + description, «Продолжить» button
- Tour runs automatically on first visit AFTER splash onboarding (when user first sees registry)
- Use existing tour infrastructure from app/components/onboarding/tour.py (Phase 12)
- Tour must be BEAUTIFUL — user specifically asked for "красивый гайдед тур, как в лучших SaaS"
- Steps: 1) Upload button, 2) Navigation tabs, 3) Search + filters, 4) Calendar toggle, 5) Client dropdown

### Tour Button (ONBR-02)
- Add «? Гид» button in header (right side, before client dropdown)
- Click resets tour_completed setting and triggers tour
- Small, subtle — doesn't compete with main CTA

### Demo Data (ONBR-03)
- Button «Загрузить тестовые данные» in empty state (registry)
- Loads sample contracts from tests/test_data/ directory
- Processes them through the pipeline (or inserts pre-computed results)
- After loading: registry shows documents, user can see stats bar, badges, calendar
- This is critical for web-mode testing where native folder picker doesn't work

### Template Demo Card (PLSH-05)
- In template empty state, show one greyed-out demo card as example
- Card shows what a real template looks like: name, type badge, left color bar
- Labeled "Пример" to distinguish from real templates

### Web Mode Fallback (RBST-01)
- templates.py _pick_file() uses webview.OPEN_DIALOG — crashes without native mode
- Add try/except: if webview not available, use NiceGUI ui.upload() component as fallback
- Same for registry upload flow in header

### Claude's Discretion
- Tour card visual design (colors, shadows, positioning)
- Demo data: pre-computed results vs real pipeline processing
- Upload fallback exact UX (inline upload vs dialog)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- app/components/onboarding/tour.py — existing guided tour from Phase 12
- app/components/onboarding/splash.py — onboarding splash screen
- tests/test_data/ — sample PDF/DOCX files for demo
- app/components/process.py — pick_folder() and start_pipeline()

### Established Patterns
- Tour uses JS spotlight + NiceGUI hidden button bridge (Phase 12 decision)
- save_setting('tour_completed', True) marks tour as done
- Template cards render via _render_cards() with TMPL_TYPE_COLORS

### Integration Points
- app/pages/registry.py — demo data button in empty state, tour trigger
- app/components/header.py — tour button
- app/pages/templates.py — demo card in empty state
- app/components/process.py — web mode fallback for pick_folder

</code_context>

<specifics>
## Specific Ideas

- User: "красивый гайдед тур, как в лучших SaaS, с подсветкой кнопок и карточками"
- User: "кнопочку отдельную добавить, начать онбординг"
- User: "добавь кнопку тестовый документ для тестирования"
- User: "я вообще не понимаю, как выглядит приложение в рабочем состоянии"

</specifics>

<deferred>
## Deferred Ideas

- Video tutorial embedded in onboarding
- Interactive walkthrough with actual document processing
- Contextual tooltips on every element

</deferred>
