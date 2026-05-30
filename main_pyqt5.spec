# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main_pyqt5.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['decimal', 'sqlite3', 'cryptography', 'pyzbar.pyzbar', 'cv2'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AlrajhiAccounting',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='alrajhi_icon.ico',
)
