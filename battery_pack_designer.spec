# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_root = Path.cwd()
package_root = project_root / "src" / "battery_pack_designer"

datas = [
    (str(package_root / "templates"), "battery_pack_designer/templates"),
    (str(package_root / "static"), "battery_pack_designer/static"),
]

hiddenimports = [
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
]


a = Analysis(
    ["src/battery_pack_designer/desktop/app.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="BatteryPackDesigner",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
