"""
Halaman Dashboard Utama Bel Otomatis Sekolah.
Menampilkan jam digital real-time, tanggal aktual, status scheduler otomatis,
kontrol Mulai/Hentikan Otomatis, Bel Manual, kartu bel berikutnya, dan hitung mundur akurat.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.config import DAYS_OF_WEEK
from src.database.db import DatabaseManager
from src.database.repositories import AudioRepository, ProfileRepository, ScheduleRepository
from src.models.models import AudioFile
from src.services.audio_player import AudioPlayer, AudioStatus
from src.services.scheduler import SchedulerService


class ManualBellDialog(QDialog):
    """Dialog Pemilihan Suara Bel Manual."""

    def __init__(self, audio_repo: AudioRepository, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.audio_repo = audio_repo
        self.setWindowTitle("Bunyikan Bel Manual")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        desc = QLabel("Pilih file suara bel yang ingin dibunyikan seketika:")
        desc.setStyleSheet("color: #475569; font-size: 13px;")
        layout.addWidget(desc)

        form_layout = QFormLayout()
        self.audio_combo = QComboBox()
        audios = self.audio_repo.get_all()
        for a in audios:
            self.audio_combo.addItem(f"{a.name} ({a.original_filename})", a.id)

        form_layout.addRow("Suara Bel:", self.audio_combo)
        layout.addLayout(form_layout)

        notice = QLabel("Catatan: Bel manual tidak akan mengganggu jadwal otomatis atau mengubah profil aktif.")
        notice.setStyleSheet("color: #64748b; font-size: 11px; font-style: italic;")
        layout.addWidget(notice)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Ok).setText("🔔 Bunyikan Sekarang")
        btn_box.button(QDialogButtonBox.Cancel).setText("Batal")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_selected_audio_id(self) -> Optional[int]:
        return self.audio_combo.currentData()

    def get_selected_audio_name(self) -> str:
        return self.audio_combo.currentText().split(" (")[0]


class DashboardPage(QWidget):
    """Halaman Dashboard Utama Bel Otomatis Sekolah."""

    navigate_requested = Signal(int, str)

    def __init__(
        self,
        db: DatabaseManager,
        scheduler: Optional[SchedulerService] = None,
        audio_player: Optional[AudioPlayer] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.db = db
        self.scheduler = scheduler
        self.audio_player = audio_player

        self.profile_repo = ProfileRepository(db)
        self.schedule_repo = ScheduleRepository(db)
        self.audio_repo = AudioRepository(db)

        self._setup_ui()
        self._init_clock_timer()
        self.refresh_data()

        if self.scheduler:
            self.scheduler.status_changed.connect(self._on_scheduler_status_changed)
            self.scheduler.next_bell_updated.connect(self._on_next_bell_updated)
            self.scheduler.schedule_missed.connect(self._on_schedule_missed)

        if self.audio_player:
            self.audio_player.status_changed.connect(self._on_audio_status_changed)

    def _setup_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # ScrollArea responsif untuk memastikan dashboard tampil sempurna pada semua ukuran jendela dan skala DPI
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background-color: transparent;")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(24, 18, 24, 18)
        main_layout.setSpacing(14)

        # 1. Baris Atas: Jam Digital & Status Operasional
        top_layout = QHBoxLayout()
        top_layout.setSpacing(14)

        clock_card = self._create_clock_card()
        top_layout.addWidget(clock_card, 3)

        status_card = self._create_status_card()
        top_layout.addWidget(status_card, 2)

        main_layout.addLayout(top_layout)

        # 2. Panel Bel Berikutnya & Kontrol Mesin
        next_bell_card = self._create_next_bell_panel()
        main_layout.addWidget(next_bell_card)

        # 3. Baris Tombol Aksi Cepat
        actions_card = self._create_quick_actions_panel()
        main_layout.addWidget(actions_card)

        # 4. Ringkasan Jadwal Hari Ini
        today_card = self._create_today_schedules_panel()
        main_layout.addWidget(today_card, 1)

        self.scroll_area.setWidget(content_widget)
        outer_layout.addWidget(self.scroll_area)

    def _create_clock_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("ClockCard")
        card.setStyleSheet(
            """
            QFrame#ClockCard {
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
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        header_label = QLabel("WAKTU SISTEM LOKAL (WINDOWS)")
        header_label.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 700; letter-spacing: 1px;")
        layout.addWidget(header_label)

        self.clock_label = QLabel("00:00:00")
        self.clock_label.setStyleSheet("color: #0f172a; font-size: 36px; font-weight: 800; font-family: monospace;")
        layout.addWidget(self.clock_label)

        self.date_label = QLabel("Memuat tanggal...")
        self.date_label.setStyleSheet("color: #475569; font-size: 13px; font-weight: 500;")
        layout.addWidget(self.date_label)

        return card

    def _create_status_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("StatusCard")
        card.setStyleSheet(
            """
            QFrame#StatusCard {
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
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        header_label = QLabel("STATUS SISTEM OPERASIONAL")
        header_label.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 700; letter-spacing: 1px;")
        layout.addWidget(header_label)

        # Status Scheduler
        sched_layout = QHBoxLayout()
        sched_title = QLabel("Mesin Otomatis:")
        sched_title.setStyleSheet("color: #334155; font-size: 13px; font-weight: 500;")
        self.scheduler_badge = QLabel("Belum Diaktifkan")
        self.scheduler_badge.setStyleSheet(
            "background-color: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; "
            "border-radius: 6px; padding: 2px 10px; font-size: 12px; font-weight: 600;"
        )
        sched_layout.addWidget(sched_title)
        sched_layout.addStretch()
        sched_layout.addWidget(self.scheduler_badge)
        layout.addLayout(sched_layout)

        # Profil Aktif
        prof_layout = QHBoxLayout()
        prof_title = QLabel("Profil Aktif:")
        prof_title.setStyleSheet("color: #334155; font-size: 13px; font-weight: 500;")
        self.profile_name_label = QLabel("-")
        self.profile_name_label.setStyleSheet("color: #0284c7; font-size: 13px; font-weight: 700;")
        prof_layout.addWidget(prof_title)
        prof_layout.addStretch()
        prof_layout.addWidget(self.profile_name_label)
        layout.addLayout(prof_layout)

        # Status Pemutar Audio
        audio_layout = QHBoxLayout()
        audio_title = QLabel("Status Audio:")
        audio_title.setStyleSheet("color: #334155; font-size: 13px; font-weight: 500;")
        self.audio_status_badge = QLabel("Siap")
        self.audio_status_badge.setStyleSheet(
            "background-color: #e0f2fe; color: #0369a1; border-radius: 6px; "
            "padding: 2px 8px; font-size: 11px; font-weight: 600;"
        )
        audio_layout.addWidget(audio_title)
        audio_layout.addStretch()
        audio_layout.addWidget(self.audio_status_badge)
        layout.addLayout(audio_layout)

        return card

    def _create_next_bell_panel(self) -> QFrame:
        card = QFrame()
        card.setObjectName("NextBellCard")
        card.setStyleSheet(
            """
            QFrame#NextBellCard {
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
        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(16)

        # Info Bel Berikutnya (Kiri)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        next_tag = QLabel("BEL BERIKUTNYA")
        next_tag.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 700; letter-spacing: 1px;")
        self.next_event_label = QLabel("Tidak ada jadwal aktif")
        self.next_event_label.setStyleSheet("color: #0f172a; font-size: 16px; font-weight: 700;")
        self.next_time_label = QLabel("Waktu: -")
        self.next_time_label.setStyleSheet("color: #475569; font-size: 13px;")

        info_layout.addWidget(next_tag)
        info_layout.addWidget(self.next_event_label)
        info_layout.addWidget(self.next_time_label)
        layout.addLayout(info_layout, 2)

        # Hitung Mundur (Tengah)
        countdown_layout = QVBoxLayout()
        countdown_layout.setSpacing(4)
        cd_title = QLabel("HITUNG MUNDUR")
        cd_title.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 700; letter-spacing: 1px;")
        self.countdown_label = QLabel("--:--:--")
        self.countdown_label.setStyleSheet(
            "color: #0284c7; font-size: 26px; font-weight: 800; font-family: monospace;"
        )
        countdown_layout.addWidget(cd_title)
        countdown_layout.addWidget(self.countdown_label)
        layout.addLayout(countdown_layout, 2)

        # Kontrol Mesin & Bel Manual (Kanan)
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)

        toggle_sched_layout = QHBoxLayout()
        toggle_sched_layout.setSpacing(6)
        self.start_sched_btn = QPushButton("▶️ Mulai Otomatis")
        self.start_sched_btn.setMinimumHeight(30)
        self.start_sched_btn.setStyleSheet(
            "background-color: #10b981; color: #ffffff; border: none; "
            "border-radius: 6px; padding: 6px 12px; font-weight: 600; font-size: 12px;"
        )
        self.start_sched_btn.setCursor(Qt.PointingHandCursor)
        self.start_sched_btn.clicked.connect(self._on_start_scheduler)
        toggle_sched_layout.addWidget(self.start_sched_btn)

        self.stop_sched_btn = QPushButton("⏹️ Hentikan")
        self.stop_sched_btn.setMinimumHeight(30)
        self.stop_sched_btn.setStyleSheet(
            "background-color: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; "
            "border-radius: 6px; padding: 6px 12px; font-weight: 600; font-size: 12px;"
        )
        self.stop_sched_btn.setCursor(Qt.PointingHandCursor)
        self.stop_sched_btn.clicked.connect(self._on_stop_scheduler)
        toggle_sched_layout.addWidget(self.stop_sched_btn)
        btn_layout.addLayout(toggle_sched_layout)

        # Tombol Bunyikan Bel Manual
        self.manual_bell_btn = QPushButton("🔔 Bunyikan Bel Manual")
        self.manual_bell_btn.setMinimumHeight(34)
        self.manual_bell_btn.setStyleSheet(
            "background-color: #f59e0b; color: #ffffff; border: none; "
            "border-radius: 6px; padding: 7px 14px; font-weight: 700; font-size: 12px;"
        )
        self.manual_bell_btn.setCursor(Qt.PointingHandCursor)
        self.manual_bell_btn.clicked.connect(self._on_manual_bell_clicked)
        btn_layout.addWidget(self.manual_bell_btn)

        layout.addLayout(btn_layout, 2)
        return card

    def _create_quick_actions_panel(self) -> QFrame:
        card = QFrame()
        card.setObjectName("QuickActionsCard")
        card.setStyleSheet(
            """
            QFrame#QuickActionsCard {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
            QFrame#QuickActionsCard QPushButton {
                background-color: #f8fafc;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 8px 12px;
                min-height: 22px;
                font-size: 12px;
                font-weight: 600;
            }
            QFrame#QuickActionsCard QPushButton:hover {
                background-color: #0284c7;
                color: #ffffff;
                border-color: #0284c7;
            }
            """
        )
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        actions = [
            ("📅 Kelola Jadwal Bel", 1, "Jadwal Bel"),
            ("⚙️ Profil Jam Pelajaran", 2, "Profil Jam Pelajaran"),
            ("🎵 Pustaka Audio", 3, "Audio Bel"),
            ("📜 Riwayat Bel", 4, "Riwayat Bel"),
        ]

        for text, page_idx, page_name in actions:
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, idx=page_idx, name=page_name: self.navigate_requested.emit(idx, name))
            layout.addWidget(btn)

        return card

    def _create_today_schedules_panel(self) -> QFrame:
        card = QFrame()
        card.setObjectName("TodayScheduleCard")
        card.setStyleSheet(
            """
            QFrame#TodayScheduleCard {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
            """
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        title = QLabel("Jadwal Hari Ini")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #0f172a;")
        self.today_day_header = QLabel("")
        self.today_day_header.setStyleSheet("color: #64748b; font-size: 13px; font-weight: 500;")

        header_layout.addWidget(title)
        header_layout.addWidget(self.today_day_header)
        header_layout.addStretch()

        manage_btn = QPushButton("Buka Pengaturan Jadwal")
        manage_btn.setStyleSheet(
            "background-color: transparent; color: #0284c7; border: none; font-size: 12px; font-weight: 600;"
        )
        manage_btn.setCursor(Qt.PointingHandCursor)
        manage_btn.clicked.connect(lambda: self.navigate_requested.emit(1, "Jadwal Bel"))
        header_layout.addWidget(manage_btn)

        layout.addLayout(header_layout)

        self.today_table = QTableWidget()
        self.today_table.setColumnCount(4)
        self.today_table.setHorizontalHeaderLabels(["Waktu", "Kegiatan Bel", "File Audio", "Status"])
        self.today_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.today_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.today_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.today_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.today_table.horizontalHeader().setMinimumSectionSize(75)
        self.today_table.verticalHeader().setVisible(False)
        self.today_table.verticalHeader().setDefaultSectionSize(40)
        self.today_table.setMinimumHeight(150)
        self.today_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.today_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.today_table.setStyleSheet(
            """
            QTableWidget {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
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
                padding: 8px;
                font-weight: 600;
                border: none;
                border-bottom: 1px solid #e2e8f0;
            }
            """
        )

        layout.addWidget(self.today_table)
        return card

    def _init_clock_timer(self) -> None:
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_clock)
        self.timer.start(1000)
        self._update_clock()

    def _update_clock(self) -> None:
        now = datetime.now()
        self.clock_label.setText(now.strftime("%H:%M:%S"))

        hari_map = {
            "Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu",
            "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu",
        }
        bulan_map = {
            1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
            5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
            9: "September", 10: "Oktober", 11: "November", 12: "Desember",
        }

        hari_nama = hari_map.get(now.strftime("%A"), now.strftime("%A"))
        bulan_nama = bulan_map.get(now.month, "")
        self.date_label.setText(f"{hari_nama}, {now.day} {bulan_nama} {now.year}")

    def refresh_data(self) -> None:
        """Memuat ulang status profil aktif, jadwal hari ini, dan info bel berikutnya."""
        active_profile = self.profile_repo.get_active()
        if active_profile:
            self.profile_name_label.setText(active_profile.name)
        else:
            self.profile_name_label.setText("Tidak Ada")

        now = datetime.now()
        day_mapping = {
            "Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu",
            "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu",
        }
        current_day = day_mapping.get(now.strftime("%A"), "Senin")
        self.today_day_header.setText(f"({current_day})")

        if current_day not in DAYS_OF_WEEK or not active_profile:
            self.today_table.setRowCount(0)
            return

        schedules = self.schedule_repo.get_by_profile_and_day(active_profile.id, current_day)
        self.today_table.setRowCount(len(schedules))

        for row, s in enumerate(schedules):
            time_item = QTableWidgetItem(s.bell_time)
            time_item.setTextAlignment(Qt.AlignCenter)
            time_item.setForeground(QColor("#0f172a"))

            event_item = QTableWidgetItem(s.event_name)
            event_item.setForeground(QColor("#0f172a"))

            if s.audio_name:
                audio_text = s.audio_name
                audio_item = QTableWidgetItem(audio_text)
                audio_item.setForeground(QColor("#0f172a"))
            else:
                audio_text = "⚠️ Belum Dipilih (Edit Jadwal)"
                audio_item = QTableWidgetItem(audio_text)
                audio_item.setForeground(QColor("#b45309"))
                audio_item.setToolTip("File suara bel belum dikaitkan dengan jadwal ini.")

            status_text = "Aktif" if s.is_enabled else "Nonaktif"
            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignCenter)
            if s.is_enabled:
                status_item.setForeground(Qt.darkGreen)
            else:
                status_item.setForeground(Qt.gray)

            self.today_table.setItem(row, 0, time_item)
            self.today_table.setItem(row, 1, event_item)
            self.today_table.setItem(row, 2, audio_item)
            self.today_table.setItem(row, 3, status_item)

        # Trigger update bel berikutnya jika scheduler tersedia
        if self.scheduler:
            self.scheduler._update_next_bell()

    def _on_start_scheduler(self) -> None:
        if self.scheduler:
            self.scheduler.start()

    def _on_stop_scheduler(self) -> None:
        if self.scheduler:
            self.scheduler.stop()

    def _on_scheduler_status_changed(self, is_active: bool) -> None:
        if is_active:
            self.scheduler_badge.setText("🟢 Otomatis Aktif")
            self.scheduler_badge.setStyleSheet(
                "background-color: #dcfce7; color: #15803d; border: 1px solid #86efac; "
                "border-radius: 6px; padding: 2px 10px; font-size: 12px; font-weight: 700;"
            )
        else:
            self.scheduler_badge.setText("⚪ Dinonaktifkan")
            self.scheduler_badge.setStyleSheet(
                "background-color: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; "
                "border-radius: 6px; padding: 2px 10px; font-size: 12px; font-weight: 600;"
            )
            self.next_event_label.setText("Mesin otomatis dihentikan")
            self.next_time_label.setText("Aktifkan kembali untuk memulai penjadwalan.")
            self.countdown_label.setText("--:--:--")

    def _on_next_bell_updated(self, event_name: Optional[str], bell_time: Optional[str], seconds_left: Optional[int]) -> None:
        if not self.scheduler or not self.scheduler.is_active:
            self.next_event_label.setText("Mesin otomatis dihentikan")
            self.next_time_label.setText("Aktifkan kembali untuk memulai penjadwalan.")
            self.countdown_label.setText("--:--:--")
            return

        if event_name and bell_time and seconds_left is not None:
            self.next_event_label.setText(event_name)
            self.next_time_label.setText(f"Waktu Jadwal: {bell_time}")

            # Format countdown HH:MM:SS
            hours = seconds_left // 3600
            minutes = (seconds_left % 3600) // 60
            seconds = seconds_left % 60
            self.countdown_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        else:
            self.next_event_label.setText("Tidak ada jadwal berikutnya")
            self.next_time_label.setText("Seluruh jadwal hari ini telah terlewati.")
            self.countdown_label.setText("00:00:00")

    def _on_schedule_missed(self, event_name: str, bell_time: str, message: str) -> None:
        """Menangani sinyal jadwal otomatis terlewat pada dashboard."""
        try:
            formatted_time = bell_time[:5] if bell_time else ""
            self.next_event_label.setText(f"⚠️ Dilewati: {event_name}")
            self.next_time_label.setText(f"Jadwal {formatted_time} dilewati karena audio manual sedang aktif.")
            self.refresh_data()
        except Exception as e:
            logger.warning("Dashboard gagal menangani notifikasi jadwal terlewat: %s", e)

    def _on_audio_status_changed(self, status: str) -> None:
        status_map = {
            AudioStatus.IDLE.value: ("Siap", "#0369a1", "#e0f2fe"),
            AudioStatus.LOADING.value: ("Memuat...", "#854d0e", "#fef9c3"),
            AudioStatus.PLAYING.value: ("Sedang Berbunyi", "#15803d", "#dcfce7"),
            AudioStatus.COMPLETED.value: ("Selesai", "#0369a1", "#e0f2fe"),
            AudioStatus.FAILED.value: ("Gagal", "#b91c1c", "#fee2e2"),
            AudioStatus.INTERRUPTED.value: ("Dihentikan", "#b45309", "#fef3c7"),
        }
        text, fg, bg = status_map.get(status, (status.capitalize(), "#334155", "#f1f5f9"))
        self.audio_status_badge.setText(text)
        if status in (AudioStatus.PLAYING.value, AudioStatus.LOADING.value) and self.audio_player and self.audio_player.current_title:
            self.audio_status_badge.setToolTip(f"Audio aktif: {self.audio_player.current_title}")
        else:
            self.audio_status_badge.setToolTip("")
        self.audio_status_badge.setStyleSheet(
            f"color: {fg}; background-color: {bg}; border-radius: 6px; "
            "padding: 2px 8px; font-size: 11px; font-weight: 600;"
        )

    def _on_manual_bell_clicked(self) -> None:
        """Menangani penekanan tombol Bunyikan Bel Manual."""
        audios = self.audio_repo.get_all()
        if not audios:
            QMessageBox.warning(
                self,
                "Pustaka Audio Kosong",
                "Pustaka audio masih kosong. Silakan buka menu Audio Bel dan impor file MP3/WAV terlebih dahulu.",
            )
            return

        dialog = ManualBellDialog(self.audio_repo, parent=self)
        if dialog.exec() == QDialog.Accepted:
            audio_id = dialog.get_selected_audio_id()
            audio_name = dialog.get_selected_audio_name()

            if self.scheduler:
                success = self.scheduler.trigger_manual_bell(audio_id=audio_id, event_name=f"Bel Manual: {audio_name}")
                if not success:
                    QMessageBox.warning(
                        self,
                        "Gagal Membunyikan Bel",
                        "Tidak dapat membunyikan bel. Pastikan tidak sedang memutar bel lain dan file audio tersedia.",
                    )
