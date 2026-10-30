"""
Pengujian Menyeluruh Layanan Mesin Penjadwal Bel (Scheduler Service).
Menguji penanganan jadwal aktif/nonaktif, profil aktif, hitung mundur,
idempotensi tepat satu kali, pergantian hari, bel terlewat, dan bel manual.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from src.database.db import DatabaseManager
from src.database.repositories import AudioRepository, BellLogRepository, ProfileRepository, ScheduleRepository
from src.models.models import AudioFile, Profile, Schedule
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
def sample_audio(temp_db: DatabaseManager) -> AudioFile:
    """Menyediakan file audio sampel di database untuk pengujian scheduler."""
    audio_repo = AudioRepository(temp_db)
    return audio_repo.create(
        AudioFile(
            id=None,
            name="Bel Standar",
            stored_path="C:/dummy/bel.wav",
            original_filename="bel.wav",
            duration_seconds=5.0,
        )
    )


class MockAudioPlayer(AudioPlayer):
    """AudioPlayer mock untuk menguji alur scheduler tanpa dependensi hardware suara."""

    def __init__(self, db: DatabaseManager):
        super().__init__(db)
        self.play_calls = []
        self.should_succeed = True

    def play_file(self, file_path, title: str = "") -> bool:
        self.play_calls.append((str(file_path), title))
        if self.should_succeed:
            self._set_status(AudioStatus.PLAYING, f"Memutar {title}")
            self.playback_started.emit(title)
            # Simulasikan selesai seketika
            self._set_status(AudioStatus.COMPLETED, "Selesai")
            self.playback_completed.emit()
            return True
        else:
            self._set_status(AudioStatus.FAILED, "Simulasi kegagalan audio")
            self.playback_failed.emit("Simulasi kegagalan audio")
            return False

    def play_audio_id(self, audio_id: int, fallback_title: str = "") -> bool:
        return self.play_file(f"dummy_audio_{audio_id}.wav", title=fallback_title)


def test_scheduler_only_processes_active_profile(qapp, temp_db: DatabaseManager, sample_audio: AudioFile):
    """Scheduler hanya mengeksekusi jadwal milik profil yang sedang aktif."""
    profile_repo = ProfileRepository(temp_db)
    schedule_repo = ScheduleRepository(temp_db)
    audio_mock = MockAudioPlayer(temp_db)

    # Profil 1 (Aktif): Reguler
    reguler = profile_repo.get_active()
    schedule_repo.create(
        Schedule(
            id=None,
            profile_id=reguler.id,
            day_of_week="Rabu",
            bell_time="07:00:00",
            event_name="Bel Reguler Pagi",
            audio_id=sample_audio.id,
        )
    )

    # Profil 2 (Nonaktif): Ramadan
    profiles = {p.name: p for p in profile_repo.get_all()}
    ramadan = profiles["Ramadan"]
    schedule_repo.create(
        Schedule(
            id=None,
            profile_id=ramadan.id,
            day_of_week="Rabu",
            bell_time="07:00:00",
            event_name="Bel Ramadan Pagi",
            audio_id=sample_audio.id,
        )
    )

    clock = SimulatedClock(datetime(2026, 10, 28, 7, 0, 0))  # Rabu 07:00:00
    scheduler = SchedulerService(temp_db, audio_mock, clock=clock)
    scheduler.start()

    # Evaluasi jadwal pada 07:00:00
    scheduler._tick()

    # Hanya bel Reguler yang diputar
    assert len(audio_mock.play_calls) == 1
    assert audio_mock.play_calls[0][1] == "Bel Reguler Pagi"


def test_scheduler_ignores_disabled_schedules(qapp, temp_db: DatabaseManager, sample_audio: AudioFile):
    """Scheduler mengabaikan jadwal yang statusnya nonaktif (is_enabled = False)."""
    profile_repo = ProfileRepository(temp_db)
    schedule_repo = ScheduleRepository(temp_db)
    audio_mock = MockAudioPlayer(temp_db)

    active_profile = profile_repo.get_active()
    schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Senin",
            bell_time="08:00:00",
            event_name="Pelajaran Dibatalkan",
            audio_id=sample_audio.id,
            is_enabled=False,
        )
    )

    clock = SimulatedClock(datetime(2026, 10, 26, 8, 0, 0))  # Senin 08:00:00
    scheduler = SchedulerService(temp_db, audio_mock, clock=clock)
    scheduler.start()
    scheduler._tick()

    assert len(audio_mock.play_calls) == 0


def test_scheduler_next_bell_selection_and_countdown(qapp, temp_db: DatabaseManager, sample_audio: AudioFile):
    """Menguji pemilihan bel berikutnya dan perhitungan hitung mundur akurat."""
    profile_repo = ProfileRepository(temp_db)
    schedule_repo = ScheduleRepository(temp_db)
    audio_mock = MockAudioPlayer(temp_db)

    active_profile = profile_repo.get_active()
    schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Senin",
            bell_time="07:00:00",
            event_name="Bel Masuk",
            audio_id=sample_audio.id,
        )
    )
    schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Senin",
            bell_time="09:30:00",
            event_name="Bel Istirahat",
            audio_id=sample_audio.id,
        )
    )

    # Waktu sekarang: Senin 07:15:00 (Bel Masuk sudah lewat, Bel Istirahat berikutnya)
    clock = SimulatedClock(datetime(2026, 10, 26, 7, 15, 0))
    scheduler = SchedulerService(temp_db, audio_mock, clock=clock)

    next_s, seconds_left = scheduler.get_next_bell()
    assert next_s is not None
    assert next_s.event_name == "Bel Istirahat"
    # Dari 07:15:00 ke 09:30:00 adalah 2 jam 15 menit = 8100 detik
    assert seconds_left == (2 * 3600) + (15 * 60)


def test_scheduler_executes_exactly_once(qapp, temp_db: DatabaseManager, sample_audio: AudioFile):
    """Mencegah eksekusi ganda pada jadwal, tanggal, dan waktu yang sama."""
    profile_repo = ProfileRepository(temp_db)
    schedule_repo = ScheduleRepository(temp_db)
    audio_mock = MockAudioPlayer(temp_db)

    active_profile = profile_repo.get_active()
    schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Kamis",
            bell_time="07:00:00",
            event_name="Bel Tepat Waktu",
            audio_id=sample_audio.id,
        )
    )

    clock = SimulatedClock(datetime(2026, 10, 29, 7, 0, 0))  # Kamis 07:00:00
    scheduler = SchedulerService(temp_db, audio_mock, clock=clock)
    scheduler.start()

    # Tick 1: Pukul 07:00:00
    scheduler._tick()
    assert len(audio_mock.play_calls) == 1

    # Tick 2: Masih pada detik yang sama atau pemeriksaan ulang
    scheduler._tick()
    assert len(audio_mock.play_calls) == 1  # Tidak bertambah!


def test_scheduler_duplicate_prevention_after_restart(qapp, temp_db: DatabaseManager, sample_audio: AudioFile):
    """Memastikan restart aplikasi tidak membunyikan ulang bel yang sudah selesai hari ini."""
    profile_repo = ProfileRepository(temp_db)
    schedule_repo = ScheduleRepository(temp_db)
    log_repo = BellLogRepository(temp_db)
    audio_mock = MockAudioPlayer(temp_db)

    active_profile = profile_repo.get_active()
    s = schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Jumat",
            bell_time="07:00:00",
            event_name="Bel Pagi Jumat",
            audio_id=sample_audio.id,
        )
    )

    clock = SimulatedClock(datetime(2026, 10, 30, 7, 0, 0))

    # Skenario: Bel telah selesai dibunyikan sebelum aplikasi ditutup
    from src.models.models import BellLog
    log_repo.add_log(
        BellLog(
            id=None,
            schedule_id=s.id,
            scheduled_at="2026-10-30T07:00:00",
            executed_at="2026-10-30T07:00:01",
            event_name="Bel Pagi Jumat",
            execution_mode="OTOMATIS",
            status="completed",
            message="Selesai pada sesi sebelumnya",
        )
    )

    # Buka sesi baru (restart)
    new_scheduler = SchedulerService(temp_db, audio_mock, clock=clock)
    new_scheduler.start()
    new_scheduler._tick()

    # Tidak boleh ada pemutaran baru karena sudah tercatat selesai
    assert len(audio_mock.play_calls) == 0


def test_scheduler_missed_schedules_not_played(qapp, temp_db: DatabaseManager, sample_audio: AudioFile):
    """Jika aplikasi baru dibuka setelah jadwal berlalu, jadwal lama tidak dibunyikan."""
    profile_repo = ProfileRepository(temp_db)
    schedule_repo = ScheduleRepository(temp_db)
    audio_mock = MockAudioPlayer(temp_db)

    active_profile = profile_repo.get_active()
    schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Senin",
            bell_time="07:00:00",
            event_name="Bel Jam Pertama",
            audio_id=sample_audio.id,
        )
    )

    # Aplikasi baru dibuka pada pukul 07:30:00
    clock = SimulatedClock(datetime(2026, 10, 26, 7, 30, 0))
    scheduler = SchedulerService(temp_db, audio_mock, clock=clock)
    scheduler.start()
    scheduler._tick()

    # Bel 07:00:00 tidak boleh diputar
    assert len(audio_mock.play_calls) == 0


def test_scheduler_stops_when_disabled(qapp, temp_db: DatabaseManager, sample_audio: AudioFile):
    """Scheduler tidak mengeksekusi apa pun saat dinonaktifkan."""
    profile_repo = ProfileRepository(temp_db)
    schedule_repo = ScheduleRepository(temp_db)
    audio_mock = MockAudioPlayer(temp_db)

    active_profile = profile_repo.get_active()
    schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Rabu",
            bell_time="07:00:00",
            event_name="Bel Pagi",
            audio_id=sample_audio.id,
        )
    )

    clock = SimulatedClock(datetime(2026, 10, 28, 7, 0, 0))
    scheduler = SchedulerService(temp_db, audio_mock, clock=clock)
    # Jangan panggil scheduler.start() -> status is_active = False
    scheduler._tick()

    assert len(audio_mock.play_calls) == 0


def test_manual_bell_does_not_affect_schedules(qapp, temp_db: DatabaseManager, sample_audio: AudioFile):
    """Bel manual dicatat terpisah dan tidak menandai jadwal otomatis sebagai selesai."""
    profile_repo = ProfileRepository(temp_db)
    schedule_repo = ScheduleRepository(temp_db)
    log_repo = BellLogRepository(temp_db)
    audio_mock = MockAudioPlayer(temp_db)

    active_profile = profile_repo.get_active()
    s = schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Rabu",
            bell_time="07:00:00",
            event_name="Bel Otomatis Terjadwal",
            audio_id=sample_audio.id,
        )
    )

    clock = SimulatedClock(datetime(2026, 10, 28, 6, 50, 0))
    scheduler = SchedulerService(temp_db, audio_mock, clock=clock)

    # Bunyikan bel manual
    scheduler.trigger_manual_bell(audio_id=sample_audio.id, event_name="Bel Manual Khusus")

    # Periksa log: ada log manual
    logs = log_repo.get_logs()
    assert len(logs) == 1
    assert logs[0].execution_mode == "MANUAL"
    assert logs[0].schedule_id is None

    # Pastikan jadwal otomatis belum ditandai selesai
    assert log_repo.is_schedule_executed_today(s.id, "2026-10-28") is False


def test_scheduler_audio_failure_logged_to_history(qapp, temp_db: DatabaseManager, sample_audio: AudioFile):
    """Kegagalan audio otomatis dicatat ke riwayat dengan status 'failed'."""
    profile_repo = ProfileRepository(temp_db)
    schedule_repo = ScheduleRepository(temp_db)
    log_repo = BellLogRepository(temp_db)
    audio_mock = MockAudioPlayer(temp_db)
    audio_mock.should_succeed = False  # Simulasikan error pemutaran

    active_profile = profile_repo.get_active()
    s = schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Selasa",
            bell_time="07:00:00",
            event_name="Bel Rusak",
            audio_id=sample_audio.id,
        )
    )

    clock = SimulatedClock(datetime(2026, 10, 27, 7, 0, 0))
    scheduler = SchedulerService(temp_db, audio_mock, clock=clock)
    scheduler.start()
    scheduler._tick()

    logs = log_repo.get_logs()
    assert len(logs) == 1
    assert logs[0].status == "failed"
    assert "Simulasi kegagalan audio" in logs[0].message


def test_main_window_close_stops_scheduler_and_audio(qapp, temp_db: DatabaseManager):
    """Menutup MainWindow menghentikan scheduler dan membersihkan audio player."""
    window = MainWindow(temp_db)
    window.scheduler.start()
    assert window.scheduler.is_active is True

    window.close()
    assert window.scheduler.is_active is False


def test_scheduler_day_rollover(qapp, temp_db: DatabaseManager, sample_audio: AudioFile):
    """Menguji bahwa pergantian hari (midnight rollover) membersihkan cache sesi dan mengeksekusi hari berikutnya."""
    profile_repo = ProfileRepository(temp_db)
    schedule_repo = ScheduleRepository(temp_db)
    audio_mock = MockAudioPlayer(temp_db)

    active_profile = profile_repo.get_active()
    # Jadwal Rabu 07:00:00
    schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Rabu",
            bell_time="07:00:00",
            event_name="Bel Hari Rabu",
            audio_id=sample_audio.id,
        )
    )
    # Jadwal Kamis 07:00:00
    schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Kamis",
            bell_time="07:00:00",
            event_name="Bel Hari Kamis",
            audio_id=sample_audio.id,
        )
    )

    clock = SimulatedClock(datetime(2026, 10, 28, 7, 0, 0))  # Rabu 07:00:00
    scheduler = SchedulerService(temp_db, audio_mock, clock=clock)
    scheduler.start()
    scheduler._tick()

    assert len(audio_mock.play_calls) == 1
    assert audio_mock.play_calls[0][1] == "Bel Hari Rabu"

    # Lompat melewati tengah malam ke Kamis 07:00:00 (1 hari = 24 jam)
    clock.set_time(datetime(2026, 10, 29, 7, 0, 0))
    scheduler._tick()

    assert len(audio_mock.play_calls) == 2
    assert audio_mock.play_calls[1][1] == "Bel Hari Kamis"


def test_scheduler_time_change_while_running(qapp, temp_db: DatabaseManager, sample_audio: AudioFile):
    """Menguji bahwa lompatan waktu sistem saat scheduler berjalan memperbarui hitung mundur secara akurat."""
    profile_repo = ProfileRepository(temp_db)
    schedule_repo = ScheduleRepository(temp_db)
    audio_mock = MockAudioPlayer(temp_db)

    active_profile = profile_repo.get_active()
    schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Senin",
            bell_time="10:00:00",
            event_name="Bel Siang",
            audio_id=sample_audio.id,
        )
    )

    clock = SimulatedClock(datetime(2026, 10, 26, 8, 0, 0))  # 2 jam menuju 10:00:00
    scheduler = SchedulerService(temp_db, audio_mock, clock=clock)

    _, seconds1 = scheduler.get_next_bell()
    assert seconds1 == 7200  # 2 jam = 7200 detik

    # Pengguna / sistem menyesuaikan jam maju 1 jam (menjadi 09:00:00)
    clock.set_time(datetime(2026, 10, 26, 9, 0, 0))
    _, seconds2 = scheduler.get_next_bell()
    assert seconds2 == 3600  # 1 jam tersisa

