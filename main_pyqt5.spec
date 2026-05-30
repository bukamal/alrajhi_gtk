# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_all

# جمع بيانات ومكتبات pyzbar
pyzbar_datas, pyzbar_binaries, pyzbar_hiddenimports = collect_all('pyzbar')

# مسار Qt platforms (للتأكد من وجود qwindows.dll)
try:
    import PyQt5
    qt_platforms_path = os.path.join(os.path.dirname(PyQt5.__file__), 'Qt5', 'plugins', 'platforms')
except:
    qt_platforms_path = ''

a = Analysis(
    ['main_pyqt5.py'],
    pathex=[],
    binaries=pyzbar_binaries + [
        ('libiconv.dll', '.'),
        ('libzbar-64.dll', '.'),
    ],
    datas=pyzbar_datas + [(qt_platforms_path, 'platforms')] if os.path.exists(qt_platforms_path) else pyzbar_datas,
    hiddenimports=['decimal', 'sqlite3', 'cryptography'] + pyzbar_hiddenimports,
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
    console=False,           # يمنع ظهور نافذة طرفية
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='alrajhi_icon.ico',
)
