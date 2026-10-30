"""
Utilitas Kompatibilitas Windows 7 (NT 6.1) — Windows 11.
Menangani:
1. Deteksi versi OS Windows (Windows 7/8 vs Windows 10/11) dan status DWM Composition (Aero).
2. Konfigurasi grafis OpenGL Software Fallback & DPI Scaling agar Qt berjalan mulus di GPU lama Windows 7.
3. Pemutaran audio native Windows MCI (winmm.dll) sebagai fallback/alternatif yang mendukung penuh MP3 & WAV di Windows 7 SP1.
"""

from __future__ import annotations

import ctypes
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def is_windows_7_or_8() -> bool:
    """Mengembalikan True jika berjalan di Windows 7 (6.1), Windows 8 (6.2), atau Windows 8.1 (6.3)."""
    if sys.platform != "win32":
        return False
    try:
        ver = sys.getwindowsversion()
        return ver.major == 6 and ver.minor in (1, 2, 3)
    except Exception:
        return False


def is_dwm_composition_enabled() -> bool:
    """
    Memeriksa apakah Desktop Window Manager (DWM / Aero Glass) aktif.
    Pada Windows 7 Basic / Classic Theme, DWM tidak aktif sehingga WA_TranslucentBackground
    akan menghasilkan latar belakang hitam pekat jika tidak ditangani.
    """
    if sys.platform != "win32":
        return True
    try:
        dwmapi = ctypes.windll.dwmapi
        enabled = ctypes.c_int(0)
        res = dwmapi.DwmIsCompositionEnabled(ctypes.byref(enabled))
        if res == 0:
            return bool(enabled.value)
        return False
    except Exception:
        # Jika dwmapi tidak tersedia, anggap komposisi tidak aktif
        return False


def configure_windows_7_environment() -> None:
    """
    Mengatur variabel lingkungan Qt sebelum QApplication dibuat agar kompatibel
    dengan Windows 7 SP1, kartu grafis lama (DirectX 9/10 / Tanpa WDDM 2.0), dan DPI klasik.
    """
    if sys.platform != "win32":
        return

    # Gunakan High-DPI scaling yang aman untuk berbagai versi Windows
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

    if is_windows_7_or_8():
        # Pada Windows 7/8, gunakan software OpenGL / GDI fallback jika driver GPU tidak mendukung Direct3D 11 penuh
        os.environ.setdefault("QT_OPENGL", "software")
        os.environ.setdefault("QT_ANGLE_PLATFORM", "d3d9")
        os.environ.setdefault("QT_QPA_PLATFORM", "windows:fontengine=gdi")
        logger.info("Mode kompatibilitas grafis Windows 7/8 diaktifkan.")


class WinMMPlayer:
    """
    Pemutar Audio berbasis Windows Multimedia API (winmm.dll mciSendStringW).
    Mendukung penuh MP3 dan WAV secara native sejak Windows XP / Windows 7 / 8 / 10 / 11
    tanpa ketergantungan pada Windows 10 Media Foundation yang sering gagal di Windows 7.
    """

    ALIAS = "BelSekolahMCI"

    def __init__(self) -> None:
        self._volume: int = 80
        self._is_open: bool = False

    def _mci_send(self, command: str) -> tuple[int, str]:
        if sys.platform != "win32":
            return -1, "Not Windows"
        try:
            buf = ctypes.create_unicode_buffer(512)
            err = ctypes.windll.winmm.mciSendStringW(command, buf, 511, 0)
            return int(err), buf.value
        except Exception as e:
            return -1, str(e)

    def play(self, file_path: str | Path, volume: int = 80) -> bool:
        """Membuka dan memutar berkas MP3/WAV menggunakan MCI."""
        self.stop()
        path_str = str(Path(file_path).resolve())
        ext = Path(path_str).suffix.lower()
        dev_type = "mpegvideo" if ext == ".mp3" else "waveaudio"

        err, _ = self._mci_send(f'open "{path_str}" type {dev_type} alias {self.ALIAS}')
        if err != 0:
            # Coba buka tanpa spesifikasi tipe agar MCI mendeteksi otomatis
            err, _ = self._mci_send(f'open "{path_str}" alias {self.ALIAS}')
            if err != 0:
                logger.error("WinMM MCI gagal membuka file %s (kode %d)", path_str, err)
                return False

        self._is_open = True
        self.set_volume(volume)

        err, _ = self._mci_send(f"play {self.ALIAS} from 0")
        if err != 0:
            logger.error("WinMM MCI gagal memutar file %s (kode %d)", path_str, err)
            self.stop()
            return False

        return True

    def set_volume(self, volume: int) -> None:
        """Mengatur volume MCI (skala 0 - 100 dikonversi ke 0 - 1000)."""
        self._volume = max(0, min(100, volume))
        if self._is_open:
            mci_vol = self._volume * 10
            self._mci_send(f"setaudio {self.ALIAS} volume to {mci_vol}")

    def is_playing(self) -> bool:
        """Memeriksa apakah MCI masih dalam status 'playing'."""
        if not self._is_open:
            return False
        err, mode = self._mci_send(f"status {self.ALIAS} mode")
        if err != 0:
            return False
        return mode.strip().lower() == "playing"

    def is_stopped_naturally(self) -> bool:
        """Memeriksa apakah pemutaran telah selesai mencapai akhir lagu ('stopped')."""
        if not self._is_open:
            return False
        err, mode = self._mci_send(f"status {self.ALIAS} mode")
        if err != 0:
            return True
        return mode.strip().lower() == "stopped"

    def stop(self) -> None:
        """Menghentikan dan menutup sesi MCI."""
        if self._is_open:
            self._mci_send(f"stop {self.ALIAS}")
            self._mci_send(f"close {self.ALIAS}")
            self._is_open = False

