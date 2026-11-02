"""
Halaman Pengaturan & Manajemen Cadangan (Settings Page) Bel Otomatis Sekolah.
Menyediakan antarmuka untuk preferensi volume, konfirmasi bel manual, kebijakan audio sibuk,
profil aktif, integrasi Windows startup opsional, serta Cadangkan & Pulihkan Data (Backup & Restore).
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from src.core.config import APP_DISPLAY_NAME
from src.database.db import DatabaseManager
from src.database.repositories import ProfileRepository, SettingsRepository
from src.core.autostart import (
    APP_REG_NAME,
    RUN_REG_KEY,
    is_windows_autostart_enabled,
    set_windows_autostart,
)
from src.services.audio_player import AudioPlayer, device_id_to_str
from src.services.backup_service import BackupService

logger = logging.getLogger(__name__)


class SettingsPage(QWidget):
    """Halaman Pengaturan Aplikasi dan Pemeliharaan Data."""

    settings_changed = Signal()
    data_restored = Signal()

    def __init__(
        self,
        db: DatabaseManager,
        audio_player: Optional[AudioPlayer] = None,
        profile_repo: Optional[ProfileRepository] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.db = db
        self.audio_player = audio_player
        self.profile_repo = profile_repo or ProfileRepository(db)
        self.settings_repo = SettingsRepository(db)
        self.backup_service = BackupService(db)

        # Hubungkan sinyal perubahan perangkat audio jika audio_player tersedia
        if self.audio_player:
            self.audio_player.audio_devices_changed.connect(self._on_devices_changed_signal)
            self.audio_player.audio_device_switched.connect(self._update_device_info_label)

        self._is_loading = True
        self._setup_ui()
        self.load_settings()
        self._is_loading = False

    def _setup_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll Area agar dapat ditampilkan di layar resolusi kecil
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(28, 24, 28, 24)
        container_layout.setSpacing(20)

        # 1. KARTU SUARA & PEMUTARAN
        card_audio = self._create_card("Audio & Pemutaran Bel")
        layout_audio = QVBoxLayout(card_audio)
        layout_audio.setContentsMargins(20, 16, 20, 16)
        layout_audio.setSpacing(14)
        title_audio = QLabel("Audio & Pemutaran Bel")
        title_audio.setStyleSheet("font-size: 15px; font-weight: 700; color: #0f172a;")
        layout_audio.addWidget(title_audio)

        # 1.A PENGATURAN PERANGKAT OUTPUT AUDIO
        dev_label = QLabel("Perangkat Output Audio (Speaker / Headphone):")
        dev_label.setStyleSheet("font-weight: 600; color: #1e293b; font-size: 13px; margin-top: 4px;")
        layout_audio.addWidget(dev_label)

        dev_row = QHBoxLayout()
        dev_row.setSpacing(10)

        self.cmb_audio_device = QComboBox()
        self.cmb_audio_device.setStyleSheet(
            "padding: 6px 12px; border: 1px solid #cbd5e1; border-radius: 6px; background-color: #ffffff; color: #0f172a; font-size: 13px;"
        )
        self.cmb_audio_device.currentIndexChanged.connect(self._on_audio_device_changed)
        dev_row.addWidget(self.cmb_audio_device, 1)

        self.btn_refresh_devices = QPushButton("Segarkan Perangkat")
        self.btn_refresh_devices.setStyleSheet(
            "background-color: #f1f5f9; color: #0f172a; font-weight: 600; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 14px; font-size: 13px;"
        )
        self.btn_refresh_devices.clicked.connect(self._on_refresh_devices_clicked)
        dev_row.addWidget(self.btn_refresh_devices)

        self.btn_test_audio = QPushButton("Tes Suara")
        self.btn_test_audio.setStyleSheet(
            "background-color: #0284c7; color: #ffffff; font-weight: 600; border: none; border-radius: 6px; padding: 6px 16px; font-size: 13px;"
        )
        self.btn_test_audio.clicked.connect(self._test_audio_playback)
        dev_row.addWidget(self.btn_test_audio)

        layout_audio.addLayout(dev_row)

        self.lbl_device_info = QLabel()
        self.lbl_device_info.setStyleSheet("color: #64748b; font-size: 12px; margin-bottom: 6px;")
        self.lbl_device_info.setWordWrap(True)
        layout_audio.addWidget(self.lbl_device_info)

        # 1.B VOLUME MASTER
        vol_label = QLabel("Volume Suara Master:")
        vol_label.setStyleSheet("font-weight: 600; color: #1e293b; font-size: 13px; margin-top: 4px;")
        layout_audio.addWidget(vol_label)

        vol_row = QHBoxLayout()
        vol_row.setSpacing(12)
        self.slider_volume = QSlider(Qt.Orientation.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(80)
        self.slider_volume.setStyleSheet(
            """
            QSlider::groove:horizontal {
                height: 6px;
                background: #e2e8f0;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #0284c7;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #0369a1;
                border: 2px solid #ffffff;
                width: 18px;
                height: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }
            """
        )
        self.slider_volume.valueChanged.connect(self._on_volume_changed)
        vol_row.addWidget(self.slider_volume, 1)

        self.lbl_volume_val = QLabel("80%")
        self.lbl_volume_val.setStyleSheet("font-weight: 700; color: #0284c7; min-width: 45px;")
        vol_row.addWidget(self.lbl_volume_val)

        layout_audio.addLayout(vol_row)

        # Kebijakan Pemutaran Saat Sibuk
        busy_label = QLabel("Kebijakan Ketika Suara Lain Sedang Diputar:")
        busy_label.setStyleSheet("font-weight: 600; color: #1e293b; font-size: 13px; margin-top: 6px;")
        layout_audio.addWidget(busy_label)

        self.cmb_busy_policy = QComboBox()
        self.cmb_busy_policy.setStyleSheet(
            "padding: 6px 12px; border: 1px solid #cbd5e1; border-radius: 6px; background-color: #ffffff; color: #0f172a;"
        )
        self.cmb_busy_policy.addItem("Tolak pemutaran baru (Cegah tumpang tindih)", "reject")
        self.cmb_busy_policy.addItem("Hentikan audio lama dan segera putar yang baru", "interrupt")
        self.cmb_busy_policy.addItem("Antrekan suara baru setelah yang lama selesai", "queue")
        self.cmb_busy_policy.currentIndexChanged.connect(self._save_busy_policy)
        layout_audio.addWidget(self.cmb_busy_policy)

        # Konfirmasi Bel Manual
        self.chk_confirm_manual = QCheckBox("Tampilkan dialog konfirmasi sebelum membunyikan bel manual")
        self.chk_confirm_manual.setStyleSheet("color: #334155; font-size: 13px; margin-top: 4px;")
        self.chk_confirm_manual.toggled.connect(self._save_confirm_manual)
        layout_audio.addWidget(self.chk_confirm_manual)

        container_layout.addWidget(card_audio)

        # 2. KARTU JADWAL & PROFIL
        card_profile = self._create_card("Profil Jam Pelajaran Aktif")
        layout_profile = QVBoxLayout(card_profile)
        layout_profile.setContentsMargins(20, 16, 20, 16)
        layout_profile.setSpacing(10)
        title_prof = QLabel("Profil Jam Pelajaran Aktif")
        title_prof.setStyleSheet("font-size: 15px; font-weight: 700; color: #0f172a;")
        layout_profile.addWidget(title_prof)

        desc_prof = QLabel("Pilih profil jam pelajaran yang saat ini berlaku sebagai acuan pembunyian bel otomatis:")
        desc_prof.setStyleSheet("color: #64748b; font-size: 13px;")
        layout_profile.addWidget(desc_prof)

        prof_row = QHBoxLayout()
        prof_row.setSpacing(12)

        self.cmb_profiles = QComboBox()
        self.cmb_profiles.setStyleSheet(
            "padding: 6px 12px; border: 1px solid #cbd5e1; border-radius: 6px; background-color: #ffffff; color: #0f172a;"
        )
        self.cmb_profiles.currentIndexChanged.connect(self._on_profile_selection_changed)
        prof_row.addWidget(self.cmb_profiles, 1)

        layout_profile.addLayout(prof_row)
        container_layout.addWidget(card_profile)

        # 3. KARTU SISTEM & WINDOWS STARTUP
        card_system = self._create_card("Sistem Operasi & Windows Startup")
        layout_system = QVBoxLayout(card_system)
        layout_system.setContentsMargins(20, 16, 20, 16)
        layout_system.setSpacing(10)
        title_sys = QLabel("Sistem Operasi & Windows Startup")
        title_sys.setStyleSheet("font-size: 15px; font-weight: 700; color: #0f172a;")
        layout_system.addWidget(title_sys)

        self.chk_autostart = QCheckBox("Jalankan aplikasi otomatis saat komputer Windows dinyalakan")
        self.chk_autostart.setStyleSheet("font-weight: 600; color: #1e293b; font-size: 13px;")
        self.chk_autostart.toggled.connect(self._on_autostart_toggled)
        layout_system.addWidget(self.chk_autostart)

        warn_box = QFrame()
        warn_box.setObjectName("WarnBox")
        warn_box.setStyleSheet(
            """
            QFrame#WarnBox {
                background-color: #fffbeb;
                border: 1px solid #fde68a;
                border-radius: 6px;
            }
            QLabel {
                color: #b45309;
                font-size: 12px;
                border: none;
                background-color: transparent;
                padding: 0px;
            }
            """
        )
        warn_layout = QVBoxLayout(warn_box)
        warn_layout.setContentsMargins(12, 10, 12, 10)
        lbl_warn = QLabel(
            "PENTING: Aplikasi Bel Otomatis hanya dapat membunyikan bel saat komputer menyala dan aktif. "
            "Aplikasi TIDAK DAPAT membunyikan bel jika komputer dimatikan, berada dalam mode tidur (Sleep), atau hibernasi. "
            "Pastikan komputer operator tetap menyala selama jam operasional sekolah."
        )
        lbl_warn.setWordWrap(True)
        warn_layout.addWidget(lbl_warn)
        layout_system.addWidget(warn_box)

        container_layout.addWidget(card_system)

        # 4. KARTU CADANGKAN & PULIHKAN DATA (BACKUP & RESTORE)
        card_backup = self._create_card("Cadangkan & Pulihkan Data (Backup & Restore)")
        layout_backup = QVBoxLayout(card_backup)
        layout_backup.setContentsMargins(20, 16, 20, 16)
        layout_backup.setSpacing(12)
        title_backup = QLabel("Cadangkan & Pulihkan Data (Backup & Restore)")
        title_backup.setStyleSheet("font-size: 15px; font-weight: 700; color: #0f172a;")
        layout_backup.addWidget(title_backup)

        desc_backup = QLabel(
            "Fitur ini mengamankan seluruh basis data (profil, jadwal bel, riwayat pembunyian, pengaturan) "
            "serta seluruh file audio MP3/WAV ke dalam satu arsip ZIP terkompresi."
        )
        desc_backup.setStyleSheet("color: #475569; font-size: 13px;")
        desc_backup.setWordWrap(True)
        layout_backup.addWidget(desc_backup)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(14)

        self.btn_backup = QPushButton("Cadangkan Data (Backup)")
        self.btn_backup.setStyleSheet(
            """
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                font-weight: 600;
                border-radius: 6px;
                padding: 10px 18px;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
            """
        )
        self.btn_backup.clicked.connect(self._handle_create_backup)
        btn_row.addWidget(self.btn_backup)

        self.btn_restore = QPushButton("Pulihkan Data (Restore)")
        self.btn_restore.setStyleSheet(
            """
            QPushButton {
                background-color: #059669;
                color: #ffffff;
                font-weight: 600;
                border-radius: 6px;
                padding: 10px 18px;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover {
                background-color: #047857;
            }
            """
        )
        self.btn_restore.clicked.connect(self._handle_restore_backup)
        btn_row.addWidget(self.btn_restore)

        btn_row.addStretch()
        layout_backup.addLayout(btn_row)

        container_layout.addWidget(card_backup)

        container_layout.addStretch()
        scroll.setWidget(container)
        outer_layout.addWidget(scroll)

    def _create_card(self, title: str) -> QFrame:
        card = QFrame()
        card.setObjectName("SettingsCard")
        card.setStyleSheet(
            """
            QFrame#SettingsCard {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
            QLabel {
                border: none;
                background-color: transparent;
                padding: 0px;
            }
            """
        )
        return card

    def load_settings(self) -> None:
        """Memuat seluruh nilai preferensi dari database dan sistem."""
        # 1. Perangkat Output Audio
        self._populate_audio_devices()

        # 2. Volume
        vol_str = self.settings_repo.get("volume", "80")
        try:
            vol_val = max(0, min(100, int(vol_str)))
        except ValueError:
            vol_val = 80
        self.slider_volume.setValue(vol_val)
        self.lbl_volume_val.setText(f"{vol_val}%")
        if self.audio_player:
            self.audio_player.set_volume(vol_val)

        # 3. Kebijakan saat audio sibuk
        busy_policy = self.settings_repo.get("playback_busy_policy", "reject")
        idx_busy = self.cmb_busy_policy.findData(busy_policy)
        if idx_busy >= 0:
            self.cmb_busy_policy.setCurrentIndex(idx_busy)

        # 4. Konfirmasi manual bell
        confirm_str = self.settings_repo.get("confirm_manual_bell", "true")
        self.chk_confirm_manual.setChecked(confirm_str.lower() != "false")

        # 5. Profil Aktif
        self.refresh_profiles()

        # 6. Windows Autostart
        self.chk_autostart.setChecked(is_windows_autostart_enabled())

    def refresh_profiles(self) -> None:
        """Memperbarui daftar profil di combo box."""
        self.cmb_profiles.blockSignals(True)
        self.cmb_profiles.clear()
        profiles = self.profile_repo.get_all()
        active_prof = self.profile_repo.get_active()

        selected_idx = -1
        for idx, p in enumerate(profiles):
            self.cmb_profiles.addItem(p.name, p.id)
            if active_prof and p.id == active_prof.id:
                selected_idx = idx

        if selected_idx >= 0:
            self.cmb_profiles.setCurrentIndex(selected_idx)
        self.cmb_profiles.blockSignals(False)

    def _populate_audio_devices(self) -> None:
        """Memperbarui daftar perangkat output audio pada combo box pilihan perangkat."""
        self.cmb_audio_device.blockSignals(True)
        self.cmb_audio_device.clear()

        # Opsi 0: Otomatis mengikuti output Windows
        self.cmb_audio_device.addItem("🔊 Otomatis mengikuti output Windows (default)", "auto")

        current_mode = "auto"
        selected_id = ""
        if self.audio_player:
            current_mode = self.audio_player.get_output_mode()
            selected_id = self.audio_player.get_selected_device_id()
            devices = self.audio_player.get_available_output_devices()
            default_dev = self.audio_player.get_default_output_device()
            default_id = device_id_to_str(default_dev)
        else:
            current_mode = self.settings_repo.get("audio_output_mode", "auto")
            selected_id = self.settings_repo.get("audio_output_device_id", "")
            devices = [d for d in QMediaDevices.audioOutputs() if not d.isNull()]
            default_dev = QMediaDevices.defaultAudioOutput()
            default_id = device_id_to_str(default_dev)

        active_index = 0
        for idx, dev in enumerate(devices, start=1):
            dev_id = device_id_to_str(dev)
            is_def = (dev_id == default_id) or dev.isDefault()
            label = f"🔈 {dev.description()}" + (" [Default Windows]" if is_def else "")
            self.cmb_audio_device.addItem(label, dev_id)

            if current_mode == "manual" and dev_id == selected_id:
                active_index = idx

        self.cmb_audio_device.setCurrentIndex(active_index)
        self.cmb_audio_device.blockSignals(False)
        self._update_device_info_label()

    def _on_volume_changed(self, value: int) -> None:
        self.lbl_volume_val.setText(f"{value}%")
        if not self._is_loading:
            self.settings_repo.set("volume", str(value))
            if self.audio_player:
                self.audio_player.set_volume(value)

    def _on_audio_device_changed(self, index: int) -> None:
        """Handler ketika operator mengubah pilihan perangkat output audio."""
        if self._is_loading:
            return
        data = self.cmb_audio_device.currentData()
        if data == "auto":
            if self.audio_player:
                self.audio_player.set_output_mode("auto")
            else:
                self.settings_repo.set("audio_output_mode", "auto")
                self.settings_repo.set("audio_output_device_id", "")
                self.settings_repo.set("audio_output_device_name", "")
        else:
            dev_id = str(data)
            dev_name = self.cmb_audio_device.currentText().replace("🔈 ", "").replace(" [Default Windows]", "").strip()
            if self.audio_player:
                self.audio_player.set_output_mode("manual", device_id=dev_id, device_name=dev_name)
            else:
                self.settings_repo.set("audio_output_mode", "manual")
                self.settings_repo.set("audio_output_device_id", dev_id)
                self.settings_repo.set("audio_output_device_name", dev_name)

        self._update_device_info_label()

    def _on_refresh_devices_clicked(self) -> None:
        """Handler tombol Segarkan Perangkat untuk memindai ulang perangkat audio fisik Windows."""
        if self.audio_player:
            self.audio_player.refresh_audio_device()
        self._populate_audio_devices()
        QMessageBox.information(
            self,
            "Segarkan Perangkat",
            "Daftar perangkat output audio berhasil dipindai dan diperbarui dari sistem Windows.",
        )

    def _on_devices_changed_signal(self) -> None:
        """Handler sinyal audio_devices_changed saat sistem Windows mendeteksi koneksi/pelepasan jack audio."""
        self._populate_audio_devices()

    def _update_device_info_label(self, device_name: str = "") -> None:
        """Menampilkan status aktif perutean perangkat output audio secara informatif."""
        if not self.audio_player:
            self.lbl_device_info.setText("Status: Layanan pemutar audio belum siap.")
            return

        mode = self.audio_player.get_output_mode()
        curr_dev = self.audio_player.get_current_output_device()
        active_desc = device_name or (curr_dev.description() if not curr_dev.isNull() else "Default Windows")

        if mode == "auto":
            self.lbl_device_info.setText(
                f"ℹ️ Mode Otomatis Aktif: Suara saat ini mengalir ke '{active_desc}'. "
                f"Ketika kabel jack 3,5 mm speaker eksternal dipasang, suara bel otomatis berpindah tanpa perlu restart aplikasi."
            )
        else:
            self.lbl_device_info.setText(
                f"🔒 Mode Manual Terkunci: Suara bel diarahkan khusus ke perangkat '{active_desc}'. "
                f"Pilihan ini akan tetap dipertahankan sampai Anda mengganti perangkat atau memilih mode otomatis kembali."
            )

    def _test_audio_playback(self) -> None:
        """
        Memutar sampel suara bel melalui perangkat output audio yang dipilih.
        Memverifikasi bahwa suara benar-benar berbunyi di speaker/headphone target.
        """
        if not self.audio_player:
            QMessageBox.information(self, "Tes Suara", "Layanan pemutar audio tidak tersedia.")
            return

        self.audio_player.refresh_audio_device()
        curr_dev = self.audio_player.get_current_output_device()
        dev_desc = curr_dev.description() if not curr_dev.isNull() else "Default Windows"

        from src.database.repositories import AudioRepository
        audio_repo = AudioRepository(self.db)
        audios = audio_repo.get_all()

        test_path: Optional[Path] = None
        test_title: str = ""

        for a in audios:
            p = Path(a.stored_path)
            if p.exists() and p.is_file():
                test_path = p
                test_title = a.name
                break

        if not test_path:
            from src.core.config import get_assets_dir
            for fallback_name in ("chime_default.wav", "bell_sample.wav", "bel_masuk.wav"):
                p = get_assets_dir() / "sounds" / fallback_name
                if p.exists() and p.is_file():
                    test_path = p
                    test_title = fallback_name
                    break

        if not test_path:
            QMessageBox.warning(
                self,
                "Tes Suara Gagal",
                "Tidak ditemukan berkas audio bel untuk pengujian. Silakan impor file audio terlebih dahulu di menu Audio Bel.",
            )
            return

        success = self.audio_player.play_file(
            test_path,
            title=f"Tes Suara [{dev_desc}]",
            interrupt=True,
            mode="MANUAL",
        )
        if not success:
            QMessageBox.warning(
                self,
                "Tes Suara Gagal",
                f"Gagal memutar audio pengujian ke perangkat '{dev_desc}'. Periksa koneksi speaker atau volume sistem.",
            )

    def _test_audio_volume(self) -> None:
        """Alias kompatibilitas untuk memutar pengujian suara bel."""
        self._test_audio_playback()

    def _save_busy_policy(self, index: int) -> None:
        if self._is_loading:
            return
        policy = self.cmb_busy_policy.currentData()
        self.settings_repo.set("playback_busy_policy", policy)

    def _save_confirm_manual(self, checked: bool) -> None:
        if self._is_loading:
            return
        self.settings_repo.set("confirm_manual_bell", "true" if checked else "false")

    def _on_profile_selection_changed(self, index: int) -> None:
        if self._is_loading:
            return
        profile_id = self.cmb_profiles.currentData()
        if profile_id:
            try:
                self.profile_repo.set_active(profile_id)
                self.settings_changed.emit()
            except Exception as e:
                QMessageBox.critical(self, "Kesalahan", f"Gagal mengubah profil aktif: {e}")

    def _on_autostart_toggled(self, checked: bool) -> None:
        if self._is_loading:
            return

        if checked:
            reply = QMessageBox.question(
                self,
                "Konfirmasi Startup Windows",
                "Apakah Anda yakin ingin mengaktifkan KRONABEL agar otomatis berjalan saat Windows dimulai?\n\n"
                "Catatan: Aplikasi hanya dapat membunyikan bel jika komputer menyala dan aktif.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                self.chk_autostart.blockSignals(True)
                self.chk_autostart.setChecked(False)
                self.chk_autostart.blockSignals(False)
                return

        success = set_windows_autostart(checked)
        if not success:
            QMessageBox.warning(
                self,
                "Gagal Mengubah Pengaturan Startup",
                "Tidak dapat mengubah pengaturan startup Windows. Pastikan Anda memiliki izin akses registry.",
            )
            self.chk_autostart.blockSignals(True)
            self.chk_autostart.setChecked(not checked)
            self.chk_autostart.blockSignals(False)

    def _handle_create_backup(self) -> None:
        """Membuat cadangan data lengkap (Database + Audio + Pengaturan + Riwayat)."""
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"Cadangan_Bel_Sekolah_{now_str}.zip"

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan Cadangan Data",
            default_filename,
            "Arsip Cadangan (*.zip)",
        )

        if not save_path:
            return

        try:
            result = self.backup_service.create_backup(save_path)
            QMessageBox.information(
                self,
                "Pencadangan Berhasil",
                f"Data berhasil dicadangkan dengan aman ke:\n{save_path}\n\n"
                f"Ringkasan Isi Cadangan:\n"
                f"• Profil Jam Pelajaran: {result['profiles_count']}\n"
                f"• Jadwal Bel: {result['schedules_count']}\n"
                f"• Riwayat Pembunyian: {result['logs_count']}\n"
                f"• File Audio: {result['audio_files_count']}",
            )
        except Exception as e:
            logger.error("Gagal mencadangkan data: %s", e, exc_info=True)
            QMessageBox.critical(
                self,
                "Pencadangan Gagal",
                f"Terjadi kesalahan saat mencadangkan data:\n{e}",
            )

    def _handle_restore_backup(self) -> None:
        """Memulihkan data dari arsip cadangan dengan validasi ketat dan pratinjau."""
        zip_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih File Cadangan Data",
            "",
            "Arsip Cadangan (*.zip)",
        )

        if not zip_path:
            return

        # 1. Periksa integritas dan baca isi manifest
        try:
            summary = self.backup_service.inspect_backup(zip_path)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Arsip Cadangan Tidak Valid",
                f"File cadangan ditolak karena tidak valid atau korup:\n{e}",
            )
            return

        # 2. Tampilkan dialog konfirmasi eksplisit operator
        created_at_fmt = summary.get("created_at", "-")[:19].replace("T", " ")
        confirm_msg = (
            f"PERINGATAN PEMULIHAN DATA:\n\n"
            f"Anda akan memulihkan data dari cadangan berikut:\n"
            f"• Tanggal Cadangan: {created_at_fmt}\n"
            f"• Versi Aplikasi Pembuat: {summary.get('app_version', '-')}\n"
            f"• Profil Jam Pelajaran: {summary.get('profiles_count', 0)}\n"
            f"• Jadwal Bel: {summary.get('schedules_count', 0)}\n"
            f"• Riwayat Pembunyian: {summary.get('logs_count', 0)}\n"
            f"• File Audio: {summary.get('audio_files_count', 0)}\n\n"
            f"Tindakan ini akan menggantikan seluruh jadwal, profil, dan riwayat yang ada saat ini dengan data dari cadangan.\n"
            f"Sistem akan otomatis membuat cadangan darurat pra-pemulihan sebelum data diganti.\n\n"
            f"Apakah Anda yakin ingin melanjutkan pemulihan?"
        )

        reply = QMessageBox.warning(
            self,
            "Konfirmasi Pemulihan Data",
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # 3. Eksekusi pemulihan
        try:
            restore_result = self.backup_service.restore_backup(zip_path, create_pre_restore_backup=True)
            pre_note = ""
            if restore_result.get("pre_restore_backup"):
                pre_note = f"\n\nCadangan darurat kondisi sebelumnya telah disimpan di:\n{restore_result['pre_restore_backup']}"

            QMessageBox.information(
                self,
                "Pemulihan Berhasil",
                f"Data berhasil dipulihkan dari arsip cadangan.{pre_note}",
            )
            self.load_settings()
            self.data_restored.emit()
        except Exception as e:
            logger.error("Gagal memulihkan data: %s", e, exc_info=True)
            QMessageBox.critical(
                self,
                "Pemulihan Gagal",
                f"Terjadi kesalahan saat memulihkan data:\n{e}\n\n"
                f"Data aktif Anda dipertahankan dan tidak mengalami kerusakan.",
            )
