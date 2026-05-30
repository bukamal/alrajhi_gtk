@echo off
echo Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo Copying pyzbar DLLs...
python -c "import pyzbar, os, shutil; src = os.path.join(os.path.dirname(pyzbar.__file__), 'libiconv.dll'); dest = '.'; shutil.copy(src, dest) if os.path.exists(src) else None"
python -c "import pyzbar, os, shutil; src = os.path.join(os.path.dirname(pyzbar.__file__), 'libzbar-64.dll'); dest = '.'; shutil.copy(src, dest) if os.path.exists(src) else None"

echo Building executable with PyInstaller...
pyinstaller --add-binary "libiconv.dll;." --add-binary "libzbar-64.dll;." --collect-all pyzbar --hidden-import decimal --hidden-import sqlite3 --hidden-import cryptography --onefile --windowed --name AlrajhiAccounting main_pyqt5.py

echo Build complete. Executable is in dist\AlrajhiAccounting.exe
pause
