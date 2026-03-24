"""Design Polish tests — verify design system compliance via source inspection."""
import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MAIN_PY = PROJECT_ROOT / "app" / "main.py"
REGISTRY_PY = PROJECT_ROOT / "app" / "pages" / "registry.py"
STYLES_PY = PROJECT_ROOT / "app" / "styles.py"
DESIGN_CSS = PROJECT_ROOT / "app" / "static" / "design-system.css"


# ── DSGN-01: Status badges use slate, not gray ──────────────────────────────


def test_status_css_slate():
    """Status CSS must use slate hex values for unknown/terminated, not gray."""
    # Since v0.6+ the app uses design-system.css with hex color values,
    # not Tailwind utility classes in main.py.
    css = DESIGN_CSS.read_text(encoding="utf-8")

    # unknown and terminated statuses use slate-100 (#f1f5f9) background
    assert "#f1f5f9" in css, "status-unknown/terminated should use #f1f5f9 (slate-100)"
    # unknown uses slate-500 (#64748b) text
    assert "#64748b" in css, "status-unknown should use #64748b (slate-500) text"
    # terminated uses slate-600 (#475569) text
    assert "#475569" in css, "status-terminated should use #475569 (slate-600) text"
    # expired uses red (#fee2e2 background, #b91c1c text)
    assert "#fee2e2" in css, "status-expired should use #fee2e2 (red-100) background"
    assert "#b91c1c" in css, "status-expired should use #b91c1c (red-700) text"


# ── DSGN-01: Action icons use slate/indigo hex codes ─────────────────────────


def test_actions_css_hex():
    """Design system CSS must use slate/indigo hex codes."""
    css = DESIGN_CSS.read_text(encoding="utf-8")

    assert "#64748b" in css, "slate-500 (#64748b) must be action icon color"
    assert "#4f46e5" in css, "indigo-600 (#4f46e5) must be action hover color"
    assert "#94a3b8" in css, "slate-400 (#94a3b8) must be expand icon color"
    assert "#475569" in css, "slate-600 (#475569) must be expand hover color"


# ── DSGN-02: Segment control uses indigo ─────────────────────────────────────


def test_seg_active_indigo():
    """SEG_ACTIVE in styles.py must use bg-indigo-600."""
    content = STYLES_PY.read_text(encoding="utf-8")
    assert "bg-indigo-600" in content
    assert "bg-gray-900" not in content


# ── DSGN-03: IBM Plex Sans font ─────────────────────────────────────────────


def test_font_injection():
    """main.py must inject IBM Plex Sans from local static files (no CDN)."""
    content = MAIN_PY.read_text(encoding="utf-8")
    assert "IBMPlexSans-Regular.woff2" in content, "Local Regular font not referenced"
    assert re.search(r"font-family.*IBM Plex Sans", content), "font-family declaration missing"


# ── DSGN-04: AppState has calendar_visible ───────────────────────────────────


def test_appstate_calendar_visible():
    """AppState must have calendar_visible: bool = False."""
    from app.state import AppState
    assert AppState().calendar_visible is False


# ── DSGN-05: Animation keyframes ────────────────────────────────────────────


def test_animation_keyframes():
    """Design system CSS must contain page fade-in and animation keyframes."""
    css = DESIGN_CSS.read_text(encoding="utf-8")

    # Page fade-in animation (AG Grid row-in was removed due to AG Grid 34 conflict)
    assert "@keyframes page-fade-in" in css, "@keyframes page-fade-in must be in design-system.css"
    # Spring easing used in dialog, badge, toast, and other transitions
    assert "cubic-bezier(0.25, 1, 0.5, 1)" in css, "Spring easing cubic-bezier(0.25, 1, 0.5, 1) must be present"
    # Stagger delay utilities present (yt-delay-* classes)
    assert "animation-delay: 60ms" in css, "Stagger delay utilities must include 60ms"
    assert "animation-delay: 300ms" in css, "Stagger delay utilities must include 300ms"


# ── DSGN-01: no gray-* in main.py ───────────────────────────────────────────


def test_no_gray_in_main():
    """main.py must have zero gray-* Tailwind classes."""
    content = MAIN_PY.read_text(encoding="utf-8")
    gray_matches = re.findall(r"(?:bg|text|border|ring)-gray-\d+", content)
    lines = content.split("\n")
    non_comment_grays = []
    for match in gray_matches:
        for line in lines:
            if match in line and not line.strip().startswith("#"):
                non_comment_grays.append(match)
                break
    assert len(non_comment_grays) == 0, f"gray-* classes found: {non_comment_grays}"
