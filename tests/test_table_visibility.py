"""
Pengujian Regresi Visibilitas Teks dan Warna Tabel (Bugfix Tabel Kosong).
Memverifikasi bahwa data pada Jadwal Bel, Profil Jam Pelajaran, dan Audio Bel
benar-benar memiliki isi teks yang valid dan warna foreground kontras (bukan putih/kosong).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from src.database.db import DatabaseManager
from src.database.repositories import AudioRepository, ProfileRepository, ScheduleRepository
from src.models.models import AudioFile, Profile, Schedule
from src.services.audio_player import AudioPlayer
from src.ui.audio_page import AudioPage
from src.ui.profile_page import ProfilePage
from src.ui.schedule_page import SchedulePage

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def _is_dark_and_visible(color: QColor) -> bool:
    """Memverifikasi bahwa warna valid, tidak transparan, dan bertipe gelap/kontras."""
    if not color.isValid():
        return False
    # Hitung luminansi relatif sederhana (0 = hitam pekat, 255 = putih pekat)
    # Teks harus kontras terhadap latar belakang putih #ffffff (luminansi < 180)
    luminance = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
    return luminance < 180 and color.alpha() > 0


def test_schedule_table_text_and_foreground_visibility(qapp, temp_db: DatabaseManager):
    """Memverifikasi bahwa baris tabel jadwal memiliki teks yang terisi dan warna kontras."""
    profile_repo = ProfileRepository(temp_db)
    schedule_repo = ScheduleRepository(temp_db)
    audio_repo = AudioRepository(temp_db)

    active_profile = profile_repo.get_active()
    assert active_profile is not None

    # Buat audio dan jadwal uji
    audio = audio_repo.create(
        AudioFile(id=None, name="Bel Masuk", original_filename="masuk.mp3", stored_path="C:/dummy/masuk.mp3")
    )
    schedule = schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Senin",
            bell_time="07:00:00",
            event_name="Upacara Bendera Hari Senin",
            audio_id=audio.id,
            is_enabled=True,
        )
    )

    page = SchedulePage(temp_db)
    page.refresh_profiles()
    page.refresh_schedules()

    table = page.table
    assert table.rowCount() >= 1

    # Cari baris dengan jadwal yang baru dibuat
    target_row = -1
    for r in range(table.rowCount()):
        if table.item(r, 2) and table.item(r, 2).text() == "Upacara Bendera Hari Senin":
            target_row = r
            break

    assert target_row != -1, "Baris jadwal Upacara Bendera tidak ditemukan di tabel UI"

    # Kolom 0: Hari
    item_day = table.item(target_row, 0)
    assert item_day is not None
    assert item_day.text() == "Senin"
    assert _is_dark_and_visible(item_day.foreground().color())

    # Kolom 1: Waktu
    item_time = table.item(target_row, 1)
    assert item_time is not None
    assert item_time.text() == "07:00:00"
    assert _is_dark_and_visible(item_time.foreground().color())

    # Kolom 2: Nama Kegiatan
    item_event = table.item(target_row, 2)
    assert item_event is not None
    assert item_event.text() == "Upacara Bendera Hari Senin"
    assert _is_dark_and_visible(item_event.foreground().color())

    # Kolom 3: File Audio
    item_audio = table.item(target_row, 3)
    assert item_audio is not None
    assert "Bel Masuk" in item_audio.text()
    assert _is_dark_and_visible(item_audio.foreground().color())

    # Kolom 4: Status
    item_status = table.item(target_row, 4)
    assert item_status is not None
    assert item_status.text() == "Aktif"
    assert _is_dark_and_visible(item_status.foreground().color())

    # Periksa Header
    header = table.horizontalHeader()
    assert table.columnCount() == 6
    expected_headers = ["Hari", "Waktu", "Nama Kegiatan", "File Audio", "Status", "Aksi"]
    for c, expected in enumerate(expected_headers):
        h_item = table.horizontalHeaderItem(c)
        assert h_item is not None
        assert h_item.text() == expected


def test_profile_table_text_and_foreground_visibility(qapp, temp_db: DatabaseManager):
    """Memverifikasi bahwa tabel profil memuat nama, deskripsi, total jadwal, dan status dengan kontras jelas."""
    profile_repo = ProfileRepository(temp_db)
    page = ProfilePage(temp_db)
    page.refresh_profiles()

    table = page.table
    assert table.rowCount() >= 1

    for r in range(table.rowCount()):
        name_item = table.item(r, 0)
        desc_item = table.item(r, 1)
        count_item = table.item(r, 2)
        status_item = table.item(r, 3)

        assert name_item is not None and len(name_item.text().strip()) > 0
        assert desc_item is not None and len(desc_item.text().strip()) > 0
        assert count_item is not None and "Jadwal" in count_item.text()
        assert status_item is not None and len(status_item.text().strip()) > 0

        # Verifikasi warna teks tidak putih / tidak transparan
        assert _is_dark_and_visible(name_item.foreground().color())
        assert _is_dark_and_visible(desc_item.foreground().color())
        assert _is_dark_and_visible(count_item.foreground().color())
        assert _is_dark_and_visible(status_item.foreground().color())


def test_audio_table_text_and_foreground_visibility(qapp, temp_db: DatabaseManager, tmp_path: Path):
    """Memverifikasi bahwa pustaka audio menampilkan nama, file asli, path, dan status dengan kontras jelas."""
    audio_repo = AudioRepository(temp_db)

    # Buat file audio fisik sementara
    test_audio_file = tmp_path / "bel_jam_1.mp3"
    test_audio_file.write_bytes(b"DUMMY_MP3_DATA")

    audio_repo.create(
        AudioFile(
            id=None,
            name="Jam Ke-1 Mulai",
            original_filename="bel_jam_1.mp3",
            stored_path=str(test_audio_file),
        )
    )

    audio_player = AudioPlayer(temp_db)
    page = AudioPage(temp_db, audio_player)
    page.refresh_audio_list()

    table = page.table
    assert table.rowCount() >= 1

    target_row = -1
    for r in range(table.rowCount()):
        if table.item(r, 0) and table.item(r, 0).text() == "Jam Ke-1 Mulai":
            target_row = r
            break

    assert target_row != -1

    # Kolom 0: Nama Label
    name_item = table.item(target_row, 0)
    assert name_item is not None
    assert name_item.text() == "Jam Ke-1 Mulai"
    assert _is_dark_and_visible(name_item.foreground().color())

    # Kolom 1: File Asli
    orig_item = table.item(target_row, 1)
    assert orig_item is not None
    assert orig_item.text() == "bel_jam_1.mp3"
    assert _is_dark_and_visible(orig_item.foreground().color())

    # Kolom 2: Path Penyimpanan
    path_item = table.item(target_row, 2)
    assert path_item is not None
    assert str(test_audio_file) in path_item.text()
    assert _is_dark_and_visible(path_item.foreground().color())

    # Kolom 3: Status
    status_item = table.item(target_row, 3)
    assert status_item is not None
    assert status_item.text() == "Tersedia"
    assert _is_dark_and_visible(status_item.foreground().color())


def test_stylesheet_selectors_do_not_leak_to_headers(qapp, temp_db: DatabaseManager):
    """Memverifikasi bahwa container card menggunakan ID selector dan tidak membocorkan generic QFrame ke QHeaderView."""
    sched_page = SchedulePage(temp_db)
    prof_page = ProfilePage(temp_db)
    audio_player = AudioPlayer(temp_db)
    audio_page = AudioPage(temp_db, audio_player)

    # Periksa objek card tabel
    sched_card = sched_page.table.parentWidget()
    prof_card = prof_page.table.parentWidget()
    audio_card = audio_page.table.parentWidget()

    assert sched_card.objectName() == "TableCard"
    assert prof_card.objectName() == "TableCard"
    assert audio_card.objectName() == "TableCard"

    # Periksa stylesheet QTableWidget memuat warna gelap eksplisit
    for page in (sched_page, prof_page, audio_page):
        ss = page.table.styleSheet()
        assert "color: #0f172a" in ss
        assert "QTableWidget::item" in ss
        assert "QHeaderView::section" in ss


def test_dashboard_and_history_table_visibility(qapp, temp_db: DatabaseManager):
    """Memverifikasi bahwa tabel Dashboard dan Halaman Riwayat juga memiliki teks yang terlihat dan kontras."""
    from src.models.models import BellLog
    from src.database.repositories import BellLogRepository
    from src.ui.dashboard import DashboardPage
    from src.ui.history_page import HistoryPage

    profile_repo = ProfileRepository(temp_db)
    schedule_repo = ScheduleRepository(temp_db)
    log_repo = BellLogRepository(temp_db)

    active_profile = profile_repo.get_active()
    assert active_profile is not None

    # Tambahkan log riwayat
    log_repo.add_log(
        BellLog(
            id=None,
            schedule_id=None,
            scheduled_at=None,
            executed_at="2026-10-28 10:00:02",
            event_name="Bel Uji Coba Visibilitas",
            execution_mode="MANUAL",
            status="completed",
            message="Pemutaran bel sukses",
        )
    )

    # 1. Halaman Riwayat
    history_page = HistoryPage(temp_db)
    history_page.load_history()

    h_table = history_page.table
    assert h_table.rowCount() >= 1
    # Periksa header riwayat
    assert h_table.columnCount() == 7
    expected_h_headers = ["Tanggal & Waktu", "Nama Kegiatan", "Jadwal", "Eksekusi", "Metode", "Status", "Keterangan"]
    for c, exp in enumerate(expected_h_headers):
        assert h_table.horizontalHeaderItem(c).text() == exp

    # Periksa teks item riwayat
    item_dt = h_table.item(0, 0)
    item_ev = h_table.item(0, 1)
    assert item_dt is not None and "2026-10-28" in item_dt.text()
    assert item_ev is not None and item_ev.text() == "Bel Uji Coba Visibilitas"

    # 2. Halaman Dashboard
    dashboard = DashboardPage(temp_db)
    dashboard.refresh_data()
    d_table = dashboard.today_table
    assert d_table.columnCount() == 4
    expected_d_headers = ["Waktu", "Kegiatan Bel", "File Audio", "Status"]
    for c, exp in enumerate(expected_d_headers):
        assert d_table.horizontalHeaderItem(c).text() == exp
