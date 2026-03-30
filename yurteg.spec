# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


datas = [
    ("app/static", "app/static"),
    ("data", "data"),
]
datas += collect_data_files("natasha")
datas += collect_data_files("pymorphy2")
datas += collect_data_files("pymorphy2_dicts_ru")
datas += collect_data_files("sentence_transformers")

hiddenimports = []
hiddenimports += collect_submodules("natasha")
hiddenimports += collect_submodules("pymorphy2")
hiddenimports += collect_submodules("sentence_transformers")
hiddenimports += collect_submodules("huggingface_hub")


a = Analysis(
    ["app/main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="YurTag",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="assets/icon.ico",
)

app = BUNDLE(
    exe,
    name="YurTag.app",
    icon=None,
    bundle_identifier="com.yurteg.desktop",
)
