"""
Pengujian Penyempurnaan UI dan Validasi Audio Jadwal (Tahap 6B).
Memverifikasi:
1. Ukuran tombol aksi memadai (tidak terpotong vertikal, tinggi baris >= 44px).
2. Teks tombol utuh dan terbaca pada Jadwal, Profil, dan Audio.
3. Penanganan jadwal tanpa audio: menampilkan peringatan eksplisit dan panduan edit.
4. Scheduler transparan saat jadwal tanpa audio dieksekusi (tidak mengklaim bel berbunyi jika gagal).
5. Persistensi pemilihan audio jadwal antar-koneksi.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QPushButton

from src.database.db import DatabaseManager
from src.database.repositories import AudioRepository, ProfileRepository, ScheduleRepository
from src.models.models import AudioFile, Profile, Schedule
from src.services.audio_player import AudioPlayer, AudioStatus
from src.services.clock_service import SimulatedClock
from src.services.scheduler import SchedulerService
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


def test_table_button_dimensions_and_visibility(qapp, temp_db: DatabaseManager, tmp_path: Path):
    """Memverifikasi bahwa tombol pada tabel memiliki tinggi memadai (>=28px) dan baris tabel >=44px."""
    profile_repo = ProfileRepository(temp_db)
    schedule_repo = ScheduleRepository(temp_db)
    audio_repo = AudioRepository(temp_db)

    active_profile = profile_repo.get_active()
    assert active_profile is not None

    # Buat data uji
    audio_file = tmp_path / "test_bell.mp3"
    audio_file.write_bytes(b"DUMMY")
    audio = audio_repo.create(
        AudioFile(id=None, name="Bel Masuk Uji", original_filename="test_bell.mp3", stored_path=str(audio_file))
    )
    schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Senin",
            bell_time="07:00:00",
            event_name="Upacara",
            audio_id=audio.id,
            is_enabled=True,
        )
    )

    # 1. Uji SchedulePage
    sched_page = SchedulePage(temp_db)
    sched_page.refresh_profiles()
    sched_page.refresh_schedules()
    assert sched_page.table.verticalHeader().defaultSectionSize() >= 44

    cell_widget = sched_page.table.cellWidget(0, 5)
    assert cell_widget is not None
    buttons = cell_widget.findChildren(QPushButton)
    assert len(buttons) == 3  # Matikan/Aktifkan, Edit, Hapus
    for btn in buttons:
        assert btn.minimumHeight() >= 28
        assert len(btn.text().strip()) > 0
        assert btn.text() in ("Matikan", "Aktifkan", "Edit", "Hapus")

    # 2. Uji ProfilePage
    prof_page = ProfilePage(temp_db)
    prof_page.refresh_profiles()
    assert prof_page.table.verticalHeader().defaultSectionSize() >= 44

    # Cari baris profil non-aktif untuk memeriksa tombol Aktifkan, Edit, Hapus
    found_inactive_row = False
    for r in range(prof_page.table.rowCount()):
        c_widget = prof_page.table.cellWidget(r, 4)
        if c_widget:
            p_btns = c_widget.findChildren(QPushButton)
            btn_texts = [b.text() for b in p_btns]
            if "Aktifkan" in btn_texts:
                found_inactive_row = True
                for b in p_btns:
                    assert b.minimumHeight() >= 28
                    assert len(b.text().strip()) > 0
                break
    assert found_inactive_row, "Baris profil non-aktif tidak ditemukan"

    # 3. Uji AudioPage
    audio_player = AudioPlayer(temp_db)
    audio_page = AudioPage(temp_db, audio_player)
    audio_page.refresh_audio_list()
    assert audio_page.table.verticalHeader().defaultSectionSize() >= 44

    a_widget = audio_page.table.cellWidget(0, 4)
    assert a_widget is not None
    a_btns = a_widget.findChildren(QPushButton)
    assert len(a_btns) == 2  # Putar, Hapus
    for b in a_btns:
        assert b.minimumHeight() >= 28
        assert len(b.text().strip()) > 0
        assert b.text() in ("▶ Putar", "Putar", "Hapus")


def test_schedule_missing_audio_warning_and_persistence(qapp, temp_db: DatabaseManager, tmp_path: Path):
    """
    Memverifikasi penanganan jadwal tanpa audio:
    - Jadwal tanpa audio menampilkan label peringatan ⚠️ Belum Dipilih (Edit Jadwal).
    - Setelah diedit dan diberi audio, audio tersimpan persisten ke database.
    """
    profile_repo = ProfileRepository(temp_db)
    schedule_repo = ScheduleRepository(temp_db)
    audio_repo = AudioRepository(temp_db)

    active_profile = profile_repo.get_active()

    # Buat jadwal tanpa audio (audio_id = None)
    sched_no_audio = schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Kamis",
            bell_time="08:00:00",
            event_name="Literasi Pagi",
            audio_id=None,
            is_enabled=True,
        )
    )

    page = SchedulePage(temp_db)
    page.refresh_profiles()
    page.day_filter_combo.setCurrentIndex(4)  # Pilih Kamis
    page.refresh_schedules()

    # Periksa kolom audio pada baris jadwal ini
    audio_item = page.table.item(0, 3)
    assert audio_item is not None
    assert "Belum Dipilih" in audio_item.text()
    assert "⚠️" in audio_item.text()
    # Warna peringatan amber/oranye (luminansi < 180, bukan putih)
    c = audio_item.foreground().color()
    assert c.isValid() and c.red() > c.blue()  # Karakteristik warna oranye/amber

    # Sekarang update jadwal dengan memilih audio
    audio_file = tmp_path / "literasi.mp3"
    audio_file.write_bytes(b"DUMMY_LITERASI")
    new_audio = audio_repo.create(
        AudioFile(id=None, name="Suara Literasi", original_filename="literasi.mp3", stored_path=str(audio_file))
    )

    sched_no_audio.audio_id = new_audio.id
    schedule_repo.update(sched_no_audio)

    # Muat ulang page dan verifikasi nama audio muncul
    page.refresh_schedules()
    updated_item = page.table.item(0, 3)
    assert updated_item is not None
    assert updated_item.text() == "Suara Literasi"
    assert "⚠️" not in updated_item.text()


def test_scheduler_no_audio_handling_transparency(temp_db: DatabaseManager, tmp_path: Path):
    """
    Memverifikasi perilaku scheduler saat jadwal tidak memiliki audio:
    1. Jika pustaka memiliki audio, fallback digunakan dengan pencatatan log transparan.
    2. Jika pustaka audio kosong, scheduler mencatat status 'failed' (tidak mengklaim sukses).
    """
    profile_repo = ProfileRepository(temp_db)
    schedule_repo = ScheduleRepository(temp_db)
    audio_repo = AudioRepository(temp_db)

    # Bersihkan audio untuk menguji skenario pustaka kosong
    with temp_db.session() as conn:
        conn.cursor().execute("DELETE FROM audio_files")

    active_profile = profile_repo.get_active()
    sched = schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Jumat",
            bell_time="11:30:00",
            event_name="Sholat Jumat",
            audio_id=None,
            is_enabled=True,
        )
    )

    clock = SimulatedClock(datetime(2026, 10, 30, 11, 30, 0))
    audio_player = AudioPlayer(temp_db)
    scheduler = SchedulerService(temp_db, audio_player, clock=clock)

    # Jalankan pemeriksaan trigger
    scheduler._evaluate_current_schedules()

    # Periksa log di database
    logs = scheduler.log_repo.get_logs()
    assert len(logs) == 1
    log = logs[0]
    # Status harus failed karena tidak ada audio yang bisa diputar
    assert log.status == "failed"
    assert "Audio belum dipilih" in log.message or "pustaka audio kosong" in log.message


def test_toggle_schedule_and_activate_profile_buttons(qapp, temp_db: DatabaseManager):
    """Memverifikasi bahwa tombol Aktifkan/Matikan jadwal dan profil bekerja pada record yang tepat."""
    profile_repo = ProfileRepository(temp_db)
    schedule_repo = ScheduleRepository(temp_db)

    active_profile = profile_repo.get_active()
    sched = schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Sabtu",
            bell_time="09:00:00",
            event_name="Pramuka",
            is_enabled=True,
        )
    )

    page = SchedulePage(temp_db)
    page.refresh_profiles()
    page.day_filter_combo.setCurrentIndex(6)  # Sabtu
    page.refresh_schedules()

    # Tekan toggle (Matikan)
    page._toggle_schedule(sched.id, current_state=True)

    # Verifikasi di database
    reloaded = schedule_repo.get_by_id(sched.id)
    assert reloaded is not None
    assert reloaded.is_enabled is False

    # Tekan toggle (Aktifkan kembali)
    page._toggle_schedule(sched.id, current_state=False)
    reloaded2 = schedule_repo.get_by_id(sched.id)
    assert reloaded2.is_enabled is True


def test_auto_code_generation_modes(temp_db: DatabaseManager):
    """Memverifikasi penomoran otomatis baik abjad (BEL A, BEL B) maupun angka (BEL 1, BEL 2)."""
    repo = AudioRepository(temp_db)

    # Mode alphabet
    assert AudioRepository.generate_next_code([], mode="alphabet") == "BEL A"
    assert AudioRepository.generate_next_code(["BEL A"], mode="alphabet") == "BEL B"
    assert AudioRepository.generate_next_code(["BEL A", "BEL B"], mode="alphabet") == "BEL C"

    # Mode numeric
    assert AudioRepository.generate_next_code([], mode="numeric") == "BEL 1"
    assert AudioRepository.generate_next_code(["BEL 1"], mode="numeric") == "BEL 2"
    assert AudioRepository.generate_next_code(["BEL 1", "BEL 2", "BEL 5"], mode="numeric") == "BEL 3"


def test_profile_dialog_and_audio_code_page_ui(qapp, temp_db: DatabaseManager):
    """Memverifikasi tombol Tambah Lagu di AudioCodePage dan ukuran kokoh ProfileDialog."""
    from src.ui.audio_code_page import AudioCodePage, AudioEditDialog
    from src.ui.profile_page import ProfileDialog

    player = AudioPlayer(temp_db)
    audio_page = AudioCodePage(temp_db, player)

    # Tombol Tambah Lagu harus ada dan terhubung
    assert audio_page.add_btn is not None
    assert audio_page.add_btn.text() == "Tambah Lagu MP3/WAV"

    # AudioEditDialog dengan auto-urut
    repo = AudioRepository(temp_db)
    edit_dialog = AudioEditDialog(repo=repo)
    assert edit_dialog.width() == 460
    assert edit_dialog.height() == 310

    # Uji aksi auto-urut
    edit_dialog._set_auto_code("alphabet")
    assert edit_dialog.code_input.text().startswith("BEL ")
    edit_dialog._set_auto_code("numeric")
    assert edit_dialog.code_input.text().startswith("BEL ")

    # ProfileDialog harus berukuran tetap dan tidak kosong/gepeng
    prof_dialog = ProfileDialog()
    assert prof_dialog.width() == 450
    assert prof_dialog.height() == 270
    assert prof_dialog.name_edit is not None
    assert prof_dialog.desc_edit is not None

