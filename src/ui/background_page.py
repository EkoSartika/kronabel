"""
Halaman Pengaturan Latar Belakang (Background Page)
Memungkinkan pengelola mengunggah dan menyesuaikan gambar latar belakang
untuk Kotak Jam Digital dan Seluruh Panel Layar Utama dengan panduan ukuran ideal.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QFrame,
    QScrollArea,
    QSlider,
)

from src.core.config import get_assets_dir, get_user_data_dir
from src.database.db import DatabaseManager
from src.database.repositories import SettingsRepository

logger = logging.getLogger(__name__)


class BackgroundPage(QWidget):
    """Halaman kustomisasi latar belakang jam dan panel utama."""

    background_changed = Signal()

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.settings_repo = SettingsRepository(db)

        self._setup_ui()
        self.refresh_previews()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(10)

        # Header Halaman
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        page_title = QLabel("Pengaturan Latar Belakang")
        page_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #064e3b; border: none;")
        title_box.addWidget(page_title)

        page_desc = QLabel("Sesuaikan gambar latar belakang untuk kotak jam digital dan panel utama tampilan awal.")
        page_desc.setStyleSheet("font-size: 12px; color: #64748b; border: none;")
        title_box.addWidget(page_desc)

        main_layout.addLayout(title_box)

        # Scroll Area untuk Kartu Pengaturan
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 4, 0, 4)
        container_layout.setSpacing(14)

        # =========================================================================
        # 1. KARTU BACKGROUND KOTAK JAM DIGITAL
        # =========================================================================
        card_clock = QFrame()
        card_clock.setObjectName("ClockCard")
        card_clock.setStyleSheet("""
            QFrame#ClockCard {
                background-color: #ffffff;
                border: 1.5px solid #e2e8f0;
                border-radius: 12px;
            }
        """)
        layout_clock = QVBoxLayout(card_clock)
        layout_clock.setContentsMargins(18, 14, 18, 14)
        layout_clock.setSpacing(10)

        lbl_clock_title = QLabel("1. Latar Belakang Kotak Jam Digital")
        lbl_clock_title.setStyleSheet("font-size: 14.5px; font-weight: 800; color: #0f172a; border: none;")
        layout_clock.addWidget(lbl_clock_title)

        content_clock = QHBoxLayout()
        content_clock.setSpacing(18)

        # Pratinjau Kotak Jam
        self.preview_clock = QLabel()
        self.preview_clock.setFixedSize(260, 75)
        self.preview_clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_clock.setStyleSheet("""
            QLabel {
                background-color: #052c20;
                border: 1.5px solid #c59f42;
                border-radius: 8px;
            }
        """)
        content_clock.addWidget(self.preview_clock)

        # Keterangan Ukuran & Tombol Aksi
        info_clock = QVBoxLayout()
        info_clock.setSpacing(6)

        desc_clock = QLabel(
            "<b>Ukuran Pas yang Direkomendasikan:</b><br>"
            "• Dimensi Ideal: <b>440 × 126 piksel</b> (atau 880 × 252 piksel)<br>"
            "• Rasio Aspek: <b>~7 : 2</b> (Lanskap Persegi Panjang)<br>"
            "• Format File: PNG, JPG, JPEG, atau WEBP"
        )
        desc_clock.setStyleSheet("font-size: 11.5px; color: #334155; line-height: 1.4; border: none;")
        info_clock.addWidget(desc_clock)

        btn_box_clock = QHBoxLayout()
        btn_box_clock.setSpacing(10)

        self.btn_upload_clock = QPushButton("Pilih Gambar Jam...")
        self.btn_upload_clock.setFixedHeight(32)
        self.btn_upload_clock.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                font-weight: 700;
                font-size: 11.5px;
                border-radius: 6px;
                padding: 0 16px;
                border: none;
            }
            QPushButton:hover { background-color: #0369a1; }
        """)
        self.btn_upload_clock.clicked.connect(self._on_upload_clock_bg)
        btn_box_clock.addWidget(self.btn_upload_clock)

        self.btn_reset_clock = QPushButton("Kembalikan Template")
        self.btn_reset_clock.setFixedHeight(32)
        self.btn_reset_clock.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #475569;
                font-weight: 600;
                font-size: 11.5px;
                border: 1.5px solid #cbd5e1;
                border-radius: 6px;
                padding: 0 14px;
            }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        self.btn_reset_clock.clicked.connect(self._on_reset_clock_bg)
        btn_box_clock.addWidget(self.btn_reset_clock)

        btn_box_clock.addStretch()
        info_clock.addLayout(btn_box_clock)

        self.lbl_clock_status = QLabel("Status: Menggunakan latar template bawaan")
        self.lbl_clock_status.setStyleSheet("font-size: 11px; color: #64748b; font-style: italic; border: none;")
        info_clock.addWidget(self.lbl_clock_status)

        content_clock.addLayout(info_clock, 1)

        layout_clock.addLayout(content_clock)
        container_layout.addWidget(card_clock)

        # =========================================================================
        # 2. KARTU BACKGROUND SELURUH PANEL UTAMA
        # =========================================================================
        card_main = QFrame()
        card_main.setObjectName("MainCard")
        card_main.setStyleSheet("""
            QFrame#MainCard {
                background-color: #ffffff;
                border: 1.5px solid #e2e8f0;
                border-radius: 12px;
            }
        """)
        layout_main = QVBoxLayout(card_main)
        layout_main.setContentsMargins(18, 14, 18, 14)
        layout_main.setSpacing(10)

        lbl_main_title = QLabel("2. Latar Belakang Seluruh Panel Layar Utama")
        lbl_main_title.setStyleSheet("font-size: 14.5px; font-weight: 800; color: #0f172a; border: none;")
        layout_main.addWidget(lbl_main_title)

        content_main = QHBoxLayout()
        content_main.setSpacing(18)

        # Pratinjau Panel Utama
        self.preview_main = QLabel()
        self.preview_main.setFixedSize(260, 134)
        self.preview_main.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_main.setStyleSheet("""
            QLabel {
                background-color: #032b1e;
                border: 1.5px solid #c59f42;
                border-radius: 8px;
            }
        """)
        content_main.addWidget(self.preview_main)

        # Keterangan Ukuran & Tombol Aksi
        info_main = QVBoxLayout()
        info_main.setSpacing(6)

        desc_main = QLabel(
            "<b>Ukuran Pas yang Direkomendasikan:</b><br>"
            "• Dimensi Ideal: <b>740 × 380 piksel</b> (atau 1480 × 760 piksel)<br>"
            "• Rasio Aspek: <b>~37 : 19</b> (Lanskap Kotak Panel)<br>"
            "• Format File: PNG, JPG, JPEG, atau WEBP"
        )
        desc_main.setStyleSheet("font-size: 11.5px; color: #334155; line-height: 1.4; border: none;")
        info_main.addWidget(desc_main)

        btn_box_main = QHBoxLayout()
        btn_box_main.setSpacing(10)

        self.btn_upload_main = QPushButton("Pilih Gambar Panel...")
        self.btn_upload_main.setFixedHeight(32)
        self.btn_upload_main.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: #ffffff;
                font-weight: 700;
                font-size: 11.5px;
                border-radius: 6px;
                padding: 0 16px;
                border: none;
            }
            QPushButton:hover { background-color: #047857; }
        """)
        self.btn_upload_main.clicked.connect(self._on_upload_main_bg)
        btn_box_main.addWidget(self.btn_upload_main)

        self.btn_reset_main = QPushButton("Kembalikan Template")
        self.btn_reset_main.setFixedHeight(32)
        self.btn_reset_main.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #475569;
                font-weight: 600;
                font-size: 11.5px;
                border: 1.5px solid #cbd5e1;
                border-radius: 6px;
                padding: 0 14px;
            }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        self.btn_reset_main.clicked.connect(self._on_reset_main_bg)
        btn_box_main.addWidget(self.btn_reset_main)

        btn_box_main.addStretch()
        info_main.addLayout(btn_box_main)

        self.lbl_main_status = QLabel("Status: Menggunakan latar template bawaan")
        self.lbl_main_status.setStyleSheet("font-size: 11px; color: #64748b; font-style: italic; border: none;")
        info_main.addWidget(self.lbl_main_status)

        content_main.addLayout(info_main, 1)

        layout_main.addLayout(content_main)
        container_layout.addWidget(card_main)

        # =========================================================================
        # 3. KARTU TRANSPARANSI LATAR BELAKANG & PANEL UTAMA
        # =========================================================================
        card_trans = QFrame()
        card_trans.setObjectName("TransCard")
        card_trans.setStyleSheet("""
            QFrame#TransCard {
                background-color: #ffffff;
                border: 1.5px solid #e2e8f0;
                border-radius: 12px;
            }
        """)
        layout_trans = QVBoxLayout(card_trans)
        layout_trans.setContentsMargins(18, 14, 18, 14)
        layout_trans.setSpacing(10)

        lbl_trans_title = QLabel("3. Transparankan Latar Belakang & Panel Layar Utama")
        lbl_trans_title.setStyleSheet("font-size: 14.5px; font-weight: 800; color: #0f172a; border: none;")
        layout_trans.addWidget(lbl_trans_title)

        desc_trans = QLabel(
            "Transparankan panel kiri dan kanan tampilan awal agar gambar latar belakang yang diisi "
            "pada nomor 1 (Kotak Jam Digital) dan nomor 2 (Panel Layar Utama) dapat terlihat jelas dan tembus pandang (Efek Kaca / Glassmorphism)."
        )
        desc_trans.setStyleSheet("font-size: 12px; color: #334155; line-height: 1.4; border: none;")
        desc_trans.setWordWrap(True)
        layout_trans.addWidget(desc_trans)

        # Kontrol Slider Transparansi
        slider_box = QVBoxLayout()
        slider_box.setSpacing(6)

        self.lbl_trans_val = QLabel("Tingkat Transparansi: 0% (Solid / Bawaan)")
        self.lbl_trans_val.setStyleSheet("font-size: 12px; font-weight: 700; color: #0284c7; border: none;")
        slider_box.addWidget(self.lbl_trans_val)

        slider_row = QHBoxLayout()
        slider_row.setSpacing(12)

        lbl_min = QLabel("Solid (0%)")
        lbl_min.setStyleSheet("font-size: 11px; color: #64748b; font-weight: 600; border: none;")
        slider_row.addWidget(lbl_min)

        self.slider_trans = QSlider(Qt.Orientation.Horizontal)
        self.slider_trans.setRange(0, 85)
        self.slider_trans.setSingleStep(5)
        self.slider_trans.setPageStep(15)
        self.slider_trans.setFixedHeight(24)
        self.slider_trans.setStyleSheet("""
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
                background: #0284c7;
                border: 2px solid #ffffff;
                width: 18px;
                margin-top: -6px;
                margin-bottom: -6px;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #0369a1;
            }
        """)
        self.slider_trans.valueChanged.connect(self._on_transparency_slider_changed)
        slider_row.addWidget(self.slider_trans, 1)

        lbl_max = QLabel("Transparan (85%)")
        lbl_max.setStyleSheet("font-size: 11px; color: #64748b; font-weight: 600; border: none;")
        slider_row.addWidget(lbl_max)

        slider_box.addLayout(slider_row)
        layout_trans.addLayout(slider_box)

        # Tombol Preset Transparansi
        preset_box = QHBoxLayout()
        preset_box.setSpacing(8)

        btn_glass = QPushButton("Efek Kaca (60% - Rekomendasi)")
        btn_glass.setFixedHeight(30)
        btn_glass.setStyleSheet("""
            QPushButton {
                background-color: #e0f2fe;
                color: #0369a1;
                font-weight: 700;
                font-size: 11.5px;
                border: 1px solid #bae6fd;
                border-radius: 6px;
                padding: 0 14px;
            }
            QPushButton:hover { background-color: #bae6fd; }
        """)
        btn_glass.clicked.connect(lambda: self.slider_trans.setValue(60))
        preset_box.addWidget(btn_glass)

        btn_high = QPushButton("Transparan Penuh (80%)")
        btn_high.setFixedHeight(30)
        btn_high.setStyleSheet("""
            QPushButton {
                background-color: #f0fdf4;
                color: #15803d;
                font-weight: 700;
                font-size: 11.5px;
                border: 1px solid #bbf7d0;
                border-radius: 6px;
                padding: 0 14px;
            }
            QPushButton:hover { background-color: #bbf7d0; }
        """)
        btn_high.clicked.connect(lambda: self.slider_trans.setValue(80))
        preset_box.addWidget(btn_high)

        btn_solid = QPushButton("Solid Bawaan (0%)")
        btn_solid.setFixedHeight(30)
        btn_solid.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #475569;
                font-weight: 600;
                font-size: 11.5px;
                border: 1.5px solid #cbd5e1;
                border-radius: 6px;
                padding: 0 14px;
            }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        btn_solid.clicked.connect(lambda: self.slider_trans.setValue(0))
        preset_box.addWidget(btn_solid)

        preset_box.addStretch()
        layout_trans.addLayout(preset_box)

        self.lbl_trans_status = QLabel("Status: Panel Bawaan Solid (0%)")
        self.lbl_trans_status.setStyleSheet("font-size: 11px; color: #64748b; font-style: italic; border: none;")
        layout_trans.addWidget(self.lbl_trans_status)

        container_layout.addWidget(card_trans)

        container_layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def refresh_data(self):
        """Memuat ulang seluruh pratinjau dan status latar belakang."""
        self.refresh_previews()

    def _on_transparency_slider_changed(self, val: int):
        self._update_transparency_ui(val)
        self.settings_repo.set("panel_transparency", str(val))
        self.background_changed.emit()

    def _update_transparency_ui(self, val: int):
        if val == 0:
            self.lbl_trans_val.setText("Tingkat Transparansi: 0% (Solid / Bawaan)")
            self.lbl_trans_val.setStyleSheet("font-size: 12px; font-weight: 700; color: #475569; border: none;")
            self.lbl_trans_status.setText("Status: Panel Bawaan Solid (0%)")
            self.lbl_trans_status.setStyleSheet("font-size: 11px; color: #64748b; font-style: italic; border: none;")
        elif val >= 75:
            self.lbl_trans_val.setText(f"Tingkat Transparansi: {val}% (Sangat Transparan)")
            self.lbl_trans_val.setStyleSheet("font-size: 12px; font-weight: 700; color: #15803d; border: none;")
            self.lbl_trans_status.setText(f"Status: Transparansi Panel Aktif ({val}%) - Latar belakang 1 & 2 terlihat maksimal")
            self.lbl_trans_status.setStyleSheet("font-size: 11px; color: #15803d; font-weight: 700; border: none;")
        else:
            self.lbl_trans_val.setText(f"Tingkat Transparansi: {val}% (Efek Kaca / Glassmorphism)")
            self.lbl_trans_val.setStyleSheet("font-size: 12px; font-weight: 700; color: #0284c7; border: none;")
            self.lbl_trans_status.setText(f"Status: Transparansi Panel Aktif ({val}%) - Latar belakang 1 & 2 terlihat jelas")
            self.lbl_trans_status.setStyleSheet("font-size: 11px; color: #0284c7; font-weight: 700; border: none;")

    def refresh_previews(self):
        """Memuat ulang gambar pratinjau kotak jam dan panel utama."""
        # 1. Preview Jam
        clock_bg_path = self.settings_repo.get("clock_background_path", "")
        if clock_bg_path and Path(clock_bg_path).exists():
            pix_clock = QPixmap(clock_bg_path).scaled(
                self.preview_clock.width(),
                self.preview_clock.height(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.preview_clock.setPixmap(pix_clock)
            if hasattr(self, "lbl_clock_status"):
                self.lbl_clock_status.setText(f"Status: Gambar Kustom Aktif ({Path(clock_bg_path).name})")
                self.lbl_clock_status.setStyleSheet("font-size: 11px; color: #0284c7; font-weight: 700; border: none;")
        else:
            default_clock = get_assets_dir() / "clock_bg_clean.png"
            if default_clock.exists():
                pix_clock = QPixmap(str(default_clock)).scaled(
                    self.preview_clock.width(),
                    self.preview_clock.height(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.preview_clock.setPixmap(pix_clock)
            else:
                self.preview_clock.setText("(Template)")
            if hasattr(self, "lbl_clock_status"):
                self.lbl_clock_status.setText("Status: Menggunakan latar template bawaan")
                self.lbl_clock_status.setStyleSheet("font-size: 11px; color: #64748b; font-style: italic; border: none;")

        # 2. Preview Panel Utama
        main_bg_path = self.settings_repo.get("main_background_path", "")
        if main_bg_path and Path(main_bg_path).exists():
            pix_main = QPixmap(main_bg_path).scaled(
                self.preview_main.width(),
                self.preview_main.height(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.preview_main.setPixmap(pix_main)
            if hasattr(self, "lbl_main_status"):
                self.lbl_main_status.setText(f"Status: Gambar Kustom Aktif ({Path(main_bg_path).name})")
                self.lbl_main_status.setStyleSheet("font-size: 11px; color: #059669; font-weight: 700; border: none;")
        else:
            self.preview_main.clear()
            self.preview_main.setText("(Template)")
            self.preview_main.setStyleSheet("""
                QLabel {
                    background-color: #032b1e;
                    color: #fef3c7;
                    font-size: 11px;
                    font-weight: 600;
                    border: 1.5px solid #c59f42;
                    border-radius: 8px;
                }
            """)
            if hasattr(self, "lbl_main_status"):
                self.lbl_main_status.setText("Status: Menggunakan latar template bawaan")
                self.lbl_main_status.setStyleSheet("font-size: 11px; color: #64748b; font-style: italic; border: none;")

        # 3. Status Slider Transparansi
        if hasattr(self, "slider_trans"):
            trans_str = self.settings_repo.get("panel_transparency", "0")
            try:
                trans_val = int(trans_str)
            except ValueError:
                trans_val = 0
            self.slider_trans.blockSignals(True)
            self.slider_trans.setValue(trans_val)
            self.slider_trans.blockSignals(False)
            self._update_transparency_ui(trans_val)

    def _get_bg_storage_dir(self) -> Path:
        """Mengembalikan folder penyimpanan gambar background persisten."""
        d = get_user_data_dir() / "backgrounds"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _on_upload_clock_bg(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih Gambar Latar Kotak Jam",
            "",
            "Berkas Gambar (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not file_path:
            return

        try:
            src = Path(file_path)
            dest = self._get_bg_storage_dir() / f"clock_custom{src.suffix.lower()}"
            shutil.copy2(src, dest)

            self.settings_repo.set("clock_background_path", str(dest))
            self.refresh_previews()
            self.background_changed.emit()

            QMessageBox.information(
                self,
                "Berhasil",
                "Latar belakang kotak jam digital berhasil diperbarui dan disesuaikan!",
            )
        except Exception as e:
            logger.error("Gagal mengunggah gambar latar jam: %s", e)
            QMessageBox.critical(self, "Error", f"Gagal menyimpan berkas gambar: {e}")

    def _reset_clock_bg(self):
        """Mereset latar kotak jam kembali ke template sistem."""
        self.settings_repo.set("clock_background_path", "")
        self.refresh_previews()
        self.background_changed.emit()

    def _on_reset_clock_bg(self):
        self._reset_clock_bg()
        QMessageBox.information(
            self,
            "Berhasil",
            "Latar belakang kotak jam dikembalikan ke template bawaan.",
        )

    def _on_upload_main_bg(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih Gambar Latar Panel Utama",
            "",
            "Berkas Gambar (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not file_path:
            return

        try:
            src = Path(file_path)
            dest = self._get_bg_storage_dir() / f"main_custom{src.suffix.lower()}"
            shutil.copy2(src, dest)

            self.settings_repo.set("main_background_path", str(dest))
            self.refresh_previews()
            self.background_changed.emit()

            QMessageBox.information(
                self,
                "Berhasil",
                "Latar belakang panel utama berhasil diperbarui dan disesuaikan!",
            )
        except Exception as e:
            logger.error("Gagal mengunggah gambar latar panel: %s", e)
            QMessageBox.critical(self, "Error", f"Gagal menyimpan berkas gambar: {e}")

    def _reset_main_bg(self):
        """Mereset latar panel utama kembali ke template sistem."""
        self.settings_repo.set("main_background_path", "")
        self.refresh_previews()
        self.background_changed.emit()

    def _on_reset_main_bg(self):
        self._reset_main_bg()
        QMessageBox.information(
            self,
            "Berhasil",
            "Latar belakang panel utama dikembalikan ke template bawaan.",
        )
