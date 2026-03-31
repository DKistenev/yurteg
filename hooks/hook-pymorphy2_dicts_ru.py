"""Runtime hook: patch pymorphy2_dicts_ru.get_path() for frozen mode."""
import importlib
import os
import sys


def _patched_get_path() -> str:
    """Return correct path to dictionary data in frozen (PyInstaller) mode."""
    if getattr(sys, "frozen", False):
        meipass: str = getattr(sys, "_MEIPASS", "")
        return os.path.join(meipass, "pymorphy2_dicts_ru", "data")
    mod = importlib.import_module("pymorphy2_dicts_ru")
    return os.path.join(os.path.dirname(mod.__file__ or ""), "data")


_dicts_mod = importlib.import_module("pymorphy2_dicts_ru")
setattr(_dicts_mod, "get_path", _patched_get_path)
