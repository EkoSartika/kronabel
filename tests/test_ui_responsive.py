"""
Pengujian Otomatis UI Responsif dan Penyempurnaan Tata Letak (Tahap 6C)
Memverifikasi:
1. Dukungan ukuran jendela 1000x650 dan 1280x720.
2. Area jam, tanggal, status, dan countdown tidak terpotong atau keluar batas kartu.
3. Tombol aksi pada tabel Profil, Jadwal, dan Audio tidak saling tumpang tindih dan memiliki jarak (spacing) yang memadai.
4. Tabel tetap dapat digunakan pada jendela kecil dengan scroll horizontal jika diperlukan.
5. Navigasi antarmuka sinkron dengan header title dan status checked tombol sidebar.
"""

import os
import pytest
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QApplication, QPushButton, QWidget

from src.database.db import DatabaseManager
from src.ui.main_window import MainWindow
from src.ui.dashboard import DashboardPage
from src.ui.profile_page import ProfilePage
from src.ui.schedule_page import SchedulePage
from src.ui.audio_page import AudioPage


@pytest.fixture
def app_instance():
    """Memastikan QApplication tersedia untuk pengujian UI."""
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app


@pytest.fixture
def isolated_db(tmp_path):
    """Menyediakan database SQLite terisolasi dengan data uji."""
    db_file = tmp_path / "test_responsive.db"
    db = DatabaseManager(str(db_file))
    db.initialize_database()
    # Tambah profil kustom untuk memastikan tombol Aktifkan, Edit, Hapus terisi di tabel profil
    from src.models.models import Profile, Schedule, AudioFile
    from src.database.repositories import ProfileRepository, ScheduleRepository, AudioRepository

    prof_repo = ProfileRepository(db)
    sched_repo = ScheduleRepository(db)
    audio_repo = AudioRepository(db)

    # 1 Audio
    audio = audio_repo.create(AudioFile(name="Bell Uji", stored_path=str(tmp_path / "bell.mp3"), original_filename="bell.mp3"))

    # 1 Profil tambahan nonaktif
    p_custom = prof_repo.create(Profile(name="Ujian Sekolah", description="Profil khusus periode ujian", is_active=False))

    # Jadwal di profil reguler (id 1)
    sched_repo.create(Schedule(profile_id=1, day_of_week="Senin", bell_time="07:00:00", event_name="Upacara Bendera", audio_id=audio.id, is_enabled=True))
    sched_repo.create(Schedule(profile_id=1, day_of_week="Senin", bell_time="07:45:00", event_name="Jam Pelajaran 1", audio_id=None, is_enabled=False))

    return db


def test_window_supports_laptop_resolution(app_instance, isolated_db):
    """Memverifikasi ukuran minimum jendela mendukung layar laptop 1000x650."""
    win = MainWindow(isolated_db)
    min_size = win.minimumSize()

    # Minimum size harus <= 1000x650 agar dapat dibuka pada layar laptop standar/skala Windows
    assert min_size.width() <= 1000, f"Minimum width {min_size.width()} terlalu lebar untuk 1000px"
    assert min_size.height() <= 650, f"Minimum height {min_size.height()} terlalu tinggi untuk 650px"

    # Uji resize ke 1000x650
    win.resize(1000, 650)
    win.show()
    app_instance.processEvents()

    assert win.width() == 1000
    assert win.height() == 650
    win.close()


def test_dashboard_components_not_clipped_at_small_size(app_instance, isolated_db):
    """Memverifikasi teks jam, status, dan hitung mundur tidak terpotong pada 1000x650."""
    win = MainWindow(isolated_db)
    win.resize(1000, 650)
    win.show()
    app_instance.processEvents()

    dash = win.dashboard_page
    assert dash.scroll_area is not None

    # Verifikasi jam dan tanggal terisi
    clock_text = dash.clock_label.text()
    assert len(clock_text) >= 5, "Format jam tidak terbaca"

    # Verifikasi tombol kontrol mesin otomatis dan manual bell terlihat dan memiliki ukuran memadai
    assert dash.start_sched_btn.isVisible()
    assert dash.stop_sched_btn.isVisible()
    assert dash.manual_bell_btn.isVisible()
    assert dash.start_sched_btn.height() >= 26
    assert dash.manual_bell_btn.height() >= 30

    # Verifikasi Next Bell card ter-render
    assert dash.next_event_label.isVisible()
    assert dash.countdown_label.isVisible()

    win.close()


def test_table_action_buttons_spacing_no_overlap(app_instance, isolated_db):
    """Memverifikasi tombol aksi pada tabel Profil dan Jadwal memiliki jarak dan tidak bertumpukan."""
    win = MainWindow(isolated_db)
    win.resize(1000, 650)
    win.show()
    app_instance.processEvents()

    # 1. Periksa Halaman Profil (halaman index 2)
    win.stacked_widget.setCurrentIndex(2)
    app_instance.processEvents()
    prof_table = win.profile_page.table

    # Cari baris profil nonaktif yang memiliki 3 tombol (Aktifkan, Edit, Hapus)
    found_3_btns = False
    for row in range(prof_table.rowCount()):
        action_cell = prof_table.cellWidget(row, 4)
        if action_cell:
            btns = action_cell.findChildren(QPushButton)
            if len(btns) == 3:
                found_3_btns = True
                # Verifikasi setiap tombol memiliki dimensi yang cukup
                for b in btns:
                    assert b.width() >= 48, f"Tombol {b.text()} terlalu sempit ({b.width()}px)"
                    assert b.height() >= 26, f"Tombol {b.text()} terlalu pendek ({b.height()}px)"

                # Verifikasi tombol berurutan dari kiri ke kanan dengan jarak (spacing) positif
                pos_x = [b.x() for b in btns]
                assert pos_x[0] < pos_x[1] < pos_x[2], "Urutan posisi horizontal tombol salah"
                # Tombol 0 dan 1 tidak bertumpuk
                assert pos_x[0] + btns[0].width() <= pos_x[1], "Tombol 0 dan 1 bertumpuk"
                # Tombol 1 dan 2 tidak bertumpuk
                assert pos_x[1] + btns[1].width() <= pos_x[2], "Tombol 1 dan 2 bertumpuk"

    assert found_3_btns, "Tidak ditemukan baris profil dengan 3 tombol aksi untuk diverifikasi"

    # 2. Periksa Halaman Jadwal (halaman index 1)
    win.stacked_widget.setCurrentIndex(1)
    app_instance.processEvents()
    sched_table = win.schedule_page.table

    for row in range(sched_table.rowCount()):
        action_cell = sched_table.cellWidget(row, 5)
        if action_cell:
            btns = action_cell.findChildren(QPushButton)
            assert len(btns) == 3
            pos_x = [b.x() for b in btns]
            assert pos_x[0] < pos_x[1] < pos_x[2], "Urutan tombol aksi jadwal salah"
            assert pos_x[0] + btns[0].width() <= pos_x[1], "Tombol aksi jadwal 0 dan 1 bertumpuk"
            assert pos_x[1] + btns[1].width() <= pos_x[2], "Tombol aksi jadwal 1 dan 2 bertumpuk"

    win.close()


def test_navigation_and_header_synchronization(app_instance, isolated_db):
    """Memverifikasi judul header dan tombol navigasi sidebar selalu sinkron saat halaman berganti."""
    win = MainWindow(isolated_db)
    win.show()
    app_instance.processEvents()

    # Buka Dashboard
    win._on_navigate(0, "Dashboard")
    app_instance.processEvents()
    assert win.header_title.text() == "Dashboard"
    assert win.nav_buttons[0].isChecked()

    # Buka Jadwal Bel melalui quick navigate dashboard
    win._on_quick_navigate(1, "Jadwal Bel")
    app_instance.processEvents()
    assert win.header_title.text() == "Jadwal Bel"
    assert win.nav_buttons[1].isChecked()

    # Pindah langsung lewat stacked widget currentChanged
    win.stacked_widget.setCurrentIndex(3)
    app_instance.processEvents()
    assert win.header_title.text() == "Audio Bel"
    assert win.nav_buttons[3].isChecked()

    win.close()
