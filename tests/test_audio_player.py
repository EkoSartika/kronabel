"""
Pengujian Unit Layanan Pemutar Audio (Tahap 3).
Menguji impor file MP3/WAV, penanganan file hilang, format tidak didukung,
kontrol volume, dan penanganan status playback.
"""

from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from src.database.db import DatabaseManager
from src.services.audio_player import AudioPlayer, AudioStatus

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def create_dummy_wav(path: Path) -> Path:
    """Membuat file WAV PCM mono 1 detik yang valid."""
    sample_rate = 8000
    num_samples = 4000
    data_size = num_samples * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sample_rate,
        sample_rate * 2,
        2,
        16,
        b"data",
        data_size,
    )
    path.write_bytes(header + (b"\x00\x00" * num_samples))
    return path


def test_import_audio_file_success(qapp, temp_db: DatabaseManager, tmp_path: Path):
    """Menguji impor file audio WAV ke penyimpanan persisten dan registrasi di database."""
    player = AudioPlayer(temp_db)
    src_wav = create_dummy_wav(tmp_path / "bel_masuk.wav")

    imported = player.import_audio_file(src_wav, custom_name="Bel Masuk Utama")
    assert imported.id is not None
    assert imported.name == "Bel Masuk Utama"
    assert imported.original_filename == "bel_masuk.wav"
    assert Path(imported.stored_path).exists()


def test_import_audio_file_not_found(qapp, temp_db: DatabaseManager, tmp_path: Path):
    """Menguji penanganan ketika file audio yang akan diimpor tidak ada."""
    player = AudioPlayer(temp_db)
    non_existent = tmp_path / "ghost_sound.mp3"
    with pytest.raises(FileNotFoundError):
        player.import_audio_file(non_existent)


def test_import_unsupported_format(qapp, temp_db: DatabaseManager, tmp_path: Path):
    """Menguji penolakan file dengan format yang tidak didukung."""
    player = AudioPlayer(temp_db)
    txt_file = tmp_path / "document.txt"
    txt_file.write_text("bukan audio")

    with pytest.raises(ValueError, match="tidak didukung"):
        player.import_audio_file(txt_file)


def test_play_file_not_found(qapp, temp_db: DatabaseManager, tmp_path: Path):
    """Menguji bahwa pemutaran file yang tidak ada memicu status FAILED."""
    player = AudioPlayer(temp_db)
    failed_messages = []
    player.playback_failed.connect(lambda err: failed_messages.append(err))

    success = player.play_file(tmp_path / "missing.wav", title="Bel Hilang")
    assert success is False
    assert player.status == AudioStatus.FAILED
    assert len(failed_messages) == 1
    assert "tidak ditemukan" in failed_messages[0]


def test_volume_control(qapp, temp_db: DatabaseManager):
    """Menguji batas kontrol volume 0 - 100."""
    player = AudioPlayer(temp_db)
    player.set_volume(50)
    assert player.get_volume() == 50

    # Uji batas atas
    player.set_volume(150)
    assert player.get_volume() == 100

    # Uji batas bawah
    player.set_volume(-20)
    assert player.get_volume() == 0


def test_audio_concurrency_lock(qapp, temp_db: DatabaseManager, tmp_path: Path):
    """Menguji kebijakan interupsi default (interrupt=True) dan penolakan eksplisit (interrupt=False)."""
    player = AudioPlayer(temp_db)
    wav_file = create_dummy_wav(tmp_path / "bel1.wav")
    wav_file_2 = create_dummy_wav(tmp_path / "bel2.wav")

    # 1. Putar audio pertama
    assert player.play_file(wav_file, title="Bel 1") is True
    assert player.status == AudioStatus.PLAYING
    assert player.current_title == "Bel 1"

    # 2. Jika interrupt=False diminta secara eksplisit, pemutaran kedua ditolak
    rejected_attempt = player.play_file(wav_file_2, title="Bel 2", interrupt=False)
    assert rejected_attempt is False
    assert player.current_title == "Bel 1"

    # 3. Default (interrupt=True) menghentikan Bel 1 dan langsung memainkan Bel 2
    interrupted_attempt = player.play_file(wav_file_2, title="Bel 2")
    assert interrupted_attempt is True
    assert player.status == AudioStatus.PLAYING
    assert player.current_title == "Bel 2"
    player.cleanup()


def test_stop_and_cleanup(qapp, temp_db: DatabaseManager):
    """Menguji penghentian audio dan status interrupted saat cleanup."""
    player = AudioPlayer(temp_db)
    player.status = AudioStatus.PLAYING
    player.current_title = "Bel Sedang Berbunyi"

    player.stop()
    assert player.status == AudioStatus.INTERRUPTED

    # Cleanup saat playing
    player.status = AudioStatus.PLAYING
    player.cleanup()
    assert player.status == AudioStatus.INTERRUPTED


def test_audio_device_failure(qapp, temp_db: DatabaseManager, monkeypatch):
    """Menguji penanganan ketika perangkat audio output tidak tersedia."""
    from PySide6.QtMultimedia import QMediaDevices
    player = AudioPlayer(temp_db)

    # Simulasikan QMediaDevices tidak menemukan output device
    monkeypatch.setattr(QMediaDevices, "audioOutputs", lambda: [])
    assert player.has_audio_output_device() is False

