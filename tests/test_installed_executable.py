"""
Pengujian Terhadap Paket Distribusi Resmi Windows 10 & Windows 11 (v1.2.0):
1. BelOtomatisSekolah_Setup_v1.2.0.exe
2. BelOtomatisSekolah_Portable_v1.2.0.zip
3. Executable hasil instalasi Inno Setup di test_isolated_install
"""

from __future__ import annotations

import os
import subprocess
import time
import zipfile
from pathlib import Path
import pytest

SETUP_EXE_124 = Path("D:/BelOtomatisSekolah/release/KRONABEL_Setup_v1.2.4.exe")
PORTABLE_ZIP_124 = Path("D:/BelOtomatisSekolah/release/KRONABEL_Portable_v1.2.4.zip")
SETUP_EXE_123 = Path("D:/BelOtomatisSekolah/release/BelOtomatisSekolah_Setup_v1.2.3.exe")
PORTABLE_ZIP_123 = Path("D:/BelOtomatisSekolah/release/BelOtomatisSekolah_Portable_v1.2.3.zip")
SETUP_EXE_122 = Path("D:/BelOtomatisSekolah/release/BelOtomatisSekolah_Setup_v1.2.2.exe")
PORTABLE_ZIP_122 = Path("D:/BelOtomatisSekolah/release/BelOtomatisSekolah_Portable_v1.2.2.zip")

SETUP_EXE = SETUP_EXE_124 if SETUP_EXE_124.exists() else (SETUP_EXE_123 if SETUP_EXE_123.exists() else SETUP_EXE_122)
PORTABLE_ZIP = PORTABLE_ZIP_124 if PORTABLE_ZIP_124.exists() else (PORTABLE_ZIP_123 if PORTABLE_ZIP_123.exists() else PORTABLE_ZIP_122)
INSTALLED_EXE = Path("D:/BelOtomatisSekolah/test_isolated_install/KRONABEL.exe") if Path("D:/BelOtomatisSekolah/test_isolated_install/KRONABEL.exe").exists() else Path("D:/BelOtomatisSekolah/test_isolated_install/BelOtomatisSekolah.exe")


def test_release_packages_exist_and_non_empty():
    """Memastikan paket rilis resmi v1.2.0 (Setup EXE & Portable ZIP) tersedia untuk Windows 10/11."""
    if not SETUP_EXE.exists() or not PORTABLE_ZIP.exists():
        pytest.skip("Paket rilis v1.2.0 belum dibuat.")
    for pkg in (SETUP_EXE, PORTABLE_ZIP):
        assert pkg.exists(), f"Paket rilis tidak ditemukan: {pkg}"
        assert pkg.stat().st_size > 20_000_000, f"Ukuran paket rilis tidak wajar (<20 MB): {pkg}"


def test_extracted_portable_zip_launch(tmp_path: Path):
    """Mengekstrak paket Portable ZIP v1.2.0 ke direktori terisolasi dan menguji peluncurannya."""
    if not PORTABLE_ZIP.exists():
        pytest.skip(f"Paket Portable ZIP belum tersedia: {PORTABLE_ZIP}")

    extract_dir = tmp_path / "extracted_portable"
    with zipfile.ZipFile(PORTABLE_ZIP, "r") as zf:
        zf.extractall(extract_dir)

    exe_candidates = [
        extract_dir / "KRONABEL" / "KRONABEL.exe",
        extract_dir / "BelOtomatisSekolah" / "BelOtomatisSekolah.exe",
    ]
    exe_path = next((p for p in exe_candidates if p.exists()), exe_candidates[0])
    app_folder = exe_path.parent
    assert exe_path.exists(), f"Executable tidak ditemukan setelah ekstraksi ZIP: {exe_path}"
    assert (app_folder / "_internal" / "python311.dll").exists()
    assert not (app_folder / "python38.dll").exists()

    isolated_data_dir = tmp_path / "portable_appdata"
    isolated_data_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["BEL_APP_DATA_DIR"] = str(isolated_data_dir)
    env["QT_QPA_PLATFORM"] = "offscreen"

    time.sleep(1.0)

    proc = subprocess.Popen(
        [str(exe_path)],
        cwd=str(tmp_path),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        expected_db = isolated_data_dir / "data" / "bel_sekolah.db"
        log_file = isolated_data_dir / "app.log"

        for _ in range(80):
            if (
                expected_db.exists()
                and log_file.exists()
                and "Database berhasil diinisialisasi" in log_file.read_text(encoding="utf-8", errors="ignore")
            ):
                break
            time.sleep(0.1)

        poll_res = proc.poll()
        assert poll_res is None, f"Executable portable berhenti mendadak dengan kode: {poll_res}"
        assert expected_db.exists(), "Database tidak terinisialisasi di folder terisolasi"

        log_text = log_file.read_text(encoding="utf-8")
        assert "Memulai aplikasi" in log_text
        assert "Database berhasil diinisialisasi" in log_text
        seeded_sounds = list((isolated_data_dir / "sounds").glob("*.mp3"))
        assert len(seeded_sounds) >= 15, f"File audio bawaan gagal disalin: {len(seeded_sounds)}"

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        time.sleep(1.5)


def test_installed_executable_launch(tmp_path: Path):
    """Menguji peluncuran BelOtomatisSekolah.exe hasil instalasi Inno Setup."""
    if not INSTALLED_EXE.exists():
        pytest.skip(f"Executable hasil instalasi tidak ditemukan di: {INSTALLED_EXE}")
    assert INSTALLED_EXE.stat().st_size > 1_000_000

    isolated_data_dir = tmp_path / "installed_appdata"
    isolated_data_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["BEL_APP_DATA_DIR"] = str(isolated_data_dir)
    env["QT_QPA_PLATFORM"] = "offscreen"

    time.sleep(1.0)

    proc = subprocess.Popen(
        [str(INSTALLED_EXE)],
        cwd=str(tmp_path),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        expected_db = isolated_data_dir / "data" / "bel_sekolah.db"
        log_file = isolated_data_dir / "app.log"

        for _ in range(80):
            if (
                expected_db.exists()
                and log_file.exists()
                and "Database berhasil diinisialisasi" in log_file.read_text(encoding="utf-8", errors="ignore")
            ):
                break
            time.sleep(0.1)

        poll_res = proc.poll()
        assert poll_res is None, f"Executable hasil instalasi berhenti mendadak dengan kode: {poll_res}"
        assert expected_db.exists(), "Database tidak terinisialisasi di folder terisolasi"

        log_text = log_file.read_text(encoding="utf-8")
        assert "Memulai aplikasi" in log_text
        assert "Database berhasil diinisialisasi" in log_text
        seeded_sounds = list((isolated_data_dir / "sounds").glob("*.mp3"))
        assert len(seeded_sounds) >= 15, f"File audio bawaan gagal disalin pada instalasi baru: {len(seeded_sounds)}"

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        time.sleep(1.5)
