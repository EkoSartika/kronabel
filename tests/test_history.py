"""
Pengujian Riwayat Bel (History Page & Repository)
Menguji:
1. Filter tanggal riwayat
2. Filter status dan metode
3. Pencarian nama kegiatan
4. Pemuatan data riwayat dan paginasi
"""

import pytest
from datetime import datetime, timedelta

from src.database.db import DatabaseManager
from src.database.repositories import BellLogRepository
from src.models.models import BellLog
from src.ui.history_page import HistoryPage


@pytest.fixture
def sample_logs(db_manager: DatabaseManager):
    """Mengisi log sampel untuk pengujian filter dan paginasi."""
    repo = BellLogRepository(db_manager)

    # Buat beberapa log dengan variasi tanggal, metode, status, dan nama kegiatan
    logs_data = [
        # Tanggal 1: 2026-10-01
        ("2026-10-01T07:00:00", "2026-10-01T07:00:01", "Masuk Pagi", "OTOMATIS", "completed", "Berhasil dibunyikan"),
        ("2026-10-01T09:30:00", "2026-10-01T09:30:00", "Istirahat 1", "OTOMATIS", "completed", "Berhasil"),
        ("2026-10-01T12:00:00", "2026-10-01T12:00:05", "Sholat Dhuhur", "OTOMATIS", "interrupted", "Dihentikan user"),
        # Tanggal 2: 2026-10-05
        ("2026-10-05T07:00:00", "2026-10-05T07:00:02", "Upacara Bendera", "OTOMATIS", "completed", "Berhasil"),
        (None, "2026-10-05T10:15:00", "Bel Darurat Gempa", "MANUAL", "completed", "Dibunyikan manual oleh guru piket"),
        ("2026-10-05T14:00:00", "2026-10-05T14:00:00", "Pulang Sekolah", "OTOMATIS", "failed", "Audio tidak ditemukan"),
        # Tanggal 3: 2026-10-10
        (None, "2026-10-10T08:00:00", "Panggilan Pembina OSIS", "MANUAL", "completed", "Manual bell"),
        ("2026-10-10T11:00:00", "2026-10-10T11:00:00", "Ganti Jam Pelajaran 4", "OTOMATIS", "missed", "Komputer mati"),
    ]

    created = []
    for sched, exec_time, name, mode, status, msg in logs_data:
        log = BellLog(
            scheduled_at=sched,
            executed_at=exec_time,
            event_name=name,
            execution_mode=mode,
            status=status,
            message=msg,
        )
        created.append(repo.create(log))
    return created


def test_history_date_filter(db_manager: DatabaseManager, sample_logs):
    """Uji 1: Filter tanggal riwayat."""
    repo = BellLogRepository(db_manager)

    # Filter rentang 2026-10-01 s/d 2026-10-02
    logs_range1 = repo.get_logs(start_date="2026-10-01", end_date="2026-10-02")
    assert len(logs_range1) == 3
    assert all("2026-10-01" in l.executed_at for l in logs_range1)

    # Filter rentang 2026-10-04 s/d 2026-10-06
    logs_range2 = repo.get_logs(start_date="2026-10-05", end_date="2026-10-05")
    assert len(logs_range2) == 3

    # Filter di luar tanggal yang ada
    logs_empty = repo.get_logs(start_date="2026-11-01", end_date="2026-11-30")
    assert len(logs_empty) == 0


def test_history_status_and_mode_filter(db_manager: DatabaseManager, sample_logs):
    """Uji 2: Filter status dan metode eksekusi."""
    repo = BellLogRepository(db_manager)

    # Filter metode MANUAL
    manual_logs = repo.get_logs(mode_filter="MANUAL")
    assert len(manual_logs) == 2
    assert all(l.execution_mode == "MANUAL" for l in manual_logs)

    # Filter metode OTOMATIS
    auto_logs = repo.get_logs(mode_filter="OTOMATIS")
    assert len(auto_logs) == 6

    # Filter status completed
    completed_logs = repo.get_logs(status_filter="completed")
    assert len(completed_logs) == 5

    # Filter status failed
    failed_logs = repo.get_logs(status_filter="failed")
    assert len(failed_logs) == 1
    assert failed_logs[0].event_name == "Pulang Sekolah"

    # Filter status missed
    missed_logs = repo.get_logs(status_filter="missed")
    assert len(missed_logs) == 1
    assert missed_logs[0].event_name == "Ganti Jam Pelajaran 4"

    # Kombinasi metode MANUAL & status completed
    manual_comp = repo.get_logs(mode_filter="MANUAL", status_filter="completed")
    assert len(manual_comp) == 2


def test_history_search_event_name(db_manager: DatabaseManager, sample_logs):
    """Uji 3: Pencarian nama kegiatan."""
    repo = BellLogRepository(db_manager)

    # Cari kata "Istirahat"
    res1 = repo.get_logs(search="Istirahat")
    assert len(res1) == 1
    assert res1[0].event_name == "Istirahat 1"

    # Cari kata "Gempa" (case-insensitive)
    res2 = repo.get_logs(search="gempa")
    assert len(res2) == 1
    assert res2[0].event_name == "Bel Darurat Gempa"

    # Cari kata umum "Jam"
    res3 = repo.get_logs(search="Jam")
    assert len(res3) == 1

    # Cari yang tidak ada
    res4 = repo.get_logs(search="Kegiatan Tidak Ada")
    assert len(res4) == 0


def test_history_pagination_and_ui_loading(qapp, db_manager: DatabaseManager, sample_logs):
    """Uji 4: Pemuatan data riwayat dan paginasi pada UI."""
    page = HistoryPage(db_manager)

    # Hitung total
    total = page.log_repo.count_logs()
    assert total == 8

    # Cek jumlah baris tabel awal
    assert page.table.rowCount() == 8

    # Cek label pagination info
    assert "total 8 riwayat" in page.lbl_info.text()
    assert "Halaman 1 / 1" in page.lbl_page.text()

    # Coba filter lewat widget UI
    page.txt_search.setText("Upacara")
    page.btn_apply.click()
    assert page.table.rowCount() == 1
    assert page.table.item(0, 1).text() == "Upacara Bendera"

    # Reset filter
    page.btn_reset.click()
    assert page.table.rowCount() == 8
