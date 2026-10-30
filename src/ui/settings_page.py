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
from src.services.audio_player import AudioPlayer
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

        # Volume Master
        vol_label = QLabel("Volume Suara Master:")
        vol_label.setStyleSheet("font-weight: 600; color: #1e293b; font-size: 13px;")
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

        btn_test_vol = QPushButton("Tes Suara")
        btn_test_vol.setStyleSheet(
            "background-color: #f1f5f9; color: #0284c7; font-weight: 600; border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px 12px;"
        )
        btn_test_vol.clicked.connect(self._test_audio_volume)
        vol_row.addWidget(btn_test_vol)

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
        # 1. Volume
        vol_str = self.settings_repo.get("volume", "80")
        try:
            vol_val = max(0, min(100, int(vol_str)))
        except ValueError:
            vol_val = 80
        self.slider_volume.setValue(vol_val)
        self.lbl_volume_val.setText(f"{vol_val}%")
        if self.audio_player:
            self.audio_player.set_volume(vol_val)

        # 2. Kebijakan saat audio sibuk
        busy_policy = self.settings_repo.get("playback_busy_policy", "reject")
        idx_busy = self.cmb_busy_policy.findData(busy_policy)
        if idx_busy >= 0:
            self.cmb_busy_policy.setCurrentIndex(idx_busy)

        # 3. Konfirmasi manual bell
        confirm_str = self.settings_repo.get("confirm_manual_bell", "true")
        self.chk_confirm_manual.setChecked(confirm_str.lower() != "false")

        # 4. Profil Aktif
        self.refresh_profiles()

        # 5. Windows Autostart
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

    def _on_volume_changed(self, value: int) -> None:
        self.lbl_volume_val.setText(f"{value}%")
        if not self._is_loading:
            self.settings_repo.set("volume", str(value))
            if self.audio_player:
                self.audio_player.set_volume(value)

    def _test_audio_volume(self) -> None:
        """Menguji suara bel singkat untuk memverifikasi volume."""
        if not self.audio_player:
            QMessageBox.information(self, "Tes Suara", "Layanan pemutar audio tidak tersedia.")
            return

        # Cari file audio pertama yang ada untuk pengujian
        from src.database.repositories import AudioRepository

        audio_repo = AudioRepository(self.db)
        audios = audio_repo.get_all()
        if not audios:
            QMessageBox.information(
                self,
                "Tes Suara",
                "Belum ada file audio bel di pustaka. Silakan impor file audio terlebih dahulu di menu Audio Bel.",
            )
            return

        first_audio = audios[0]
        if not Path(first_audio.stored_path).exists():
            QMessageBox.warning(
                self,
                "Tes Suara Gagal",
                f"File fisik untuk '{first_audio.name}' tidak ditemukan di disk.",
            )
            return

        self.audio_player.play(first_audio.stored_path, event_name=f"Tes Suara ({first_audio.name})")

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
                "Apakah Anda yakin ingin mengaktifkan Bel Otomatis Sekolah agar otomatis berjalan saat Windows dimulai?\n\n"
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
