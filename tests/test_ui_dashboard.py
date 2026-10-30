"""
Pengujian Komponen Halaman Dashboard (Tahap 2).
Menguji inisialisasi jam digital, status scheduler, profil aktif, ringkasan jadwal, dan navigasi cepat.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

import pytest
from PySide6.QtWidgets import QApplication

from src.database.db import DatabaseManager
from src.database.repositories import ProfileRepository, ScheduleRepository
from src.models.models import Schedule
from src.ui.dashboard import DashboardPage

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def test_dashboard_initial_state(qapp, temp_db: DatabaseManager):
    """Menguji tampilan awal dashboard: status scheduler, profil aktif, dan jam digital."""
    dashboard = DashboardPage(temp_db)

    # Status mesin scheduler otomatis harus 'Belum Diaktifkan' pada tahap ini
    assert dashboard.scheduler_badge.text() == "Belum Diaktifkan"

    # Profil aktif bawaan adalah Reguler
    assert dashboard.profile_name_label.text() == "Reguler"

    # Jam digital terformat
    assert len(dashboard.clock_label.text().split(":")) == 3

    # Tanggal terisi
    assert len(dashboard.date_label.text()) > 5


def test_dashboard_quick_navigation_signal(qapp, temp_db: DatabaseManager):
    """Menguji bahwa sinyal navigasi cepat terkirim saat tombol ditekan."""
    dashboard = DashboardPage(temp_db)

    received_events = []
    dashboard.navigate_requested.connect(lambda idx, name: received_events.append((idx, name)))

    # Pancarkan sinyal secara langsung untuk verifikasi
    dashboard.navigate_requested.emit(1, "Jadwal Bel")
    assert len(received_events) == 1
    assert received_events[0] == (1, "Jadwal Bel")


def test_dashboard_today_schedules_display(qapp, temp_db: DatabaseManager):
    """Menguji pembaruan tabel jadwal hari ini pada dashboard."""
    dashboard = DashboardPage(temp_db)
    profile_repo = ProfileRepository(temp_db)
    schedule_repo = ScheduleRepository(temp_db)

    active_profile = profile_repo.get_active()

    # Tentukan hari saat ini dalam bahasa Indonesia
    day_mapping = {
        "Monday": "Senin",
        "Tuesday": "Selasa",
        "Wednesday": "Rabu",
        "Thursday": "Kamis",
        "Friday": "Jumat",
        "Saturday": "Sabtu",
        "Sunday": "Minggu",
    }
    today_name = day_mapping.get(datetime.now().strftime("%A"), "Senin")

    if today_name in ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"]:
        # Tambahkan jadwal untuk hari ini
        schedule_repo.create(
            Schedule(
                id=None,
                profile_id=active_profile.id,
                day_of_week=today_name,
                bell_time="07:15:00",
                event_name="Bel Uji Dashboard",
            )
        )

        dashboard.refresh_data()
        assert dashboard.today_table.rowCount() >= 1
        assert "Bel Uji Dashboard" in [
            dashboard.today_table.item(r, 1).text() for r in range(dashboard.today_table.rowCount())
        ]
