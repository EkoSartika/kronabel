"""
Pengujian Integrasi Operasional Satu Hari Sekolah Penuh (Full-Day Simulation Test)
Mensimulasikan seluruh operasional bel sekolah dari sebelum bel pertama hingga pergantian hari berikutnya.

Mencakup 12 Skenario Wajib:
1. Aplikasi dibuka dan profil aktif terbaca dengan benar.
2. Countdown menunjukkan waktu menuju bel berikutnya secara konsisten.
3. Bel otomatis dijalankan tepat satu kali pada waktu yang dijadwalkan.
4. Scheduler tidak membunyikan bel yang sama berulang kali pada menit yang sama.
5. Jadwal yang sudah dieksekusi tidak dijalankan ulang setelah waktu simulasi bergerak maju.
6. Pergantian hari dan perubahan tanggal ditangani dengan benar (midnight rollover).
7. Jadwal yang dinonaktifkan (is_enabled=False) tidak dijalankan.
8. Profil yang aktif menentukan jadwal yang benar.
9. Bel manual tidak merusak status scheduler atau menyebabkan bel otomatis ganda.
10. Kegagalan audio tercatat dengan status dan keterangan yang sesuai.
11. Penutupan aplikasi menghentikan proses yang relevan dengan aman.
12. Pembukaan kembali aplikasi (restart di tengah hari) tidak mengeksekusi ulang jadwal yang sudah selesai.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import pytest

from src.database.db import DatabaseManager
from src.database.repositories import (
    AudioRepository,
    BellLogRepository,
    ProfileRepository,
    ScheduleRepository,
)
from src.models.models import AudioFile, Profile, Schedule
from src.services.audio_player import AudioPlayer, AudioStatus
from src.services.clock_service import SimulatedClock
from src.services.scheduler import SchedulerService


@pytest.fixture
def school_day_setup(tmp_path: Path):
    """Menyiapkan database dan berkas audio untuk simulasi satu hari penuh."""
    db_file = tmp_path / "school_sim.db"
    db = DatabaseManager(db_file)
    db.initialize_database()

    audio_dir = tmp_path / "sounds"
    audio_dir.mkdir(parents=True, exist_ok=True)

    # 1. Buat audio uji valid (WAV header minimal)
    valid_audio_path = audio_dir / "bell_valid.wav"
    valid_audio_path.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00data\x00\x00\x00\x00")

    audio_repo = AudioRepository(db)
    valid_audio = audio_repo.create(
        AudioFile(
            name="Nada Standar Sekolah",
            stored_path=str(valid_audio_path),
            original_filename="bell_valid.wav",
            duration_seconds=5.0,
        )
    )

    # Audio sengaja hilang / path fiktif untuk menguji skenario kegagalan audio
    broken_audio = audio_repo.create(
        AudioFile(
            name="Nada Rusak / Hilang",
            stored_path=str(audio_dir / "missing_bell.wav"),
            original_filename="missing_bell.wav",
            duration_seconds=3.0,
        )
    )

    # 2. Buat profil dan jadwal
    prof_repo = ProfileRepository(db)
    reguler_prof = prof_repo.get_active()
    if not reguler_prof:
        reguler_prof = prof_repo.create(Profile(name="Reguler", is_active=True))
    prof_repo.set_active(reguler_prof.id)

    sched_repo = ScheduleRepository(db)

    # Bersihkan jadwal bawaan di hari Senin & Selasa agar terkontrol penuh
    for s in sched_repo.get_by_profile_and_day(reguler_prof.id, "Senin"):
        sched_repo.delete(s.id)
    for s in sched_repo.get_by_profile_and_day(reguler_prof.id, "Selasa"):
        sched_repo.delete(s.id)

    # Susun jadwal Senin:
    schedules_senin = [
        ("07:00:00", "Bel Masuk Pagi & Upacara", valid_audio.id, True),
        ("08:30:00", "Pergantian Jam Pelajaran 2", valid_audio.id, True),
        ("09:30:00", "Bel Istirahat Pertama", valid_audio.id, True),
        ("09:45:00", "Bel Masuk Pasca-Istirahat", valid_audio.id, True),
        ("11:15:00", "Kegiatan Literasi Mandiri", valid_audio.id, False),  # Disabled!
        ("12:00:00", "Bel Istirahat Dhuhur", valid_audio.id, True),
        ("12:30:00", "Bel Masuk Jam Siang", valid_audio.id, True),
        ("14:00:00", "Bel Pulang Sekolah", broken_audio.id, True),  # Broken audio!
    ]

    for b_time, ev_name, a_id, en in schedules_senin:
        sched_repo.create(
            Schedule(
                profile_id=reguler_prof.id,
                day_of_week="Senin",
                bell_time=b_time,
                event_name=ev_name,
                audio_id=a_id,
                is_enabled=en,
            )
        )

    # Susun jadwal Selasa:
    sched_repo.create(
        Schedule(
            profile_id=reguler_prof.id,
            day_of_week="Selasa",
            bell_time="07:00:00",
            event_name="Bel Masuk Pagi Hari Selasa",
            audio_id=valid_audio.id,
            is_enabled=True,
        )
    )

    # Profil alternatif: Ujian Semester
    ujian_prof = prof_repo.create(Profile(name="Ujian Semester", is_active=False))
    sched_repo.create(
        Schedule(
            profile_id=ujian_prof.id,
            day_of_week="Senin",
            bell_time="07:30:00",
            event_name="Mulai Ujian Sesi 1",
            audio_id=valid_audio.id,
            is_enabled=True,
        )
    )

    return {
        "db": db,
        "valid_audio": valid_audio,
        "broken_audio": broken_audio,
        "reguler_prof": reguler_prof,
        "ujian_prof": ujian_prof,
        "sched_repo": sched_repo,
        "log_repo": BellLogRepository(db),
        "prof_repo": prof_repo,
    }


def test_full_school_day_simulation(qapp, school_day_setup):
    """
    Simulasi komprehensif satu hari penuh operasional sekolah dari jam 06:45:00 Senin
    sampai dengan jam 07:00:00 Selasa hari berikutnya.
    """
    db = school_day_setup["db"]
    log_repo: BellLogRepository = school_day_setup["log_repo"]
    prof_repo: ProfileRepository = school_day_setup["prof_repo"]
    reguler_prof = school_day_setup["reguler_prof"]
    ujian_prof = school_day_setup["ujian_prof"]

    # Inisialisasi clock simulasi: Senin, 02 November 2026 pukul 06:45:00
    sim_clock = SimulatedClock(datetime(2026, 11, 2, 6, 45, 0))
    assert sim_clock.day_name() == "Senin"

    audio_player = AudioPlayer(db)
    scheduler = SchedulerService(db, audio_player, clock=sim_clock)

    # Rekam sinyal pembunyian bel
    triggered_events = []
    scheduler.bell_triggered.connect(lambda name, s_id, mode: triggered_events.append((name, s_id, mode, sim_clock.time_str())))

    def complete_audio(p: AudioPlayer):
        from PySide6.QtMultimedia import QMediaPlayer
        p._on_playback_state_changed(QMediaPlayer.PlaybackState.StoppedState)

    # =========================================================================
    # SKENARIO 1: Aplikasi dibuka dan profil aktif terbaca dengan benar
    # =========================================================================
    active_profile = prof_repo.get_active()
    assert active_profile is not None
    assert active_profile.id == reguler_prof.id
    assert active_profile.name == reguler_prof.name

    scheduler.start()
    assert scheduler.is_active is True

    # =========================================================================
    # SKENARIO 2: Countdown menunjukkan waktu menuju bel berikutnya secara konsisten
    # Pukul 06:45:00, bel berikutnya adalah 07:00:00 (15 menit = 900 detik)
    # =========================================================================
    next_s, seconds_left = scheduler.get_next_bell()
    assert next_s is not None
    assert next_s.bell_time == "07:00:00"
    assert next_s.event_name == "Bel Masuk Pagi & Upacara"
    assert seconds_left == 900

    # Majukan waktu 10 menit ke 06:55:00
    sim_clock.set_time(datetime(2026, 11, 2, 6, 55, 0))
    scheduler._tick()
    next_s, seconds_left = scheduler.get_next_bell()
    assert next_s.bell_time == "07:00:00"
    assert seconds_left == 300  # Tersisa 5 menit

    # =========================================================================
    # SKENARIO 3: Bel otomatis dijalankan tepat satu kali pada waktu yang dijadwalkan
    # Pukul 07:00:00
    # =========================================================================
    sim_clock.set_time(datetime(2026, 11, 2, 7, 0, 0))
    scheduler._tick()

    assert len(triggered_events) == 1
    assert triggered_events[-1][0] == "Bel Masuk Pagi & Upacara"
    assert triggered_events[-1][2] == "OTOMATIS"

    # =========================================================================
    # SKENARIO 4: Scheduler tidak membunyikan bel ganda pada menit/detik yang sama
    # =========================================================================
    sim_clock.set_time(datetime(2026, 11, 2, 7, 0, 15))
    scheduler._tick()
    sim_clock.set_time(datetime(2026, 11, 2, 7, 0, 45))
    scheduler._tick()
    sim_clock.set_time(datetime(2026, 11, 2, 7, 0, 59))
    scheduler._tick()

    # Jumlah pemicuan tetap 1
    assert len(triggered_events) == 1

    # Selesaikan playback
    complete_audio(audio_player)

    # =========================================================================
    # SKENARIO 5: Bel kedua dieksekusi saat waktu simulasi bergerak maju ke 08:30:00
    # =========================================================================
    sim_clock.set_time(datetime(2026, 11, 2, 8, 30, 0))
    scheduler._tick()
    assert len(triggered_events) == 2
    assert triggered_events[-1][0] == "Pergantian Jam Pelajaran 2"
    complete_audio(audio_player)

    # =========================================================================
    # SKENARIO 9: Bel manual tidak merusak status scheduler atau memicu bel ganda
    # Pada 09:00:00, operator membunyikan bel manual panggilan guru piket
    # =========================================================================
    sim_clock.set_time(datetime(2026, 11, 2, 9, 0, 0))
    manual_success = scheduler.trigger_manual_bell(audio_id=school_day_setup["valid_audio"].id, event_name="Panggilan Guru Piket")
    assert manual_success is True
    assert len(triggered_events) == 3
    assert triggered_events[-1][0] == "Panggilan Guru Piket"
    assert triggered_events[-1][2] == "MANUAL"
    complete_audio(audio_player)

    # Scheduler otomatis tetap berjalan normal
    assert scheduler.is_active is True
    next_s, _ = scheduler.get_next_bell()
    assert next_s.bell_time == "09:30:00"


    # Pukul 09:30:00 bel istirahat berbunyi
    sim_clock.set_time(datetime(2026, 11, 2, 9, 30, 0))
    scheduler._tick()
    assert len(triggered_events) == 4
    assert triggered_events[-1][0] == "Bel Istirahat Pertama"
    complete_audio(audio_player)

    # Pukul 09:45:00 bel masuk kelas berbunyi
    sim_clock.set_time(datetime(2026, 11, 2, 9, 45, 0))
    scheduler._tick()
    assert len(triggered_events) == 5
    assert triggered_events[-1][0] == "Bel Masuk Pasca-Istirahat"
    complete_audio(audio_player)

    # =========================================================================
    # SKENARIO 11 & 12: Penutupan aplikasi aman & pembukaan kembali (Restart Tengah Hari)
    # tidak menyebabkan eksekusi ulang jadwal yang sudah selesai
    # =========================================================================
    # Simulasi aplikasi ditutup pada pukul 10:00:00
    scheduler.stop()
    assert scheduler.is_active is False
    audio_player.cleanup()

    # Simulasi aplikasi dibuka kembali pada pukul 10:15:00 dengan instance baru
    new_audio_player = AudioPlayer(db)
    new_scheduler = SchedulerService(db, new_audio_player, clock=sim_clock)
    new_triggered_events = []
    new_scheduler.bell_triggered.connect(lambda name, s_id, mode: new_triggered_events.append((name, s_id, mode)))

    sim_clock.set_time(datetime(2026, 11, 2, 10, 15, 0))
    new_scheduler.start()

    # Cek bahwa bel yang sudah lewat (07:00, 08:30, 09:30, 09:45) TIDAK dieksekusi ulang
    new_scheduler._tick()
    assert len(new_triggered_events) == 0

    # =========================================================================
    # SKENARIO 7: Jadwal yang dinonaktifkan (11:15:00) TIDAK dijalankan
    # =========================================================================
    sim_clock.set_time(datetime(2026, 11, 2, 11, 15, 0))
    new_scheduler._tick()
    assert len(new_triggered_events) == 0  # 11:15:00 diabaikan karena is_enabled=False

    # Pukul 12:00:00 & 12:30:00
    sim_clock.set_time(datetime(2026, 11, 2, 12, 0, 0))
    new_scheduler._tick()
    assert len(new_triggered_events) == 1
    assert new_triggered_events[-1][0] == "Bel Istirahat Dhuhur"
    complete_audio(new_audio_player)

    sim_clock.set_time(datetime(2026, 11, 2, 12, 30, 0))
    new_scheduler._tick()
    assert len(new_triggered_events) == 2
    assert new_triggered_events[-1][0] == "Bel Masuk Jam Siang"
    complete_audio(new_audio_player)

    # =========================================================================
    # SKENARIO 10: Kegagalan audio tercatat dengan status 'failed' & pesan error sesuai
    # Pukul 14:00:00 (Bel Pulang dengan file audio yang hilang di disk)
    # =========================================================================
    sim_clock.set_time(datetime(2026, 11, 2, 14, 0, 0))
    new_scheduler._tick()

    assert len(new_triggered_events) == 3
    assert new_triggered_events[-1][0] == "Bel Pulang Sekolah"

    # Periksa log database: harus tercatat sebagai failed
    today_logs = log_repo.get_logs(date_filter="2026-11-02", status_filter="failed")
    assert len(today_logs) >= 1
    failed_log = [l for l in today_logs if l.event_name == "Bel Pulang Sekolah"][0]
    assert failed_log.status == "failed"
    assert "tidak ditemukan" in failed_log.message.lower() or "gagal" in failed_log.message.lower()

    # =========================================================================
    # SKENARIO 6: Pergantian hari dan perubahan tanggal (Midnight Rollover)
    # Bergerak ke malam hari 23:59:59, lalu ke 00:00:01 hari Selasa (2026-11-03)
    # =========================================================================
    sim_clock.set_time(datetime(2026, 11, 2, 23, 59, 59))
    new_scheduler._tick()

    # Menyeberang ke hari Selasa
    sim_clock.set_time(datetime(2026, 11, 3, 0, 0, 1))
    new_scheduler._tick()

    assert sim_clock.day_name() == "Selasa"
    assert new_scheduler._last_checked_day == "2026-11-03"
    assert len(new_scheduler._executed_cache) == 0  # Cache sesi di-reset untuk hari baru

    # Pukul 07:00:00 Selasa: Bel Masuk Hari Selasa terpicu dengan sukses
    sim_clock.set_time(datetime(2026, 11, 3, 7, 0, 0))
    new_scheduler._tick()
    assert len(new_triggered_events) == 4
    assert new_triggered_events[-1][0] == "Bel Masuk Pagi Hari Selasa"
    complete_audio(new_audio_player)


    # =========================================================================
    # SKENARIO 8: Profil aktif menentukan jadwal yang benar
    # Ketika profil diganti ke 'Ujian Semester', jadwal berganti ke jadwal ujian
    # =========================================================================
    prof_repo.set_active(ujian_prof.id)
    next_s, _ = new_scheduler.get_next_bell()
    # Hari Selasa jadwal Ujian tidak ada, maka mencari hari berikutnya (Senin 07:30:00)
    assert next_s is not None
    assert next_s.profile_id == ujian_prof.id
    assert next_s.event_name == "Mulai Ujian Sesi 1"

    # Hentikan scheduler dengan aman
    new_scheduler.stop()
    new_audio_player.cleanup()
