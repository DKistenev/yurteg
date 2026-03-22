"""Design Polish test scaffold — Phase 13, Plan 01.

Tests DSGN-01 through DSGN-05 via source-level inspection (no browser needed).
All tests fail initially (RED phase — code not yet migrated), then pass after Task 2.

Approach: read main.py as text (avoids ui.run() side-effect on import).
For AppState — import app.state directly (no ui.run dependency).
"""
import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MAIN_PY = PROJECT_ROOT / "app" / "main.py"
REGISTRY_PY = PROJECT_ROOT / "app" / "pages" / "registry.py"


def _extract_css_block(content: str, var_name: str) -> str:
    """Extract a CSS string literal from Python source by variable name."""
    # Match: VAR_NAME = """..."""  (triple-quoted)
    pattern = rf'{var_name}\s*=\s*"""(.*?)"""'
    m = re.search(pattern, content, re.DOTALL)
    if m:
        return m.group(1)
    return ""


# ── DSGN-01: Status badges use slate, not gray ────────────────────────────────


def test_status_css_slate():
    """_STATUS_CSS must use slate-100/slate-500 for unknown/terminated, not gray."""
    content = MAIN_PY.read_text(encoding="utf-8")
    css = _extract_css_block(content, "_STATUS_CSS")

    # unknown and terminated must use slate
    assert "bg-slate-100" in css, "status-unknown/terminated should use bg-slate-100, not bg-gray-100"
    assert "text-slate-500" in css, "status-unknown/terminated should use text-slate-500, not text-gray-500"

    # old gray values must be gone
    assert "bg-gray-100" not in css, "bg-gray-100 found in _STATUS_CSS — should be migrated to bg-slate-100"

    # semantic status colors must still be present (DO NOT touch these)
    assert "bg-green-50" in css, "status-active bg-green-50 must not be removed"
    assert "text-green-700" in css, "status-active text-green-700 must not be removed"
    assert "bg-yellow-50" in css, "status-expiring bg-yellow-50 must not be removed"
    assert "text-yellow-700" in css, "status-expiring text-yellow-700 must not be removed"
    assert "bg-red-50" in css, "status-expired bg-red-50 must not be removed"
    assert "text-red-700" in css, "status-expired text-red-700 must not be removed"
    assert "bg-blue-50" in css, "status-extended bg-blue-50 must not be removed"
    assert "bg-purple-50" in css, "status-negotiation bg-purple-50 must not be removed"
    assert "bg-orange-50" in css, "status-suspended bg-orange-50 must not be removed"


# ── DSGN-01, DSGN-02: Action icons use slate/indigo hex codes ─────────────────


def test_actions_css_hex():
    """_ACTIONS_CSS must use slate/indigo hex codes, not gray-500/gray-900."""
    content = MAIN_PY.read_text(encoding="utf-8")
    css = _extract_css_block(content, "_ACTIONS_CSS")

    # new slate/indigo values must be present
    assert "#64748b" in css, "slate-500 (#64748b) must replace #6b7280 in _ACTIONS_CSS"
    assert "#4f46e5" in css, "indigo-600 (#4f46e5) must replace #111827 as hover color"
    assert "#94a3b8" in css, "slate-400 (#94a3b8) must replace #9ca3af as expand icon color"
    assert "#475569" in css, "slate-600 (#475569) must replace #374151 as expand hover color"

    # old gray hex values must be gone
    assert "#6b7280" not in css, "#6b7280 (gray-500) found — must be migrated to #64748b (slate-500)"
    assert "#111827" not in css, "#111827 (gray-900) found — must be migrated to #4f46e5 (indigo-600)"


# ── DSGN-02: Segment control active state uses indigo ─────────────────────────


def test_seg_active_indigo():
    """registry.py _SEG_ACTIVE must use bg-indigo-600, not bg-gray-900."""
    content = REGISTRY_PY.read_text(encoding="utf-8")

    assert "bg-indigo-600" in content, "registry.py must use bg-indigo-600 for _SEG_ACTIVE"
    assert "bg-gray-900" not in content, "bg-gray-900 found in registry.py — must be migrated to bg-indigo-600"


# ── DSGN-03: IBM Plex Sans font injected globally ────────────────────────────


def test_font_injection():
    """app/main.py must inject IBM Plex Sans via Google Fonts link."""
    content = MAIN_PY.read_text(encoding="utf-8")

    assert "IBM+Plex+Sans" in content, "IBM+Plex+Sans Google Fonts link not found in app/main.py"
    assert re.search(r"font-family.*IBM Plex Sans", content), (
        "font-family: IBM Plex Sans declaration not found in app/main.py"
    )


# ── DSGN-04: AppState has calendar_visible field ─────────────────────────────


def test_appstate_calendar_visible():
    """AppState must have calendar_visible: bool = False field."""
    from app.state import AppState  # noqa: PLC0415

    state = AppState()
    assert hasattr(state, "calendar_visible"), "AppState missing calendar_visible field"
    assert state.calendar_visible is False, "AppState.calendar_visible default must be False"


# ── DSGN-05: Animation keyframes present ────────────────────────────────────


def test_animation_keyframes():
    """app/main.py must contain staggered row and page fade-in keyframes."""
    content = MAIN_PY.read_text(encoding="utf-8")

    assert "@keyframes row-in" in content, "@keyframes row-in not found in app/main.py"
    assert "@keyframes page-fade-in" in content, "@keyframes page-fade-in not found in app/main.py"
    assert "cubic-bezier(0.25, 1, 0.5, 1)" in content, "row-in easing cubic-bezier(0.25, 1, 0.5, 1) not found"
    assert "animation-delay: 560ms" in content, "8th row animation-delay: 560ms not found (stagger cap check)"


# ── DSGN-01 holistic: no gray- in main.py (outside semantic status) ──────────


def test_no_gray_in_main():
    """app/main.py must have zero remaining gray-* Tailwind classes (non-semantic)."""
    content = MAIN_PY.read_text(encoding="utf-8")

    # Find all gray- occurrences for Tailwind bg/text/border/ring classes
    gray_matches = re.findall(r"(?:bg|text|border|ring)-gray-\d+", content)

    # Filter out lines that are inside Python comments (start with #)
    lines = content.split("\n")
    non_comment_grays = []
    for match in gray_matches:
        for line in lines:
            if match in line and not line.strip().startswith("#"):
                non_comment_grays.append(match)
                break

    assert len(non_comment_grays) == 0, (
        f"Found {len(non_comment_grays)} gray-* class(es) in app/main.py — all must be migrated to slate: "
        f"{non_comment_grays}"
    )
