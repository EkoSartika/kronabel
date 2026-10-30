"""
Pengujian Pengaturan Aplikasi (Settings Page & Repository)
Menguji:
5. Penyimpanan dan pembacaan pengaturan
13. Persistensi setelah aplikasi dibuka kembali
Serta interaksi kontrol UI settings.
"""

import pytest

from src.database.db import DatabaseManager
from src.database.repositories import ProfileRepository, SettingsRepository
from src.services.audio_player import AudioPlayer
from src.ui.settings_page import SettingsPage


def test_settings_storage_and_retrieval(db_manager: DatabaseManager):
    """Uji 5: Penyimpanan dan pembacaan preferensi pada SettingsRepository."""
    repo = SettingsRepository(db_manager)

    # Nilai default saat belum disetel
    assert repo.get("volume", default="80") == "80"
    assert repo.get("confirm_manual_bell", default="true") == "true"
    assert repo.get("playback_busy_policy", default="reject") == "reject"

    # Simpan nilai baru
    repo.set("volume", "95")
    repo.set("confirm_manual_bell", "false")
    repo.set("playback_busy_policy", "interrupt")

    # Baca kembali
    assert repo.get("volume") == "95"
    assert repo.get("confirm_manual_bell") == "false"
    assert repo.get("playback_busy_policy") == "interrupt"


def test_settings_persistence_across_connections(tmp_path):
    """Uji 13: Persistensi pengaturan setelah aplikasi ditutup dan dibuka kembali dengan koneksi baru."""
    db_file = tmp_path / "persistence_test.db"
    
    # 1. Buka koneksi pertama, setel pengaturan
    db1 = DatabaseManager(db_file)
    db1.initialize_database()
    repo1 = SettingsRepository(db1)

    repo1.set("volume", "65")
    repo1.set("confirm_manual_bell", "true")
    repo1.set("custom_school_name", "SMA Negeri 1 Prestasi")

    # Pastikan tersimpan
    assert repo1.get("volume") == "65"

    # 2. Tutup dan buka koneksi kedua (mensimulasikan restart aplikasi)
    db2 = DatabaseManager(db_file)
    repo2 = SettingsRepository(db2)

    assert repo2.get("volume") == "65"
    assert repo2.get("confirm_manual_bell") == "true"
    assert repo2.get("custom_school_name") == "SMA Negeri 1 Prestasi"


def test_settings_ui_integration(qapp, db_manager: DatabaseManager):
    """Pengujian integrasi antarmuka SettingsPage dengan repositori."""
    audio_player = AudioPlayer(db_manager)
    profile_repo = ProfileRepository(db_manager)
    settings_repo = SettingsRepository(db_manager)

    # Simpan pengaturan awal
    settings_repo.set("volume", "70")
    settings_repo.set("confirm_manual_bell", "true")
    settings_repo.set("playback_busy_policy", "reject")

    page = SettingsPage(
        db=db_manager,
        audio_player=audio_player,
        profile_repo=profile_repo,
    )

    # Periksa nilai UI cocok dengan setting
    assert page.slider_volume.value() == 70
    assert page.lbl_volume_val.text() == "70%"
    assert page.chk_confirm_manual.isChecked() is True
    assert page.cmb_busy_policy.currentData() == "reject"

    # Ubah slider volume di UI
    page.slider_volume.setValue(85)
    assert settings_repo.get("volume") == "85"
    assert page.lbl_volume_val.text() == "85%"

    # Ubah checkbox konfirmasi manual
    page.chk_confirm_manual.setChecked(False)
    assert settings_repo.get("confirm_manual_bell") == "false"

    # Ubah kebijakan pemutaran saat sibuk
    idx_interrupt = page.cmb_busy_policy.findData("interrupt")
    page.cmb_busy_policy.setCurrentIndex(idx_interrupt)
    assert settings_repo.get("playback_busy_policy") == "interrupt"
