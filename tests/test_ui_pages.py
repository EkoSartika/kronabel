"""
Pengujian Komponen Halaman Jadwal Bel dan Profil Jam Pelajaran (Tahap 2).
Menguji pemuatan data, interaksi tabel, filter hari/profil, aktivasi profil,
dan proteksi integritas.
"""

from __future__ import annotations

import os
import sys

import pytest
from PySide6.QtWidgets import QApplication

from src.database.db import DatabaseManager
from src.database.repositories import ProfileRepository, ScheduleRepository
from src.models.models import Profile, Schedule
from src.ui.main_window import MainWindow
from src.ui.profile_page import ProfilePage
from src.ui.schedule_page import SchedulePage

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def test_schedule_page_loading_and_filter(qapp, temp_db: DatabaseManager):
    """Menguji pemuatan jadwal dan fungsi filter hari pada SchedulePage."""
    sched_page = SchedulePage(temp_db)
    profile_repo = ProfileRepository(temp_db)
    schedule_repo = ScheduleRepository(temp_db)

    active_profile = profile_repo.get_active()

    # Tambahkan 2 jadwal di Senin dan 1 di Selasa
    schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Senin",
            bell_time="07:00:00",
            event_name="Upacara",
        )
    )
    schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Senin",
            bell_time="09:45:00",
            event_name="Istirahat",
        )
    )
    schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Selasa",
            bell_time="07:00:00",
            event_name="Senam Pagi",
        )
    )

    sched_page.refresh_schedules()

    # Default 'Semua Hari' -> 3 baris
    assert sched_page.table.rowCount() == 3

    # Filter ke 'Senin'
    senin_idx = sched_page.day_filter_combo.findData("Senin")
    sched_page.day_filter_combo.setCurrentIndex(senin_idx)
    assert sched_page.table.rowCount() == 2

    # Filter ke 'Selasa'
    selasa_idx = sched_page.day_filter_combo.findData("Selasa")
    sched_page.day_filter_combo.setCurrentIndex(selasa_idx)
    assert sched_page.table.rowCount() == 1

    # Filter ke 'Rabu' (kosong)
    rabu_idx = sched_page.day_filter_combo.findData("Rabu")
    sched_page.day_filter_combo.setCurrentIndex(rabu_idx)
    assert sched_page.table.rowCount() == 0


def test_schedule_page_toggle_schedule(qapp, temp_db: DatabaseManager):
    """Menguji pengaktifan/penonaktifan jadwal langsung dari halaman."""
    sched_page = SchedulePage(temp_db)
    profile_repo = ProfileRepository(temp_db)
    schedule_repo = ScheduleRepository(temp_db)

    active_profile = profile_repo.get_active()
    s = schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Kamis",
            bell_time="10:00:00",
            event_name="Literasi",
            is_enabled=True,
        )
    )

    # Matikan jadwal
    sched_page._toggle_schedule(s.id, current_state=True)
    updated = schedule_repo.get_by_id(s.id)
    assert updated.is_enabled is False

    # Hidupkan kembali
    sched_page._toggle_schedule(s.id, current_state=False)
    updated = schedule_repo.get_by_id(s.id)
    assert updated.is_enabled is True


def test_profile_page_listing_and_counts(qapp, temp_db: DatabaseManager):
    """Menguji tampilan profil dan penghitungan jumlah jadwal terdaftar."""
    profile_page = ProfilePage(temp_db)
    profile_repo = ProfileRepository(temp_db)
    schedule_repo = ScheduleRepository(temp_db)

    active_profile = profile_repo.get_active()

    # Tambahkan jadwal di profil aktif
    schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Jumat",
            bell_time="11:30:00",
            event_name="Sholat Jumat",
        )
    )

    profile_page.refresh_profiles()
    assert profile_page.table.rowCount() >= 3

    # Cari baris profil aktif
    for row in range(profile_page.table.rowCount()):
        name_text = profile_page.table.item(row, 0).text()
        if name_text == active_profile.name:
            count_text = profile_page.table.item(row, 2).text()
            assert "Jadwal" in count_text
            status_text = profile_page.table.item(row, 3).text()
            assert "AKTIF" in status_text


def test_profile_page_activation(qapp, temp_db: DatabaseManager):
    """Menguji aktivasi profil Ramadan dari ProfilePage."""
    profile_page = ProfilePage(temp_db)
    profile_repo = ProfileRepository(temp_db)

    profiles = {p.name: p for p in profile_repo.get_all()}
    ramadan = profiles["Ramadan"]

    # Aktifkan profil Ramadan
    profile_page._on_activate_profile(ramadan.id, ramadan.name)

    current_active = profile_repo.get_active()
    assert current_active.name == "Ramadan"


def test_main_window_cross_page_updates(qapp, temp_db: DatabaseManager):
    """Menguji sinkronisasi lintas halaman pada MainWindow saat profil berganti."""
    window = MainWindow(temp_db)
    profile_repo = ProfileRepository(temp_db)

    profiles = {p.name: p for p in profile_repo.get_all()}
    ujian = profiles["Ujian"]

    # Aktifkan profil Ujian
    profile_repo.set_active(ujian.id)
    window._on_profile_updated()

    # Header badge harus terbarui
    assert "Ujian" in window.profile_badge.text()

    # Dashboard label harus terbarui
    assert window.dashboard_page.profile_name_label.text() == "Ujian"

    # Schedule page combobox harus terbarui
    assert "Ujian" in window.schedule_page.profile_combo.currentText()
    window.close()


def test_schedule_dialog_validation(qapp, temp_db: DatabaseManager):
    """Menguji validasi nama kosong dan format waktu pada ScheduleDialog."""
    from src.ui.schedule_page import ScheduleDialog

    # Nama kosong
    dialog = ScheduleDialog(profile_id=1)
    dialog.event_edit.setText("")
    dialog._validate_and_accept()
    assert dialog.result() != ScheduleDialog.Accepted

    # Format waktu salah
    dialog.event_edit.setText("Istirahat")
    dialog.time_edit.setText("25:99")
    dialog._validate_and_accept()
    assert dialog.result() != ScheduleDialog.Accepted

    # Valid
    dialog.time_edit.setText("08:30")
    dialog._validate_and_accept()
    assert dialog.result() == ScheduleDialog.Accepted
    data = dialog.get_schedule_data()
    assert data.bell_time == "08:30:00"
    assert data.event_name == "Istirahat"


def test_profile_dialog_validation(qapp):
    """Menguji validasi nama kosong pada ProfileDialog."""
    from src.ui.profile_page import ProfileDialog

    dialog = ProfileDialog()
    dialog.name_edit.setText("   ")
    dialog._validate_and_accept()
    assert dialog.result() != ProfileDialog.Accepted

    dialog.name_edit.setText("Profil Ujian Semester")
    dialog.desc_edit.setText("Deskripsi singkat")
    dialog._validate_and_accept()
    assert dialog.result() == ProfileDialog.Accepted
    data = dialog.get_profile_data()
    assert data.name == "Profil Ujian Semester"


def test_audio_page_listing_and_volume_slider(qapp, temp_db: DatabaseManager):
    """Menguji tampilan tabel AudioPage dan kontrol volume slider."""
    from src.models.models import AudioFile
    from src.services.audio_player import AudioPlayer
    from src.ui.audio_page import AudioPage

    audio_player = AudioPlayer(temp_db)
    audio_page = AudioPage(temp_db, audio_player)

    # Tambahkan record audio ke db
    audio_page.audio_repo.create(
        AudioFile(
            id=None,
            name="Bel Masuk UI",
            stored_path="C:/dummy/bel_ui.wav",
            original_filename="bel_ui.wav",
            duration_seconds=3.0,
        )
    )

    audio_page.refresh_audio_list()
    assert audio_page.table.rowCount() == 1
    assert audio_page.table.item(0, 0).text() == "Bel Masuk UI"

    # Uji perubahan volume slider
    audio_page.volume_slider.setValue(65)
    assert audio_player.get_volume() == 65
    assert audio_page.vol_value_label.text() == "65%"


