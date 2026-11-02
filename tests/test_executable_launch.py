"""
Pengujian Verifikasi Runtime Executable Standalone (Windows 10 & Windows 11).
Menguji:
1. Executable D:\\BelOtomatisSekolah\\dist\\BelOtomatisSekolah\\BelOtomatisSekolah.exe dapat dijalankan.
2. Kemurnian dependensi Python 3.11 + PySide6 (bebas dari Python 3.8, PySide2, atau shiboken2).
3. Independensi CWD: Aplikasi dapat dijalankan dari working directory sembarang.
4. Pembuatan database, seeding 19 audio bawaan, dan log startup di lokasi data pengguna yang benar.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
import pytest

DIST_EXE_KRONABEL = Path("D:/BelOtomatisSekolah/dist/KRONABEL/KRONABEL.exe")
DIST_EXE_LEGACY = Path("D:/BelOtomatisSekolah/dist/BelOtomatisSekolah/BelOtomatisSekolah.exe")
DIST_EXE = DIST_EXE_KRONABEL if DIST_EXE_KRONABEL.exists() else DIST_EXE_LEGACY


def test_executable_exists_and_clean_win10_11_dependencies():
    """Memverifikasi bahwa file executable, struktur aset runtime, dan dependensi Python 3.11 + PySide6 murni."""
    if not DIST_EXE.exists():
        pytest.skip(f"Executable belum dibuild: {DIST_EXE}")

    assert DIST_EXE.stat().st_size > 500_000, "Ukuran executable terlalu kecil (<500 KB)."

    dist_dir = DIST_EXE.parent
    internal_dir = dist_dir / "_internal"
    assert (dist_dir / "assets" / "app_icon.png").exists()
    assert (dist_dir / "assets" / "app_icon.ico").exists()
    assert internal_dir.exists()
    assert (internal_dir / "python311.dll").exists(), "python311.dll harus ada di _internal"
    assert (internal_dir / "PySide6").exists(), "Direktori PySide6 harus ada di _internal"

    # Pastikan TIDAK ADA artefak Python 3.8 / PySide2 / shiboken2 / Qt5
    forbidden = ("python38.dll", "pyside2", "shiboken2", "qt5core.dll", "qt5gui.dll", "qt5widgets.dll")
    for item in dist_dir.rglob("*"):
        name_low = item.name.lower()
        assert not any(f in name_low for f in forbidden), (
            f"Ditemukan artefak Python 3.8/PySide2 di dalam build Windows 10/11: {item}"
        )


def test_executable_launch_and_clean_termination(tmp_path: Path):
    """
    Menjalankan BelOtomatisSekolah.exe dari direktori kerja sembarang (tmp_path),
    memastikan proses startup sukses, menulis log, dan berhenti dengan aman.
    """
    if not DIST_EXE.exists():
        pytest.skip("Executable belum dibuild.")

    isolated_user_dir = tmp_path / "appdata_test"
    isolated_user_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["BEL_APP_DATA_DIR"] = str(isolated_user_dir)
    env["QT_QPA_PLATFORM"] = "offscreen"

    time.sleep(1.0)

    proc = subprocess.Popen(
        [str(DIST_EXE)],
        cwd=str(tmp_path),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        expected_db = isolated_user_dir / "data" / "bel_sekolah.db"
        log_file = isolated_user_dir / "app.log"

        for _ in range(80):
            if (
                expected_db.exists()
                and log_file.exists()
                and "Database berhasil diinisialisasi" in log_file.read_text(encoding="utf-8", errors="ignore")
            ):
                break
            time.sleep(0.1)

        poll_res = proc.poll()
        assert poll_res is None, f"Aplikasi crash atau keluar mendadak dengan kode: {poll_res}"

        log_content = log_file.read_text(encoding="utf-8") if log_file.exists() else "NO_LOG"
        assert expected_db.exists(), f"Database tidak dibuat: {expected_db}. Log: {log_content}"
        assert "Memulai aplikasi" in log_content
        assert "Database berhasil diinisialisasi" in log_content
        seeded_sounds = list((isolated_user_dir / "sounds").glob("*.mp3"))
        assert len(seeded_sounds) >= 15, f"File audio bawaan gagal disalin ke folder data pengguna: {len(seeded_sounds)}"

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        time.sleep(1.5)
