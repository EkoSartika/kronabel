"""
Pengujian Sistem Interupsi dan Prioritas Audio Bel (Update v1.2.1).
Menguji secara deterministik seluruh 15 skenario wajib:
1. Bel otomatis berjalan -> tombol bel manual ditekan -> audio otomatis berhenti, audio manual langsung berbunyi.
2. Bel manual A berjalan -> tombol bel manual B ditekan -> A berhenti, B langsung berbunyi.
3. Tombol bel manual yang sama ditekan dua kali saat audio berjalan -> pemutaran sebelumnya berhenti dan dimulai ulang dari awal.
4. Tombol Stop ditekan saat bel otomatis berjalan -> audio otomatis berhenti dan status bersih.
5. Tombol Stop ditekan saat bel manual berjalan -> audio manual berhenti dan status bersih.
6. Audio selesai normal -> status aktif dibersihkan.
7. Audio gagal dimuat/diputar -> error ditangani dan status aktif dibersihkan.
8. Scheduler otomatis tetap ON setelah interupsi manual.
9. Scheduler OFF tidak menghalangi bel manual berbunyi.
10. Jadwal otomatis berikutnya tetap berjalan setelah bel otomatis sebelumnya diinterupsi manual (tanpa mengulang jadwal yang diinterupsi).
11. Dua perintah audio beruntun tidak menghasilkan dua audio aktif bersamaan.
12. Callback/sinyal selesai dari audio lama yang sudah dihentikan tidak mengubah status audio baru.
13. File audio hilang atau path tidak valid tidak menyebabkan aplikasi crash.
14. Pergantian bel manual berulang-ulang berjalan tanpa crash atau duplikasi sinyal.
15. Kebijakan konflik deterministik ketika jadwal otomatis baru tiba saat bel manual masih aktif berbunyi & integrasi UI MainWindow.
"""

from __future__ import annotations

import os
import struct
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

import pytest
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication, QPushButton

from src.database.db import DatabaseManager
from src.database.repositories import (
    AudioRepository,
    BellLogRepository,
    ProfileRepository,
    ScheduleRepository,
)
from src.models.models import AudioFile, Schedule
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


def make_test_wav(path: Path, freq_marker: int = 1) -> Path:
    """Membuat berkas WAV PCM mono 1 detik yang valid."""
    sample_rate = 8000
    num_samples = 8000
    data_size = num_samples * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sample_rate,
        sample_rate * 2,
        2,
        16,
        b"data",
        data_size,
    )
    sample_bytes = struct.pack("<h", freq_marker * 100) * num_samples
    path.write_bytes(header + sample_bytes)
    return path


@pytest.fixture
def env_setup(qapp, tmp_path: Path) -> Tuple[DatabaseManager, Dict[str, AudioFile]]:
    """Menyiapkan database terisolasi dengan profil aktif dan beberapa berkas audio WAV uji."""
    db_path = tmp_path / "interruption_v121.db"
    db = DatabaseManager(db_path)
    db.initialize_database()

    audio_repo = AudioRepository(db)
    audios: Dict[str, AudioFile] = {}

    for idx, (code, name) in enumerate(
        [
            ("BEL A", "Bel Masuk Pagi"),
            ("BEL B", "Bel Pergantian Jam"),
            ("BEL C", "Bel Istirahat"),
            ("TES 1", "Tes Audio 1"),
        ],
        start=1,
    ):
        wav_path = make_test_wav(tmp_path / f"audio_{idx}.wav", freq_marker=idx)
        created = audio_repo.create(
            AudioFile(
                code=code,
                name=name,
                stored_path=str(wav_path),
                original_filename=wav_path.name,
            )
        )
        assert created is not None
        audios[code] = created

    return db, audios


# ==============================================================================
# Skenario 1: Bel otomatis berjalan -> tombol bel manual ditekan ->
#             audio otomatis berhenti, audio manual langsung berbunyi.
# ==============================================================================
def test_01_auto_bell_interrupted_by_manual_bell(env_setup):
    db, audios = env_setup
    sched_repo = ScheduleRepository(db)
    prof_repo = ProfileRepository(db)
    log_repo = BellLogRepository(db)
    active_prof = prof_repo.get_active()

    with db.session() as conn:
        conn.execute("DELETE FROM schedules")
    created_sched = sched_repo.create(
        Schedule(
            id=None,
            profile_id=active_prof.id,
            day_of_week="Senin",
            bell_time="07:00:00",
            event_name="Bel Masuk Otomatis",
            audio_id=audios["BEL A"].id,
            is_enabled=True,
        )
    )
    sched_id = created_sched.id

    clock = SimulatedClock(datetime(2026, 6, 1, 7, 0, 0))  # Senin 07:00:00
    player = AudioPlayer(db)
    scheduler = SchedulerService(db, player, clock)

    interrupted_reasons = []
    started_titles = []
    player.playback_interrupted.connect(lambda r: interrupted_reasons.append(r))
    player.playback_started.connect(lambda t: started_titles.append(t))

    # 1. Picu bel otomatis pukul 07:00:00
    scheduler.start()
    scheduler._tick()
    assert player.is_playing() is True
    assert player.current_mode == "OTOMATIS"
    assert player.current_title == "Bel Masuk Otomatis"
    auto_session_id = player.active_session_id

    # 2. Operator menekan tombol bel manual BEL B saat bel otomatis masih berjalan
    ok = scheduler.trigger_manual_bell(
        audio_id=audios["BEL B"].id,
        event_name="Manual [BEL B] Bel Pergantian Jam",
        audio_path=audios["BEL B"].stored_path,
    )
    assert ok is True
    assert len(interrupted_reasons) == 1
    assert player.is_playing() is True
    assert player.current_mode == "MANUAL"
    assert player.current_title == "Manual [BEL B] Bel Pergantian Jam"
    assert player.current_file_path == Path(audios["BEL B"].stored_path).resolve()
    assert player.active_session_id > auto_session_id

    # Verifikasi log bel otomatis tercatat 'interrupted' dan bel manual 'playing'
    logs = log_repo.get_logs(limit=5)
    auto_log = next(l for l in logs if l.schedule_id == sched_id)
    manual_log = next(l for l in logs if l.execution_mode == "MANUAL")
    assert auto_log.status == "interrupted"
    assert manual_log.status == "playing"

    scheduler.stop()
    player.cleanup()


# ==============================================================================
# Skenario 2: Bel manual A berjalan -> tombol bel manual B ditekan ->
#             A berhenti, B langsung berbunyi.
# ==============================================================================
def test_02_manual_a_interrupted_by_manual_b(env_setup):
    db, audios = env_setup
    log_repo = BellLogRepository(db)
    clock = SimulatedClock(datetime(2026, 6, 1, 8, 0, 0))
    player = AudioPlayer(db)
    scheduler = SchedulerService(db, player, clock)

    interrupted_events = []
    player.playback_interrupted.connect(lambda r: interrupted_events.append(r))

    # 1. Putar Bel Manual A
    assert scheduler.trigger_manual_bell(
        audio_id=audios["BEL A"].id,
        event_name="Manual [BEL A]",
        audio_path=audios["BEL A"].stored_path,
    ) is True
    session_a = player.active_session_id
    assert player.is_playing() is True
    assert player.current_title == "Manual [BEL A]"
    assert player.current_audio_id == audios["BEL A"].id

    # 2. Tekan Bel Manual B saat A sedang berbunyi
    assert scheduler.trigger_manual_bell(
        audio_id=audios["BEL B"].id,
        event_name="Manual [BEL B]",
        audio_path=audios["BEL B"].stored_path,
    ) is True
    session_b = player.active_session_id

    assert len(interrupted_events) == 1
    assert session_b > session_a
    assert player.is_playing() is True
    assert player.current_title == "Manual [BEL B]"
    assert player.current_audio_id == audios["BEL B"].id

    logs = log_repo.get_logs(limit=5)
    log_a = next(l for l in logs if l.event_name == "Manual [BEL A]")
    log_b = next(l for l in logs if l.event_name == "Manual [BEL B]")
    assert log_a.status == "interrupted"
    assert log_b.status == "playing"

    player.cleanup()


# ==============================================================================
# Skenario 3: Tombol bel manual yang sama ditekan dua kali saat audio berjalan ->
#             pemutaran sebelumnya berhenti dan dimulai ulang dari awal.
# ==============================================================================
def test_03_same_manual_button_pressed_twice_restarts_from_beginning(env_setup):
    db, audios = env_setup
    clock = SimulatedClock(datetime(2026, 6, 1, 8, 10, 0))
    player = AudioPlayer(db)
    scheduler = SchedulerService(db, player, clock)

    interrupted_signals = []
    started_signals = []
    player.playback_interrupted.connect(lambda r: interrupted_signals.append(r))
    player.playback_started.connect(lambda t: started_signals.append(t))

    # Tekan BEL A pertama kali
    assert scheduler.trigger_manual_bell(
        audio_id=audios["BEL A"].id,
        event_name="Manual [BEL A]",
        audio_path=audios["BEL A"].stored_path,
    ) is True
    first_session = player.active_session_id
    assert player.start_count == 1

    # Tekan BEL A kedua kali saat masih berbunyi
    assert scheduler.trigger_manual_bell(
        audio_id=audios["BEL A"].id,
        event_name="Manual [BEL A]",
        audio_path=audios["BEL A"].stored_path,
    ) is True
    second_session = player.active_session_id

    assert len(interrupted_signals) == 1
    assert len(started_signals) == 2
    assert second_session > first_session
    assert player.start_count == 2
    assert player.is_playing() is True
    assert player.current_title == "Manual [BEL A]"
    assert player.player.position() == 0

    player.cleanup()


# ==============================================================================
# Skenario 4: Tombol Stop ditekan saat bel otomatis berjalan ->
#             audio otomatis berhenti dan status bersih.
# ==============================================================================
def test_04_stop_button_stops_automatic_bell_and_cleans_state(env_setup):
    db, audios = env_setup
    sched_repo = ScheduleRepository(db)
    prof_repo = ProfileRepository(db)
    log_repo = BellLogRepository(db)
    active_prof = prof_repo.get_active()

    with db.session() as conn:
        conn.execute("DELETE FROM schedules")
    created_sched = sched_repo.create(
        Schedule(
            id=None,
            profile_id=active_prof.id,
            day_of_week="Senin",
            bell_time="07:00:00",
            event_name="Bel Masuk",
            audio_id=audios["BEL A"].id,
            is_enabled=True,
        )
    )
    sched_id = created_sched.id

    clock = SimulatedClock(datetime(2026, 6, 1, 7, 0, 0))
    player = AudioPlayer(db)
    scheduler = SchedulerService(db, player, clock)
    # 1. Picu bel otomatis pukul 07:00:00
    scheduler.start()
    scheduler._tick()

    assert player.is_playing() is True
    assert player.current_title == "Bel Masuk"

    # Tekan Stop
    player.stop(reason="Tombol Stop ditekan operator")

    assert player.is_playing() is False
    assert player.status == AudioStatus.INTERRUPTED
    assert player.current_title == ""
    assert player.current_file_path is None
    assert player.current_mode == ""
    assert player.current_audio_id is None
    assert player.active_session_id == 0

    logs = log_repo.get_logs(limit=5)
    auto_log = next(l for l in logs if l.schedule_id == sched_id)
    assert auto_log.status == "interrupted"

    scheduler.stop()
    player.cleanup()


# ==============================================================================
# Skenario 5: Tombol Stop ditekan saat bel manual berjalan ->
#             audio manual berhenti dan status bersih.
# ==============================================================================
def test_05_stop_button_stops_manual_bell_and_cleans_state(env_setup):
    db, audios = env_setup
    log_repo = BellLogRepository(db)
    clock = SimulatedClock(datetime(2026, 6, 1, 9, 0, 0))
    player = AudioPlayer(db)
    scheduler = SchedulerService(db, player, clock)

    assert scheduler.trigger_manual_bell(
        audio_id=audios["BEL C"].id,
        event_name="Manual [BEL C]",
        audio_path=audios["BEL C"].stored_path,
    ) is True
    assert player.is_playing() is True

    # Tekan Stop
    player.stop(reason="Tombol Stop ditekan")

    assert player.is_playing() is False
    assert player.status == AudioStatus.INTERRUPTED
    assert player.current_title == ""
    assert player.current_file_path is None
    assert player.current_mode == ""
    assert player.current_audio_id is None
    assert player.active_session_id == 0

    logs = log_repo.get_logs(limit=5)
    assert logs[0].status == "interrupted"
    player.cleanup()


# ==============================================================================
# Skenario 6: Audio selesai normal -> status aktif dibersihkan.
# ==============================================================================
def test_06_normal_playback_completion_cleans_active_state(env_setup):
    db, audios = env_setup
    log_repo = BellLogRepository(db)
    clock = SimulatedClock(datetime(2026, 6, 1, 9, 15, 0))
    player = AudioPlayer(db)
    scheduler = SchedulerService(db, player, clock)

    completed_count = []
    player.playback_completed.connect(lambda: completed_count.append(1))

    assert scheduler.trigger_manual_bell(
        audio_id=audios["BEL A"].id,
        event_name="Manual [BEL A]",
        audio_path=audios["BEL A"].stored_path,
    ) is True
    assert player.is_playing() is True

    # Simulasikan sinyal selesai normal dari QMediaPlayer (EndOfMedia)
    player._on_media_status_changed(QMediaPlayer.MediaStatus.EndOfMedia)

    assert len(completed_count) == 1
    assert player.status == AudioStatus.COMPLETED
    assert player.is_playing() is False
    assert player.current_title == ""
    assert player.current_file_path is None
    assert player.current_mode == ""
    assert player.current_audio_id is None
    assert player.active_session_id == 0

    logs = log_repo.get_logs(limit=5)
    assert logs[0].status == "completed"
    player.cleanup()


# ==============================================================================
# Skenario 7: Audio gagal dimuat/diputar -> error ditangani dan status aktif dibersihkan.
# ==============================================================================
def test_07_playback_error_cleans_active_state(env_setup):
    db, audios = env_setup
    log_repo = BellLogRepository(db)
    clock = SimulatedClock(datetime(2026, 6, 1, 9, 30, 0))
    player = AudioPlayer(db)
    scheduler = SchedulerService(db, player, clock)

    errors = []
    player.playback_failed.connect(lambda msg: errors.append(msg))

    assert scheduler.trigger_manual_bell(
        audio_id=audios["BEL A"].id,
        event_name="Manual [BEL A]",
        audio_path=audios["BEL A"].stored_path,
    ) is True

    # Simulasikan kegagalan media runtime (InvalidMedia)
    player._on_media_status_changed(QMediaPlayer.MediaStatus.InvalidMedia)

    assert len(errors) == 1
    assert player.status == AudioStatus.FAILED
    assert player.is_playing() is False
    assert player.current_title == ""
    assert player.current_file_path is None
    assert player.current_mode == ""
    assert player.current_audio_id is None
    assert player.active_session_id == 0

    logs = log_repo.get_logs(limit=5)
    assert logs[0].status == "failed"
    player.cleanup()


# ==============================================================================
# Skenario 8: Scheduler otomatis tetap ON setelah interupsi manual.
# ==============================================================================
def test_08_scheduler_remains_on_after_manual_interruption(env_setup):
    db, audios = env_setup
    sched_repo = ScheduleRepository(db)
    prof_repo = ProfileRepository(db)
    active_prof = prof_repo.get_active()

    with db.session() as conn:
        conn.execute("DELETE FROM schedules")
    sched_repo.create(
        Schedule(
            id=None,
            profile_id=active_prof.id,
            day_of_week="Senin",
            bell_time="07:00:00",
            event_name="Bel Masuk",
            audio_id=audios["BEL A"].id,
            is_enabled=True,
        )
    )

    clock = SimulatedClock(datetime(2026, 6, 1, 7, 0, 0))
    player = AudioPlayer(db)
    scheduler = SchedulerService(db, player, clock)
    scheduler.start()
    assert scheduler.is_active is True

    # Interupsi dengan bel manual
    scheduler.trigger_manual_bell(
        audio_id=audios["BEL B"].id,
        event_name="Manual [BEL B]",
        audio_path=audios["BEL B"].stored_path,
    )
    assert scheduler.is_active is True
    assert scheduler._timer.isActive() is True

    # Bahkan setelah tombol Stop ditekan, scheduler tetap ON
    player.stop()
    assert scheduler.is_active is True
    assert scheduler._timer.isActive() is True

    scheduler.stop()
    player.cleanup()


# ==============================================================================
# Skenario 9: Scheduler OFF tidak menghalangi bel manual berbunyi.
# ==============================================================================
def test_09_scheduler_off_does_not_block_manual_bell(env_setup):
    db, audios = env_setup
    clock = SimulatedClock(datetime(2026, 6, 1, 10, 0, 0))
    player = AudioPlayer(db)
    scheduler = SchedulerService(db, player, clock)

    # Pastikan scheduler berstatus OFF
    scheduler.stop()
    assert scheduler.is_active is False

    # Tekan bel manual A, lalu interupsi dengan bel manual B saat scheduler OFF
    assert scheduler.trigger_manual_bell(
        audio_id=audios["BEL A"].id,
        event_name="Manual [BEL A]",
        audio_path=audios["BEL A"].stored_path,
    ) is True
    assert player.is_playing() is True
    assert scheduler.is_active is False

    assert scheduler.trigger_manual_bell(
        audio_id=audios["BEL B"].id,
        event_name="Manual [BEL B]",
        audio_path=audios["BEL B"].stored_path,
    ) is True
    assert player.is_playing() is True
    assert player.current_title == "Manual [BEL B]"
    assert scheduler.is_active is False

    player.cleanup()


# ==============================================================================
# Skenario 10: Jadwal otomatis berikutnya tetap berjalan setelah bel otomatis
#              sebelumnya diinterupsi manual (dan jadwal yang diinterupsi tidak diulang).
# ==============================================================================
def test_10_next_automatic_schedule_runs_after_manual_interrupt(env_setup):
    db, audios = env_setup
    sched_repo = ScheduleRepository(db)
    prof_repo = ProfileRepository(db)
    log_repo = BellLogRepository(db)
    active_prof = prof_repo.get_active()

    with db.session() as conn:
        conn.execute("DELETE FROM schedules")
    sc_0700 = sched_repo.create(
        Schedule(
            id=None,
            profile_id=active_prof.id,
            day_of_week="Senin",
            bell_time="07:00:00",
            event_name="Bel 07:00",
            audio_id=audios["BEL A"].id,
            is_enabled=True,
        )
    )
    id_0700 = sc_0700.id

    sc_0740 = sched_repo.create(
        Schedule(
            id=None,
            profile_id=active_prof.id,
            day_of_week="Senin",
            bell_time="07:40:00",
            event_name="Bel 07:40",
            audio_id=audios["BEL B"].id,
            is_enabled=True,
        )
    )
    id_0740 = sc_0740.id

    clock = SimulatedClock(datetime(2026, 6, 1, 7, 0, 0))
    player = AudioPlayer(db)
    scheduler = SchedulerService(db, player, clock)

    triggered = []
    scheduler.bell_triggered.connect(lambda name, sid, mode: triggered.append((name, sid, mode)))

    # 1. Pukul 07:00:00 -> Bel 07:00 berbunyi otomatis
    scheduler.start()
    scheduler._tick()
    assert len(triggered) == 1
    assert triggered[-1] == ("Bel 07:00", id_0700, "OTOMATIS")

    # 2. Pukul 07:00:01 -> Operator menginterupsi dengan Bel Manual C
    clock.set_time(datetime(2026, 6, 1, 7, 0, 1))
    scheduler.trigger_manual_bell(
        audio_id=audios["BEL C"].id,
        event_name="Manual [BEL C]",
        audio_path=audios["BEL C"].stored_path,
    )
    assert player.current_title == "Manual [BEL C]"

    # 3. Detik masih di menit 07:00 (misal 07:00:05) -> Bel 07:00 TIDAK boleh diulang!
    player._on_media_status_changed(QMediaPlayer.MediaStatus.EndOfMedia)  # Manual C selesai
    clock.set_time(datetime(2026, 6, 1, 7, 0, 5))
    scheduler._tick()
    auto_0700_triggers = [t for t in triggered if t[1] == id_0700]
    assert len(auto_0700_triggers) == 1
    assert log_repo.is_schedule_executed_today(id_0700, "2026-06-01") is True

    # 4. Pukul 07:40:00 -> Jadwal otomatis berikutnya (Bel 07:40) tetap dieksekusi normal
    clock.set_time(datetime(2026, 6, 1, 7, 40, 0))
    scheduler._tick()
    assert triggered[-1] == ("Bel 07:40", id_0740, "OTOMATIS")
    assert player.is_playing() is True
    assert player.current_title == "Bel 07:40"

    scheduler.stop()
    player.cleanup()


# ==============================================================================
# Skenario 11: Dua perintah audio beruntun tidak menghasilkan dua audio aktif bersamaan.
# ==============================================================================
def test_11_back_to_back_commands_enforce_single_active_audio(env_setup):
    db, audios = env_setup
    player = AudioPlayer(db)

    ok1 = player.play_file(audios["BEL A"].stored_path, title="Audio 1", mode="MANUAL", audio_id=audios["BEL A"].id)
    s1 = player.active_session_id
    ok2 = player.play_file(audios["BEL B"].stored_path, title="Audio 2", mode="MANUAL", audio_id=audios["BEL B"].id)
    s2 = player.active_session_id

    assert ok1 is True
    assert ok2 is True
    assert s2 == s1 + 1
    assert player.is_playing() is True
    assert player.current_title == "Audio 2"
    assert player.current_audio_id == audios["BEL B"].id
    assert player.current_file_path == Path(audios["BEL B"].stored_path).resolve()

    player.cleanup()


# ==============================================================================
# Skenario 12: Callback/sinyal selesai dari audio lama yang sudah dihentikan
#              tidak mengubah status audio baru.
# ==============================================================================
def test_12_stale_callback_from_old_audio_does_not_affect_new_audio(env_setup):
    db, audios = env_setup
    player = AudioPlayer(db)

    # 1. Mulai Audio A (session 1)
    assert player.play_file(audios["BEL A"].stored_path, title="Audio Lama", mode="MANUAL") is True
    old_session = player.active_session_id

    # 2. Interupsi dengan Audio B (session 2)
    assert player.play_file(audios["BEL B"].stored_path, title="Audio Baru", mode="MANUAL") is True
    new_session = player.active_session_id
    assert new_session > old_session

    # 3. Simulasikan callback terlambat/usang yang membawa session_id lama (old_session)
    player._on_playback_state_changed(QMediaPlayer.PlaybackState.StoppedState, session_id=old_session)
    player._on_media_status_changed(QMediaPlayer.MediaStatus.EndOfMedia, session_id=old_session)
    player._on_error_occurred(QMediaPlayer.Error.ResourceError, "Stale error", session_id=old_session)

    # Status Audio Baru TIDAK boleh terganggu oleh callback sesi lama
    assert player.status == AudioStatus.PLAYING
    assert player.is_playing() is True
    assert player.current_title == "Audio Baru"
    assert player.active_session_id == new_session

    # 4. Simulasikan juga selama flag _suppress_callbacks aktif
    player._suppress_callbacks = True
    try:
        player._on_playback_state_changed(QMediaPlayer.PlaybackState.StoppedState, session_id=new_session)
    finally:
        player._suppress_callbacks = False

    assert player.status == AudioStatus.PLAYING
    assert player.current_title == "Audio Baru"

    player.cleanup()


# ==============================================================================
# Skenario 13: File audio hilang atau path tidak valid tidak menyebabkan aplikasi crash.
# ==============================================================================
def test_13_missing_or_invalid_audio_file_handled_gracefully(env_setup, tmp_path: Path):
    db, audios = env_setup
    clock = SimulatedClock(datetime(2026, 6, 1, 11, 0, 0))
    player = AudioPlayer(db)
    scheduler = SchedulerService(db, player, clock)

    # Putar audio valid terlebih dahulu
    assert scheduler.trigger_manual_bell(
        audio_id=audios["BEL A"].id,
        event_name="Manual [BEL A]",
        audio_path=audios["BEL A"].stored_path,
    ) is True
    assert player.is_playing() is True

    # Sekarang picu bel manual dengan path file yang tidak ada -> audio sebelumnya harus berhenti & tidak crash
    missing_path = tmp_path / "tidak_ada_file.mp3"
    ok = scheduler.trigger_manual_bell(
        audio_id=99999,
        event_name="Manual File Hilang",
        audio_path=missing_path,
    )
    assert ok is False
    assert player.status == AudioStatus.FAILED
    assert player.is_playing() is False
    assert player.current_title == ""
    assert player.active_session_id == 0

    # Setelah gagal, tombol bel manual yang valid berikutnya tetap bisa langsung berbunyi
    assert scheduler.trigger_manual_bell(
        audio_id=audios["BEL B"].id,
        event_name="Manual [BEL B]",
        audio_path=audios["BEL B"].stored_path,
    ) is True
    assert player.is_playing() is True
    assert player.current_title == "Manual [BEL B]"

    player.cleanup()


# ==============================================================================
# Skenario 14: Pergantian bel manual berulang-ulang berjalan tanpa crash atau duplikasi sinyal.
# ==============================================================================
def test_14_rapid_repeated_manual_switching_no_crash_or_signal_leak(env_setup):
    db, audios = env_setup
    clock = SimulatedClock(datetime(2026, 6, 1, 12, 0, 0))
    player = AudioPlayer(db)
    scheduler = SchedulerService(db, player, clock)

    started_events = []
    interrupted_events = []
    player.playback_started.connect(lambda title: started_events.append(title))
    player.playback_interrupted.connect(lambda reason: interrupted_events.append(reason))

    codes = ["BEL A", "BEL B", "BEL C", "TES 1", "BEL A", "BEL A", "BEL B", "BEL C", "TES 1", "BEL A"]
    for idx, code in enumerate(codes):
        af = audios[code]
        ok = scheduler.trigger_manual_bell(
            audio_id=af.id,
            event_name=f"Rapid #{idx} [{code}]",
            audio_path=af.stored_path,
        )
        assert ok is True
        assert player.is_playing() is True
        assert player.current_title == f"Rapid #{idx} [{code}]"

    # 10 pemutaran beruntun -> 10 kali playback_started dan tepat 9 kali playback_interrupted
    assert len(started_events) == len(codes)
    assert len(interrupted_events) == len(codes) - 1
    assert player.active_session_id == len(codes)

    player.stop()
    assert player.is_playing() is False
    assert player.current_title == ""
    player.cleanup()


# ==============================================================================
# Skenario 15: Kebijakan konflik deterministik saat jadwal otomatis baru tiba
#              ketika bel manual masih sedang berjalan & integrasi UI MainWindow.
# ==============================================================================
def test_15_conflict_policy_and_ui_main_window_integration(qapp, env_setup):
    db, audios = env_setup
    sched_repo = ScheduleRepository(db)
    prof_repo = ProfileRepository(db)
    log_repo = BellLogRepository(db)
    active_prof = prof_repo.get_active()

    with db.session() as conn:
        conn.execute("DELETE FROM schedules")
    created_sc = sched_repo.create(
        Schedule(
            id=None,
            profile_id=active_prof.id,
            day_of_week="Senin",
            bell_time="08:00:00",
            event_name="Bel Otomatis 08:00",
            audio_id=audios["BEL A"].id,
            is_enabled=True,
        )
    )
    sched_id = created_sc.id

    # A. Uji kebijakan konflik: bel manual sedang aktif saat pukul 08:00:00 tiba
    clock = SimulatedClock(datetime(2026, 6, 1, 7, 59, 55))
    player = AudioPlayer(db)
    scheduler = SchedulerService(db, player, clock)
    scheduler.start()

    missed_signals = []
    scheduler.schedule_missed.connect(lambda ev, bt, msg: missed_signals.append((ev, bt, msg)))

    # Operator menyalakan bel manual pada 07:59:55
    scheduler.trigger_manual_bell(
        audio_id=audios["TES 1"].id,
        event_name="Manual [TES 1]",
        audio_path=audios["TES 1"].stored_path,
    )
    assert player.is_playing() is True
    assert player.current_mode == "MANUAL"

    # Pukul 08:00:00 tiba saat bel manual masih berbunyi ->
    # Bel manual TIDAK boleh terpotong diam-diam, sinyal notifikasi dipancarkan, dan konflik dicatat eksplisit sebagai 'missed'
    clock.set_time(datetime(2026, 6, 1, 8, 0, 0))
    scheduler._tick()

    assert player.is_playing() is True
    assert player.current_mode == "MANUAL"
    assert player.current_title == "Manual [TES 1]"
    assert len(missed_signals) == 1
    assert missed_signals[0][0] == "Bel Otomatis 08:00"
    assert "08:00" in missed_signals[0][1]

    logs = log_repo.get_logs(limit=5)
    conflict_log = next(l for l in logs if l.schedule_id == sched_id)
    assert conflict_log.status == "missed"
    assert "dilewati" in conflict_log.message

    scheduler.stop()
    player.cleanup()

    # B. Uji integrasi langsung tombol manual & tombol Stop pada MainWindow UI
    win = MainWindow(db)
    win.show()
    qapp.processEvents()

    btn_bel_a = next(b for b in win.manual_container.findChildren(QPushButton) if b.text() == "BEL A")
    btn_bel_b = next(b for b in win.manual_container.findChildren(QPushButton) if b.text() == "BEL B")

    # Klik BEL A
    btn_bel_a.click()
    qapp.processEvents()
    assert win.audio_player.is_playing() is True
    assert "BEL A" in win.active_audio_title
    assert "BEL A" in win.btn_stop_audio.toolTip()

    # Klik BEL B saat BEL A masih berjalan -> langsung berganti ke BEL B
    btn_bel_b.click()
    qapp.processEvents()
    assert win.audio_player.is_playing() is True
    assert "BEL B" in win.active_audio_title
    assert "BEL B" in win.btn_stop_audio.toolTip()

    # Klik Stop -> audio berhenti dan status UI bersih
    win.btn_stop_audio.click()
    qapp.processEvents()
    assert win.audio_player.is_playing() is False
    assert win.active_audio_title == ""
    assert win.btn_stop_audio.toolTip() == "Tidak ada audio aktif"

    win.close()

