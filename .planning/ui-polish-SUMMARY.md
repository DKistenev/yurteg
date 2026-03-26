# UI Polish Summary

**Date:** 2026-03-26
**Duration:** ~5 minutes
**Tasks:** 6/6 complete

## One-liner

Visual polish across document card, calendar timeline, bulk toolbar, deadline widget, settings spacing, and global typography.

## Changes

### 1. Document Card (app/pages/document.py)
- Counterparty name: 16px, font-weight 600
- Amount: 18px, font-weight 700
- Removed confidence indicator ("Точность распознавания: 94%") from template review section
- Template review section wrapped in Apple card
- Right preview panel max-width capped at 50%
- Removed filename from preview toolbar
- Card spacing increased (mb-3 -> mb-4)
- Removed dividers between sections for cleaner look
- **Commit:** 045ef72

### 2. Calendar Timeline (design-system.css + registry.py)
- Timeline cards: increased shadow (0 1px 3px), better hover effect
- Replaced border-left type indicators with colored pill badges (background + text)
- Timeline group titles: 10px -> 12px for readability
- Calendar container: added px-6 horizontal padding
- **Commit:** c784261

### 3. Bulk Toolbar (bulk_actions.py)
- "Удалить": red text (#dc2626) with delete icon
- "Изменить статус": indigo text (#4f46e5) with edit icon
- "Снять выбор": slate text with deselect icon
- Counter: bolder, indigo-colored number
- **Commit:** 80f8840

### 4. Deadline Widget (registry.py)
- Replaced SVG clock with Material "schedule" icon
- Status text now uses colored pill badges (expired: red bg, expiring: amber bg)
- Subtle bottom borders between alert items
- Improved padding per item (8px 12px)
- **Commit:** 42a6122

### 5. Settings Spacing (settings.py)
- Section headers: mb-2 -> mb-4 after subtitle
- Settings rows: py-3 -> py-4 (more breathing room)
- Telegram unbound section: gap-2 -> gap-3 between badge and input
- **Commit:** 568b088

### 6. Global Typography (main.py)
- Added letter-spacing: -0.01em to body for tighter, professional feel
- **Commit:** 1bef19f

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

All 6 commits verified, all modified files compile, all imports pass.
