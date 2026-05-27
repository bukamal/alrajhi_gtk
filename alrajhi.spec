# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main_pyqt5.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('data', 'data'),                     # مجلد البيانات (سيتم إنشاؤه عند التشغيل)
        ('views_pyqt5', 'views_pyqt5'),       # ملفات الواجهات
        ('alrajhi_icon.ico', '.'),            # أيقونة التطبيق
        ('alrajhi_logo.png', '.'),            # شعار التطبيق
        ('activation.py', '.'),
        ('auth.py', '.'),
        ('config.py', '.'),
        ('database.py', '.'),
        ('utils_pyqt5.py', '.'),
        ('login_dialog_pyqt5.py', '.'),
        ('activation_dialog_pyqt5.py', '.'),
        ('splash_screen.py', '.'),
        ('welcome_screen.py', '.'),
    ],
    hiddenimports=[
        'PyQt5.sip',
        'qt_material',
        'cryptography',
        'cryptography.hazmat.backends.openssl',
        'cryptography.hazmat.primitives',
        'requests',
        'openpyxl',
        'pyqtgraph',
        'qtawesome',
        'pysqlite2',
    ],
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
    name='AlrajhiAccounting',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # لا نافذة سوداء (GUI فقط)
    icon='alrajhi_icon.ico',
    version='1.0.0.0',
)
