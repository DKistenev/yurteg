# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow>=10.0"]
# ///
"""Generate YurTag DMG background image.

Usage: python assets/dmg_background_gen.py

Produces:
  assets/dmg_background.png  -- 600x400 branding image for DMG window

Requires: pip install Pillow
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import Any

# Dynamic import -- Pillow is a runtime dependency, not available in type-checker env
_pil_image: Any = importlib.import_module("PIL.Image")
_pil_draw: Any = importlib.import_module("PIL.ImageDraw")
_pil_font: Any = importlib.import_module("PIL.ImageFont")

# -- Config ---------------------------------------------------------------
BG_COLOR = (79, 70, 229)  # #4F46E5 -- indigo-600
FG_COLOR = (255, 255, 255)  # white
BRAND_TEXT = "\u042e\u0440\u0422\u044d\u0433"  # ЮрТэг
FONT_SIZE = 48
WIDTH = 600
HEIGHT = 400

ASSETS_DIR = Path(__file__).parent

# Font candidates (Cyrillic-capable, bold preferred)
FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/System/Library/Fonts/SFNS.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
    "C:\\Windows\\Fonts\\arialbd.ttf",  # Windows
]


def _find_font() -> str:
    """Return the first available font path."""
    for candidate in FONT_CANDIDATES:
        if os.path.isfile(candidate):
            return candidate
    return ""


def main() -> None:
    font_path = _find_font()
    if font_path:
        print(f"Font: {font_path}")
    else:
        print("WARNING: No Cyrillic font found, using PIL default")

    img = _pil_image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = _pil_draw.Draw(img)

    # Load font
    if font_path:
        font = _pil_font.truetype(font_path, FONT_SIZE)
    else:
        font = _pil_font.load_default()

    # Draw brand text centered horizontally, upper third (~y=80)
    bbox = draw.textbbox((0, 0), BRAND_TEXT, font=font)
    text_w = bbox[2] - bbox[0]
    x = (WIDTH - text_w) / 2 - bbox[0]
    y = 80 - bbox[1]
    draw.text((x, y), BRAND_TEXT, fill=FG_COLOR, font=font)

    # Subtle thin white line below the icon area (y=320)
    line_y = 320
    line_margin = 150
    line_color = (255, 255, 255, 80)  # subtle white
    # Use RGBA for alpha support, then convert back
    overlay = _pil_image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    overlay_draw = _pil_draw.Draw(overlay)
    overlay_draw.line(
        [(line_margin, line_y), (WIDTH - line_margin, line_y)],
        fill=line_color,
        width=1,
    )
    img_rgba = img.convert("RGBA")
    img_rgba = _pil_image.alpha_composite(img_rgba, overlay)
    img = img_rgba.convert("RGB")

    out_path = ASSETS_DIR / "dmg_background.png"
    img.save(str(out_path), "PNG")
    print(f"  -> {out_path}")
    print("Done!")


if __name__ == "__main__":
    main()
