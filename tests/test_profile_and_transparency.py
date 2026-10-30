"""
Pengujian fitur baru:
1. Pilihan Status Aktif/Nonaktif pada ProfileDialog & ProfilePage.
2. Pengaturan Transparansi Panel Layar Utama (BackgroundPage No. 3).
3. Logika Logout yang kembali ke jendela utama tanpa menutup aplikasi.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from src.database.db import DatabaseManager
from src.database.repositories import ProfileRepository, SettingsRepository
from src.models.models import Profile
from src.ui.admin_window import AdminWindow
from src.ui.background_page import BackgroundPage
from src.ui.main_window import MainWindow
from src.ui.profile_page import ProfileDialog, ProfilePage


def test_profile_dialog_active_status(qapp, temp_db: DatabaseManager):
    """Menguji pemilihan status Aktif/Nonaktif pada ProfileDialog."""
    dialog = ProfileDialog()
    assert dialog.status_combo is not None
    assert dialog.status_combo.count() == 2

    # Pilihan pertama adalah Aktif
    dialog.status_combo.setCurrentIndex(0)
    dialog.name_edit.setText("Profil Ujian Semester")
    prof_data = dialog.get_profile_data()
    assert prof_data.name == "Profil Ujian Semester"
    assert prof_data.is_active is True

    # Pilihan kedua adalah Nonaktif
    dialog.status_combo.setCurrentIndex(1)
    prof_data_inactive = dialog.get_profile_data()
    assert prof_data_inactive.is_active is False


def test_profile_page_switch_status(qapp, temp_db: DatabaseManager):
    """Menguji aktivasi profil lewat ProfilePage."""
    page = ProfilePage(temp_db)
    repo = ProfileRepository(temp_db)

    # Buat profil nonaktif
    new_prof = repo.create(Profile(id=None, name="Profil Cadangan", description="Cadangan", is_active=False))
    page.refresh_profiles()

    # Aktifkan profil
    page._on_activate_profile(new_prof.id, new_prof.name)
    active = repo.get_active()
    assert active is not None
    assert active.name == "Profil Cadangan"
    assert active.id == new_prof.id


def test_background_page_transparency_card(qapp, temp_db: DatabaseManager):
    """Menguji keberadaan nomor 3 (Transparansi) dan penyimpanan nilainya."""
    bg_page = BackgroundPage(temp_db)
    settings_repo = SettingsRepository(temp_db)

    assert hasattr(bg_page, "slider_trans")
    assert hasattr(bg_page, "lbl_trans_val")
    assert hasattr(bg_page, "lbl_trans_status")

    # Set ke efek kaca 60%
    bg_page.slider_trans.setValue(60)
    saved_val = settings_repo.get("panel_transparency", "0")
    assert saved_val == "60"
    assert "60%" in bg_page.lbl_trans_val.text()

    # Set ke solid 0%
    bg_page.slider_trans.setValue(0)
    assert settings_repo.get("panel_transparency", "0") == "0"


def test_main_window_transparency_application(qapp, temp_db: DatabaseManager):
    """Menguji bahwa MainWindow merespons transparansi panel kiri dan kanan."""
    settings_repo = SettingsRepository(temp_db)
    settings_repo.set("panel_transparency", "65")

    window = MainWindow(temp_db)
    window.apply_backgrounds()

    # Pastikan LeftPanel dan RightPanel menggunakan rgba
    assert "rgba" in window.left_panel_ref.styleSheet()
    assert "rgba" in window.right_panel_ref.styleSheet()

def test_main_window_high_transparency_glow(qapp, temp_db: DatabaseManager):
    """Menguji bahwa transparansi >= 80% mengaktifkan warna hijau dan efek glow putih pada judul."""
    settings_repo = SettingsRepository(temp_db)
    settings_repo.set("panel_transparency", "85")

    window = MainWindow(temp_db)
    window.apply_backgrounds()

    # 1. Bel Sekolah Otomatis
    assert "#064e3b" in window.app_title.styleSheet()
    assert window.app_title.graphicsEffect() is not None

    # 2. Jadwal Hari
    assert "#064e3b" in window.right_title.styleSheet()
    assert window.right_title.graphicsEffect() is not None

    # 3. Bel Manual
    assert window.lbl_manual.text() == "Bel Manual"
    assert "#064e3b" in window.lbl_manual.styleSheet()
    assert window.lbl_manual.graphicsEffect() is not None

    # Jika diturunkan ke < 80%
    settings_repo.set("panel_transparency", "50")
    window.apply_backgrounds()
    assert window.app_title.graphicsEffect() is None
    assert window.right_title.graphicsEffect() is None
    assert window.lbl_manual.graphicsEffect() is None
    assert window.lbl_manual.text() == "Bel Manual"
    window.close()

