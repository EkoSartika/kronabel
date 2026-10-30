"""
Pengujian Ketahanan Operasional, Perangkat Audio, dan Isolasi Lingkungan (Tahap 5).
Menguji:
1. Enumerasi perangkat audio Windows tanpa memodifikasi perangkat default sistem.
2. Penanganan berbagai format dan error path (karakter khusus, spasi, unicode).
3. Kebijakan pemutaran audio saat sibuk (reject vs interrupt).
4. Penanganan cleanup proses audio dan timer setelah shutdown/penutupan.
5. Independensi working directory (menjalankan operasi database dan path dari lokasi arbitrary).
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest
from PySide6.QtMultimedia import QMediaDevices

from src.core.config import get_user_data_dir, get_db_path, get_audio_storage_dir
from src.database.db import DatabaseManager
from src.database.repositories import AudioRepository, ProfileRepository, SettingsRepository
from src.models.models import AudioFile
from src.services.audio_player import AudioPlayer, AudioStatus
from src.services.scheduler import SchedulerService
from src.ui.main_window import MainWindow


def test_audio_device_enumeration_non_destructive():
    """
    Memverifikasi enumerasi perangkat audio Windows melalui QMediaDevices.
    Hanya membaca daftar perangkat dan default output device tanpa mengubah konfigurasi Windows.
    """
    outputs = QMediaDevices.audioOutputs()
    assert isinstance(outputs, list)

    default_device = QMediaDevices.defaultAudioOutput()
    assert default_device is not None
    # Pastikan nama perangkat dapat dibaca tanpa melempar exception
    device_description = default_device.description()
    assert isinstance(device_description, str)


def test_audio_player_busy_policy_handling(tmp_path: Path):
    """
    Menguji kepatuhan terhadap kebijakan saat pemutaran sedang berlangsung:
    - Default (Reject): Tolak audio baru saat audio lama berbunyi.
    - Interrupt: Menghentikan audio lama dan memutar audio baru secara terkontrol.
    """
    db_file = tmp_path / "busy_test.db"
    db = DatabaseManager(db_file)
    db.initialize_database()

    # Buat 2 file audio dummy
    audio_dir = tmp_path / "audio_busy"
    audio_dir.mkdir()
    f1 = audio_dir / "bell1.wav"
    f2 = audio_dir / "bell2.wav"
    wav_content = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00data\x00\x00\x00\x00"
    f1.write_bytes(wav_content)
    f2.write_bytes(wav_content)

    player = AudioPlayer(db)

    # 1. Putar audio pertama
    res1 = player.play_file(f1, title="Bel 1")
    assert res1 is True
    assert player.status == AudioStatus.PLAYING

    # 2. Coba putar audio kedua dengan kebijakan eksplisit interrupt=False (Reject)
    res2 = player.play_file(f2, title="Bel 2", interrupt=False)
    assert res2 is False  # Ditolak
    assert player.current_title == "Bel 1"

    # 3. Putar audio kedua dengan kebijakan default (interrupt=True): menginterupsi Bel 1 dan memutar Bel 2
    res_interrupt = player.play_file(f2, title="Bel 2")
    assert res_interrupt is True
    assert player.status == AudioStatus.PLAYING
    assert player.current_title == "Bel 2"

    # 4. Hentikan audio secara eksplisit (Stop)
    player.stop()
    assert player.status == AudioStatus.INTERRUPTED
    assert player.current_title == ""

    # 5. Pemutaran baru setelah Stop diizinkan
    res3 = player.play_file(f1, title="Bel 1 Ulang")
    assert res3 is True
    assert player.current_title == "Bel 1 Ulang"

    player.cleanup()


def test_audio_import_with_special_characters_and_spaces(tmp_path: Path, monkeypatch):
    """
    Menguji bahwa impor audio dengan nama file yang mengandung spasi, karakter tanda kurung,
    dan karakter khusus ditangani dengan aman tanpa kegagalan path.
    """
    db_file = tmp_path / "special_names.db"
    db = DatabaseManager(db_file)
    db.initialize_database()

    storage_dir = tmp_path / "safe_storage"
    storage_dir.mkdir()
    monkeypatch.setattr("src.services.audio_player.get_audio_storage_dir", lambda: storage_dir)

    source_file = tmp_path / "Bel Masuk (Pagi & Upacara) #1 [Final].mp3"
    source_file.write_bytes(b"FAKE_MP3_DATA_HEADER")

    player = AudioPlayer(db)
    imported = player.import_audio_file(source_file, custom_name="Bel Upacara (Khusus)")

    assert imported.id is not None
    assert imported.name == "Bel Upacara (Khusus)"
    assert Path(imported.stored_path).exists()
    assert Path(imported.stored_path).parent == storage_dir


def test_working_directory_independence(tmp_path: Path, monkeypatch):
    """
    Menguji bahwa modul database dan konfigurasi bekerja secara independen
    meskipun working directory (cwd) dipindah ke folder arbitrary.
    """
    orig_cwd = os.getcwd()
    sub_dir = tmp_path / "some_other_folder"
    sub_dir.mkdir()

    try:
        os.chdir(str(sub_dir))
        # Panggil fungsi resolusi path konfigurasi
        user_dir = get_user_data_dir()
        db_path = get_db_path()
        audio_dir = get_audio_storage_dir()

        assert user_dir.is_absolute()
        assert db_path.is_absolute()
        assert audio_dir.is_absolute()

        # Database manager dapat diinisialisasi tanpa ketergantungan cwd
        db = DatabaseManager(tmp_path / "cwd_test.db")
        db.initialize_database()
        prof_repo = ProfileRepository(db)
        assert prof_repo.get_active() is not None
    finally:
        os.chdir(orig_cwd)


def test_cleanup_and_resource_release_on_close(qapp, tmp_path: Path):
    """
    Menguji bahwa SchedulerService dan AudioPlayer melepaskan timer dan file lock secara aman saat ditutup.
    """
    db_file = tmp_path / "cleanup_test.db"
    db = DatabaseManager(db_file)
    db.initialize_database()

    player = AudioPlayer(db)
    scheduler = SchedulerService(db, player)

    scheduler.start()
    assert scheduler.is_active is True
    assert scheduler._timer.isActive() is True

    # Panggil stop & cleanup
    scheduler.stop()
    assert scheduler.is_active is False
    assert scheduler._timer.isActive() is False

    player.cleanup()
    assert player.status in (AudioStatus.IDLE, AudioStatus.INTERRUPTED)
