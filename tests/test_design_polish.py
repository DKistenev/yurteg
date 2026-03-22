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
    """Status CSS must use slate for unknown/terminated, not gray."""
    content = MAIN_PY.read_text(encoding="utf-8")

    assert "bg-slate-100" in content, "status-unknown/terminated should use bg-slate-100"
    assert "text-slate-500" in content, "status-unknown/terminated should use text-slate-500"
    assert "bg-gray-100" not in content, "bg-gray-100 found — should be migrated to slate"

    # Semantic status colors preserved
    assert "bg-green-50" in content
    assert "bg-yellow-50" in content
    assert "bg-red-50" in content
    assert "bg-indigo-50" in content
    assert "bg-purple-50" in content
    assert "bg-orange-50" in content


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
    """main.py must inject IBM Plex Sans."""
    content = MAIN_PY.read_text(encoding="utf-8")
    assert "IBM+Plex+Sans" in content
    assert re.search(r"font-family.*IBM Plex Sans", content)


# ── DSGN-04: AppState has calendar_visible ───────────────────────────────────


def test_appstate_calendar_visible():
    """AppState must have calendar_visible: bool = False."""
    from app.state import AppState
    assert AppState().calendar_visible is False


# ── DSGN-05: Animation keyframes ────────────────────────────────────────────


def test_animation_keyframes():
    """Design system CSS must contain staggered row and page fade-in keyframes."""
    css = DESIGN_CSS.read_text(encoding="utf-8")

    assert "@keyframes row-in" in css
    assert "@keyframes page-fade-in" in css
    assert "cubic-bezier(0.25, 1, 0.5, 1)" in css
    assert "animation-delay: 560ms" in css


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
