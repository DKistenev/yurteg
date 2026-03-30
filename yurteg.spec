# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import shutil
from pathlib import Path

# --- llama-server binary ---
_LLAMA_SRC = Path.home() / ".yurteg" / "llama-server"
_LLAMA_LOCAL = Path("llama-server")
if _LLAMA_SRC.exists() and not _LLAMA_LOCAL.exists():
    shutil.copy2(_LLAMA_SRC, _LLAMA_LOCAL)

binaries = []
if _LLAMA_LOCAL.exists():
    binaries.append((str(_LLAMA_LOCAL), "."))

# --- Data files ---
datas = [
    ("app/static", "app/static"),
    ("data", "data"),
    ("assets/icon_512.png", "assets"),
]
datas += collect_data_files("natasha")
datas += collect_data_files("pymorphy2")
datas += collect_data_files("pymorphy2_dicts_ru")
datas += collect_data_files("sentence_transformers")
datas += collect_data_files("pdfplumber")
datas += collect_data_files("nicegui")

# --- Hidden imports ---
hiddenimports = []
hiddenimports += collect_submodules("natasha")
hiddenimports += collect_submodules("pymorphy2")
hiddenimports += collect_submodules("sentence_transformers")
hiddenimports += collect_submodules("huggingface_hub")
hiddenimports += collect_submodules("pdfplumber")
hiddenimports += collect_submodules("logtail")
hiddenimports += collect_submodules("nicegui")
hiddenimports += collect_submodules("webview")


a = Analysis(
    ["app/main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "torch.cuda",
        "torch.distributed",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="YurTag",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="assets/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="YurTag",
)

app = BUNDLE(
    coll,
    name="YurTag.app",
    icon='assets/icon.icns',
    bundle_identifier="com.yurteg.desktop",
)
