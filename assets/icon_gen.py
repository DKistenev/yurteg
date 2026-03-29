# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow>=10.0"]
# ///
"""Generate YurTag app icon in all required formats.

Usage: python assets/icon_gen.py

Produces:
  assets/icon_512.png  — 512x512 source PNG
  assets/icon.ico      — Windows icon (16/32/128/256)
  assets/icon.icns     — macOS icon (via iconutil, macOS only)

Requires: pip install Pillow
"""

from __future__ import annotations

import importlib
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# Dynamic import — Pillow is a runtime dependency, not available in type-checker env
_pil_image: Any = importlib.import_module("PIL.Image")
_pil_draw: Any = importlib.import_module("PIL.ImageDraw")
_pil_font: Any = importlib.import_module("PIL.ImageFont")

# ── Config ────────────────────────────────────────────────────────────────────
BG_COLOR = (79, 70, 229)  # #4f46e5 — indigo-600
FG_COLOR = (255, 255, 255)  # white
LETTER = "\u042e"  # Ю
FONT_SIZE_RATIO = 0.70  # letter fills ~70% of icon dimension

ASSETS_DIR = Path(__file__).parent
SIZES = [16, 32, 64, 128, 256, 512]

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


def _make_icon(size: int, font_path: str) -> Any:
    """Create a single icon image at the given size."""
    img = _pil_image.new("RGBA", (size, size), BG_COLOR + (255,))
    draw = _pil_draw.Draw(img)

    font_size = max(int(size * FONT_SIZE_RATIO), 8)
    if font_path:
        font = _pil_font.truetype(font_path, font_size)
    else:
        font = _pil_font.load_default()

    # Center the letter using textbbox
    bbox = draw.textbbox((0, 0), LETTER, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) / 2 - bbox[0]
    y = (size - text_h) / 2 - bbox[1]
    draw.text((x, y), LETTER, fill=FG_COLOR, font=font)

    return img


def main() -> None:
    font_path = _find_font()
    if font_path:
        print(f"Font: {font_path}")
    else:
        print("WARNING: No Cyrillic font found, using PIL default")

    # Generate PNGs at all sizes
    images: dict[int, Any] = {}
    for size in SIZES:
        img = _make_icon(size, font_path)
        images[size] = img
        png_path = ASSETS_DIR / f"icon_{size}.png"
        img.save(str(png_path), "PNG")
        print(f"  {png_path.name} ({size}x{size})")

    # Save main 512px PNG
    icon_512 = ASSETS_DIR / "icon_512.png"
    images[512].save(str(icon_512), "PNG")
    print(f"  -> {icon_512}")

    # ── .ico (Windows) ────────────────────────────────────────────────────────
    ico_path = ASSETS_DIR / "icon.ico"
    ico_sizes = [(16, 16), (32, 32), (128, 128), (256, 256)]
    images[256].save(
        str(ico_path),
        format="ICO",
        sizes=ico_sizes,
        append_images=[images[s[0]] for s in ico_sizes[:-1]],
    )
    print(f"  -> {ico_path}")

    # ── .icns (macOS only) ────────────────────────────────────────────────────
    if platform.system() != "Darwin":
        print("  Skipping .icns (not macOS)")
        return

    iconset_dir = ASSETS_DIR / "icon.iconset"
    if iconset_dir.exists():
        shutil.rmtree(iconset_dir)
    iconset_dir.mkdir()

    # iconutil naming convention
    iconset_map = {
        "icon_16x16.png": 16,
        "icon_16x16@2x.png": 32,
        "icon_32x32.png": 32,
        "icon_32x32@2x.png": 64,
        "icon_128x128.png": 128,
        "icon_128x128@2x.png": 256,
        "icon_256x256.png": 256,
        "icon_256x256@2x.png": 512,
        "icon_512x512.png": 512,
    }
    for name, size in iconset_map.items():
        images[size].save(str(iconset_dir / name), "PNG")

    icns_path = ASSETS_DIR / "icon.icns"
    result = subprocess.run(
        ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(icns_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  iconutil error: {result.stderr}")
        sys.exit(1)

    # Cleanup iconset directory
    shutil.rmtree(iconset_dir)
    print(f"  -> {icns_path}")
    print("Done!")


if __name__ == "__main__":
    main()
