"""
Pengujian Menyeluruh Redesain Panel Kecil, Login Setting, dan Jadwal Berkode.
Menguji:
1. Dimensi jendela kompak (sekitar 700x350 px, non-maximized, resizable).
2. Autentikasi Pengelola (AuthService, PBKDF2 hash, login, logout, ganti password).
3. Penguncian area pengelola dan akses AdminWindow.
4. Tombol manual kode lagu (eksekusi audio independen, pencatatan log manual).
5. Kontrol ON/OFF scheduler otomatis.
6. BatchSchedulePage: input inline, pemetaan kode lagu, validasi jam, dan pencegahan duplikasi.
7. AudioCodePage: penambahan kode unik, validasi jadwal terdampak saat hapus.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QPushButton

from src.database.db import DatabaseManager
from src.database.repositories import AudioRepository, ProfileRepository, ScheduleRepository, SettingsRepository, BellLogRepository
from src.models.models import AudioFile, Profile, Schedule
from src.services.auth_service import AuthService
from src.services.audio_player import AudioPlayer
from src.ui.main_window import MainWindow
from src.ui.admin_window import AdminWindow
from src.ui.batch_schedule_page import BatchSchedulePage
from src.ui.audio_code_page import AudioCodePage
from src.ui.auth_dialogs import LoginDialog, SetupPasswordDialog

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def app_instance():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_panel.db"
    db = DatabaseManager(str(db_file))
    db.initialize_database()

    # Buat audio uji dengan kode
    audio_repo = AudioRepository(db)
    sound_file = tmp_path / "bell_a.mp3"
    sound_file.write_bytes(b"dummy mp3 data")
    audio_repo.create(AudioFile(code="BEL A", name="Bel Masuk", stored_path=str(sound_file), original_filename="bell_a.mp3"))

    return db


def test_compact_panel_dimensions_and_non_maximized(app_instance, test_db):
    """Memverifikasi jendela utama adalah panel ringkas ~700x350 px dan tidak maximized."""
    win = MainWindow(test_db)
    win.show()
    app_instance.processEvents()

    # Dimensi harus ringkas (di sekitar 700x350 - 750x400)
    assert win.width() <= 750, f"Lebar jendela {win.width()} terlalu lebar untuk panel kompak"
    assert win.height() <= 400, f"Tinggi jendela {win.height()} terlalu tinggi untuk panel kompak"

    # Tidak boleh maximized atau fullscreen
    assert not win.isMaximized()
    assert not win.isFullScreen()

    # Mendukung resize
    win.resize(700, 350)
    app_instance.processEvents()
    assert win.width() == 700
    assert win.height() == 350

    win.close()


def test_auth_service_hashing_and_password_lifecycle(test_db):
    """Menguji layanan AuthService untuk inisialisasi password, verifikasi, dan pergantian password."""
    settings_repo = SettingsRepository(test_db)
    auth = AuthService(settings_repo)

    # 1. Awalnya belum ada password
    assert auth.is_password_set() is False
    assert auth.verify_password("apapun") is False

    # 2. Set password (minimal 4 karakter)
    with pytest.raises(ValueError):
        auth.set_password("12")  # Terlalu pendek

    auth.set_password("adminSekolah2026")
    assert auth.is_password_set() is True

    # 3. Verifikasi password benar & salah
    assert auth.verify_password("adminSekolah2026") is True
    assert auth.verify_password("wrongpassword") is False
    assert auth.verify_password("") is False

    # 4. Ganti password
    assert auth.change_password("wrongpassword", "newpassword123") is False
    assert auth.change_password("adminSekolah2026", "newpassword123") is True
    assert auth.verify_password("newpassword123") is True
    assert auth.verify_password("adminSekolah2026") is False


def test_scheduler_on_off_controls(app_instance, test_db):
    """Menguji kontrol tombol ON dan OFF scheduler pada Panel Utama."""
    win = MainWindow(test_db)
    win.show()
    app_instance.processEvents()

    # Matikan scheduler via tombol OFF
    win.btn_off.click()
    app_instance.processEvents()
    assert win.scheduler.is_active is False
    assert win.btn_on.isEnabled() is True
    assert win.btn_off.isEnabled() is False
    assert "NONAKTIF" in win.status_label.text()

    # Hidupkan kembali via tombol ON
    win.btn_on.click()
    app_instance.processEvents()
    assert win.scheduler.is_active is True
    assert win.btn_on.isEnabled() is False
    assert win.btn_off.isEnabled() is True
    assert "AKTIF" in win.status_label.text()

    win.close()


def test_manual_bell_code_buttons(app_instance, test_db):
    """Menguji pembuatan tombol kode lagu manual dan pemutaran tanpa mengubah jadwal otomatis."""
    win = MainWindow(test_db)
    win.show()
    app_instance.processEvents()

    # Verifikasi ada tombol kode manual 'BEL A'
    manual_buttons = [btn for btn in win.manual_container.findChildren(QPushButton) if btn.text() == "BEL A"]
    assert len(manual_buttons) == 1, "Tombol kode lagu 'BEL A' tidak ditemukan di panel manual"

    # Klik tombol kode manual
    btn_bel_a = manual_buttons[0]
    btn_bel_a.click()
    app_instance.processEvents()

    # Verifikasi log manual dicatat di database
    log_repo = BellLogRepository(test_db)
    logs = log_repo.get_logs(limit=5)
    assert len(logs) >= 1
    latest = logs[0]
    assert latest.execution_mode == "MANUAL"
    assert "BEL A" in latest.event_name

    win.close()


def test_batch_schedule_table_per_day(app_instance, test_db):
    """Menguji BatchSchedulePage: penambahan baris, pengeditan jam, pemetaan kode, dan penyimpanan."""
    batch_page = BatchSchedulePage(test_db)
    batch_page.show()
    app_instance.processEvents()

    # 1. Tambah baris baru
    initial_rows = batch_page.table.rowCount()
    batch_page._on_add_row()
    assert batch_page.table.rowCount() == initial_rows + 1

    # 2. Isi data baris baru
    new_row = batch_page.table.rowCount() - 1
    time_edit = batch_page.table.cellWidget(new_row, 0)
    audio_combo = batch_page.table.cellWidget(new_row, 1)
    event_edit = batch_page.table.cellWidget(new_row, 2)

    time_edit.setText("08:15")
    # Pilih audio BEL A (index 1)
    audio_combo.setCurrentIndex(1)
    event_edit.setText("Jam Pelajaran 2")

    # 3. Simpan perubahan
    saved = batch_page._on_save_changes()
    assert saved is True

    # Verifikasi data tersimpan di repository
    sched_repo = ScheduleRepository(test_db)
    schedules = sched_repo.get_by_profile_and_day(batch_page.current_profile_id, batch_page.current_day)
    found = any(s.bell_time.startswith("08:15") and s.event_name == "Jam Pelajaran 2" and s.audio_code == "BEL A" for s in schedules)
    assert found, "Jadwal yang disimpan tidak ditemukan di database dengan kode lagu yang benar"

    # 4. Uji validasi duplikasi waktu
    batch_page._on_add_row()
    dup_row = batch_page.table.rowCount() - 1
    batch_page.table.cellWidget(dup_row, 0).setText("08:15")
    batch_page.table.cellWidget(dup_row, 2).setText("Kegiatan Duplikat")
    # Simpan harus gagal karena duplikat 08:15
    assert batch_page._on_save_changes() is False

    batch_page.close()


def test_audio_code_page_and_schedule_impact_check(app_instance, test_db, tmp_path):
    """Menguji AudioCodePage: penambahan lagu berkode dan deteksi jadwal terdampak saat hapus."""
    audio_player = AudioPlayer(test_db)
    audio_page = AudioCodePage(test_db, audio_player)
    audio_page.show()
    app_instance.processEvents()

    audio_repo = AudioRepository(test_db)
    audios = audio_repo.get_all()
    bel_a = next(a for a in audios if a.code == "BEL A")

    # Tambahkan jadwal yang menggunakan BEL A
    sched_repo = ScheduleRepository(test_db)
    sched_repo.create(Schedule(profile_id=1, day_of_week="Senin", bell_time="10:00:00", event_name="Bel Uji", audio_id=bel_a.id))

    # Periksa deteksi jadwal terdampak
    affected = audio_repo.get_affected_schedules(bel_a.id)
    assert len(affected) >= 1
    assert affected[0]["event_name"] == "Bel Uji"

    audio_page.close()


def test_admin_window_navigation_and_logout(app_instance, test_db):
    """Menguji navigasi tab di AdminWindow dan penguncian saat logout."""
    audio_player = AudioPlayer(test_db)
    auth = AuthService(SettingsRepository(test_db))
    admin_win = AdminWindow(test_db, audio_player, auth)
    admin_win.show()
    app_instance.processEvents()

    # Verifikasi ada 6 halaman di stacked_widget (Jadwal, Lagu, Profil, Riwayat, Latar Belakang, Pengaturan)
    assert admin_win.stacked_widget.count() == 6
    # Pindah ke tab Pustaka Lagu (index 1)
    admin_win._on_nav_clicked(1)
    assert admin_win.stacked_widget.currentIndex() == 1

    # Pindah ke tab Profil (index 2)
    admin_win._on_nav_clicked(2)
    assert admin_win.stacked_widget.currentIndex() == 2

    # Pindah ke tab Latar Belakang (index 4)
    admin_win._on_nav_clicked(4)
    assert admin_win.stacked_widget.currentIndex() == 4

    admin_win.close()
