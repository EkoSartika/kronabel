"""
Halaman Riwayat Pembunyian Bel (History Page) Bel Otomatis Sekolah.
Menampilkan log eksekusi bel otomatis dan manual secara persisten dari SQLite,
dilengkapi fitur filter rentang tanggal, filter metode, filter status,
pencarian nama kegiatan, pengurutan waktu terbaru, dan paginasi hemat memori.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.database.db import DatabaseManager
from src.database.repositories import BellLogRepository

logger = logging.getLogger(__name__)

PAGE_SIZE = 25

STATUS_COLORS = {
    "completed": ("#dcfce7", "#15803d", "Berhasil"),       # Background, Text, Label
    "failed": ("#fee2e2", "#b91c1c", "Gagal"),
    "missed": ("#ffedd5", "#c2410c", "Terlewat"),
    "interrupted": ("#fef9c3", "#a16207", "Terpotong"),
    "playing": ("#e0f2fe", "#0369a1", "Memutar"),
    "requested": ("#f1f5f9", "#475569", "Diminta"),
}

METHOD_COLORS = {
    "OTOMATIS": ("#eff6ff", "#1d4ed8"),
    "MANUAL": ("#faf5ff", "#7e22ce"),
}


class HistoryPage(QWidget):
    """Komponen tampilan riwayat pembunyian bel sekolah."""

    def __init__(self, db: DatabaseManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db
        self.log_repo = BellLogRepository(db)

        self.current_page = 1
        self.total_records = 0
        self.total_pages = 1

        self._setup_ui()
        self.load_history()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # 1. Filter Card Bar
        filter_card = QFrame()
        filter_card.setObjectName("FilterCard")
        filter_card.setStyleSheet(
            """
            QFrame#FilterCard {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
            }
            QLabel {
                color: #334155;
                font-size: 13px;
                font-weight: 500;
                border: none;
                background-color: transparent;
                padding: 0px;
            }
            QComboBox, QDateEdit, QLineEdit {
                border: 1.5px solid #cbd5e1;
                border-radius: 6px;
                padding: 5px 10px;
                background-color: #ffffff;
                font-size: 12.5px;
                color: #0f172a;
            }
            QComboBox:focus, QDateEdit:focus, QLineEdit:focus {
                border-color: #0284c7;
                background-color: #ffffff;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #0f172a;
                selection-background-color: #0284c7;
                selection-color: #ffffff;
                border: 1.5px solid #cbd5e1;
                border-radius: 6px;
                padding: 4px;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                min-height: 26px;
                padding: 4px 8px;
                color: #0f172a;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #e0f2fe;
                color: #0369a1;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #0284c7;
                color: #ffffff;
            }
            QCheckBox {
                color: #0f172a;
                font-weight: 600;
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 17px;
                height: 17px;
                border: 1.5px solid #94a3b8;
                border-radius: 4px;
                background-color: #ffffff;
            }
            QCheckBox::indicator:checked {
                background-color: #0284c7;
                border-color: #0284c7;
            }
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                font-weight: 600;
                border-radius: 6px;
                padding: 6px 14px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
            QPushButton#BtnSecondary {
                background-color: #f1f5f9;
                color: #475569;
                border: 1px solid #cbd5e1;
            }
            QPushButton#BtnSecondary:hover {
                background-color: #e2e8f0;
                color: #1e293b;
            }
            QCalendarWidget {
                background-color: #ffffff;
                color: #0f172a;
            }
            QCalendarWidget QWidget {
                alternate-background-color: #f8fafc;
                color: #0f172a;
            }
            QCalendarWidget QAbstractItemView:enabled {
                color: #0f172a;
                background-color: #ffffff;
                selection-background-color: #0284c7;
                selection-color: #ffffff;
                font-size: 12px;
                font-weight: 600;
            }
            QCalendarWidget QAbstractItemView:disabled {
                color: #94a3b8;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #f1f5f9;
                color: #0f172a;
                border-bottom: 1.5px solid #cbd5e1;
                min-height: 32px;
            }
            QCalendarWidget QToolButton {
                color: #0f172a;
                background-color: transparent;
                font-size: 12px;
                font-weight: 700;
                border-radius: 4px;
                padding: 4px 8px;
                margin: 2px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #e2e8f0;
                color: #0284c7;
            }
            QCalendarWidget QMenu {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #cbd5e1;
            }
            QCalendarWidget QSpinBox {
                background-color: #ffffff;
                color: #0f172a;
                border: 1.5px solid #cbd5e1;
                border-radius: 4px;
                font-weight: bold;
                padding: 2px 4px;
            }
            QCalendarWidget QHeaderView::section {
                background-color: #f8fafc;
                color: #334155;
                font-size: 11px;
                font-weight: 700;
                padding: 4px;
                border: none;
                border-bottom: 1px solid #e2e8f0;
            }
            """
        )
        filter_layout = QVBoxLayout(filter_card)
        filter_layout.setContentsMargins(10, 10, 10, 10)
        filter_layout.setSpacing(10)

        # Baris 1: Filter Tanggal & Pencarian
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(10)

        self.chk_date_filter = QCheckBox("Filter Tanggal:")
        self.chk_date_filter.setChecked(True)
        self.chk_date_filter.toggled.connect(self._on_date_filter_toggled)
        row1_layout.addWidget(self.chk_date_filter)

        today = QDate.currentDate()
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(today.addDays(-30))
        self.date_start.setEnabled(True)
        self.date_start.setMinimumWidth(110)
        self.date_start.dateChanged.connect(self._apply_filters)
        cal_start = self.date_start.calendarWidget()
        if cal_start:
            cal_start.setGridVisible(True)
        row1_layout.addWidget(self.date_start)

        lbl_to = QLabel("s/d")
        row1_layout.addWidget(lbl_to)

        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(today)
        self.date_end.setEnabled(True)
        self.date_end.setMinimumWidth(110)
        self.date_end.dateChanged.connect(self._apply_filters)
        cal_end = self.date_end.calendarWidget()
        if cal_end:
            cal_end.setGridVisible(True)
        row1_layout.addWidget(self.date_end)

        row1_layout.addSpacing(12)

        lbl_search = QLabel("Cari Kegiatan:")
        row1_layout.addWidget(lbl_search)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Ketik nama kegiatan...")
        self.txt_search.setMinimumWidth(150)
        self.txt_search.returnPressed.connect(self._apply_filters)
        row1_layout.addWidget(self.txt_search, 1)

        filter_layout.addLayout(row1_layout)

        # Baris 2: Filter Metode, Status, dan Tombol Aksi
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(8)

        lbl_mode = QLabel("Metode:")
        row2_layout.addWidget(lbl_mode)

        self.cmb_mode = QComboBox()
        self.cmb_mode.setMinimumWidth(130)
        self.cmb_mode.addItem("Semua Metode", "")
        self.cmb_mode.addItem("Otomatis", "OTOMATIS")
        self.cmb_mode.addItem("Manual", "MANUAL")
        self.cmb_mode.currentIndexChanged.connect(self._apply_filters)
        row2_layout.addWidget(self.cmb_mode)

        lbl_status = QLabel("Status:")
        row2_layout.addWidget(lbl_status)

        self.cmb_status = QComboBox()
        self.cmb_status.setMinimumWidth(170)
        self.cmb_status.addItem("Semua Status", "")
        self.cmb_status.addItem("Berhasil (completed)", "completed")
        self.cmb_status.addItem("Gagal (failed)", "failed")
        self.cmb_status.addItem("Terlewat (missed)", "missed")
        self.cmb_status.addItem("Terpotong (interrupted)", "interrupted")
        self.cmb_status.addItem("Sedang Memutar (playing)", "playing")
        self.cmb_status.currentIndexChanged.connect(self._apply_filters)
        row2_layout.addWidget(self.cmb_status)

        row2_layout.addStretch()

        self.btn_apply = QPushButton("Terapkan")
        self.btn_apply.setMinimumHeight(30)
        self.btn_apply.setStyleSheet("padding: 4px 12px; font-weight: 600; font-size: 12px;")
        self.btn_apply.clicked.connect(self._apply_filters)
        row2_layout.addWidget(self.btn_apply)

        self.btn_reset = QPushButton("Reset Filter")
        self.btn_reset.setObjectName("BtnSecondary")
        self.btn_reset.setMinimumHeight(30)
        self.btn_reset.setStyleSheet("padding: 4px 10px; font-size: 12px;")
        self.btn_reset.clicked.connect(self._reset_filters)
        row2_layout.addWidget(self.btn_reset)

        self.btn_refresh = QPushButton("Muat Ulang")
        self.btn_refresh.setObjectName("BtnSecondary")
        self.btn_refresh.setMinimumHeight(30)
        self.btn_refresh.setStyleSheet("padding: 4px 10px; font-size: 12px;")
        self.btn_refresh.clicked.connect(self.load_history)
        row2_layout.addWidget(self.btn_refresh)

        filter_layout.addLayout(row2_layout)
        main_layout.addWidget(filter_card)

        # 2. Tabel Riwayat
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Tanggal & Waktu",
            "Nama Kegiatan",
            "Jadwal",
            "Eksekusi",
            "Metode",
            "Status",
            "Keterangan",
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet(
            """
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                gridline-color: #f1f5f9;
                font-size: 13px;
                color: #1e293b;
            }
            QTableWidget::item {
                padding: 8px 10px;
            }
            QTableWidget::item:selected {
                background-color: #e0f2fe;
                color: #0369a1;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                color: #475569;
                font-weight: 600;
                font-size: 12px;
                padding: 10px;
                border: none;
                border-bottom: 2px solid #e2e8f0;
            }
            """
        )

        # Ukuran Kolom
        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        header.setMinimumSectionSize(65)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.verticalHeader().setDefaultSectionSize(42)

        main_layout.addWidget(self.table, 1)

        # 3. Baris Paginasi & Status
        pagination_layout = QHBoxLayout()
        pagination_layout.setContentsMargins(4, 4, 4, 4)

        self.lbl_info = QLabel("Memuat data...")
        self.lbl_info.setStyleSheet("color: #64748b; font-size: 13px; font-weight: 500;")
        pagination_layout.addWidget(self.lbl_info)

        pagination_layout.addStretch()

        self.btn_first = QPushButton("Pertama")
        self.btn_first.setObjectName("BtnSecondary")
        self.btn_first.setStyleSheet("padding: 4px 10px; font-size: 12px;")
        self.btn_first.clicked.connect(self._go_first_page)
        pagination_layout.addWidget(self.btn_first)

        self.btn_prev = QPushButton("Sebelumnya")
        self.btn_prev.setObjectName("BtnSecondary")
        self.btn_prev.setStyleSheet("padding: 4px 10px; font-size: 12px;")
        self.btn_prev.clicked.connect(self._go_prev_page)
        pagination_layout.addWidget(self.btn_prev)

        self.lbl_page = QLabel("Halaman 1 / 1")
        self.lbl_page.setStyleSheet("font-size: 13px; font-weight: 600; color: #1e293b; padding: 0 8px;")
        pagination_layout.addWidget(self.lbl_page)

        self.btn_next = QPushButton("Berikutnya")
        self.btn_next.setObjectName("BtnSecondary")
        self.btn_next.setStyleSheet("padding: 4px 10px; font-size: 12px;")
        self.btn_next.clicked.connect(self._go_next_page)
        pagination_layout.addWidget(self.btn_next)

        self.btn_last = QPushButton("Terakhir")
        self.btn_last.setObjectName("BtnSecondary")
        self.btn_last.setStyleSheet("padding: 4px 10px; font-size: 12px;")
        self.btn_last.clicked.connect(self._go_last_page)
        pagination_layout.addWidget(self.btn_last)

        main_layout.addLayout(pagination_layout)

    def _on_date_filter_toggled(self, checked: bool) -> None:
        self.date_start.setEnabled(checked)
        self.date_end.setEnabled(checked)
        self._apply_filters()

    def _apply_filters(self) -> None:
        self.current_page = 1
        self.load_history()

    def _reset_filters(self) -> None:
        self.chk_date_filter.setChecked(False)
        self.cmb_mode.setCurrentIndex(0)
        self.cmb_status.setCurrentIndex(0)
        self.txt_search.clear()
        self.current_page = 1
        self.load_history()

    def _go_first_page(self) -> None:
        if self.current_page > 1:
            self.current_page = 1
            self.load_history()

    def _go_prev_page(self) -> None:
        if self.current_page > 1:
            self.current_page -= 1
            self.load_history()

    def _go_next_page(self) -> None:
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_history()

    def _go_last_page(self) -> None:
        if self.current_page < self.total_pages:
            self.current_page = self.total_pages
            self.load_history()

    def load_history(self) -> None:
        """Mengambil data riwayat dari database berdasarkan filter dan halaman aktif."""
        # Kumpulkan filter
        start_date = None
        end_date = None
        if self.chk_date_filter.isChecked():
            start_date = self.date_start.date().toString("yyyy-MM-dd")
            end_date = self.date_end.date().toString("yyyy-MM-dd")

        mode_filter = self.cmb_mode.currentData() or None
        status_filter = self.cmb_status.currentData() or None
        search = self.txt_search.text().strip() or None

        # 1. Hitung total data yang cocok
        try:
            self.total_records = self.log_repo.count_logs(
                start_date=start_date,
                end_date=end_date,
                mode_filter=mode_filter,
                status_filter=status_filter,
                search=search,
            )
        except Exception as e:
            logger.error("Gagal menghitung total data log: %s", e)
            self.total_records = 0

        self.total_pages = max(1, (self.total_records + PAGE_SIZE - 1) // PAGE_SIZE)
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages

        offset = (self.current_page - 1) * PAGE_SIZE

        # 2. Ambil data dengan paginasi
        try:
            logs = self.log_repo.get_logs(
                limit=PAGE_SIZE,
                offset=offset,
                start_date=start_date,
                end_date=end_date,
                mode_filter=mode_filter,
                status_filter=status_filter,
                search=search,
            )
        except Exception as e:
            logger.error("Gagal memuat daftar log: %s", e)
            logs = []

        # 3. Render ke tabel
        self.table.setRowCount(len(logs))
        for row_idx, log in enumerate(logs):
            # Kolom 0: Tanggal & Waktu Eksekusi
            exec_time_str = log.executed_at[:19].replace("T", " ") if log.executed_at else "-"
            item_datetime = QTableWidgetItem(exec_time_str)
            item_datetime.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 0, item_datetime)

            # Kolom 1: Nama Kegiatan
            item_event = QTableWidgetItem(log.event_name)
            font_bold = QFont()
            font_bold.setBold(True)
            item_event.setFont(font_bold)
            self.table.setItem(row_idx, 1, item_event)

            # Kolom 2: Waktu yang dijadwalkan
            sched_time_str = "-"
            if log.scheduled_at:
                # Format HH:MM atau YYYY-MM-DD HH:MM
                if "T" in log.scheduled_at:
                    sched_time_str = log.scheduled_at.split("T")[1][:5]
                elif " " in log.scheduled_at:
                    sched_time_str = log.scheduled_at.split(" ")[1][:5]
                else:
                    sched_time_str = log.scheduled_at[:5]
            item_sched = QTableWidgetItem(sched_time_str)
            item_sched.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 2, item_sched)

            # Kolom 3: Waktu Eksekusi (Jam Saja)
            exec_clock = "-"
            if log.executed_at:
                if "T" in log.executed_at:
                    exec_clock = log.executed_at.split("T")[1][:8]
                elif " " in log.executed_at:
                    exec_clock = log.executed_at.split(" ")[1][:8]
                else:
                    exec_clock = log.executed_at[:8]
            item_clock = QTableWidgetItem(exec_clock)
            item_clock.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 3, item_clock)

            # Kolom 4: Metode
            mode = log.execution_mode.upper()
            item_mode = QTableWidgetItem(f" {mode} ")
            item_mode.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            bg_mode, fg_mode = METHOD_COLORS.get(mode, ("#f1f5f9", "#334155"))
            item_mode.setBackground(QColor(bg_mode))
            item_mode.setForeground(QColor(fg_mode))
            self.table.setItem(row_idx, 4, item_mode)

            # Kolom 5: Status
            status_key = log.status.lower()
            bg_col, fg_col, label_text = STATUS_COLORS.get(
                status_key, ("#f1f5f9", "#475569", status_key.title())
            )
            item_status = QTableWidgetItem(f" {label_text} ")
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_status.setBackground(QColor(bg_col))
            item_status.setForeground(QColor(fg_col))
            self.table.setItem(row_idx, 5, item_status)

            # Kolom 6: Keterangan
            item_msg = QTableWidgetItem(log.message or "-")
            self.table.setItem(row_idx, 6, item_msg)

        # 4. Update Kontrol Paginasi
        start_item = offset + 1 if self.total_records > 0 else 0
        end_item = min(offset + len(logs), self.total_records)
        self.lbl_info.setText(
            f"Menampilkan {start_item}–{end_item} dari total {self.total_records} riwayat"
        )
        self.lbl_page.setText(f"Halaman {self.current_page} / {self.total_pages}")

        self.btn_first.setEnabled(self.current_page > 1)
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < self.total_pages)
        self.btn_last.setEnabled(self.current_page < self.total_pages)
