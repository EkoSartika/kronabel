"""
Halaman Pustaka & Pengujian Audio Bel Otomatis Sekolah.
Menyediakan pengelolaan berkas MP3/WAV, impor persisten, pratinjau audio,
kontrol volume, dan pengujian suara.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.database.db import DatabaseManager
from src.database.repositories import AudioRepository
from src.models.models import AudioFile
from src.services.audio_player import AudioPlayer, AudioStatus


class AudioPage(QWidget):
    """Halaman Pustaka Audio Bel."""

    audio_list_changed = Signal()

    def __init__(self, db: DatabaseManager, audio_player: AudioPlayer, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db
        self.audio_player = audio_player
        self.audio_repo = AudioRepository(db)

        self._setup_ui()
        self.refresh_audio_list()

        # Hubungkan sinyal dari audio player
        self.audio_player.status_changed.connect(self._on_player_status_changed)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # 1. Baris Kontrol Atas (Informasi & Tombol Impor)
        header_card = QFrame()
        header_card.setObjectName("HeaderCard")
        header_card.setStyleSheet(
            """
            QFrame#HeaderCard {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
            }
            """
        )
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(14, 10, 14, 10)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        title = QLabel("Pustaka Audio Bel (MP3 & WAV)")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #0f172a;")
        desc = QLabel(
            "File audio yang diimpor akan disalin secara permanen ke direktori data aplikasi Windows "
            "dan siap dipilih pada jadwal bel harian."
        )
        desc.setStyleSheet("color: #64748b; font-size: 12px;")
        desc.setWordWrap(True)
        info_layout.addWidget(title)
        info_layout.addWidget(desc)
        header_layout.addLayout(info_layout, 1)

        self.import_btn = QPushButton("Impor File Audio")
        self.import_btn.setMinimumHeight(32)
        self.import_btn.setStyleSheet(
            "background-color: #0284c7; color: #ffffff; border: none; "
            "border-radius: 6px; padding: 7px 16px; font-weight: 600; font-size: 12px;"
        )
        self.import_btn.setCursor(Qt.PointingHandCursor)
        self.import_btn.clicked.connect(self._on_import_audio)
        header_layout.addWidget(self.import_btn)

        main_layout.addWidget(header_card)

        # 2. Panel Kontrol Volume & Status Pemutaran
        controls_card = QFrame()
        controls_card.setObjectName("ControlsCard")
        controls_card.setStyleSheet(
            """
            QFrame#ControlsCard {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
            }
            """
        )
        controls_layout = QHBoxLayout(controls_card)
        controls_layout.setContentsMargins(16, 12, 16, 12)
        controls_layout.setSpacing(16)

        # Volume Slider
        vol_label = QLabel("Volume:")
        vol_label.setStyleSheet("font-weight: 600; color: #334155;")
        controls_layout.addWidget(vol_label)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.audio_player.get_volume())
        self.volume_slider.setFixedWidth(160)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        controls_layout.addWidget(self.volume_slider)

        self.vol_value_label = QLabel(f"{self.volume_slider.value()}%")
        self.vol_value_label.setStyleSheet("font-weight: 600; color: #0f172a; min-width: 40px;")
        controls_layout.addWidget(self.vol_value_label)

        controls_layout.addSpacing(20)

        # Status Audio Aktif
        status_title = QLabel("Status Audio:")
        status_title.setStyleSheet("font-weight: 600; color: #334155;")
        self.status_display = QLabel("Siap (Idle)")
        self.status_display.setStyleSheet(
            "color: #0369a1; background-color: #e0f2fe; padding: 4px 10px; "
            "border-radius: 6px; font-weight: 600; font-size: 12px;"
        )
        controls_layout.addWidget(status_title)
        controls_layout.addWidget(self.status_display)

        controls_layout.addStretch()

        # Tombol Hentikan Audio
        self.stop_btn = QPushButton("Hentikan Pemutaran")
        self.stop_btn.setStyleSheet(
            "background-color: #fee2e2; color: #991b1b; border: 1px solid #fecdd3; "
            "border-radius: 6px; padding: 6px 14px; font-weight: 600;"
        )
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.clicked.connect(self.audio_player.stop)
        controls_layout.addWidget(self.stop_btn)

        main_layout.addWidget(controls_card)

        # 3. Tabel Daftar Audio
        table_card = QFrame()
        table_card.setObjectName("TableCard")
        table_card.setStyleSheet(
            """
            QFrame#TableCard {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
            }
            """
        )
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(12, 12, 12, 12)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Nama Label Audio", "File Asli", "Path Penyimpanan Persisten", "Status Berkas", "Aksi"
        ])
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Interactive)
        self.table.setColumnWidth(4, 160)
        self.table.horizontalHeader().setMinimumSectionSize(60)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setStyleSheet(
            """
            QTableWidget {
                border: 1px solid #f1f5f9;
                gridline-color: #f1f5f9;
                background-color: #ffffff;
                color: #0f172a;
                font-size: 13px;
            }
            QTableWidget::item {
                color: #0f172a;
                background-color: #ffffff;
                padding: 6px 8px;
            }
            QTableWidget::item:selected {
                background-color: #e0f2fe;
                color: #0369a1;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                color: #334155;
                padding: 10px 8px;
                font-weight: 700;
                border: none;
                border-bottom: 2px solid #e2e8f0;
            }
            """
        )

        table_layout.addWidget(self.table)
        main_layout.addWidget(table_card, 1)

    def refresh_audio_list(self) -> None:
        """Memuat daftar audio dari database."""
        audio_files = self.audio_repo.get_all()
        self.table.setRowCount(len(audio_files))

        for row, a in enumerate(audio_files):
            # 0. Nama Label
            name_item = QTableWidgetItem(a.name)
            name_item.setFont(QFont("Arial", 10, QFont.Bold))
            name_item.setForeground(QColor("#0f172a"))
            self.table.setItem(row, 0, name_item)

            # 1. File Asli
            orig_item = QTableWidgetItem(a.original_filename)
            orig_item.setForeground(QColor("#0f172a"))
            self.table.setItem(row, 1, orig_item)

            # 2. Path Penyimpanan
            path_item = QTableWidgetItem(a.stored_path)
            path_item.setForeground(QColor("#475569"))
            self.table.setItem(row, 2, path_item)

            # 3. Status Keberadaan Berkas
            exists = Path(a.stored_path).exists()
            status_item = QTableWidgetItem("Tersedia" if exists else "File Hilang")
            status_item.setTextAlignment(Qt.AlignCenter)
            if exists:
                status_item.setForeground(Qt.darkGreen)
            else:
                status_item.setForeground(Qt.red)
            self.table.setItem(row, 3, status_item)

            # 4. Tombol Aksi (Putar/Pratinjau, Hapus)
            action_widget = QWidget()
            action_widget.setStyleSheet("background-color: transparent;")
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(6, 4, 6, 4)
            action_layout.setSpacing(8)
            action_layout.setAlignment(Qt.AlignCenter)

            play_btn = QPushButton("Putar")
            play_btn.setMinimumHeight(28)
            play_btn.setMinimumWidth(68)
            play_btn.setStyleSheet(
                "min-height: 28px; padding: 4px 12px; font-size: 11px; font-weight: 600; border-radius: 5px; "
                "background-color: #e0f2fe; color: #0284c7; border: 1px solid #bae6fd;"
            )
            play_btn.setCursor(Qt.PointingHandCursor)
            play_btn.clicked.connect(lambda _=False, path=a.stored_path, name=a.name: self._play_preview(path, name))
            action_layout.addWidget(play_btn)

            del_btn = QPushButton("Hapus")
            del_btn.setMinimumHeight(28)
            del_btn.setMinimumWidth(56)
            del_btn.setStyleSheet(
                "min-height: 28px; padding: 4px 12px; font-size: 11px; font-weight: 600; border-radius: 5px; "
                "background-color: #fff1f2; color: #be123c; border: 1px solid #fecdd3;"
            )
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.clicked.connect(lambda _=False, af=a: self._on_delete_audio(af))
            action_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 4, action_widget)

    def _on_import_audio(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih File Audio Bel",
            "",
            "Audio Files (*.mp3 *.wav);;Semua File (*.*)",
        )
        if not file_path:
            return

        suggested_name = Path(file_path).stem
        label_name, ok = QInputDialog.getText(
            self,
            "Nama Label Audio",
            "Masukkan label/nama untuk audio ini:",
            text=suggested_name,
        )
        if not ok or not label_name.strip():
            label_name = suggested_name

        try:
            imported = self.audio_player.import_audio_file(file_path, custom_name=label_name)
            QMessageBox.information(
                self,
                "Impor Berhasil",
                f"File '{imported.original_filename}' berhasil disalin ke pustaka dengan nama '{imported.name}'.",
            )
            self.refresh_audio_list()
            self.audio_list_changed.emit()
        except Exception as e:
            QMessageBox.warning(self, "Gagal Mengimpor", f"Terjadi kesalahan saat mengimpor audio:\n\n{e}")

    def _play_preview(self, file_path: str, title: str) -> None:
        if not self.audio_player.has_audio_output_device():
            QMessageBox.warning(
                self,
                "Perangkat Audio Tidak Ditemukan",
                "Tidak ada perangkat output audio (speaker/headphone) yang terdeteksi pada komputer ini.",
            )
            return

        success = self.audio_player.play_file(file_path, title=f"Pratinjau: {title}")
        if not success:
            QMessageBox.warning(
                self,
                "Pemutaran Gagal",
                f"Tidak dapat memutar file audio. Pastikan file tersedia dan tidak sedang memutar audio lain.",
            )

    def _on_delete_audio(self, audio: AudioFile) -> None:
        # Cek apakah audio masih digunakan jadwal
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS total FROM schedules WHERE audio_id = ?", (audio.id,))
            used_count = cursor.fetchone()["total"]

        extra_msg = ""
        if used_count > 0:
            extra_msg = f"\n\nPERINGATAN: File audio ini saat ini digunakan oleh {used_count} jadwal bel. " \
                        f"Jika dihapus, jadwal terkait akan kembali ke audio default."

        confirm = QMessageBox.question(
            self,
            "Konfirmasi Hapus Audio",
            f"Apakah Anda yakin ingin menghapus '{audio.name}' dari pustaka?{extra_msg}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            self.audio_repo.delete(audio.id)
            self.refresh_audio_list()
            self.audio_list_changed.emit()

    def _on_volume_changed(self, value: int) -> None:
        self.audio_player.set_volume(value)
        self.vol_value_label.setText(f"{value}%")

    def _on_player_status_changed(self, status: str) -> None:
        status_map = {
            AudioStatus.IDLE.value: ("Siap (Idle)", "#0369a1", "#e0f2fe"),
            AudioStatus.LOADING.value: ("Memuat...", "#854d0e", "#fef9c3"),
            AudioStatus.PLAYING.value: (f"Sedang Memutar: {self.audio_player.current_title}", "#15803d", "#dcfce7"),
            AudioStatus.COMPLETED.value: ("Selesai", "#0369a1", "#e0f2fe"),
            AudioStatus.FAILED.value: ("Gagal Memutar", "#b91c1c", "#fee2e2"),
            AudioStatus.INTERRUPTED.value: ("Dihentikan", "#b45309", "#fef3c7"),
        }
        text, fg, bg = status_map.get(status, (status.capitalize(), "#334155", "#f1f5f9"))
        self.status_display.setText(text)
        self.status_display.setStyleSheet(
            f"color: {fg}; background-color: {bg}; padding: 4px 10px; "
            "border-radius: 6px; font-weight: 600; font-size: 12px;"
        )
