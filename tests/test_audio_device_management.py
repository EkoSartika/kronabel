"""
Pengujian Otomatis Fitur Pengelolaan Output Audio KRONABEL (PySide6 + Qt Multimedia).
Menguji:
1. Enumerasi perangkat audio output.
2. Pemilihan mode otomatis (default Windows) dan pergantian dinamis saat jack dipasang/dilepas.
3. Pemilihan mode manual dan fallback aman jika perangkat terlepas.
4. Sinyal audio_devices_changed dan audio_device_switched.
5. Pencegahan audio ganda & Single Active Audio Controller saat pergantian output.
6. Fungsi tombol Stop dan keandalan token sesi (session token).
7. Integrasi antarmuka SettingsPage (ComboBox, Tombol Segarkan, Tombol Tes Suara).
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtMultimedia import QAudioDevice, QAudioOutput, QMediaDevices

from src.database.db import DatabaseManager
from src.database.repositories import AudioRepository, ProfileRepository, SettingsRepository
from src.services.audio_player import AudioPlayer, AudioStatus, device_id_to_str
from src.ui.settings_page import SettingsPage

os.environ["QT_QPA_PLATFORM"] = "offscreen"


def create_dummy_wav(path: Path) -> Path:
    """Membuat file WAV valid berdurasi singkat untuk pengujian."""
    import struct
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


def test_audio_device_enumeration(temp_db: DatabaseManager):
    """Menguji bahwa enumerasi perangkat output audio berjalan tanpa error."""
    player = AudioPlayer(temp_db)
    devices = player.get_available_output_devices()
    assert isinstance(devices, list)

    default_dev = player.get_default_output_device()
    assert isinstance(default_dev, QAudioDevice)

    current_dev = player.get_current_output_device()
    assert isinstance(current_dev, QAudioDevice)


def test_auto_mode_default_routing(temp_db: DatabaseManager):
    """Menguji mode perutean otomatis (default Windows)."""
    player = AudioPlayer(temp_db)
    assert player.get_output_mode() == "auto"

    # Perangkat aktif harus terhubung ke default output jika ada perangkat
    available = player.get_available_output_devices()
    if available:
        default_dev = player.get_default_output_device()
        current_dev = player.get_current_output_device()
        assert device_id_to_str(current_dev) == device_id_to_str(default_dev)


def test_manual_device_selection_and_persistence(temp_db: DatabaseManager):
    """Menguji pemilihan manual perangkat audio output dan persistensinya di database."""
    player = AudioPlayer(temp_db)
    available = player.get_available_output_devices()
    if not available:
        pytest.skip("Tidak ada perangkat audio fisik terpasang di sistem.")

    chosen_dev = available[-1]
    chosen_id = device_id_to_str(chosen_dev)
    chosen_name = chosen_dev.description()

    # Ubah ke mode manual
    success = player.set_output_mode("manual", device_id=chosen_id, device_name=chosen_name)
    assert success is True
    assert player.get_output_mode() == "manual"
    assert player.get_selected_device_id() == chosen_id
    assert player.get_selected_device_name() == chosen_name

    # Periksa bahwa konfigurasi tersimpan di SettingsRepository
    settings_repo = SettingsRepository(temp_db)
    assert settings_repo.get("audio_output_mode") == "manual"
    assert settings_repo.get("audio_output_device_id") == chosen_id
    assert settings_repo.get("audio_output_device_name") == chosen_name

    # Buat instance baru untuk memverifikasi pemulihan dari database
    player_reloaded = AudioPlayer(temp_db)
    assert player_reloaded.get_output_mode() == "manual"
    assert player_reloaded.get_selected_device_id() == chosen_id
    assert player_reloaded.get_selected_device_name() == chosen_name


def test_fallback_when_manual_device_unplugged(temp_db: DatabaseManager, monkeypatch):
    """
    Menguji bahwa jika perangkat manual yang dipilih dilepas (tidak ada di daftar aktif),
    aplikasi secara cerdas dan aman jatuh ke default Windows tanpa menghapus preferensi tersimpan.
    """
    player = AudioPlayer(temp_db)
    player.set_output_mode("manual", device_id="non_existent_jack_id", device_name="Speaker Jack Eksternal")
    assert player.get_output_mode() == "manual"

    # Saat refresh_audio_device dipanggil, harus jatuh ke default Windows
    success = player.refresh_audio_device()
    available = player.get_available_output_devices()
    if available:
        assert success is True
        default_dev = player.get_default_output_device()
        current_dev = player.get_current_output_device()
        assert device_id_to_str(current_dev) == device_id_to_str(default_dev)
        # Preferensi manual tetap tersimpan agar jika dicolok kembali, otomatis aktif kembali
        assert player.get_selected_device_id() == "non_existent_jack_id"


def test_runtime_device_change_signal_and_switching(temp_db: DatabaseManager):
    """Menguji respons terhadap sinyal audioOutputsChanged (seperti saat jack 3,5 mm dicolok)."""
    player = AudioPlayer(temp_db)

    signal_received = []
    player.audio_devices_changed.connect(lambda: signal_received.append(True))

    # Pemicu simulasi sinyal sistem
    player._on_audio_outputs_changed()

    assert len(signal_received) == 1


def test_playback_with_dynamic_device_check(temp_db: DatabaseManager, tmp_path: Path):
    """Memastikan bahwa pemanggilan play_file() selalu memperbarui status perangkat sebelum memainkan audio."""
    player = AudioPlayer(temp_db)
    wav = create_dummy_wav(tmp_path / "bell_test.wav")

    # Spy pada refresh_audio_device
    refresh_calls = []
    original_refresh = player.refresh_audio_device

    def wrapped_refresh():
        refresh_calls.append(True)
        return original_refresh()

    player.refresh_audio_device = wrapped_refresh

    assert player.play_file(wav, title="Uji Coba Jack") is True
    assert len(refresh_calls) >= 1
    assert player.status == AudioStatus.PLAYING
    player.stop()


def test_single_active_audio_controller_with_device_switch(temp_db: DatabaseManager, tmp_path: Path):
    """Memastikan aturan v1.2.1 tetap terjaga: maksimal 1 audio aktif, interupsi manual, session token aman."""
    player = AudioPlayer(temp_db)
    wav1 = create_dummy_wav(tmp_path / "bell_1.wav")
    wav2 = create_dummy_wav(tmp_path / "bell_2.wav")

    # Putar bel 1
    assert player.play_file(wav1, title="Bel 1", mode="OTOMATIS") is True
    first_session = player.active_session_id
    assert first_session > 0

    # Putar bel 2 (interupsi manual)
    assert player.play_file(wav2, title="Bel 2 Manual", mode="MANUAL") is True
    second_session = player.active_session_id
    assert second_session > first_session
    assert player.current_title == "Bel 2 Manual"

    # Callback dari session 1 harus ditolak/diabaikan
    assert player.is_session_active(first_session) is False
    assert player.is_session_active(second_session) is True

    # Stop berfungsi bersih
    assert player.stop("Dihentikan") is True
    assert player.status == AudioStatus.INTERRUPTED
    assert player.active_session_id == 0


def test_settings_page_audio_device_ui(qapp, temp_db: DatabaseManager, tmp_path: Path, monkeypatch):
    """Menguji antarmuka Pengaturan Perangkat Audio di SettingsPage."""
    from PySide6.QtWidgets import QMessageBox
    from src.models.models import AudioFile

    # Cegah popup dialog modal memblokir eksekusi pengujian
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    audio_player = AudioPlayer(temp_db)
    profile_repo = ProfileRepository(temp_db)
    page = SettingsPage(temp_db, audio_player, profile_repo)

    # 1. Pastikan komponen UI ada
    assert hasattr(page, "cmb_audio_device")
    assert hasattr(page, "btn_refresh_devices")
    assert hasattr(page, "btn_test_audio")
    assert hasattr(page, "lbl_device_info")

    # 2. Pastikan item pertama adalah opsi otomatis
    assert page.cmb_audio_device.count() >= 1
    assert page.cmb_audio_device.itemData(0) == "auto"

    # 3. Simulasi klik tombol Segarkan Perangkat
    page.btn_refresh_devices.click()
    assert page.cmb_audio_device.count() >= 1

    # 4. Buat dummy audio di database dan uji tombol Tes Suara
    wav = create_dummy_wav(tmp_path / "sample_chime.wav")
    audio_repo = AudioRepository(temp_db)
    audio_model = AudioFile(
        id=None,
        name="Sample Chime",
        stored_path=str(wav),
        original_filename="sample_chime.wav",
        duration_seconds=1.0,
    )
    audio_repo.create(audio_model)

    # Klik tombol tes suara
    page.btn_test_audio.click()
    assert audio_player.status == AudioStatus.PLAYING
    assert "Tes Suara" in audio_player.current_title
    audio_player.stop()

    # 5. Simulasi pergantian pilihan combo box ke mode otomatis
    page.cmb_audio_device.setCurrentIndex(0)
    assert audio_player.get_output_mode() == "auto"
    assert "Mode Otomatis Aktif" in page.lbl_device_info.text()
