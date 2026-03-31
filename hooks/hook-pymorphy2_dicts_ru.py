"""Runtime hook: make pymorphy2 find dicts in frozen (PyInstaller) mode.

pymorphy2 discovers dictionaries via entry_points('pymorphy2_dicts'),
which don't work in frozen mode. We set the PYMORPHY2_DICT_PATH env var
to point directly to the bundled dictionary data.
"""
import os
import sys

if getattr(sys, "frozen", False):
    _meipass = getattr(sys, "_MEIPASS", "")
    os.environ["PYMORPHY2_DICT_PATH"] = os.path.join(
        _meipass, "pymorphy2_dicts_ru", "data"
    )
