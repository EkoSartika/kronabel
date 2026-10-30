# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Specification File untuk Bel Otomatis Sekolah (Windows 10 & Windows 11 64-bit)
Konfigurasi: Python 3.11 + PySide6 (Qt 6)
Mode: onedir (Folder Distribusi Standalone untuk Inno Setup Installer & Paket Portable)
"""

import os
import sys
from pathlib import Path

block_cipher = None

BASE_DIR = Path(SPECPATH).resolve()

# Aset runtime yang diperlukan (Seluruh berkas gambar & suara bawaan di folder assets)
added_datas = [
    (str(BASE_DIR / 'assets'), 'assets'),
]

# Hidden imports yang dibutuhkan aplikasi pada Python 3.11 + PySide6
hidden_imports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtNetwork',
    'PySide6.QtMultimedia',
    'sqlite3',
    'hashlib',
    'zipfile',
    'json',
    'logging',
    'winreg',
    'ctypes',
    'ctypes.wintypes',
]

a = Analysis(
    [str(BASE_DIR / 'main.py')],
    pathex=[str(BASE_DIR)],
    binaries=[],
    datas=added_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'pytest',
        'scipy',
        'matplotlib',
        'numpy',
        'pandas',
        'tests',
        'PySide2',
        'shiboken2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BelOtomatisSekolah',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # Aplikasi GUI Windows tanpa konsol hitam
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(BASE_DIR / 'assets' / 'app_icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='BelOtomatisSekolah',
)
