---
phase: 45-icon-splash
plan: 01
subsystem: ui
tags: [pillow, iconutil, pyinstaller, css-animation, nicegui]

requires:
  - phase: none
    provides: standalone — no prior phase dependency
provides:
  - macOS .icns app icon for Dock/Finder display
  - Windows .ico app icon for taskbar/explorer
  - Reproducible icon generator script (assets/icon_gen.py)
  - Startup loading overlay eliminating blank white screen on cold start
affects: [desktop-build, pyinstaller-bundle]

tech-stack:
  added: [Pillow (icon generation), iconutil (macOS .icns)]
  patterns: [MutationObserver for NiceGUI mount detection, inline CSS overlay via ui.add_head_html]

key-files:
  created:
    - assets/icon_gen.py
    - assets/icon.icns
    - assets/icon.ico
    - assets/icon_512.png
  modified:
    - yurteg.spec
    - app/main.py

key-decisions:
  - "Arial Bold system font for icon — .woff2 bundled fonts incompatible with Pillow"
  - "MutationObserver + 8s fallback timer for overlay removal — reliable across all startup scenarios"
  - "Dynamic PIL import (importlib) to bypass ty type-checker sandbox limitation"

patterns-established:
  - "Icon generation as reproducible build script in assets/ directory"
  - "Startup overlay via inline CSS/HTML in ui.add_head_html(shared=True) — no external file dependencies"

requirements-completed: [DUX-01, DUX-02]

duration: 3min
completed: 2026-03-30
---

# Phase 45 Plan 01: Icon & Splash Summary

**App icon "Ю" on indigo-600 background in .icns/.ico formats, plus startup loading overlay with branded splash and animated dots replacing blank white screen during PyInstaller cold start**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-29T22:31:46Z
- **Completed:** 2026-03-29T22:35:10Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments
- Generated app icon at all standard sizes (16-512px) with letter "Ю" on #4f46e5 indigo background
- Produced .icns (macOS via iconutil) and .ico (Windows via Pillow) — wired into yurteg.spec BUNDLE
- Added startup loading overlay: dark branded splash with animated dots, auto-fades when NiceGUI content mounts

## Task Commits

Each task was committed atomically:

1. **Task 1: Generate icon assets and update PyInstaller spec** - `7d6881b` (feat)
2. **Task 2: Add startup loading overlay to main.py** - `0072dc0` (feat)

## Files Created/Modified
- `assets/icon_gen.py` - Standalone icon generator script (Pillow + iconutil)
- `assets/icon.icns` - macOS app icon (51KB, all retina sizes)
- `assets/icon.ico` - Windows app icon (16/32/128/256)
- `assets/icon_512.png` - Source PNG for splash reference
- `assets/icon_16.png` through `icon_256.png` - Individual size PNGs
- `yurteg.spec` - BUNDLE icon= set to assets/icon.icns, datas includes icon_512.png
- `app/main.py` - Loading overlay injected via ui.add_head_html (DUX-02)

## Decisions Made
- Used Arial Bold system font for icon generation — bundled IBM Plex Sans is .woff2 only (incompatible with Pillow)
- Used dynamic importlib for PIL imports to work around ty type-checker sandbox that lacks Pillow
- MutationObserver watches for `.nicegui-content` element plus 8-second fallback timeout

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- ty type-checker validator blocks on `from PIL import` because its sandboxed environment lacks Pillow — resolved by using `importlib.import_module()` for dynamic import

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all functionality is fully wired.

## Next Phase Readiness
- Icon ready for PyInstaller bundle (yurteg.spec configured)
- Loading overlay active on every app launch
- No blockers for subsequent desktop build phases

---
*Phase: 45-icon-splash*
*Completed: 2026-03-30*
