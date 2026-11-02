"""
Layanan Pemutar Audio Bel Sekolah Terpusat (Single Active Audio Controller — Qt Multimedia).
Mendukung pemutaran file MP3 dan WAV, interupsi terkontrol antara bel otomatis & manual,
token sesi pemutaran (session ID) untuk menangkal callback basi, impor persisten,
kontrol volume, serta penanganan berkas dan perangkat output.
"""

from __future__ import annotations

import logging
import os
import shutil
from enum import Enum
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtMultimedia import QAudioDevice, QAudioOutput, QMediaDevices, QMediaPlayer

from src.core.config import get_assets_dir, get_audio_storage_dir
from src.core.win7_compat import WinMMPlayer, is_windows_7_or_8
from src.database.db import DatabaseManager
from src.database.repositories import AudioRepository, SettingsRepository
from src.models.models import AudioFile

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".mp3", ".wav"}


def device_id_to_str(dev_id_or_device) -> str:
    """Mengonversi ID QAudioDevice / QByteArray menjadi string yang konsisten."""
    if dev_id_or_device is None:
        return ""
    if hasattr(dev_id_or_device, "id"):
        dev_id_or_device = dev_id_or_device.id()
    if hasattr(dev_id_or_device, "data"):
        return dev_id_or_device.data().decode("utf-8", "ignore")
    if isinstance(dev_id_or_device, (bytes, bytearray)):
        return bytes(dev_id_or_device).decode("utf-8", "ignore")
    return str(dev_id_or_device)


class AudioStatus(str, Enum):
    IDLE = "idle"
    LOADING = "loading"
    PLAYING = "playing"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class AudioPlayer(QObject):
    """
    Pengelola Pemutaran Audio Terpusat (Single Active Audio Controller).
    Menjamin maksimal hanya satu audio bel yang aktif pada satu waktu, menangani
    interupsi serta pembersihan status secara deterministik menggunakan ID sesi,
    serta mengelola perutean perangkat output audio secara dinamis (Speaker internal vs eksternal).
    """

    # Sinyal perubahan status
    status_changed = Signal(str)           # AudioStatus value
    playback_started = Signal(str)         # title / filename
    playback_completed = Signal()
    playback_failed = Signal(str)          # error message
    playback_interrupted = Signal(str)     # interrupted title / reason

    # Sinyal perangkat audio
    audio_devices_changed = Signal()       # Terpanggil saat perangkat audio tersambung/terputus
    audio_device_switched = Signal(str)    # Terpanggil saat perangkat aktif berpindah (nama perangkat)

    def __init__(self, db: DatabaseManager, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.db = db
        self.audio_repo = AudioRepository(db)
        self.settings_repo = SettingsRepository(db)

        self.status: AudioStatus = AudioStatus.IDLE
        self.current_title: str = ""
        self.current_file_path: Optional[Path] = None
        self.current_mode: str = ""             # "OTOMATIS", "MANUAL", "PREVIEW", atau ""
        self.current_audio_id: Optional[int] = None

        # Token sesi pemutaran untuk mencegah callback dari pemutaran lama mengotori pemutaran baru
        self._session_counter: int = 0
        self.active_session_id: int = 0
        self._suppress_callbacks: bool = False
        self.start_count: int = 0

        # Setup Qt Multimedia tunggal
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)

        # Pengelolaan Perangkat Output Audio (QMediaDevices)
        self.media_devices = QMediaDevices(self)
        self.media_devices.audioOutputsChanged.connect(self._on_audio_outputs_changed)

        # Konfigurasi mode output: "auto" (default Windows) atau "manual"
        self.output_mode: str = "auto"
        self.selected_device_id: str = ""
        self.selected_device_name: str = ""
        self._load_device_settings()

        # Inisialisasi perangkat target pada QAudioOutput
        self.refresh_audio_device()

        # Setup WinMM MCI Fallback
        self._winmm = WinMMPlayer()
        self._using_winmm = False
        self._winmm_poll_timer = QTimer(self)
        self._winmm_poll_timer.setInterval(500)
        self._winmm_poll_timer.timeout.connect(self._poll_winmm_status)

        self.set_volume(80)  # Default volume 80%

        # Hubungkan sinyal internal Qt Multimedia
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.player.errorOccurred.connect(self._on_error_occurred)

    def _load_device_settings(self) -> None:
        """Memuat preferensi perangkat output audio dari database."""
        try:
            self.output_mode = self.settings_repo.get("audio_output_mode", "auto")
            self.selected_device_id = self.settings_repo.get("audio_output_device_id", "")
            self.selected_device_name = self.settings_repo.get("audio_output_device_name", "")
        except Exception as e:
            logger.warning("Gagal memuat preferensi perangkat audio: %s", e)
            self.output_mode = "auto"
            self.selected_device_id = ""
            self.selected_device_name = ""

    def _on_audio_outputs_changed(self) -> None:
        """Handler saat sistem mendeteksi penambahan atau pelepasan perangkat audio (misal jack 3,5 mm)."""
        logger.info("Perubahan topologi perangkat output audio terdeteksi oleh QMediaDevices.")
        self.refresh_audio_device()
        self.audio_devices_changed.emit()

    def get_available_output_devices(self) -> list[QAudioDevice]:
        """Mengembalikan daftar seluruh perangkat output audio yang terdeteksi pada komputer."""
        try:
            return [d for d in QMediaDevices.audioOutputs() if not d.isNull()]
        except Exception as e:
            logger.warning("Gagal mengambil daftar audio output: %s", e)
            return []

    def get_default_output_device(self) -> QAudioDevice:
        """Mengembalikan perangkat audio default Windows saat ini."""
        try:
            return QMediaDevices.defaultAudioOutput()
        except Exception as e:
            logger.warning("Gagal mengambil default audio output: %s", e)
            return QAudioDevice()

    def get_current_output_device(self) -> QAudioDevice:
        """Mengembalikan objek QAudioDevice yang sedang aktif pada QAudioOutput."""
        try:
            return self.audio_output.device()
        except Exception as e:
            logger.warning("Gagal membaca device aktif: %s", e)
            return QAudioDevice()

    def get_output_mode(self) -> str:
        """Mengembalikan mode output ('auto' atau 'manual')."""
        return self.output_mode

    def get_selected_device_id(self) -> str:
        """Mengembalikan ID unik perangkat terpilih jika dalam mode manual."""
        return self.selected_device_id

    def get_selected_device_name(self) -> str:
        """Mengembalikan nama deskriptif perangkat terpilih jika dalam mode manual."""
        return self.selected_device_name

    def _matches_device(self, dev: QAudioDevice, target_id: str, target_name: str = "") -> bool:
        """Memeriksa apakah QAudioDevice cocok dengan ID atau nama yang dicari."""
        if dev.isNull():
            return False
        dev_id_str = device_id_to_str(dev)
        if target_id and dev_id_str == target_id:
            return True
        if target_name and dev.description().strip() == target_name.strip():
            return True
        return False

    def set_output_mode(
        self,
        mode: str,
        device_id: Optional[str] = None,
        device_name: Optional[str] = None,
    ) -> bool:
        """
        Mengatur preferensi perutean perangkat audio:
        - mode='auto': Otomatis mengikuti output Windows (default), berpindah dinamis saat jack dicolok/dilepas.
        - mode='manual': Mengunci audio ke perangkat fisik tertentu.
        """
        self.output_mode = "manual" if mode == "manual" else "auto"
        if self.output_mode == "manual":
            self.selected_device_id = device_id or ""
            if not device_name and self.selected_device_id:
                for dev in self.get_available_output_devices():
                    if device_id_to_str(dev) == self.selected_device_id:
                        device_name = dev.description()
                        break
            self.selected_device_name = device_name or ""
        else:
            self.selected_device_id = ""
            self.selected_device_name = ""

        try:
            self.settings_repo.set("audio_output_mode", self.output_mode)
            self.settings_repo.set("audio_output_device_id", self.selected_device_id)
            self.settings_repo.set("audio_output_device_name", self.selected_device_name)
        except Exception as e:
            logger.warning("Gagal menyimpan preferensi perangkat audio: %s", e)

        result = self.refresh_audio_device()
        self.audio_devices_changed.emit()
        return result

    def refresh_audio_device(self) -> bool:
        """
        Memeriksa dan memperbarui perangkat output pada QAudioOutput secara aman tanpa merusak pemutar:
        - Mode 'auto': Selalu menyelaraskan diri dengan default Windows terkini.
        - Mode 'manual': Mencari perangkat target; jika perangkat dilepas/hilang,
          jatuh ke default Windows sebagai fallback sementara tanpa menghapus preferensi tersimpan.
        """
        try:
            available = self.get_available_output_devices()
            if not available:
                logger.warning("Tidak ada perangkat output audio yang terdeteksi.")
                return False

            target_device: Optional[QAudioDevice] = None

            if self.output_mode == "manual" and (self.selected_device_id or self.selected_device_name):
                for dev in available:
                    if self._matches_device(dev, self.selected_device_id, self.selected_device_name):
                        target_device = dev
                        break
                if not target_device:
                    logger.warning(
                        "Perangkat output audio manual '%s' (%s) tidak ditemukan dalam daftar aktif. "
                        "Menggunakan default output Windows sebagai fallback sementara.",
                        self.selected_device_name,
                        self.selected_device_id,
                    )
                    target_device = self.get_default_output_device()
            else:
                target_device = self.get_default_output_device()

            if not target_device or target_device.isNull():
                target_device = available[0]

            current_device = self.audio_output.device()
            current_id = device_id_to_str(current_device)
            target_id = device_id_to_str(target_device)

            if current_device.isNull() or current_id != target_id:
                logger.info(
                    "Peralihan perangkat audio: '%s' -> '%s' (mode=%s)",
                    current_device.description() if not current_device.isNull() else "None",
                    target_device.description(),
                    self.output_mode,
                )
                curr_vol = self.audio_output.volume()
                self.audio_output.setDevice(target_device)
                self.audio_output.setVolume(curr_vol)
                self.audio_device_switched.emit(target_device.description())
                return True

            return True
        except Exception as e:
            logger.error("Terjadi kesalahan saat memperbarui perangkat audio output: %s", e)
            return False
        self.player.errorOccurred.connect(self._on_error_occurred)

    def _set_status(self, new_status: AudioStatus, message: str = "") -> None:
        self.status = new_status
        logger.info("Status Audio berubah: %s (%s)", new_status.value, message)
        self.status_changed.emit(new_status.value)

    def _clear_active_metadata(self) -> None:
        """Membersihkan metadata pemutaran aktif secara konsisten."""
        self.current_title = ""
        self.current_file_path = None
        self.current_mode = ""
        self.current_audio_id = None
        self.active_session_id = 0

    def _halt_backends(self) -> None:
        """
        Menghentikan seluruh backend audio (Qt Multimedia & WinMM) dengan aman
        sambil menekan sinyal callback sinkron dari pemutar lama.
        """
        prev_suppress = self._suppress_callbacks
        self._suppress_callbacks = True
        try:
            if hasattr(self, "_winmm_poll_timer") and self._winmm_poll_timer.isActive():
                self._winmm_poll_timer.stop()
            if getattr(self, "_using_winmm", False) or (hasattr(self, "_winmm") and self._winmm._is_open):
                self._winmm.stop()
                self._using_winmm = False
            try:
                self.player.stop()
                self.player.setPosition(0)
            except Exception as e:
                logger.debug("Peringatan saat menghentikan QMediaPlayer: %s", e)
        finally:
            self._suppress_callbacks = prev_suppress

    def is_playing(self) -> bool:
        """Mengembalikan True apabila ada sesi audio yang sedang dimuat atau diputar."""
        return self.status in (AudioStatus.PLAYING, AudioStatus.LOADING)

    def is_session_active(self, session_id: int) -> bool:
        """Memeriksa apakah ID sesi tertentu masih merupakan sesi pemutaran yang aktif."""
        return (
            not self._suppress_callbacks
            and self.active_session_id != 0
            and self.active_session_id == session_id
            and self.status in (AudioStatus.PLAYING, AudioStatus.LOADING)
        )

    def set_volume(self, volume: int) -> None:
        """Mengatur volume output (0 - 100)."""
        clamped = max(0, min(100, volume))
        self.audio_output.setVolume(clamped / 100.0)
        if hasattr(self, "_winmm"):
            self._winmm.set_volume(clamped)

    def get_volume(self) -> int:
        """Mengembalikan level volume (0 - 100)."""
        return int(round(self.audio_output.volume() * 100.0))

    def has_audio_output_device(self) -> bool:
        """Memeriksa ketersediaan perangkat output audio pada komputer Windows."""
        try:
            devices = self.get_available_output_devices()
            return len(devices) > 0
        except Exception as e:
            logger.warning("Gagal memeriksa perangkat audio: %s", e)
            return True  # Fallback toleran

    def import_audio_file(self, source_path: str | Path, custom_name: Optional[str] = None) -> AudioFile:
        """
        Menyalin file audio MP3/WAV ke direktori persisten (%APPDATA%/BelOtomatisSekolah/sounds),
        memvalidasi ekstensi dan integritas file, serta menyimpannya ke database.
        """
        src = Path(source_path).resolve()
        if not src.exists() or not src.is_file():
            raise FileNotFoundError(f"File audio sumber tidak ditemukan: {src}")

        ext = src.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Format file '{ext}' tidak didukung. Harap gunakan file MP3 atau WAV ({', '.join(SUPPORTED_EXTENSIONS)})."
            )

        file_size = src.stat().st_size
        if file_size == 0:
            raise ValueError("File audio kosong (0 bytes).")

        storage_dir = get_audio_storage_dir()
        storage_dir.mkdir(parents=True, exist_ok=True)

        original_filename = src.name
        label_name = custom_name.strip() if custom_name and custom_name.strip() else src.stem

        dest = storage_dir / original_filename
        if dest.exists():
            if dest.stat().st_size != file_size:
                stem = src.stem
                counter = 1
                while dest.exists():
                    dest = storage_dir / f"{stem}_{counter}{ext}"
                    counter += 1
                shutil.copy2(src, dest)
        else:
            shutil.copy2(src, dest)

        existing = [a for a in self.audio_repo.get_all() if a.stored_path == str(dest)]
        if existing:
            return existing[0]

        audio_model = AudioFile(
            id=None,
            name=label_name,
            stored_path=str(dest),
            original_filename=original_filename,
            duration_seconds=0.0,
        )
        return self.audio_repo.create(audio_model)

    def _resolve_audio_path(self, file_path: str | Path) -> Optional[Path]:
        """Menemukan path fisik berkas audio atau mencari fallback di storage pengguna & assets bawaan."""
        if not file_path or not str(file_path).strip():
            return None
        path = Path(file_path)
        if path.exists() and path.is_file():
            return path.resolve()

        alt_storage = get_audio_storage_dir() / path.name
        if alt_storage.exists() and alt_storage.is_file():
            return alt_storage.resolve()

        alt_bundled = get_assets_dir() / "sounds" / path.name
        if alt_bundled.exists() and alt_bundled.is_file():
            return alt_bundled.resolve()

        return None

    def play_file(
        self,
        file_path: str | Path,
        title: str = "",
        *,
        interrupt: bool = True,
        mode: str = "MANUAL",
        audio_id: Optional[int] = None,
    ) -> bool:
        """
        Memulai pemutaran file audio MP3/WAV secara terpusat.
        - Jika `interrupt=True` (default): apabila ada audio otomatis atau manual yang sedang berjalan,
          audio sebelumnya langsung dihentikan secara bersih sebelum audio baru dimainkan dari awal.
        - Jika `interrupt=False`: menolak pemutaran baru apabila pemutar masih aktif.
        """
        # Pastikan perangkat output audio tersinkronisasi sebelum pemutaran
        # (misalnya kabel jack speaker eksternal baru saja dicolokkan)
        self.refresh_audio_device()

        if self.is_playing():
            if not interrupt:
                logger.warning(
                    "Pemutaran '%s' ditolak (interrupt=False): Audio '%s' masih sedang dimainkan.",
                    title or file_path,
                    self.current_title,
                )
                return False

            prev_title = self.current_title or "Audio Sebelumnya"
            logger.info(
                "Menginterupsi audio aktif '%s' (mode=%s) untuk memutar '%s' (mode=%s).",
                prev_title,
                self.current_mode or "UNKNOWN",
                title or Path(str(file_path)).stem,
                mode,
            )
            self.stop(reason=f"Diinterupsi oleh {title or Path(str(file_path)).stem}")
        else:
            # Pastikan backend benar-benar bersih sebelum sesi baru
            self._halt_backends()
            self._clear_active_metadata()

        raw_path = Path(str(file_path)) if file_path else Path("")
        resolved_path = self._resolve_audio_path(file_path)
        if resolved_path is None:
            err_msg = f"File audio tidak ditemukan di: {raw_path}"
            logger.error(err_msg)
            self._clear_active_metadata()
            self._set_status(AudioStatus.FAILED, err_msg)
            self.playback_failed.emit(err_msg)
            return False

        if resolved_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            err_msg = f"Format file tidak didukung: {resolved_path.suffix}"
            logger.error(err_msg)
            self._clear_active_metadata()
            self._set_status(AudioStatus.FAILED, err_msg)
            self.playback_failed.emit(err_msg)
            return False

        try:
            if resolved_path.stat().st_size == 0:
                err_msg = f"File audio kosong atau rusak (0 bytes): {resolved_path}"
                logger.error(err_msg)
                self._clear_active_metadata()
                self._set_status(AudioStatus.FAILED, err_msg)
                self.playback_failed.emit(err_msg)
                return False
        except OSError as e:
            err_msg = f"Gagal mengakses file audio {resolved_path}: {e}"
            logger.error(err_msg)
            self._clear_active_metadata()
            self._set_status(AudioStatus.FAILED, err_msg)
            self.playback_failed.emit(err_msg)
            return False

        # Buat sesi pemutaran baru dengan ID unik
        self._session_counter += 1
        session_id = self._session_counter
        self.active_session_id = session_id

        self.current_title = title if title else resolved_path.stem
        self.current_file_path = resolved_path
        self.current_mode = mode
        self.current_audio_id = audio_id

        self._set_status(AudioStatus.LOADING, f"Memuat {resolved_path.name} [sesi #{session_id}]")

        # Jika berjalan di Windows 7/8, gunakan langsung WinMM MCI
        if is_windows_7_or_8():
            if self._start_winmm_playback(resolved_path, session_id=session_id):
                return True

        url = QUrl.fromLocalFile(str(resolved_path))
        self._using_winmm = False

        # Hindari bug handle D3D11/FFmpeg Qt6 (0xc0000008) saat memutar file audio di mode headless offscreen
        is_headless = os.environ.get("QT_QPA_PLATFORM") == "offscreen"

        if not is_headless:
            self._suppress_callbacks = True
            try:
                self.player.stop()
                # Jika file yang sama diputar ulang, reset source terlebih dahulu agar selalu mulai dari 0
                if self.player.source() == url:
                    self.player.setSource(QUrl())
                self.player.setSource(url)
                self.player.setPosition(0)
            finally:
                self._suppress_callbacks = False

            self.player.play()

            # Jika terjadi error sinkron saat play() yang sudah menggagalkan sesi ini
            if self.active_session_id != session_id or self.status == AudioStatus.FAILED:
                return False

        self.start_count += 1
        self._set_status(AudioStatus.PLAYING, f"Memutar {self.current_title} [sesi #{session_id}]")
        self.playback_started.emit(self.current_title)
        return True

    def _start_winmm_playback(self, path: Path, session_id: Optional[int] = None) -> bool:
        """Memulai pemutaran menggunakan WinMM MCI."""
        active_sid = session_id if session_id is not None else self.active_session_id
        if self._winmm.play(path, volume=self.get_volume()):
            self.active_session_id = active_sid
            self._using_winmm = True
            self._winmm_poll_timer.start()
            self.start_count += 1
            self._set_status(AudioStatus.PLAYING, f"Memutar (WinMM) {self.current_title} [sesi #{active_sid}]")
            self.playback_started.emit(self.current_title)
            return True
        return False

    def _poll_winmm_status(self, session_id: Optional[int] = None) -> None:
        """Memantau status pemutaran WinMM MCI secara berkala."""
        if self._suppress_callbacks:
            return
        if session_id is not None and session_id != self.active_session_id:
            return
        if not self._using_winmm or self.status != AudioStatus.PLAYING or self.active_session_id == 0:
            self._winmm_poll_timer.stop()
            return
        if self._winmm.is_stopped_naturally():
            self._winmm_poll_timer.stop()
            self._winmm.stop()
            self._using_winmm = False
            finished_title = self.current_title
            self._clear_active_metadata()
            self._set_status(AudioStatus.COMPLETED, f"Pemutaran selesai (WinMM): {finished_title}")
            self.playback_completed.emit()

    def play(
        self,
        file_path: str | Path,
        event_name: str = "",
        *,
        interrupt: bool = True,
        mode: str = "MANUAL",
    ) -> bool:
        """Alias kompatibilitas untuk play_file."""
        return self.play_file(file_path, title=event_name, interrupt=interrupt, mode=mode)

    def play_audio_id(
        self,
        audio_id: int,
        fallback_title: str = "",
        *,
        interrupt: bool = True,
        mode: str = "MANUAL",
    ) -> bool:
        """Memutar audio berdasarkan ID dari database."""
        audio_record = self.audio_repo.get_by_id(audio_id)
        if not audio_record:
            if interrupt and self.is_playing():
                self.stop(reason=f"Diinterupsi oleh permintaan audio ID {audio_id} yang tidak ditemukan")
            err_msg = f"Data audio dengan ID {audio_id} tidak ditemukan di database."
            logger.error(err_msg)
            self._clear_active_metadata()
            self._set_status(AudioStatus.FAILED, err_msg)
            self.playback_failed.emit(err_msg)
            return False

        title = fallback_title if fallback_title else audio_record.name
        return self.play_file(
            audio_record.stored_path,
            title=title,
            interrupt=interrupt,
            mode=mode,
            audio_id=audio_record.id,
        )

    def stop(self, reason: str = "Dihentikan oleh operator/sistem.") -> bool:
        """
        Menghentikan pemutaran audio yang sedang aktif (baik otomatis maupun manual)
        dan membersihkan seluruh status pemutaran secara konsisten.
        """
        was_active = self.is_playing()
        interrupted_title = self.current_title

        # Invalidate sesi aktif terlebih dahulu agar tidak ada callback lama yang lolos
        self.active_session_id = 0
        self._halt_backends()
        self._clear_active_metadata()

        if was_active:
            detail = f"{reason} ({interrupted_title})" if interrupted_title else reason
            self._set_status(AudioStatus.INTERRUPTED, detail)
            self.playback_interrupted.emit(interrupted_title or reason)
            return True
        return False

    def cleanup(self) -> None:
        """Melepaskan sumber daya audio secara aman ketika aplikasi ditutup."""
        was_active = self.is_playing()
        interrupted_title = self.current_title
        self.active_session_id = 0
        self._halt_backends()
        self._clear_active_metadata()
        if was_active:
            self._set_status(AudioStatus.INTERRUPTED, "Aplikasi ditutup saat audio berbunyi.")
            self.playback_interrupted.emit(interrupted_title or "Aplikasi ditutup")

    def _on_playback_state_changed(
        self,
        state: QMediaPlayer.PlaybackState,
        session_id: Optional[int] = None,
    ) -> None:
        if self._suppress_callbacks:
            return
        if session_id is not None and session_id != self.active_session_id:
            logger.debug(
                "Mengabaikan playbackStateChanged basi dari sesi #%s (aktif: #%s)",
                session_id,
                self.active_session_id,
            )
            return
        if self.active_session_id == 0 or self.status != AudioStatus.PLAYING:
            return

        if state == QMediaPlayer.PlaybackState.StoppedState:
            finished_title = self.current_title
            self._clear_active_metadata()
            self._set_status(AudioStatus.COMPLETED, f"Pemutaran selesai: {finished_title}")
            self.playback_completed.emit()

    def _on_media_status_changed(
        self,
        media_status: QMediaPlayer.MediaStatus,
        session_id: Optional[int] = None,
    ) -> None:
        if self._suppress_callbacks:
            return
        if session_id is not None and session_id != self.active_session_id:
            logger.debug(
                "Mengabaikan mediaStatusChanged basi dari sesi #%s (aktif: #%s)",
                session_id,
                self.active_session_id,
            )
            return
        if self.active_session_id == 0 or self.status != AudioStatus.PLAYING:
            return

        if media_status == QMediaPlayer.MediaStatus.EndOfMedia:
            finished_title = self.current_title
            self._clear_active_metadata()
            self._set_status(AudioStatus.COMPLETED, f"Mencapai akhir file audio: {finished_title}")
            self.playback_completed.emit()
        elif media_status == QMediaPlayer.MediaStatus.InvalidMedia:
            err_msg = f"Berkas media tidak valid atau rusak: {self.current_title}"
            logger.error(err_msg)
            self._halt_backends()
            self._clear_active_metadata()
            self._set_status(AudioStatus.FAILED, err_msg)
            self.playback_failed.emit(err_msg)

    def _on_error_occurred(
        self,
        error: QMediaPlayer.Error,
        error_string: str,
        session_id: Optional[int] = None,
    ) -> None:
        if self._suppress_callbacks:
            return
        if session_id is not None and session_id != self.active_session_id:
            logger.debug(
                "Mengabaikan errorOccurred basi dari sesi #%s (aktif: #%s)",
                session_id,
                self.active_session_id,
            )
            return
        if self.active_session_id == 0:
            return

        if error != QMediaPlayer.Error.NoError:
            active_sid = self.active_session_id
            logger.warning("Qt Multimedia Error [%s]: %s. Mencoba fallback ke WinMM MCI...", error, error_string)
            if self.current_file_path and self.current_file_path.exists():
                if self._start_winmm_playback(self.current_file_path, session_id=active_sid):
                    return
            logger.error("Pemutaran gagal baik di Qt Multimedia maupun WinMM: %s", error_string)
            self._halt_backends()
            self._clear_active_metadata()
            self._set_status(AudioStatus.FAILED, error_string)
            self.playback_failed.emit(error_string)
