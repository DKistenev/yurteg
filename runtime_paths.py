"""Helpers for resolving bundled resources in source and frozen builds."""

from __future__ import annotations

import sys
from pathlib import Path


def get_bundle_root() -> Path:
    """Return the base directory that contains bundled app resources."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_resource_path(*parts: str) -> Path:
    """Return an absolute path to a bundled resource."""
    return get_bundle_root().joinpath(*parts)
