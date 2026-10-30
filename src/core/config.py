"""
Konfigurasi Inti Aplikasi Bel Otomatis Sekolah
Menangani penentuan direktori data persisten Windows, aset aplikasi, dan konstanta sistem.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Nama aplikasi dan organisasi
APP_NAME = "BelOtomatisSekolah"
APP_DISPLAY_NAME = "Bel Otomatis Sekolah"
APP_VERSION = "1.2.2"

# Hari operasional sekolah (Senin - Sabtu)
DAYS_OF_WEEK = (
    "Senin",
    "Selasa",
    "Rabu",
    "Kamis",
    "Jumat",
    "Sabtu",
)

def get_app_dir() -> Path:
    """
    Mengembalikan direktori root aplikasi (mendukung mode development, PyInstaller onedir, maupun onefile).
    """
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS)
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent


def get_user_data_dir() -> Path:
    """
    Mengembalikan direktori penyimpanan data pengguna Windows yang persisten.
    Menggunakan %APPDATA%/BelOtomatisSekolah agar aman dari penimpaan saat update/instalasi ulang.
    Dapat dioverride via variabel lingkungan BEL_APP_DATA_DIR (berguna untuk isolated testing).
    """
    env_override = os.environ.get("BEL_APP_DATA_DIR")
    if env_override:
        path = Path(env_override)
    else:
        app_data = os.environ.get("APPDATA")
        if app_data:
            path = Path(app_data) / APP_NAME
        else:
            path = Path.home() / f".{APP_NAME.lower()}"

    path.mkdir(parents=True, exist_ok=True)
    return path


def get_db_path() -> Path:
    """Mengembalikan path file database SQLite persisten."""
    user_dir = get_user_data_dir()
    data_dir = user_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "bel_sekolah.db"


def get_audio_storage_dir() -> Path:
    """Mengembalikan direktori penyimpanan file audio bel persisten."""
    audio_dir = get_user_data_dir() / "sounds"
    audio_dir.mkdir(parents=True, exist_ok=True)
    return audio_dir


def get_assets_dir() -> Path:
    """Mengembalikan direktori aset aplikasi (ikon, audio bawaan, dll)."""
    if getattr(sys, "frozen", False):
        exe_assets = Path(sys.executable).parent / "assets"
        if exe_assets.exists():
            return exe_assets
    return get_app_dir() / "assets"
