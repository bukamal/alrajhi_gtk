@echo off
echo Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo Building executable with PyInstaller...
pyinstaller --hidden-import decimal --hidden-import sqlite3 --hidden-import cryptography --hidden-import pyzbar.pyzbar --hidden-import cv2 --onefile --windowed --name AlrajhiAccounting main_pyqt5.py

echo Build complete. Executable is in dist\AlrajhiAccounting.exe
pause
