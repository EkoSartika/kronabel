"""
Jendela Area Pengelola Bel Otomatis Sekolah (Admin Area)
Hanya dapat diakses setelah login. Berisi Jadwal, Pustaka Lagu, Profil Jadwal, Riwayat, Pengaturan, Backup/Restore, dan Logout.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QButtonGroup,
    QMessageBox,
    QFrame,
)

from src.core.config import get_assets_dir
from src.core.win7_compat import is_dwm_composition_enabled
from src.database.db import DatabaseManager
from src.services.audio_player import AudioPlayer
from src.services.auth_service import AuthService
from src.ui.batch_schedule_page import BatchSchedulePage
from src.ui.audio_code_page import AudioCodePage
from src.ui.profile_page import ProfilePage
from src.ui.history_page import HistoryPage
from src.ui.background_page import BackgroundPage
from src.ui.settings_page import SettingsPage
from src.ui.auth_dialogs import SetupPasswordDialog
from src.ui.dialog_helper import patch_qmessagebox

logger = logging.getLogger(__name__)


class AdminWindow(QMainWindow):
    """Jendela Area Pengelola yang terlindungi autentikasi."""

    data_updated = Signal()
    logged_out = Signal()

    def __init__(self, db: DatabaseManager, audio_player: AudioPlayer, auth_service: AuthService, parent=None):
        super().__init__(parent)
        patch_qmessagebox()
        self.db = db
        self.audio_player = audio_player
        self.auth = auth_service

        self.setWindowTitle("Area Pengelola — Bel Otomatis Sekolah")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, is_dwm_composition_enabled())
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.resize(1024, 680)
        self.setMinimumSize(920, 580)
        self._drag_pos = None
        self._has_centered = False

        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #04261c;
            }
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
        central.setObjectName("AdminCentral")
        central.setStyleSheet("""
            QWidget#AdminCentral {
                background-color: #04261c;
                border: 2px solid #c59f42;
                border-radius: 16px;
            }
        """)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header Area Pengelola (Nuansa Keraton Sumedang Larang)
        header = QFrame()
        header.setFixedHeight(64)
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #064e3b, stop:1 #022c22);
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
                border-bottom: 2.5px solid #d97706;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 24, 0)
        header_layout.setSpacing(12)

        title = QLabel("Pengelola Bel Sekolah Otomatis")
        title.setStyleSheet("color: #fde047; font-size: 16px; font-weight: 900; letter-spacing: 0.5px; border: none; background: transparent;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Tombol Ganti Password (Aksen Cokelat Tembaga Keemasan - Tanpa Ikon)
        change_pw_btn = QPushButton("Ganti Password")
        change_pw_btn.setFixedHeight(34)
        change_pw_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #a16207, stop:1 #78350f);
                color: #ffffff;
                border: 1.5px solid #d97706;
                border-radius: 6px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 800;
            }
            QPushButton:hover { background: #b45309; }
        """)
        change_pw_btn.clicked.connect(self._on_change_password)
        header_layout.addWidget(change_pw_btn)

        # Tombol Logout (Merah Marun - Tanpa Ikon)
        logout_btn = QPushButton("Logout")
        logout_btn.setFixedHeight(34)
        logout_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #dc2626, stop:1 #991b1b);
                color: #ffffff;
                border: 1.5px solid #7f1d1d;
                border-radius: 6px;
                padding: 0 18px;
                font-size: 12px;
                font-weight: 800;
            }
            QPushButton:hover { background: #b91c1c; }
        """)
        logout_btn.clicked.connect(self._on_logout)
        header_layout.addWidget(logout_btn)

        main_layout.addWidget(header)

        # Konten Bawah: Sidebar Navigasi & Stacked Widget
        body = QWidget()
        body.setStyleSheet("background-color: transparent;")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(10, 10, 10, 10)
        body_layout.setSpacing(10)

        # Sidebar Navigasi (Hijau Tua Keraton dengan Ilustrasi Pendopo Sumedang)
        sidebar = QFrame()
        sidebar.setFixedWidth(210)
        pendopo_path = (get_assets_dir() / "admin_sidebar_pendopo.png").as_posix()
        sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: #032017;
                background-image: url("{pendopo_path}");
                background-repeat: no-repeat;
                background-position: bottom left;
                border: 1.5px solid #064e3b;
                border-radius: 12px;
            }}
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 16, 10, 16)
        sidebar_layout.setSpacing(8)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        nav_items = [
            ("Jadwal Pelajaran", 0),
            ("Lagu Bel", 1),
            ("Profil Jadwal", 2),
            ("Riwayat Bel", 3),
            ("Latar Belakang", 4),
            ("Pengaturan && Backup", 5),
        ]

        self.nav_buttons = []
        for text, idx in nav_items:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setFixedHeight(40)
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding-left: 14px;
                    border: none;
                    border-radius: 8px;
                    color: #fef3c7;
                    font-size: 13px;
                    font-weight: 600;
                    background-color: transparent;
                }
                QPushButton:hover {
                    background-color: #064e3b;
                    color: #fde047;
                }
                QPushButton:checked {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #fde68a, stop:1 #f59e0b);
                    color: #04261c;
                    font-weight: 800;
                    border: none;
                }
            """)
            btn.clicked.connect(lambda _=False, i=idx: self._on_nav_clicked(i))
            self.nav_group.addButton(btn, idx)
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_layout.addStretch()

        body_layout.addWidget(sidebar)

        # Kartu Pembungkus Konten Utama (Putih Gading dengan Border Halus)
        content_card = QFrame()
        content_card.setObjectName("ContentCard")
        content_card.setStyleSheet("""
            QFrame#ContentCard {
                background-color: #ffffff;
                border: 1.5px solid #e2d6b5;
                border-radius: 14px;
            }
        """)
        card_layout = QVBoxLayout(content_card)
        card_layout.setContentsMargins(4, 4, 4, 4)

        # Stacked Pages
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setObjectName("AdminStackedWidget")
        self.stacked_widget.setStyleSheet("QStackedWidget#AdminStackedWidget { background-color: #ffffff; border-radius: 12px; }")

        # 0. Batch Schedule Page
        self.schedule_page = BatchSchedulePage(self.db)
        self.schedule_page.schedules_changed.connect(self._on_sub_data_changed)
        self.stacked_widget.addWidget(self.schedule_page)

        # 1. Audio Code Page
        self.audio_page = AudioCodePage(self.db, self.audio_player)
        self.audio_page.audio_list_changed.connect(self._on_audio_changed)
        self.stacked_widget.addWidget(self.audio_page)

        # 2. Profile Page
        self.profile_page = ProfilePage(self.db)
        self.profile_page.profile_changed.connect(self._on_sub_data_changed)
        self.stacked_widget.addWidget(self.profile_page)

        # 3. History Page
        self.history_page = HistoryPage(self.db)
        self.stacked_widget.addWidget(self.history_page)

        # 4. Background Page (Kustomisasi Latar Belakang)
        self.background_page = BackgroundPage(self.db)
        self.background_page.background_changed.connect(self._on_sub_data_changed)
        self.stacked_widget.addWidget(self.background_page)

        # 5. Settings Page (termasuk Backup & Restore)
        self.settings_page = SettingsPage(self.db, self.audio_player)
        self.settings_page.settings_changed.connect(self._on_sub_data_changed)
        self.settings_page.data_restored.connect(self._on_sub_data_changed)
        self.stacked_widget.addWidget(self.settings_page)

        card_layout.addWidget(self.stacked_widget)
        body_layout.addWidget(content_card)
        main_layout.addWidget(body)

        # Default buka tab 0
        self.nav_buttons[0].setChecked(True)
        self.stacked_widget.setCurrentIndex(0)

    def _on_nav_clicked(self, index: int):
        if 0 <= index < len(self.nav_buttons):
            self.nav_buttons[index].setChecked(True)
        self.stacked_widget.setCurrentIndex(index)
        # Refresh halaman terkait
        widget = self.stacked_widget.widget(index)
        if hasattr(widget, "refresh_data"):
            widget.refresh_data()
        elif hasattr(widget, "refresh_table"):
            widget.refresh_table()

    def _on_sub_data_changed(self):
        self.schedule_page.refresh_data()
        self.profile_page.refresh_data()
        self.data_updated.emit()

    def _on_audio_changed(self):
        self.schedule_page.refresh_data()
        self.data_updated.emit()

    def _on_change_password(self):
        dialog = SetupPasswordDialog(self.auth, is_initial=False, parent=self)
        dialog.exec()

    def _on_logout(self):
        """Keluar dari Area Pengelola dan kembali ke halaman utama (tanpa menutup aplikasi)."""
        ans = QMessageBox.question(
            self,
            "Konfirmasi Logout",
            "Apakah Anda ingin keluar dari Area Pengelola dan mengunci pengaturan?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            self._is_logging_out = True
            self.hide()
            self.data_updated.emit()
            self.logged_out.emit()

    def closeEvent(self, event):
        """Menangani penutupan jendela Area Pengelola (kembali ke halaman utama, bukan mematikan aplikasi)."""
        if not getattr(self, "_is_logging_out", False):
            self.data_updated.emit()
            self.logged_out.emit()
        self._is_logging_out = False
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and getattr(self, "_drag_pos", None) is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            geo = self.frameGeometry()
            geo.moveCenter(screen_geo.center())
            self.move(geo.topLeft())

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_has_centered", False):
            self._center_on_screen()
            self._has_centered = True
