"""
Panel Utama Bel Otomatis Sekolah (Compact Desktop Panel)
Desain ringkas (~720x360 px) dengan Jam Digital Besar, Tombol ON/OFF Scheduler,
Tombol Bel Manual Berkode, Tombol Setting Berautentikasi, dan Daftar Jadwal di Sisi Kanan.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.config import APP_DISPLAY_NAME, APP_VERSION, DAYS_OF_WEEK, get_assets_dir
from src.core.win7_compat import is_dwm_composition_enabled
from src.database.db import DatabaseManager
from src.database.repositories import AudioRepository, BellLogRepository, ProfileRepository, ScheduleRepository, SettingsRepository
from src.models.models import AudioFile, BellLog, Schedule
from src.services.audio_player import AudioPlayer
from src.services.auth_service import AuthService
from src.services.clock_service import SystemClock, IClock
from src.services.scheduler import SchedulerService
from src.ui.admin_window import AdminWindow
from src.ui.auth_dialogs import LoginDialog, SetupPasswordDialog
from src.ui.dialog_helper import patch_qmessagebox

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Panel Utama Aplikasi Bel Otomatis Sekolah."""

    def __init__(self, db: Optional[DatabaseManager] = None, parent=None):
        super().__init__(parent)
        patch_qmessagebox()
        self.db = db if db else DatabaseManager()
        self.profile_repo = ProfileRepository(self.db)
        self.schedule_repo = ScheduleRepository(self.db)
        self.audio_repo = AudioRepository(self.db)
        self.settings_repo = SettingsRepository(self.db)
        self.log_repo = BellLogRepository(self.db)

        # Layanan Inti
        self.audio_player = AudioPlayer(self.db)
        self.clock: IClock = SystemClock()
        self.scheduler = SchedulerService(self.db, self.audio_player, self.clock)
        self.auth = AuthService(self.settings_repo)

        self.admin_window: Optional[AdminWindow] = None
        self.current_day_schedules: List[Schedule] = []

        # Konfigurasi Jendela Ringkas (Kecil, Non-Maximized, Frameless, Tanpa Taskbar, Terkunci di Tengah)
        self.setWindowTitle(f"{APP_DISPLAY_NAME} v{APP_VERSION}")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        # Hanya aktifkan WA_TranslucentBackground jika DWM (Aero) aktif agar tidak berlatar hitam di Windows 7 Basic/Classic
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, is_dwm_composition_enabled())
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        if QApplication.instance():
            QApplication.instance().setQuitOnLastWindowClosed(False)
        self.resize(740, 380)
        self.setMinimumSize(680, 340)
        self._has_centered = False
        self.tray: Optional[QSystemTrayIcon] = None

        self._setup_ui()
        self._setup_tray()
        self._init_services()
        self.refresh_all_data()
        self._center_on_screen()

    def _setup_ui(self):
        self.setStyleSheet("""
            QMessageBox {
                background-color: #ffffff;
            }
            QMessageBox QLabel {
                color: #0f172a;
                background-color: transparent;
                font-size: 13px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QMessageBox QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border: 1.5px solid #1d4ed8;
                border-radius: 6px;
                padding: 6px 22px;
                min-width: 80px;
                min-height: 28px;
                font-size: 12px;
                font-weight: 700;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QMessageBox QPushButton:default {
                background-color: #2563eb;
                color: #ffffff;
                border: 1.5px solid #1d4ed8;
            }
            QMessageBox QPushButton:focus {
                background-color: #2563eb;
                color: #ffffff;
                border: 2px solid #60a5fa;
            }
            QMessageBox QPushButton:hover {
                background-color: #1d4ed8;
                border-color: #1e40af;
                color: #ffffff;
            }
            QMessageBox QPushButton:pressed {
                background-color: #1e40af;
                color: #ffffff;
            }
            QMessageBox QPushButton:!default {
                background-color: #f1f5f9;
                color: #0f172a;
                border: 1.5px solid #cbd5e1;
            }
            QMessageBox QPushButton:!default:hover {
                background-color: #e2e8f0;
                border-color: #94a3b8;
                color: #0f172a;
            }
            QMessageBox QPushButton:!default:focus {
                background-color: #f1f5f9;
                color: #0f172a;
                border: 2px solid #2563eb;
            }
        """)

        central = QWidget()
        central.setObjectName("CentralWidget")
        self.central_widget_ref = central
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(12)

        # =========================================================================
        # 1. PANEL KIRI: KONTROL UTAMA (~460px)
        # =========================================================================
        left_panel = QFrame()
        left_panel.setObjectName("LeftPanel")
        self.left_panel_ref = left_panel
        left_panel.setStyleSheet("""
            QFrame#LeftPanel {
                background-color: #fffcf4;
                border: 1.5px solid #e5d8b8;
                border-radius: 12px;
            }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(14, 10, 14, 10)
        left_layout.setSpacing(8)

        # A. Header Kiri: Nama App (Terpusat Horizontal Sejajar Jam Digital) & Profil Aktif
        header_layout = QGridLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)

        self.app_title = QLabel("KRONABEL")
        self.app_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.app_title.setStyleSheet("font-size: 15px; font-weight: 900; color: #0b3b2d; border: none; letter-spacing: 0.6px; background: transparent;")

        self.profile_badge = QLabel("Profil: Reguler")
        self.profile_badge.setFixedHeight(26)
        self.profile_badge.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fef3c7, stop:1 #fde68a);
            color: #78350f;
            font-size: 11px;
            font-weight: 800;
            padding: 2px 12px;
            border-radius: 13px;
            border: 1.5px solid #ca8a04;
        """)

        # Tempatkan tulisan KRONABEL di tengah horizontal sempurna (kolom 0 span 3),
        # sehingga berada persis satu garis horizontal dengan pusat jam digital di bawahnya.
        # Profil badge disematkan di pojok kanan (kolom 2) tanpa menggeser pusat judul.
        header_layout.addWidget(self.app_title, 0, 0, 1, 3, Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.profile_badge, 0, 2, 1, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        left_layout.addLayout(header_layout)

        # B. Jam Digital Besar & Tanggal (Latar Lanskap Gunung & Pendopo Sumedang Emas / Custom)
        clock_box = QFrame()
        clock_box.setObjectName("ClockBox")
        clock_box.setFixedHeight(126)
        self.clock_box = clock_box
        clock_layout = QVBoxLayout(clock_box)
        clock_layout.setContentsMargins(8, 6, 8, 6)
        clock_layout.setSpacing(1)

        self.clock_label = QLabel("00:00:00")
        self.clock_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.clock_label.setStyleSheet("""
            font-family: 'Georgia', 'Cinzel', 'Palatino Linotype', 'Times New Roman', serif;
            font-size: 38px;
            font-weight: bold;
            color: #fff7d6;
            border: none;
            background: transparent;
        """)
        clock_layout.addWidget(self.clock_label)

        self.date_label = QLabel("Senin, 01 Januari 2026")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.date_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
            color: #fef9ee;
            border: none;
            background: transparent;
        """)
        clock_layout.addWidget(self.date_label)

        left_layout.addWidget(clock_box)

        # C. Baris Tombol ON/OFF, Status, Stop & Setting
        control_bar = QHBoxLayout()
        control_bar.setSpacing(8)

        # Tombol ON
        self.btn_on = QPushButton("ON")
        self.btn_on.setFixedHeight(34)
        self.btn_on.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #059669, stop:1 #047857);
                color: #ffffff;
                font-size: 12px;
                font-weight: 800;
                border: 1.5px solid #065f46;
                border-radius: 8px;
                padding: 0 16px;
            }
            QPushButton:hover { background: #059669; }
            QPushButton:disabled { background-color: #a7f3d0; color: #065f46; border: none; }
        """)
        self.btn_on.clicked.connect(self._on_start_scheduler)
        control_bar.addWidget(self.btn_on)

        # Tombol OFF
        self.btn_off = QPushButton("OFF")
        self.btn_off.setFixedHeight(34)
        self.btn_off.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #dc2626, stop:1 #991b1b);
                color: #ffffff;
                font-size: 12px;
                font-weight: 800;
                border: 1.5px solid #7f1d1d;
                border-radius: 8px;
                padding: 0 16px;
            }
            QPushButton:hover { background: #b91c1c; }
            QPushButton:disabled { background-color: #fecaca; color: #991b1b; border: none; }
        """)
        self.btn_off.clicked.connect(self._on_stop_scheduler)
        control_bar.addWidget(self.btn_off)

        # Status Scheduler
        self.status_label = QLabel("AKTIF")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFixedHeight(34)
        self.status_label.setStyleSheet("""
            background: #dcfce7;
            color: #15803d;
            font-weight: 800;
            font-size: 12px;
            border: 1.5px solid #86efac;
            border-radius: 8px;
            padding: 0 14px;
        """)
        control_bar.addWidget(self.status_label)

        control_bar.addStretch()

        # Tombol Stop Audio (Satu baris berdampingan dengan Setting)
        self.btn_stop_audio = QPushButton("Stop")
        self.btn_stop_audio.setFixedHeight(34)
        self.btn_stop_audio.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #b45309, stop:1 #78350f);
                color: #ffffff;
                font-size: 12px;
                font-weight: 800;
                border: 1.5px solid #78350f;
                border-radius: 8px;
                padding: 0 16px;
            }
            QPushButton:hover { background: #92400e; }
        """)
        self.btn_stop_audio.clicked.connect(self._on_stop_audio)
        control_bar.addWidget(self.btn_stop_audio)

        # Tombol Setting (Nuansa Keraton Hijau Tua & Emas)
        self.btn_setting = QPushButton("Setting")
        self.btn_setting.setFixedHeight(34)
        self.btn_setting.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0f3b2e, stop:1 #062b1e);
                color: #ffffff;
                font-size: 12px;
                font-weight: 800;
                border: 1.5px solid #064e3b;
                border-radius: 8px;
                padding: 0 16px;
            }
            QPushButton:hover { background: #064e3b; }
        """)
        self.btn_setting.clicked.connect(self._on_click_setting)
        control_bar.addWidget(self.btn_setting)

        left_layout.addLayout(control_bar)

        # D. Bagian Tombol Manual Kode Lagu
        self.lbl_manual = QLabel("Bel Manual")
        self.lbl_manual.setStyleSheet("font-size: 11px; font-weight: 800; color: #78350f; border: none; padding-top: 2px;")
        left_layout.addWidget(self.lbl_manual)

        # Scroll Area Tombol Kode Lagu (Grid 3 Baris Penuh Kompak)
        self.manual_scroll = QScrollArea()
        self.manual_scroll.setObjectName("ManualScroll")
        self.manual_scroll.setWidgetResizable(True)
        self.manual_scroll.setFixedHeight(114)
        self.manual_scroll.setStyleSheet("""
            QScrollArea#ManualScroll {
                border: 1.5px solid #e5d8b8;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QScrollBar:horizontal {
                height: 4px;
                background: #f1f5f9;
                border-radius: 2px;
            }
            QScrollBar::handle:horizontal {
                background: #d97706;
                border-radius: 2px;
            }
        """)

        self.manual_container = QWidget()
        self.manual_container.setStyleSheet("background-color: transparent;")
        self.manual_layout = QGridLayout(self.manual_container)
        self.manual_layout.setContentsMargins(6, 6, 6, 6)
        self.manual_layout.setSpacing(4)
        self.manual_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.manual_scroll.setWidget(self.manual_container)

        left_layout.addWidget(self.manual_scroll)

        main_layout.addWidget(left_panel, stretch=6)

        # =========================================================================
        # 2. PANEL KANAN: DAFTAR JADWAL HARI INI (Nuansa Hijau Keraton & Emas)
        # =========================================================================
        right_panel = QFrame()
        right_panel.setObjectName("RightPanel")
        self.right_panel_ref = right_panel
        right_panel.setStyleSheet("""
            QFrame#RightPanel {
                background-color: #04261c;
                border: 2px solid #c59f42;
                border-radius: 12px;
            }
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 8)
        right_layout.setSpacing(6)

        # Header Kanan
        self.right_title = QLabel("Jadwal Hari Ini")
        self.right_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.right_title.setStyleSheet("""
            color: #ffffff;
            font-size: 13px;
            font-weight: 800;
            letter-spacing: 0.5px;
            border: none;
            padding-bottom: 2px;
        """)
        right_layout.addWidget(self.right_title)

        # Tabel Jadwal Sisi Kanan (Kontras Emas di atas Hijau Zamrud)
        self.schedule_table = QTableWidget()
        self.schedule_table.setColumnCount(2)
        self.schedule_table.setHorizontalHeaderLabels(["Jam", "Kode / Bel"])
        self.schedule_table.verticalHeader().setVisible(False)
        self.schedule_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.schedule_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.schedule_table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                color: #fef3c7;
                border: 1px solid #064e3b;
                border-radius: 6px;
                gridline-color: #064e3b;
                font-size: 12px;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d97706, stop:1 #b45309);
                color: #451a03;
                font-size: 11px;
                font-weight: 900;
                border: none;
                padding: 4px;
            }
        """)

        r_hdr = self.schedule_table.horizontalHeader()
        r_hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        r_hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.schedule_table.setColumnWidth(0, 60)

        right_layout.addWidget(self.schedule_table)

        # Footer Kanan: Countdown Bel Berikutnya
        self.next_bell_label = QLabel("Berikutnya: -")
        self.next_bell_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.next_bell_label.setStyleSheet("""
            color: #86efac;
            font-size: 11px;
            font-weight: 800;
            border: none;
            padding-top: 2px;
        """)
        right_layout.addWidget(self.next_bell_label)

        # Banner Notifikasi Jadwal Terlewat (Non-blocking, tersembunyi secara default)
        self.missed_notif_banner = QLabel("")
        self.missed_notif_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.missed_notif_banner.setWordWrap(True)
        self.missed_notif_banner.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fef3c7, stop:1 #fde68a);
                color: #78350f;
                font-size: 10px;
                font-weight: 800;
                border: 1px solid #d97706;
                border-radius: 5px;
                padding: 3px 6px;
            }
        """)
        self.missed_notif_banner.setVisible(False)
        right_layout.addWidget(self.missed_notif_banner)

        main_layout.addWidget(right_panel, stretch=4)
        self.apply_backgrounds()

    def apply_backgrounds(self):
        """Menerapkan latar belakang kustom atau bawaan untuk Kotak Jam dan Panel Utama."""
        # A. Kotak Jam Digital (ClockBox: ~440x126 px)
        custom_clock_bg = self.settings_repo.get("clock_background_path", "")
        if custom_clock_bg and Path(custom_clock_bg).exists():
            clock_img_url = Path(custom_clock_bg).as_posix()
        else:
            default_clock_bg = get_assets_dir() / "clock_bg_clean.png"
            clock_img_url = default_clock_bg.as_posix() if default_clock_bg.exists() else ""

        if hasattr(self, "clock_box") and self.clock_box:
            if clock_img_url:
                self.clock_box.setStyleSheet(f"""
                    QFrame#ClockBox {{
                        border: 1.5px solid #c59f42;
                        border-radius: 10px;
                        background-image: url("{clock_img_url}");
                        background-repeat: no-repeat;
                        background-position: center center;
                        background-color: #052c20;
                    }}
                """)
            else:
                self.clock_box.setStyleSheet("""
                    QFrame#ClockBox {
                        border: 1.5px solid #c59f42;
                        border-radius: 10px;
                        background-color: #052c20;
                    }
                """)

        # B. Seluruh Panel Utama (CentralWidget: ~740x380 px)
        custom_main_bg = self.settings_repo.get("main_background_path", "")
        if custom_main_bg and Path(custom_main_bg).exists():
            main_img_url = Path(custom_main_bg).as_posix()
            if hasattr(self, "central_widget_ref") and self.central_widget_ref:
                self.central_widget_ref.setStyleSheet(f"""
                    QWidget#CentralWidget {{
                        background-color: #032b1e;
                        background-image: url("{main_img_url}");
                        background-repeat: no-repeat;
                        background-position: center center;
                        border: 2px solid #c59f42;
                        border-radius: 16px;
                    }}
                """)
        else:
            if hasattr(self, "central_widget_ref") and self.central_widget_ref:
                self.central_widget_ref.setStyleSheet("""
                    QWidget#CentralWidget {
                        background-color: #032b1e;
                        border: 2px solid #c59f42;
                        border-radius: 16px;
                    }
                """)

        # C. Transparansi Panel Kiri & Kanan (agar latar belakang 1 & 2 tembus pandang)
        trans_str = self.settings_repo.get("panel_transparency", "0")
        try:
            transparency = int(trans_str)
        except ValueError:
            transparency = 0

        if transparency > 0:
            # Hitung alpha untuk panel kiri dan kanan
            alpha_left = max(0.12, (100 - transparency) / 100.0)
            alpha_scroll = max(0.15, alpha_left * 0.85)
            alpha_right = max(0.18, (100 - transparency * 0.82) / 100.0)

            if hasattr(self, "left_panel_ref") and self.left_panel_ref:
                self.left_panel_ref.setStyleSheet(f"""
                    QFrame#LeftPanel {{
                        background-color: rgba(255, 252, 244, {alpha_left:.2f});
                        border: 1.5px solid rgba(229, 216, 184, 0.7);
                        border-radius: 12px;
                    }}
                """)
            if hasattr(self, "manual_scroll") and self.manual_scroll:
                self.manual_scroll.setStyleSheet(f"""
                    QScrollArea#ManualScroll {{
                        border: 1.5px solid rgba(229, 216, 184, 0.6);
                        border-radius: 8px;
                        background-color: rgba(255, 255, 255, {alpha_scroll:.2f});
                    }}
                    QScrollBar:horizontal {{
                        height: 4px;
                        background: rgba(241, 245, 249, 0.5);
                        border-radius: 2px;
                    }}
                    QScrollBar::handle:horizontal {{
                        background: #d97706;
                        border-radius: 2px;
                    }}
                """)
            if hasattr(self, "right_panel_ref") and self.right_panel_ref:
                self.right_panel_ref.setStyleSheet(f"""
                    QFrame#RightPanel {{
                        background-color: rgba(4, 38, 28, {alpha_right:.2f});
                        border: 2px solid rgba(197, 159, 66, 0.8);
                        border-radius: 12px;
                    }}
                """)
        else:
            # Bawaan Solid
            if hasattr(self, "left_panel_ref") and self.left_panel_ref:
                self.left_panel_ref.setStyleSheet("""
                    QFrame#LeftPanel {
                        background-color: #fffcf4;
                        border: 1.5px solid #e5d8b8;
                        border-radius: 12px;
                    }
                """)
            if hasattr(self, "manual_scroll") and self.manual_scroll:
                self.manual_scroll.setStyleSheet("""
                    QScrollArea#ManualScroll {
                        border: 1.5px solid #e5d8b8;
                        border-radius: 8px;
                        background-color: #ffffff;
                    }
                    QScrollBar:horizontal {
                        height: 4px;
                        background: #f1f5f9;
                        border-radius: 2px;
                    }
                    QScrollBar::handle:horizontal {
                        background: #d97706;
                        border-radius: 2px;
                    }
                """)
            if hasattr(self, "right_panel_ref") and self.right_panel_ref:
                self.right_panel_ref.setStyleSheet("""
                    QFrame#RightPanel {
                        background-color: #04261c;
                        border: 2px solid #c59f42;
                        border-radius: 12px;
                    }
                """)

        # D. Efek Teks Hijau & Glow Putih (Saat Transparansi di atas 80%)
        # Berlaku untuk: 1. Bel Sekolah Otomatis, 2. Jadwal Hari Ini, 3. Bel Manual
        if transparency >= 80:
            glow_title = QGraphicsDropShadowEffect(self)
            glow_title.setColor(QColor(255, 255, 255, 255))
            glow_title.setBlurRadius(16)
            glow_title.setOffset(0, 0)
            if hasattr(self, "app_title") and self.app_title:
                self.app_title.setGraphicsEffect(glow_title)
                self.app_title.setStyleSheet("font-size: 15px; font-weight: 900; color: #064e3b; border: none; letter-spacing: 0.6px; background: transparent;")

            glow_right = QGraphicsDropShadowEffect(self)
            glow_right.setColor(QColor(255, 255, 255, 255))
            glow_right.setBlurRadius(16)
            glow_right.setOffset(0, 0)
            if hasattr(self, "right_title") and self.right_title:
                self.right_title.setGraphicsEffect(glow_right)
                self.right_title.setStyleSheet("font-size: 13.5px; font-weight: 900; color: #064e3b; letter-spacing: 0.5px; border: none; padding-bottom: 2px; background: transparent;")

            glow_manual = QGraphicsDropShadowEffect(self)
            glow_manual.setColor(QColor(255, 255, 255, 255))
            glow_manual.setBlurRadius(16)
            glow_manual.setOffset(0, 0)
            if hasattr(self, "lbl_manual") and self.lbl_manual:
                self.lbl_manual.setText("Bel Manual")
                self.lbl_manual.setGraphicsEffect(glow_manual)
                self.lbl_manual.setStyleSheet("font-size: 11.5px; font-weight: 900; color: #064e3b; border: none; padding-top: 2px; background: transparent;")
        else:
            if hasattr(self, "app_title") and self.app_title:
                self.app_title.setGraphicsEffect(None)
                self.app_title.setStyleSheet("font-size: 15px; font-weight: 900; color: #0b3b2d; border: none; letter-spacing: 0.6px; background: transparent;")

            if hasattr(self, "right_title") and self.right_title:
                self.right_title.setGraphicsEffect(None)
                self.right_title.setStyleSheet("font-size: 13px; font-weight: 800; color: #ffffff; letter-spacing: 0.5px; border: none; padding-bottom: 2px; background: transparent;")

            if hasattr(self, "lbl_manual") and self.lbl_manual:
                self.lbl_manual.setText("Bel Manual")
                self.lbl_manual.setGraphicsEffect(None)
                self.lbl_manual.setStyleSheet("font-size: 11px; font-weight: 800; color: #78350f; border: none; padding-top: 2px; background: transparent;")

    def _init_services(self):
        # Timer untuk jam digital & tanggal
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._on_clock_tick)
        self.clock_timer.start(500)
        self._on_clock_tick()

        # Hubungkan sinyal scheduler
        self.scheduler.status_changed.connect(self._update_scheduler_buttons)
        self.scheduler.next_bell_updated.connect(self._on_next_bell_updated)
        self.scheduler.bell_triggered.connect(self._on_bell_triggered)
        self.scheduler.schedule_missed.connect(self._on_schedule_missed)

        # Hubungkan sinyal AudioPlayer untuk sinkronisasi status audio aktif di UI
        self.active_audio_title: str = ""
        self.audio_player.status_changed.connect(self._on_audio_status_changed)
        self.audio_player.playback_started.connect(self._on_audio_started)
        self.audio_player.playback_completed.connect(self._on_audio_cleared)
        self.audio_player.playback_failed.connect(self._on_audio_failed)
        self.audio_player.playback_interrupted.connect(self._on_audio_interrupted)
        self._sync_audio_ui_state()

        # Status scheduler dari pengaturan
        auto_enabled = self.settings_repo.get("auto_scheduler_enabled", "1") == "1"
        if auto_enabled:
            self.scheduler.start()
        self._update_scheduler_buttons(self.scheduler.is_active)

    def refresh_all_data(self):
        """Memuat ulang data profil, tombol manual, dan daftar jadwal hari ini."""
        # 1. Update Profil Aktif
        active_prof = self.profile_repo.get_active()
        prof_name = active_prof.name if active_prof else "Reguler"
        self.profile_badge.setText(f"Profil: {prof_name}")

        # 2. Update Tombol Manual Kode Lagu
        self._populate_manual_buttons()

        # 3. Update Jadwal Hari Ini
        self._load_today_schedules()

        # 4. Update Background Tampilan
        self.apply_backgrounds()

    def _populate_manual_buttons(self):
        """Membuat tombol manual dinamis dari daftar berkas audio yang memiliki kode."""
        # Bersihkan layout lama
        while self.manual_layout.count() > 0:
            item = self.manual_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        audios = self.audio_repo.get_all()
        if not audios:
            lbl_empty = QLabel("(Belum ada file audio)")
            lbl_empty.setStyleSheet("color: #94a3b8; font-size: 11px; font-style: italic;")
            self.manual_layout.addWidget(lbl_empty, 0, 0)
            return

        # Pisahkan menjadi grup BEL dan grup TES / Lainnya
        bel_audios = [a for a in audios if (a.code or "").upper().startswith("BEL")]
        other_audios = [a for a in audios if not (a.code or "").upper().startswith("BEL")]

        # Susun rapi 3 Baris:
        # Baris 0: BEL A s/d BEL G (7 item pertama)
        # Baris 1: BEL H s/d BEL N (7 item berikutnya)
        # Baris 2: Tes 1 s/d Tes 5 (dan berkas audio tambahan lainnya)
        for idx, a in enumerate(bel_audios):
            if idx < 7:
                row = 0
                col = idx
            elif idx < 14:
                row = 1
                col = idx - 7
            else:
                row = 2
                col = idx - 14
            btn = self._create_manual_button(a, is_test=False)
            self.manual_layout.addWidget(btn, row, col)

        start_col_row2 = max(0, len(bel_audios) - 14)
        for idx, a in enumerate(other_audios):
            col = (start_col_row2 + idx) % 7
            row = 2 + (start_col_row2 + idx) // 7
            is_test = (a.code or "").upper().startswith("TES")
            btn = self._create_manual_button(a, is_test=is_test)
            self.manual_layout.addWidget(btn, row, col)

    def _create_manual_button(self, audio: AudioFile, is_test: bool = False) -> QPushButton:
        """Membuat satu tombol manual berkode dengan styling sesuai kategori."""
        code_text = audio.code if audio.code else f"BEL {audio.id}"
        btn = QPushButton(code_text)
        btn.setFixedHeight(29)
        btn.setMinimumWidth(50)
        btn.setToolTip(f"{code_text}: {audio.name}")

        if is_test:
            btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #e0f2fe);
                    color: #0369a1;
                    border: 1.5px solid #0284c7;
                    border-radius: 5px;
                    font-size: 11px;
                    font-weight: 800;
                    padding: 0 8px;
                }
                QPushButton:hover {
                    background: #bae6fd;
                    border-color: #0369a1;
                    color: #0c4a6e;
                }
                QPushButton:pressed {
                    background: #0284c7;
                    color: #ffffff;
                }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #fef3c7);
                    color: #78350f;
                    border: 1.5px solid #d97706;
                    border-radius: 5px;
                    font-size: 11px;
                    font-weight: 800;
                    padding: 0 8px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fef3c7, stop:1 #fde68a);
                    border-color: #b45309;
                    color: #451a03;
                }
                QPushButton:pressed {
                    background: #f59e0b;
                    color: #ffffff;
                }
            """)

        btn.clicked.connect(lambda _=False, item=audio: self._play_manual_bell(item))
        return btn

    def _play_manual_bell(self, audio: AudioFile):
        """Membunyikan bel manual berdasarkan tombol kode yang ditekan via pengelola terpusat."""
        code_label = audio.code if audio.code else f"BEL {audio.id}"
        event_name = f"Manual [{code_label}] {audio.name}"
        self.scheduler.trigger_manual_bell(
            audio_id=audio.id,
            event_name=event_name,
            audio_path=audio.stored_path,
        )

    def _on_stop_audio(self):
        self.audio_player.stop(reason="Dihentikan melalui tombol Stop")
        self._sync_audio_ui_state()

    def _on_audio_started(self, title: str):
        self.active_audio_title = title
        self._sync_audio_ui_state()

    def _on_audio_status_changed(self, status: str):
        self._sync_audio_ui_state()

    def _on_audio_cleared(self):
        self.active_audio_title = ""
        self._sync_audio_ui_state()

    def _on_audio_failed(self, _error: str):
        self.active_audio_title = ""
        self._sync_audio_ui_state()

    def _on_audio_interrupted(self, _reason: str):
        self.active_audio_title = ""
        self._sync_audio_ui_state()

    def _sync_audio_ui_state(self):
        """Menjaga konsistensi status audio aktif di antarmuka (tidak pernah menampilkan audio lama yang sudah berhenti)."""
        from src.services.audio_player import AudioStatus
        if self.audio_player.status in (AudioStatus.PLAYING, AudioStatus.LOADING) and self.audio_player.current_title:
            self.active_audio_title = self.audio_player.current_title
            self.btn_stop_audio.setToolTip(f"Hentikan audio aktif: {self.active_audio_title}")
        else:
            self.active_audio_title = ""
            self.btn_stop_audio.setToolTip("Tidak ada audio aktif")

    def _load_today_schedules(self):
        """Memuat jadwal untuk hari saat ini di sisi kanan."""
        day_str = self.clock.day_name()
        self.right_title.setText(f"Jadwal Hari {day_str}")

        active_prof = self.profile_repo.get_active()
        if not active_prof:
            self.schedule_table.setRowCount(0)
            self.next_bell_label.setText("Tidak ada profil aktif")
            return

        self.current_day_schedules = self.schedule_repo.get_by_profile_and_day(active_prof.id, day_str)
        self.schedule_table.setRowCount(0)

        for row, s in enumerate(self.current_day_schedules):
            self.schedule_table.insertRow(row)
            self.schedule_table.setRowHeight(row, 26)

            # Jam (HH:mm)
            time_item = QTableWidgetItem(s.bell_time[:5])
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            font = time_item.font()
            font.setBold(True)
            time_item.setFont(font)
            self.schedule_table.setItem(row, 0, time_item)

            # Kode Lagu & Nama Kegiatan
            code_label = s.audio_code if s.audio_code else "-"
            display_text = f"[{code_label}] {s.event_name}"
            event_item = QTableWidgetItem(display_text)
            self.schedule_table.setItem(row, 1, event_item)

    def _on_clock_tick(self):
        now = self.clock.now()
        self.clock_label.setText(now.strftime("%H:%M:%S"))

        day_text = self.clock.day_name()
        month_names = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        month_text = month_names[now.month - 1]
        self.date_label.setText(f"{day_text}, {now.day:02d} {month_text} {now.year}")

    def _on_next_bell_updated(self, event_name, bell_time, seconds_remaining):
        if event_name and bell_time and seconds_remaining is not None:
            if seconds_remaining >= 3600:
                h = seconds_remaining // 3600
                m = (seconds_remaining % 3600) // 60
                s = seconds_remaining % 60
                time_fmt = f"{h:02d}:{m:02d}:{s:02d}"
            else:
                m = seconds_remaining // 60
                s = seconds_remaining % 60
                time_fmt = f"{m:02d}:{s:02d}"

            code = "-"
            for sc in self.current_day_schedules:
                if sc.bell_time[:5] == bell_time[:5]:
                    code = sc.audio_code if sc.audio_code else "-"
                    break
            self.next_bell_label.setText(f"Berikutnya: {bell_time[:5]} [{code}] ({time_fmt})")
            self._highlight_schedule_row(bell_time[:5])
        else:
            self.next_bell_label.setText("Semua jadwal hari ini selesai")
            self._clear_schedule_highlights()

    def _highlight_schedule_row(self, target_time: str):
        for r in range(self.schedule_table.rowCount()):
            t_item = self.schedule_table.item(r, 0)
            e_item = self.schedule_table.item(r, 1)
            if t_item and t_item.text() == target_time:
                t_item.setBackground(QColor("#f59e0b"))
                t_item.setForeground(QColor("#022c22"))
                if e_item:
                    e_item.setBackground(QColor("#f59e0b"))
                    e_item.setForeground(QColor("#022c22"))
            else:
                if t_item:
                    t_item.setBackground(QColor("#064e3b"))
                    t_item.setForeground(QColor("#fef3c7"))
                if e_item:
                    e_item.setBackground(QColor("#064e3b"))
                    e_item.setForeground(QColor("#fef3c7"))

    def _clear_schedule_highlights(self):
        for r in range(self.schedule_table.rowCount()):
            t_item = self.schedule_table.item(r, 0)
            e_item = self.schedule_table.item(r, 1)
            if t_item:
                t_item.setBackground(QColor("#064e3b"))
                t_item.setForeground(QColor("#fef3c7"))
            if e_item:
                e_item.setBackground(QColor("#064e3b"))
                e_item.setForeground(QColor("#fef3c7"))

    def _on_bell_triggered(self, event_name: str, schedule_id: Optional[int], mode: str):
        self._load_today_schedules()

    def _on_schedule_missed(self, event_name: str, bell_time: str, message: str):
        """Menampilkan notifikasi ringkas dan informatif saat jadwal otomatis terlewat tanpa menginterupsi audio manual."""
        try:
            formatted_time = bell_time[:5] if bell_time else ""
            display_time = f"pukul {formatted_time}" if formatted_time else ""
            notif_text = f"Jadwal '{event_name}' {display_time} dilewati (audio manual sedang berlangsung)."

            logger.info("Notifikasi jadwal otomatis terlewat: %s", notif_text)

            # 1. Tampilkan banner notifikasi di antarmuka
            if hasattr(self, "missed_notif_banner") and self.missed_notif_banner:
                self.missed_notif_banner.setText(f"⚠️ {notif_text}")
                self.missed_notif_banner.setVisible(True)
                # Sembunyikan otomatis setelah 7 detik
                QTimer.singleShot(7000, lambda: self.missed_notif_banner.setVisible(False))

            # 2. Notifikasi Sistem Tray (Windows Toast / Tray Balloon) saat window di background atau minimize
            if hasattr(self, "tray") and self.tray:
                try:
                    self.tray.showMessage(
                        "Jadwal Bel Dilewati",
                        f"Jadwal bel {display_time} dilewati karena audio manual masih berlangsung.",
                        QSystemTrayIcon.MessageIcon.Warning,
                        6000,
                    )
                except Exception as te:
                    logger.debug("Tray showMessage exception: %s", te)

            # 3. Perbarui daftar jadwal hari ini
            self._load_today_schedules()
        except Exception as e:
            logger.warning("Gagal menangani notifikasi jadwal terlewat: %s", e)

    def _on_start_scheduler(self):
        self.scheduler.start()
        self.settings_repo.set("auto_scheduler_enabled", "1")
        self._update_scheduler_buttons(True)

    def _on_stop_scheduler(self):
        self.scheduler.stop()
        self.settings_repo.set("auto_scheduler_enabled", "0")
        self._update_scheduler_buttons(False)

    def _update_scheduler_buttons(self, is_running: bool):
        if is_running:
            self.btn_on.setEnabled(False)
            self.btn_off.setEnabled(True)
            self.status_label.setText("AKTIF")
            self.status_label.setStyleSheet("""
                background: #dcfce7;
                color: #15803d;
                font-weight: 800;
                font-size: 12px;
                border: 1.5px solid #86efac;
                border-radius: 8px;
                padding: 0 14px;
            """)
        else:
            self.btn_on.setEnabled(True)
            self.btn_off.setEnabled(False)
            self.status_label.setText("NONAKTIF")
            self.status_label.setStyleSheet("""
                background: #fee2e2;
                color: #dc2626;
                font-weight: 800;
                font-size: 12px;
                border: 1.5px solid #fca5a5;
                border-radius: 8px;
                padding: 0 14px;
            """)

    def _on_click_setting(self):
        """Membuka alur Setting: inisialisasi password jika baru, atau LoginDialog jika sudah ada."""
        if not self.auth.is_password_set():
            # Inisialisasi Akun Pengelola Pertama Kali
            init_dlg = SetupPasswordDialog(self.auth, is_initial=True, parent=self)
            if init_dlg.exec() != QDialog.DialogCode.Accepted:
                return

        # Buka Login Dialog
        login_dlg = LoginDialog(self.auth, parent=self)
        if login_dlg.exec() == QDialog.DialogCode.Accepted:
            self._open_admin_window()

    def _open_admin_window(self):
        """Membuka Jendela Pengelola yang telah terautentikasi."""
        if self.admin_window is None:
            self.admin_window = AdminWindow(self.db, self.audio_player, self.auth)
            self.admin_window.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
            self.admin_window.data_updated.connect(self.refresh_all_data)
            self.admin_window.data_updated.connect(self.apply_backgrounds)
            self.admin_window.logged_out.connect(self._on_admin_logged_out)

        self.admin_window._is_logging_out = False
        self.admin_window.show()
        self.admin_window.raise_()
        self.admin_window.activateWindow()

    def _on_admin_logged_out(self):
        """Kembali ke halaman utama setelah pengelola melakukan Logout (aplikasi tetap berjalan)."""
        if self.admin_window is not None:
            admin_win = self.admin_window
            self.admin_window = None
            admin_win.hide()
            admin_win.deleteLater()

        self.apply_backgrounds()
        self.refresh_all_data()
        self.show()
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self._center_on_screen()

    def _center_on_screen(self):
        """Memposisikan jendela utama tepat di tengah layar monitor dan menguncinya."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            geo = self.frameGeometry()
            geo.moveCenter(screen_geo.center())
            self.move(geo.topLeft())

    def contextMenuEvent(self, event):
        """Menampilkan menu klik kanan pada layar utama dengan opsi Keluar."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                color: #0f172a;
                border: 1.5px solid #cbd5e1;
                border-radius: 8px;
                padding: 4px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
                font-weight: 600;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #059669;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #e2e8f0;
                margin: 4px 8px;
            }
        """)

        action_hide = QAction("Sembunyikan ke Tray", self)
        action_hide.triggered.connect(self.hide)
        menu.addAction(action_hide)

        menu.addSeparator()

        action_quit = QAction("Keluar", self)
        action_quit.triggered.connect(self._quit_application)
        menu.addAction(action_quit)

        menu.exec(event.globalPos())

    def _setup_tray(self):
        """Menyiapkan ikon sistem tray Windows di area notifikasi (hidden tray)."""
        icon_path = get_assets_dir() / "app_icon.png"
        if not icon_path.exists():
            icon_path = get_assets_dir() / "bell_badge.png"

        tray_icon = QIcon(str(icon_path))
        self.tray = QSystemTrayIcon(tray_icon, self)
        self.tray.setToolTip(f"{APP_DISPLAY_NAME} v{APP_VERSION}")

        tray_menu = QMenu()
        tray_menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                color: #0f172a;
                border: 1.5px solid #cbd5e1;
                border-radius: 8px;
                padding: 4px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
                font-weight: 600;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #059669;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #e2e8f0;
                margin: 4px 8px;
            }
        """)

        action_show = QAction("Tampilkan Bel Sekolah", self)
        action_show.triggered.connect(self._show_and_activate)
        tray_menu.addAction(action_show)

        tray_menu.addSeparator()

        action_quit = QAction("Keluar", self)
        action_quit.triggered.connect(self._quit_application)
        tray_menu.addAction(action_quit)

        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            if self.isVisible():
                self.hide()
            else:
                self._show_and_activate()

    def _show_and_activate(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self._center_on_screen()

    def cleanup(self):
        """Menghentikan seluruh thread scheduler, timer, audio, dan menutup child window secara aman."""
        if getattr(self, "_cleaned_up", False):
            return
        self._cleaned_up = True
        logger.info("Membersihkan resource Bel Otomatis Sekolah...")
        if hasattr(self, "tray") and self.tray:
            try:
                self.tray.hide()
            except Exception:
                pass
        if hasattr(self, "scheduler") and self.scheduler:
            try:
                self.scheduler.stop()
            except Exception:
                pass
        if hasattr(self, "clock_timer") and self.clock_timer:
            try:
                self.clock_timer.stop()
            except Exception:
                pass
        if hasattr(self, "audio_player") and self.audio_player:
            try:
                self.audio_player.cleanup()
            except Exception:
                pass
        if self.admin_window:
            try:
                self.admin_window.close()
            except Exception:
                pass

    def nativeEvent(self, event_type, message):
        """Menangani sinyal native Windows (WM_QUERYENDSESSION, WM_ENDSESSION) untuk shutdown bersih."""
        if sys.platform == "win32":
            try:
                from ctypes import wintypes
                msg = wintypes.MSG.from_address(int(message))
                WM_QUERYENDSESSION = 0x0011
                WM_ENDSESSION = 0x0016

                if msg.message == WM_QUERYENDSESSION:
                    logger.info("Menerima sinyal WM_QUERYENDSESSION (Windows mematikan sistem). Menyetujui shutdown...")
                    return True, 1

                elif msg.message == WM_ENDSESSION:
                    if msg.wParam != 0:
                        logger.info("Menerima sinyal WM_ENDSESSION. Mematikan aplikasi dan membebaskan resource...")
                        self.cleanup()
                        QApplication.quit()
                        return True, 0
            except Exception as e:
                logger.debug("Error saat memproses nativeEvent Windows: %s", e)

        return super().nativeEvent(event_type, message)

    def _quit_application(self):
        self.cleanup()
        self.close()
        QApplication.quit()

    def showEvent(self, event):
        super().showEvent(event)
        self._center_on_screen()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._center_on_screen()

    def closeEvent(self, event):
        logger.info("Menutup Panel Utama: menghentikan scheduler dan mematikan timer clock...")
        self.cleanup()
        event.accept()
        QApplication.quit()

    # =========================================================================
    # Kompatibilitas Navigasi dan Pengujian Lintas Komponen
    # =========================================================================
    def _on_profile_updated(self):
        self.refresh_all_data()
        if hasattr(self, "_dashboard_page"):
            self._dashboard_page.refresh_data()
        if self.admin_window:
            self.admin_window.profile_page.refresh_profiles()
            self.admin_window.schedule_page.refresh_data()

    def update_active_profile_label(self):
        active_prof = self.profile_repo.get_active()
        prof_name = active_prof.name if active_prof else "Reguler"
        self.profile_badge.setText(f"Profil: {prof_name}")

    @property
    def header_title(self):
        if not hasattr(self, "_fake_header"):
            self._fake_header = QLabel("Dashboard")
        return self._fake_header

    @property
    def nav_buttons(self):
        if not hasattr(self, "_fake_nav_buttons"):
            self._fake_nav_buttons = [QPushButton() for _ in range(6)]
            for b in self._fake_nav_buttons:
                b.setCheckable(True)
            self._fake_nav_buttons[0].setChecked(True)
        return self._fake_nav_buttons

    @property
    def dashboard_page(self):
        if not hasattr(self, "_dashboard_page") or self._dashboard_page is None:
            from src.ui.dashboard import DashboardPage
            self._dashboard_page = DashboardPage(self.db, scheduler=self.scheduler, audio_player=self.audio_player)
            self._dashboard_page.show()
        return self._dashboard_page

    @property
    def schedule_page(self):
        if self.admin_window is None:
            self._open_admin_window()
        return self.admin_window.schedule_page

    @property
    def profile_page(self):
        if self.admin_window is None:
            self._open_admin_window()
        return self.admin_window.profile_page

    @property
    def audio_page(self):
        if self.admin_window is None:
            self._open_admin_window()
        return self.admin_window.audio_page

    @property
    def history_page(self):
        if self.admin_window is None:
            self._open_admin_window()
        return self.admin_window.history_page

    @property
    def settings_page(self):
        if self.admin_window is None:
            self._open_admin_window()
        return self.admin_window.settings_page

    @property
    def stacked_widget(self):
        if self.admin_window is None:
            self._open_admin_window()
        # Hubungkan currentChanged jika belum terhubung
        if not hasattr(self, "_stacked_synced"):
            self._stacked_synced = True
            def _sync_idx(idx):
                names = ["Jadwal Bel", "Pustaka Lagu", "Profil Jam Pelajaran", "Audio Bel", "Riwayat Bel", "Pengaturan"]
                if 0 <= idx < len(names):
                    self.header_title.setText(names[idx])
                if 0 <= idx < len(self.nav_buttons):
                    for b in self.nav_buttons: b.setChecked(False)
                    self.nav_buttons[idx].setChecked(True)
            self.admin_window.stacked_widget.currentChanged.connect(_sync_idx)
        return self.admin_window.stacked_widget

    def _on_navigate(self, page_index: int, page_name: str = ""):
        if page_name:
            self.header_title.setText(page_name)
        if 0 <= page_index < len(self.nav_buttons):
            for b in self.nav_buttons:
                b.setChecked(False)
            self.nav_buttons[page_index].setChecked(True)
        if self.admin_window is not None:
            self.admin_window._on_nav_clicked(page_index)

    def _on_quick_navigate(self, page_index: int, page_name: str = ""):
        self._on_navigate(page_index, page_name)

    # -------------------------------------------------------------------------
    # Penanganan Jendela Frameless: Drag Pemindahan & Context Menu
    # -------------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, "_drag_pos") and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 4px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #f1f5f9;
                color: #065f46;
                font-weight: 600;
            }
            QMenu::separator {
                height: 1px;
                background-color: #e2e8f0;
                margin: 4px 8px;
            }
        """)
        act_setting = menu.addAction("Buka Pengaturan")
        act_min = menu.addAction("Minimize")
        menu.addSeparator()
        act_close = menu.addAction("Tutup Aplikasi")

        action = menu.exec(event.globalPos())
        if action == act_setting:
            self._on_click_setting()
        elif action == act_min:
            self.showMinimized()
        elif action == act_close:
            self._quit_application()
