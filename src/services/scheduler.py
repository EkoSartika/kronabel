"""
Mesin Penjadwal Bel Otomatis (Scheduler Service).
Mengevaluasi jadwal harian, mencegah eksekusi ganda (idempotensi),
menghitung hitung mundur ke bel berikutnya, serta mengoordinasikan pemutaran
dan interupsi antara bel otomatis dan bel manual.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Set, Tuple

from PySide6.QtCore import QObject, QTimer, Signal

from src.core.config import DAYS_OF_WEEK
from src.database.db import DatabaseManager
from src.database.repositories import BellLogRepository, ProfileRepository, ScheduleRepository
from src.models.models import BellLog, Schedule
from src.services.audio_player import AudioPlayer, AudioStatus
from src.services.clock_service import IClock, SystemClock

logger = logging.getLogger(__name__)


class SchedulerService(QObject):
    """Layanan Penjadwalan Otomatis Bel Sekolah."""

    # Sinyal perubahan status scheduler (True = Aktif, False = Berhenti)
    status_changed = Signal(bool)
    # Sinyal info bel berikutnya: (event_name, bell_time, seconds_remaining)
    next_bell_updated = Signal(object, object, object)
    # Sinyal saat bel dipicu: (event_name, schedule_id, mode)
    bell_triggered = Signal(str, object, str)
    # Sinyal saat jadwal otomatis dilewati (misal karena ada audio manual yang aktif):
    # (event_name, bell_time, message)
    schedule_missed = Signal(str, str, str)

    def __init__(
        self,
        db: DatabaseManager,
        audio_player: AudioPlayer,
        clock: Optional[IClock] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.db = db
        self.audio_player = audio_player
        self.clock: IClock = clock if clock else SystemClock()

        self.profile_repo = ProfileRepository(db)
        self.schedule_repo = ScheduleRepository(db)
        self.log_repo = BellLogRepository(db)

        self.is_active: bool = False
        self._current_log_id: Optional[int] = None
        self._last_checked_day: str = self.clock.today_str()

        # Cache memori untuk pencegahan eksekusi berulang dalam satu sesi: (date_str, schedule_id)
        self._executed_cache: Set[Tuple[str, int]] = set()

        # Timer periodik evaluasi (1000 ms)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        # Hubungkan sinyal dari audio player untuk sinkronisasi riwayat
        self.audio_player.playback_completed.connect(self._on_playback_completed)
        self.audio_player.playback_failed.connect(self._on_playback_failed)
        if hasattr(self.audio_player, "playback_interrupted"):
            self.audio_player.playback_interrupted.connect(self._on_playback_interrupted)

    def start(self) -> None:
        """Mengaktifkan mesin penjadwal otomatis."""
        if not self.is_active:
            self.is_active = True
            self._timer.start(1000)
            logger.info("Scheduler Otomatis diaktifkan.")
            self.status_changed.emit(True)
            self._update_next_bell()

    def stop(self) -> None:
        """Menghentikan mesin penjadwal otomatis."""
        if self.is_active:
            self.is_active = False
            self._timer.stop()
            logger.info("Scheduler Otomatis dihentikan.")
            self.status_changed.emit(False)
            self.next_bell_updated.emit(None, None, None)

    def set_clock(self, clock: IClock) -> None:
        """Mengganti penyedia clock (berguna untuk pengujian unit simulasi waktu)."""
        self.clock = clock

    def _play_by_id(
        self,
        audio_id: int,
        fallback_title: str,
        *,
        interrupt: bool = True,
        mode: str = "OTOMATIS",
    ) -> bool:
        try:
            return self.audio_player.play_audio_id(
                audio_id,
                fallback_title=fallback_title,
                interrupt=interrupt,
                mode=mode,
            )
        except TypeError:
            # Kompatibilitas dengan MockAudioPlayer pengujian yang hanya menerima 2 argumen
            self.audio_player.current_mode = mode
            return self.audio_player.play_audio_id(audio_id, fallback_title=fallback_title)

    def _play_by_path(
        self,
        file_path: str | Path,
        title: str,
        *,
        interrupt: bool = True,
        mode: str = "OTOMATIS",
        audio_id: Optional[int] = None,
    ) -> bool:
        try:
            return self.audio_player.play_file(
                file_path,
                title=title,
                interrupt=interrupt,
                mode=mode,
                audio_id=audio_id,
            )
        except TypeError:
            self.audio_player.current_mode = mode
            return self.audio_player.play_file(file_path, title=title)

    def _tick(self) -> None:
        """Pemeriksaan rutin setiap detik."""
        # 1. Bersihkan cache sesi jika terjadi pergantian hari (midnight rollover)
        today = self.clock.today_str()
        if today != self._last_checked_day:
            self._last_checked_day = today
            self._executed_cache.clear()

        # 2. Evaluasi jadwal yang jatuh tempo jika scheduler aktif
        if self.is_active:
            self._evaluate_current_schedules()
            self._update_next_bell()

    def _evaluate_current_schedules(self) -> None:
        """Memeriksa apakah ada jadwal yang jatuh tempo pada detik ini."""
        if not self.clock.is_school_day():
            return

        active_profile = self.profile_repo.get_active()
        if not active_profile:
            return

        current_day = self.clock.day_name()
        current_time_str = self.clock.time_str()  # "HH:MM:SS"
        today_date = self.clock.today_str()

        schedules = self.schedule_repo.get_by_profile_and_day(active_profile.id, current_day)
        for s in schedules:
            if not s.is_enabled:
                continue

            # Kecocokan waktu tepat pada detik yang dijadwalkan
            if s.bell_time == current_time_str:
                self._trigger_schedule(s, today_date)

    def _trigger_schedule(self, schedule: Schedule, today_date: str) -> None:
        """Mengeksekusi jadwal dengan pengamanan idempotensi dan kebijakan konflik deterministik."""
        cache_key = (today_date, schedule.id)

        # 1. Cek cache memori sesi ini
        if cache_key in self._executed_cache:
            logger.debug("Jadwal ID %d sudah dieksekusi hari ini (memori cache).", schedule.id)
            return

        # 2. Cek database persisten (idempotensi antar-restart)
        if self.log_repo.is_schedule_executed_today(schedule.id, today_date):
            logger.info("Jadwal ID %d sudah dieksekusi hari ini (database log).", schedule.id)
            self._executed_cache.add(cache_key)
            return

        # Catat klaim eksekusi segera ke cache agar tidak dieksekusi ulang
        self._executed_cache.add(cache_key)
        now_iso = self.clock.now().isoformat()

        # 3. Kebijakan Konflik Deterministik:
        # Jika bel manual sedang aktif berbunyi ketika waktu jadwal otomatis tiba,
        # jangan memotong bel manual secara diam-diam; catat konflik secara eksplisit dan pancarkan notifikasi.
        is_manual_playing = (
            self.audio_player.status in (AudioStatus.PLAYING, AudioStatus.LOADING)
            and getattr(self.audio_player, "current_mode", "") in ("MANUAL", "PREVIEW")
        )
        if is_manual_playing:
            formatted_time = schedule.bell_time[:5] if schedule.bell_time else ""
            active_manual_title = self.audio_player.current_title or "Bel Manual"
            conflict_msg = (
                f"Jadwal bel '{schedule.event_name}' pukul {formatted_time} dilewati karena "
                f"audio manual '{active_manual_title}' masih berlangsung."
            )
            logger.warning("Jadwal terlewat: %s", conflict_msg)
            conflict_log = BellLog(
                id=None,
                schedule_id=schedule.id,
                scheduled_at=f"{today_date}T{schedule.bell_time}",
                executed_at=now_iso,
                event_name=schedule.event_name,
                execution_mode="OTOMATIS",
                status="missed",
                message=conflict_msg,
            )
            self.log_repo.add_log(conflict_log)
            try:
                self.schedule_missed.emit(schedule.event_name, schedule.bell_time, conflict_msg)
            except Exception as e:
                logger.warning("Gagal memancarkan sinyal schedule_missed: %s", e)
            return

        # Jika ada bel otomatis sebelumnya yang masih berjalan, hentikan terlebih dahulu
        if self.audio_player.status in (AudioStatus.PLAYING, AudioStatus.LOADING):
            self.audio_player.stop(reason=f"Diinterupsi oleh jadwal otomatis baru: {schedule.event_name}")

        # 4. Buat catatan riwayat dengan status awal 'playing'
        log = BellLog(
            id=None,
            schedule_id=schedule.id,
            scheduled_at=f"{today_date}T{schedule.bell_time}",
            executed_at=now_iso,
            event_name=schedule.event_name,
            execution_mode="OTOMATIS",
            status="playing",
            message=f"Memulai pemutaran bel otomatis: {schedule.event_name}",
        )
        self._current_log_id = self.log_repo.add_log(log)
        self.bell_triggered.emit(schedule.event_name, schedule.id, "OTOMATIS")

        # 5. Putar audio melalui AudioPlayer
        success = False
        if schedule.audio_id:
            success = self._play_by_id(
                schedule.audio_id,
                fallback_title=schedule.event_name,
                interrupt=True,
                mode="OTOMATIS",
            )
        elif schedule.audio_path:
            success = self._play_by_path(
                schedule.audio_path,
                title=schedule.event_name,
                interrupt=True,
                mode="OTOMATIS",
            )
        else:
            # Jadwal belum memilih file audio khusus
            available_audios = self.audio_player.audio_repo.get_all()
            if available_audios:
                fallback_audio = available_audios[0]
                logger.warning(
                    "Jadwal '%s' (ID %d) belum memiliki audio khusus. Memutar audio bawaan pustaka: '%s'.",
                    schedule.event_name,
                    schedule.id,
                    fallback_audio.name,
                )
                success = self._play_by_path(
                    fallback_audio.stored_path,
                    title=schedule.event_name,
                    interrupt=True,
                    mode="OTOMATIS",
                    audio_id=fallback_audio.id,
                )
                if success and self._current_log_id:
                    self.log_repo.update_status(
                        self._current_log_id,
                        "playing",
                        f"Memutar audio bawaan pustaka ({fallback_audio.name}) karena jadwal belum memiliki audio khusus.",
                    )
            else:
                err_msg = (
                    f"Gagal membunyikan bel '{schedule.event_name}': "
                    "Audio belum dipilih pada jadwal dan pustaka audio kosong."
                )
                logger.error(err_msg)
                if self._current_log_id:
                    self.log_repo.update_status(self._current_log_id, "failed", err_msg)
                    self._current_log_id = None
                self.audio_player._set_status(AudioStatus.FAILED, err_msg)
                self.audio_player.playback_failed.emit(err_msg)
                return

        if not success:
            err_msg = f"Gagal memutar audio bel '{schedule.event_name}' (perangkat sibuk atau file audio rusak/tidak ditemukan)."
            logger.error(err_msg)
            if self._current_log_id:
                self.log_repo.update_status(self._current_log_id, "failed", err_msg)
                self._current_log_id = None
            self.audio_player._set_status(AudioStatus.FAILED, err_msg)
            self.audio_player.playback_failed.emit(err_msg)

    def trigger_manual_bell(
        self,
        audio_id: Optional[int] = None,
        event_name: str = "Bel Manual",
        audio_path: Optional[str | Path] = None,
    ) -> bool:
        """
        Membunyikan bel secara manual atas permintaan operator.
        - Menginterupsi (menghentikan) audio otomatis maupun manual yang sedang berjalan.
        - Tidak menonaktifkan scheduler otomatis, tidak mengubah jadwal/profil, dan dicatat terpisah.
        """
        # 1. Jika sedang ada audio aktif (otomatis atau manual), hentikan terlebih dahulu
        if self.audio_player.status in (AudioStatus.PLAYING, AudioStatus.LOADING):
            self.audio_player.stop(reason=f"Diinterupsi oleh {event_name}")

        now_iso = self.clock.now().isoformat()
        log = BellLog(
            id=None,
            schedule_id=None,
            scheduled_at=None,
            executed_at=now_iso,
            event_name=event_name,
            execution_mode="MANUAL",
            status="playing",
            message=f"Dibunyikan secara manual oleh operator: {event_name}",
        )
        log_id = self.log_repo.add_log(log)
        self._current_log_id = log_id
        self.bell_triggered.emit(event_name, None, "MANUAL")

        success = False
        if audio_path:
            success = self._play_by_path(
                audio_path,
                title=event_name,
                interrupt=True,
                mode="MANUAL",
                audio_id=audio_id,
            )
        elif audio_id:
            success = self._play_by_id(
                audio_id,
                fallback_title=event_name,
                interrupt=True,
                mode="MANUAL",
            )
        else:
            available_audios = self.audio_player.audio_repo.get_all()
            if available_audios:
                first_audio = available_audios[0]
                success = self._play_by_path(
                    first_audio.stored_path,
                    title=event_name,
                    interrupt=True,
                    mode="MANUAL",
                    audio_id=first_audio.id,
                )
            else:
                err_msg = "Pustaka audio kosong. Harap impor file audio terlebih dahulu."
                self.log_repo.update_status(log_id, "failed", err_msg)
                self._current_log_id = None
                self.audio_player._set_status(AudioStatus.FAILED, err_msg)
                self.audio_player.playback_failed.emit(err_msg)
                return False

        if not success:
            self.log_repo.update_status(log_id, "failed", "Audio tidak dapat diputar.")
            if self._current_log_id == log_id:
                self._current_log_id = None
            return False

        return True

    def get_next_bell(self) -> Tuple[Optional[Schedule], Optional[int]]:
        """
        Mencari jadwal bel aktif berikutnya berdasarkan profil aktif dan waktu aktual saat ini.
        Mengembalikan: (Schedule berikutnya, detik tersisa menuju bel).
        """
        active_profile = self.profile_repo.get_active()
        if not active_profile:
            return None, None

        now = self.clock.now()
        current_time_str = now.strftime("%H:%M:%S")
        current_day = self.clock.day_name()

        # 1. Periksa jadwal yang tersisa hari ini
        if current_day in DAYS_OF_WEEK:
            today_schedules = self.schedule_repo.get_by_profile_and_day(active_profile.id, current_day)
            for s in today_schedules:
                if s.is_enabled and s.bell_time > current_time_str:
                    target_time = datetime.strptime(s.bell_time, "%H:%M:%S").time()
                    target_dt = datetime.combine(now.date(), target_time)
                    seconds_left = max(0, int((target_dt - now).total_seconds()))
                    return s, seconds_left

        # 2. Jika jadwal hari ini sudah habis, cari hari operasional terdekat berikutnya
        day_names_list = list(DAYS_OF_WEEK)
        for offset in range(1, 8):
            next_date = now.date() + timedelta(days=offset)
            english_next_day = next_date.strftime("%A")
            from src.services.clock_service import DAY_NAMES_MAP
            next_day_name = DAY_NAMES_MAP.get(english_next_day, english_next_day)

            if next_day_name in day_names_list:
                schedules = self.schedule_repo.get_by_profile_and_day(active_profile.id, next_day_name)
                active_schedules = [s for s in schedules if s.is_enabled]
                if active_schedules:
                    earliest_s = active_schedules[0]
                    target_time = datetime.strptime(earliest_s.bell_time, "%H:%M:%S").time()
                    target_dt = datetime.combine(next_date, target_time)
                    seconds_left = max(0, int((target_dt - now).total_seconds()))
                    return earliest_s, seconds_left

        return None, None

    def _update_next_bell(self) -> None:
        """Memancarkan sinyal jadwal berikutnya dan hitung mundurnya."""
        next_s, seconds = self.get_next_bell()
        if next_s:
            self.next_bell_updated.emit(next_s.event_name, next_s.bell_time, seconds)
        else:
            self.next_bell_updated.emit(None, None, None)

    def _on_playback_completed(self) -> None:
        if self._current_log_id:
            self.log_repo.update_status(self._current_log_id, "completed", "Pemutaran bel selesai.")
            self._current_log_id = None

    def _on_playback_failed(self, error_message: str) -> None:
        if self._current_log_id:
            self.log_repo.update_status(self._current_log_id, "failed", f"Gagal: {error_message}")
            self._current_log_id = None

    def _on_playback_interrupted(self, reason: str) -> None:
        if self._current_log_id:
            self.log_repo.update_status(
                self._current_log_id,
                "interrupted",
                f"Pemutaran dihentikan/diinterupsi: {reason}",
            )
            self._current_log_id = None
