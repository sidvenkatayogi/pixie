# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files

# Collect data files from open_clip
datas = collect_data_files('open_clip')

# Add the assets folder
datas += [
    ('assets/Inter.ttc', 'assets'),
    ('assets/Pinterest-logo.png', 'assets'),
    ('assets/pixie.ico', 'assets')
]

a = Analysis(
    ['pixie.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['open_clip'],
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
    [],
    exclude_binaries=True,
    name='Pixie',
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
    icon='assets/pixie.ico'
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Pixie',
)
