"""
Pengujian Khusus Penyempurnaan Operasional v1.2.2:
1. Notifikasi jadwal otomatis yang terlewat (missed) muncul tanpa memotong audio manual.
2. Informasi notifikasi memuat nama jadwal, waktu, dan keterangan jelas.
3. Satu jadwal missed hanya dicatat satu kali di database (anti-duplikasi).
4. Jadwal missed tidak diulang pada hari yang sama.
5. Jadwal berikutnya tetap berjalan normal.
6. Restart aplikasi (instansiasi SchedulerService baru) tidak memutar ulang jadwal yang sudah selesai atau missed.
7. Pergantian hari berikutnya (midnight rollover) mereset evaluasi dan jadwal hari berikutnya dapat dieksekusi.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

import pytest
from PySide6.QtWidgets import QApplication

from src.database.db import DatabaseManager
from src.database.repositories import (
    AudioRepository,
    BellLogRepository,
    ProfileRepository,
    ScheduleRepository,
)
from src.models.models import AudioFile, BellLog, Schedule
from src.services.audio_player import AudioPlayer, AudioStatus
from src.services.clock_service import SimulatedClock
from src.services.scheduler import SchedulerService
from src.ui.main_window import MainWindow

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def test_setup(qapp, tmp_path: Path) -> Tuple[DatabaseManager, Dict[str, AudioFile]]:
    db_path = tmp_path / "v122_test.db"
    db = DatabaseManager(db_path)
    db.initialize_database()

    audio_repo = AudioRepository(db)
    audios: Dict[str, AudioFile] = {}

    for idx, (code, name) in enumerate([("BEL A", "Bel Masuk Pagi"), ("BEL B", "Bel Istirahat")], start=1):
        f = tmp_path / f"sound_{idx}.wav"
        f.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00data\x00\x00\x00\x00")
        created = audio_repo.create(AudioFile(code=code, name=name, stored_path=str(f), original_filename=f.name))
        audios[code] = created

    return db, audios


def test_missed_schedule_notification_without_cutting_manual_audio(qapp, test_setup):
    """Memverifikasi notifikasi jadwal terlewat dipancarkan tanpa menghentikan audio manual."""
    db, audios = test_setup
    sched_repo = ScheduleRepository(db)
    prof_repo = ProfileRepository(db)
    log_repo = BellLogRepository(db)
    active_prof = prof_repo.get_active()

    with db.session() as conn:
        conn.execute("DELETE FROM schedules")

    sched = sched_repo.create(
        Schedule(
            id=None,
            profile_id=active_prof.id,
            day_of_week="Senin",
            bell_time="07:00:00",
            event_name="Upacara Bendera",
            audio_id=audios["BEL A"].id,
            is_enabled=True,
        )
    )

    clock = SimulatedClock(datetime(2026, 6, 1, 6, 59, 50))
    player = AudioPlayer(db)
    scheduler = SchedulerService(db, player, clock)
    scheduler.start()

    missed_notifs = []
    scheduler.schedule_missed.connect(lambda ev, tm, msg: missed_notifs.append((ev, tm, msg)))

    # 1. Operator memutar bel manual pada 06:59:50
    ok = scheduler.trigger_manual_bell(
        audio_id=audios["BEL B"].id,
        event_name="Pengumuman Manual",
        audio_path=audios["BEL B"].stored_path,
    )
    assert ok is True
    assert player.is_playing() is True
    assert player.current_mode == "MANUAL"
    assert player.current_title == "Pengumuman Manual"

    # 2. Waktu jadwal 07:00:00 tiba saat audio manual masih berlangsung
    clock.set_time(datetime(2026, 6, 1, 7, 0, 0))
    scheduler._tick()

    # Verifikasi audio manual TIDAK dipotong
    assert player.is_playing() is True
    assert player.current_mode == "MANUAL"
    assert player.current_title == "Pengumuman Manual"

    # Verifikasi notifikasi terpancar tepat 1 kali
    assert len(missed_notifs) == 1
    ev_name, bell_time, notif_text = missed_notifs[0]
    assert ev_name == "Upacara Bendera"
    assert "07:00" in bell_time
    assert "07:00" in notif_text
    assert "dilewati" in notif_text
    assert "audio manual" in notif_text

    # Verifikasi log database mencatat status 'missed'
    logs = log_repo.get_logs(limit=5)
    missed_logs = [l for l in logs if l.schedule_id == sched.id]
    assert len(missed_logs) == 1
    assert missed_logs[0].status == "missed"
    assert missed_logs[0].execution_mode == "OTOMATIS"

    scheduler.stop()
    player.cleanup()


def test_missed_schedule_single_log_and_no_replay_same_day(test_setup):
    """Memverifikasi satu kejadian jadwal missed hanya dicatat satu kali dan tidak diulang pada hari yang sama."""
    db, audios = test_setup
    sched_repo = ScheduleRepository(db)
    prof_repo = ProfileRepository(db)
    log_repo = BellLogRepository(db)
    active_prof = prof_repo.get_active()

    with db.session() as conn:
        conn.execute("DELETE FROM schedules")

    sched = sched_repo.create(
        Schedule(
            id=None,
            profile_id=active_prof.id,
            day_of_week="Senin",
            bell_time="07:00:00",
            event_name="Bel Jam 1",
            audio_id=audios["BEL A"].id,
            is_enabled=True,
        )
    )

    clock = SimulatedClock(datetime(2026, 6, 1, 6, 59, 58))
    player = AudioPlayer(db)
    scheduler = SchedulerService(db, player, clock)
    scheduler.start()

    scheduler.trigger_manual_bell(audio_id=audios["BEL B"].id, event_name="Bel Manual")

    # Detik 07:00:00 pertama
    clock.set_time(datetime(2026, 6, 1, 7, 0, 0))
    scheduler._tick()

    # Detik 07:00:00 berulang atau detik berikutnya di menit yang sama (07:00:01)
    clock.set_time(datetime(2026, 6, 1, 7, 0, 1))
    scheduler._tick()

    # Manual selesai diputar
    player.stop()

    # Detik 07:00:10 (audio manual sudah berhenti, tetapi jam 07:00 sudah terlewat) -> TIDAK boleh dieksekusi lagi
    clock.set_time(datetime(2026, 6, 1, 7, 0, 10))
    scheduler._tick()

    logs = log_repo.get_logs(limit=10)
    sched_logs = [l for l in logs if l.schedule_id == sched.id]
    # Tepat 1 catatan
    assert len(sched_logs) == 1
    assert sched_logs[0].status == "missed"

    scheduler.stop()
    player.cleanup()


def test_app_restart_does_not_replay_completed_or_missed_schedules(test_setup):
    """
    Memverifikasi bahwa instansiasi baru SchedulerService (mensimulasikan restart aplikasi)
    tidak memutar ulang jadwal yang sudah tercatat sebagai 'completed', 'interrupted', atau 'missed'.
    """
    db, audios = test_setup
    sched_repo = ScheduleRepository(db)
    prof_repo = ProfileRepository(db)
    log_repo = BellLogRepository(db)
    active_prof = prof_repo.get_active()

    with db.session() as conn:
        conn.execute("DELETE FROM schedules")

    # Buat jadwal pukul 07:00
    sched = sched_repo.create(
        Schedule(
            id=None,
            profile_id=active_prof.id,
            day_of_week="Senin",
            bell_time="07:00:00",
            event_name="Bel Pagi",
            audio_id=audios["BEL A"].id,
            is_enabled=True,
        )
    )

    # 1. Catat log seolah-olah jadwal 07:00 sudah tercatat 'missed' sebelumnya hari ini
    today_str = "2026-06-01"
    log_repo.add_log(
        BellLog(
            id=None,
            schedule_id=sched.id,
            scheduled_at=f"{today_str}T07:00:00",
            executed_at=f"{today_str}T07:00:00",
            event_name="Bel Pagi",
            execution_mode="OTOMATIS",
            status="missed",
            message="Dilewati sebelumnya",
        )
    )

    # 2. Buka instans baru scheduler (simulasi restart aplikasi di jam 07:00:00)
    clock = SimulatedClock(datetime(2026, 6, 1, 7, 0, 0))
    new_player = AudioPlayer(db)
    new_scheduler = SchedulerService(db, new_player, clock)
    new_scheduler.start()
    new_scheduler._tick()

    # Verifikasi audio tidak diputar
    assert new_player.is_playing() is False
    assert (today_str, sched.id) in new_scheduler._executed_cache

    # 3. Uji hal yang sama untuk status 'completed'
    with db.session() as conn:
        conn.execute("DELETE FROM bell_logs")
    log_repo.add_log(
        BellLog(
            id=None,
            schedule_id=sched.id,
            scheduled_at=f"{today_str}T07:00:00",
            executed_at=f"{today_str}T07:00:00",
            event_name="Bel Pagi",
            execution_mode="OTOMATIS",
            status="completed",
            message="Selesai sebelumnya",
        )
    )

    restart_player = AudioPlayer(db)
    restart_scheduler = SchedulerService(db, restart_player, clock)
    restart_scheduler.start()
    restart_scheduler._tick()

    assert restart_player.is_playing() is False
    assert (today_str, sched.id) in restart_scheduler._executed_cache

    restart_scheduler.stop()
    restart_player.cleanup()


def test_next_day_schedules_execute_normally_after_midnight_rollover(test_setup):
    """Memverifikasi bahwa jadwal di hari berikutnya dieksekusi secara normal setelah midnight rollover."""
    db, audios = test_setup
    sched_repo = ScheduleRepository(db)
    prof_repo = ProfileRepository(db)
    log_repo = BellLogRepository(db)
    active_prof = prof_repo.get_active()

    with db.session() as conn:
        conn.execute("DELETE FROM schedules")

    # Buat jadwal Senin 07:00 dan Selasa 07:00
    sched_senin = sched_repo.create(
        Schedule(
            id=None,
            profile_id=active_prof.id,
            day_of_week="Senin",
            bell_time="07:00:00",
            event_name="Bel Senin",
            audio_id=audios["BEL A"].id,
            is_enabled=True,
        )
    )
    sched_selasa = sched_repo.create(
        Schedule(
            id=None,
            profile_id=active_prof.id,
            day_of_week="Selasa",
            bell_time="07:00:00",
            event_name="Bel Selasa",
            audio_id=audios["BEL B"].id,
            is_enabled=True,
        )
    )

    # 1. Hari Senin 07:00:00 dieksekusi normal
    clock = SimulatedClock(datetime(2026, 6, 1, 7, 0, 0))  # Senin
    player = AudioPlayer(db)
    scheduler = SchedulerService(db, player, clock)
    scheduler.start()
    scheduler._tick()

    assert player.is_playing() is True
    assert player.current_title == "Bel Senin"
    player.stop()

    # 2. Pindah ke hari Selasa 07:00:00 (pergantian hari)
    clock.set_time(datetime(2026, 6, 2, 7, 0, 0))  # Selasa
    scheduler._tick()

    # Jadwal Selasa harus berbunyi secara normal
    assert player.is_playing() is True
    assert player.current_title == "Bel Selasa"

    logs = log_repo.get_logs(limit=5)
    selasa_log = next(l for l in logs if l.schedule_id == sched_selasa.id)
    assert selasa_log.status == "playing"

    scheduler.stop()
    player.cleanup()


def test_main_window_missed_banner_ui_integration(qapp, test_setup):
    """Memverifikasi tampilan banner notifikasi jadwal terlewat pada MainWindow."""
    db, audios = test_setup
    win = MainWindow(db)
    win.show()
    qapp.processEvents()

    assert hasattr(win, "missed_notif_banner")
    assert win.missed_notif_banner.isVisible() is False

    # Simulasikan sinyal schedule_missed dari scheduler
    win.scheduler.schedule_missed.emit("Bel Upacara", "07:00:00", "Dilewati karena audio manual")
    qapp.processEvents()

    assert win.missed_notif_banner.isVisible() is True
    assert "Bel Upacara" in win.missed_notif_banner.text()
    assert "07:00" in win.missed_notif_banner.text()

    win.close()

