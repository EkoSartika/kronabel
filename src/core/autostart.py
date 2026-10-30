"""
Modul Utilitas Windows Autostart & Manajemen Startup Bel Otomatis Sekolah.
Mengelola integrasi pendaftaran autostart ke Windows HKCU Run Registry sehingga
aplikasi otomatis berjalan saat komputer/laptop dinyalakan atau login pengguna.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

RUN_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "BelOtomatisSekolah"


def get_recommended_autostart_command() -> str:
    """
    Menghasilkan string perintah eksekusi yang optimal untuk autostart Windows.
    - Mode rilis terkompilasi (PyInstaller): Menggunakan path executable biner mandiri.
    - Mode lingkungan development: Memprioritaskan executable dist jika ada,
      atau menggunakan pythonw.exe (tanpa console window) jika tersedia.
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'

    base_dir = Path(__file__).resolve().parent.parent.parent
    dist_exe = base_dir / "dist" / "BelOtomatisSekolah" / "BelOtomatisSekolah.exe"
    if dist_exe.exists():
        return f'"{dist_exe}"'

    py_exe = Path(sys.executable)
    pythonw_candidate = py_exe.with_name("pythonw.exe")
    exec_to_use = str(pythonw_candidate) if pythonw_candidate.exists() else str(py_exe)
    main_py = base_dir / "main.py"
    return f'"{exec_to_use}" "{main_py}"'


def is_windows_autostart_enabled() -> bool:
    """Memeriksa apakah registri autostart Windows aktif untuk aplikasi ini."""
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0, winreg.KEY_READ) as key:
            try:
                val, _ = winreg.QueryValueEx(key, APP_REG_NAME)
                return bool(val and str(val).strip())
            except FileNotFoundError:
                return False
    except Exception as e:
        logger.warning("Gagal membaca registry Windows autostart: %s", e)
        return False


def set_windows_autostart(enable: bool, command: Optional[str] = None) -> bool:
    """
    Mengatur autostart Windows via HKCU Run registry.
    
    Args:
        enable: True untuk mendaftarkan ke startup Windows, False untuk menghapus.
        command: String perintah opsional. Jika None, menggunakan perintah default yang direkomendasikan.
    
    Returns:
        True jika berhasil, False jika gagal.
    """
    if sys.platform != "win32":
        return False
    try:
        import winreg

        if enable:
            exe_cmd = command or get_recommended_autostart_command()
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, exe_cmd)
                logger.info("Autostart Windows diaktifkan dengan perintah: %s", exe_cmd)
        else:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, APP_REG_NAME)
                    logger.info("Autostart Windows dinonaktifkan.")
            except FileNotFoundError:
                pass
        return True
    except Exception as e:
        logger.error("Gagal mengubah registry Windows autostart: %s", e)
        return False
