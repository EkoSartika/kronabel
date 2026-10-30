"""
Halaman Jadwal Bel Dalam Tabel Per Hari (Batch Editing)
Memungkinkan penambahan dan pengeditan langsung jadwal Senin-Sabtu dengan pemetaan Kode Lagu.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QLineEdit,
    QCheckBox,
    QHeaderView,
    QMessageBox,
    QFrame,
    QAbstractItemView,
)

from src.core.config import DAYS_OF_WEEK
from src.database.db import DatabaseManager
from src.database.repositories import ProfileRepository, ScheduleRepository, AudioRepository
from src.models.models import Schedule, validate_time_format

logger = logging.getLogger(__name__)


class BatchCopyDayDialog(QDialog):
    """Dialog rapi dan terukur untuk menyalin jadwal dari hari lain."""

    def __init__(self, target_day: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.target_day = target_day
        self.setWindowTitle("Salin Jadwal Hari Lain")
        self.setFixedSize(380, 190)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                color: #0f172a;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #1e293b;
                font-size: 13px;
                border: none;
                background: transparent;
            }
            QComboBox {
                color: #0f172a;
                background-color: #ffffff;
                border: 1.5px solid #cbd5e1;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 13px;
                font-weight: 600;
            }
            QComboBox QAbstractItemView {
                color: #0f172a;
                background-color: #ffffff;
                selection-background-color: #059669;
                selection-color: #ffffff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        desc = QLabel(f"Salin seluruh jadwal dari hari lain ke hari <b>{target_day}</b>:")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        form_box = QHBoxLayout()
        form_box.setSpacing(10)
        lbl = QLabel("Hari Sumber:")
        lbl.setStyleSheet("font-weight: 700; color: #064e3b;")
        form_box.addWidget(lbl)

        self.day_combo = QComboBox()
        self.day_combo.setFixedHeight(34)
        for d in DAYS_OF_WEEK:
            if d != target_day:
                self.day_combo.addItem(d)
        form_box.addWidget(self.day_combo, 1)
        layout.addLayout(form_box)

        layout.addStretch()

        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_box.addStretch()

        cancel_btn = QPushButton("Batal")
        cancel_btn.setFixedHeight(32)
        cancel_btn.setMinimumWidth(85)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #475569;
                border: 1.5px solid #cbd5e1;
                border-radius: 6px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        copy_btn = QPushButton("Mulai Salin")
        copy_btn.setFixedHeight(32)
        copy_btn.setMinimumWidth(105)
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #047857; }
        """)
        copy_btn.clicked.connect(self.accept)
        btn_box.addWidget(copy_btn)

        layout.addLayout(btn_box)

    def get_source_day(self) -> str:
        return self.day_combo.currentText()


class BatchSchedulePage(QWidget):
    """Pengelolaan jadwal per hari dalam bentuk tabel langsung (inline-editable)."""

    schedules_changed = Signal()

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.profile_repo = ProfileRepository(db)
        self.schedule_repo = ScheduleRepository(db)
        self.audio_repo = AudioRepository(db)

        self.current_profile_id: Optional[int] = None
        self.current_day: str = "Senin"
        self.available_audios = []
        self.has_unsaved_changes: bool = False

        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # 1. Baris Atas: Judul Halaman & Tombol Aksi Utama
        header_bar = QHBoxLayout()
        header_bar.setSpacing(10)

        lbl_page_title = QLabel("Jadwal Pelajaran")
        lbl_page_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #064e3b; border: none; background: transparent;")
        header_bar.addWidget(lbl_page_title)

        header_bar.addStretch()

        # Tombol Salin Jadwal
        self.copy_btn = QPushButton("Salin Hari Lain")
        self.copy_btn.setFixedHeight(32)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #334155;
                border: 1.5px solid #cbd5e1;
                border-radius: 6px;
                padding: 0 14px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover { background-color: #f1f5f9; border-color: #94a3b8; }
        """)
        self.copy_btn.clicked.connect(self._on_copy_day)
        header_bar.addWidget(self.copy_btn)

        # Tombol Tambah Baris
        self.add_row_btn = QPushButton("Tambah Baris")
        self.add_row_btn.setFixedHeight(32)
        self.add_row_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 0 14px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover { background-color: #0369a1; }
        """)
        self.add_row_btn.clicked.connect(self._on_add_row)
        header_bar.addWidget(self.add_row_btn)

        # Tombol Simpan Perubahan
        self.save_btn = QPushButton("Simpan Perubahan")
        self.save_btn.setFixedHeight(32)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 0 16px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover { background-color: #047857; }
        """)
        self.save_btn.clicked.connect(self._on_save_changes)
        header_bar.addWidget(self.save_btn)

        main_layout.addLayout(header_bar)

        # 2. Baris Filter: Panel Ramping untuk Profil, Hari, dan Status
        filter_card = QFrame()
        filter_card.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border: 1.5px solid #e2e8f0;
                border-radius: 8px;
            }
        """)
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(12, 6, 12, 6)
        filter_layout.setSpacing(10)

        # Profil Selector
        lbl_prof = QLabel("Profil:")
        lbl_prof.setStyleSheet("font-weight: 700; color: #064e3b; font-size: 12px; border: none; background: transparent;")
        self.profile_combo = QComboBox()
        self.profile_combo.setFixedHeight(30)
        self.profile_combo.setMinimumWidth(150)
        self.profile_combo.setStyleSheet("""
            QComboBox {
                color: #0f172a;
                background-color: #ffffff;
                border: 1.5px solid #cbd5e1;
                border-radius: 6px;
                padding: 2px 8px;
                font-weight: 600;
                font-size: 12px;
            }
            QComboBox QAbstractItemView {
                color: #0f172a;
                background-color: #ffffff;
                selection-background-color: #059669;
                selection-color: #ffffff;
            }
        """)
        self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        filter_layout.addWidget(lbl_prof)
        filter_layout.addWidget(self.profile_combo)

        filter_layout.addSpacing(8)

        # Hari Selector (Senin - Sabtu)
        lbl_day = QLabel("Hari:")
        lbl_day.setStyleSheet("font-weight: 700; color: #064e3b; font-size: 12px; border: none; background: transparent;")
        self.day_combo = QComboBox()
        self.day_combo.setFixedHeight(30)
        self.day_combo.setMinimumWidth(110)
        self.day_combo.setStyleSheet("""
            QComboBox {
                color: #0f172a;
                background-color: #ffffff;
                border: 1.5px solid #cbd5e1;
                border-radius: 6px;
                padding: 2px 8px;
                font-weight: 600;
                font-size: 12px;
            }
            QComboBox QAbstractItemView {
                color: #0f172a;
                background-color: #ffffff;
                selection-background-color: #059669;
                selection-color: #ffffff;
            }
        """)
        for d in DAYS_OF_WEEK:
            self.day_combo.addItem(d)
        self.day_combo.currentIndexChanged.connect(self._on_day_changed)
        filter_layout.addWidget(lbl_day)
        filter_layout.addWidget(self.day_combo)

        filter_layout.addSpacing(12)

        # Indikator status perubahan
        self.status_banner = QLabel("Menampilkan jadwal.")
        self.status_banner.setStyleSheet("color: #475569; font-size: 12px; font-weight: 500; border: none; background: transparent;")
        filter_layout.addWidget(self.status_banner, 1)

        main_layout.addWidget(filter_card)

        # Tabel Jadwal
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Jam (HH:mm)",
            "Kode Lagu",
            "Nama Kegiatan",
            "Aktif",
            "Aksi",
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1.5px solid #e2e8f0;
                border-radius: 8px;
                background-color: #ffffff;
                gridline-color: #f1f5f9;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #ecfdf5;
                color: #064e3b;
                font-weight: 800;
                padding: 9px 8px;
                border: none;
                border-bottom: 2px solid #a7f3d0;
                border-right: 1px solid #f0fdf4;
            }
        """)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(0, 120)
        self.table.setColumnWidth(1, 170)
        self.table.setColumnWidth(3, 80)
        self.table.setColumnWidth(4, 95)

        main_layout.addWidget(self.table)

    def refresh_data(self):
        """Memuat daftar profil dan daftar audio terbaru."""
        profiles = self.profile_repo.get_all()
        self.available_audios = self.audio_repo.get_all()

        current_idx = self.profile_combo.currentIndex()
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        selected_idx = 0
        for idx, p in enumerate(profiles):
            self.profile_combo.addItem(f"{p.name} {'(Aktif)' if p.is_active else ''}", p.id)
            if p.is_active:
                selected_idx = idx
        if current_idx >= 0 and current_idx < len(profiles):
            self.profile_combo.setCurrentIndex(current_idx)
        else:
            self.profile_combo.setCurrentIndex(selected_idx)
        self.profile_combo.blockSignals(False)

        self.current_profile_id = self.profile_combo.currentData()
        self.load_schedules_for_current_view()

    def load_schedules_for_current_view(self):
        """Memuat jadwal untuk profil dan hari terpilih."""
        if not self.current_profile_id:
            return

        self.current_day = self.day_combo.currentText()
        schedules = self.schedule_repo.get_by_profile_and_day(self.current_profile_id, self.current_day)

        self.table.setRowCount(0)
        for sched in schedules:
            self._insert_table_row(sched)

        self.has_unsaved_changes = False
        self.status_banner.setText(f"Menampilkan {len(schedules)} jadwal untuk hari {self.current_day}.")
        self.status_banner.setStyleSheet("color: #64748b; font-size: 11px;")

    def _insert_table_row(self, sched: Optional[Schedule] = None):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setRowHeight(row, 40)

        # 1. Jam (HH:mm)
        time_str = sched.bell_time[:5] if sched and sched.bell_time else "07:00"
        time_edit = QLineEdit(time_str)
        time_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_edit.setMaxLength(5)
        time_edit.setPlaceholderText("HH:mm")
        time_edit.setStyleSheet("""
            QLineEdit {
                color: #0f172a;
                background-color: #ffffff;
                border: 1.5px solid #cbd5e1;
                border-radius: 4px;
                padding: 4px;
                font-weight: bold;
                font-size: 13px;
            }
            QLineEdit:focus { border-color: #2563eb; }
        """)
        time_edit.textChanged.connect(self._mark_unsaved)
        self.table.setCellWidget(row, 0, time_edit)

        # 2. Kode Lagu (ComboBox)
        audio_combo = QComboBox()
        audio_combo.setStyleSheet("""
            QComboBox {
                color: #0f172a;
                background-color: #ffffff;
                border: 1.5px solid #cbd5e1;
                border-radius: 4px;
                padding: 2px 6px;
                font-weight: 600;
                font-size: 12px;
            }
            QComboBox QAbstractItemView {
                color: #0f172a;
                background-color: #ffffff;
                selection-background-color: #2563eb;
                selection-color: #ffffff;
            }
        """)
        audio_combo.addItem("(Pilih Kode Lagu)", None)
        selected_audio_idx = 0
        for idx, a in enumerate(self.available_audios, start=1):
            code_label = a.code if a.code else f"ID:{a.id}"
            audio_combo.addItem(f"{code_label} — {a.name}", a.id)
            if sched and sched.audio_id == a.id:
                selected_audio_idx = idx

        audio_combo.setCurrentIndex(selected_audio_idx)
        audio_combo.currentIndexChanged.connect(self._mark_unsaved)
        self.table.setCellWidget(row, 1, audio_combo)

        # 3. Nama Kegiatan
        event_name = sched.event_name if sched else ""
        event_edit = QLineEdit(event_name)
        event_edit.setPlaceholderText("Nama kegiatan (misal: Masuk Sekolah, Istirahat)...")
        event_edit.setStyleSheet("""
            QLineEdit {
                color: #0f172a;
                background-color: #ffffff;
                border: 1.5px solid #cbd5e1;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: 500;
                font-size: 13px;
            }
            QLineEdit:focus { border-color: #2563eb; }
        """)
        event_edit.textChanged.connect(self._mark_unsaved)
        self.table.setCellWidget(row, 2, event_edit)

        # 4. Status Aktif (CheckBox)
        cb_container = QWidget()
        cb_layout = QHBoxLayout(cb_container)
        cb_layout.setContentsMargins(0, 0, 0, 0)
        cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        is_enabled = sched.is_enabled if sched else True
        chk = QCheckBox()
        chk.setChecked(is_enabled)
        chk.toggled.connect(self._mark_unsaved)
        cb_layout.addWidget(chk)
        self.table.setCellWidget(row, 3, cb_container)

        # 5. Tombol Hapus Baris
        del_btn = QPushButton("Hapus")
        del_btn.setFixedHeight(28)
        del_btn.setStyleSheet("""
            QPushButton {
                background-color: #fee2e2;
                color: #dc2626;
                border: 1px solid #fecaca;
                border-radius: 6px;
                font-weight: 600;
                font-size: 11px;
                padding: 0 10px;
            }
            QPushButton:hover { background-color: #fecaca; }
        """)
        del_btn.clicked.connect(lambda _=False, r=row: self._on_delete_row(r))
        self.table.setCellWidget(row, 4, del_btn)

        # Simpan objek Schedule asli atau ID di UserRole row pertama jika ada
        item = QTableWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, sched.id if sched else None)
        self.table.setItem(row, 0, item)

    def _mark_unsaved(self):
        self.has_unsaved_changes = True
        self.status_banner.setText("[!] Terdapat perubahan yang belum disimpan. Klik 'Simpan Perubahan' untuk memperbarui.")
        self.status_banner.setStyleSheet("color: #b45309; font-size: 11px; font-weight: bold;")

    def _on_profile_changed(self):
        if self.has_unsaved_changes:
            ans = QMessageBox.question(
                self,
                "Perubahan Belum Disimpan",
                "Ada perubahan yang belum disimpan. Apakah Anda ingin menyimpannya sekarang?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            )
            if ans == QMessageBox.StandardButton.Yes:
                if not self._on_save_changes():
                    return
            elif ans == QMessageBox.StandardButton.Cancel:
                return

        self.current_profile_id = self.profile_combo.currentData()
        self.load_schedules_for_current_view()

    def _on_day_changed(self):
        if self.has_unsaved_changes:
            ans = QMessageBox.question(
                self,
                "Perubahan Belum Disimpan",
                "Ada perubahan yang belum disimpan. Apakah Anda ingin menyimpannya sekarang?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            )
            if ans == QMessageBox.StandardButton.Yes:
                if not self._on_save_changes():
                    return
            elif ans == QMessageBox.StandardButton.Cancel:
                return

        self.load_schedules_for_current_view()

    def _on_add_row(self):
        self._insert_table_row(None)
        self._mark_unsaved()
        self.table.scrollToBottom()

    def _on_delete_row(self, row: int):
        ans = QMessageBox.question(
            self,
            "Konfirmasi Hapus Baris",
            "Apakah Anda yakin ingin menghapus baris jadwal ini?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            self.table.removeRow(row)
            # Rebind tombol hapus untuk baris-baris berikutnya
            for r in range(self.table.rowCount()):
                btn = self.table.cellWidget(r, 4)
                if btn:
                    btn.clicked.disconnect()
                    btn.clicked.connect(lambda _=False, curr=r: self._on_delete_row(curr))
            self._mark_unsaved()

    def _on_save_changes(self) -> bool:
        """Menyimpan seluruh jadwal hari ini secara transaksional."""
        if not self.current_profile_id:
            return False

        validated_schedules = []
        seen_times = set()

        for row in range(self.table.rowCount()):
            time_widget: QLineEdit = self.table.cellWidget(row, 0)
            audio_combo: QComboBox = self.table.cellWidget(row, 1)
            event_widget: QLineEdit = self.table.cellWidget(row, 2)
            cb_container: QWidget = self.table.cellWidget(row, 3)

            raw_time = time_widget.text().strip() if time_widget else ""
            try:
                clean_time = validate_time_format(raw_time)
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Format Jam Salah",
                    f"Baris ke-{row + 1}: Format jam '{raw_time}' tidak valid. Gunakan format HH:mm (00:00 - 23:59).",
                )
                time_widget.setFocus()
                return False

            if clean_time in seen_times:
                QMessageBox.warning(
                    self,
                    "Duplikasi Waktu Bel",
                    f"Baris ke-{row + 1}: Waktu {clean_time} duplikat pada hari {self.current_day}.",
                )
                time_widget.setFocus()
                return False
            seen_times.add(clean_time)

            event_name = event_widget.text().strip() if event_widget else ""
            if not event_name:
                QMessageBox.warning(
                    self,
                    "Nama Kegiatan Kosong",
                    f"Baris ke-{row + 1}: Nama kegiatan bel tidak boleh kosong.",
                )
                event_widget.setFocus()
                return False

            audio_id = audio_combo.currentData() if audio_combo else None
            chk = cb_container.findChild(QCheckBox)
            is_enabled = chk.isChecked() if chk else True

            # ID lama jika ada
            item = self.table.item(row, 0)
            sched_id = item.data(Qt.ItemDataRole.UserRole) if item else None

            sched = Schedule(
                id=sched_id,
                profile_id=self.current_profile_id,
                day_of_week=self.current_day,
                bell_time=clean_time,
                event_name=event_name,
                audio_id=audio_id,
                is_enabled=is_enabled,
            )
            validated_schedules.append(sched)

        # Simpan perubahan secara sinkron
        try:
            # Ambil jadwal lama di hari ini
            existing = self.schedule_repo.get_by_profile_and_day(self.current_profile_id, self.current_day)
            existing_ids = {s.id for s in existing if s.id is not None}
            kept_ids = {s.id for s in validated_schedules if s.id is not None}

            # 1. Hapus jadwal yang tidak ada lagi di tabel
            deleted_ids = existing_ids - kept_ids
            for did in deleted_ids:
                self.schedule_repo.delete(did)

            # 2. Simpan atau perbarui baris yang ada
            for s in validated_schedules:
                if s.id is not None and s.id in existing_ids:
                    self.schedule_repo.update(s)
                else:
                    self.schedule_repo.create(s)

            self.has_unsaved_changes = False
            self.load_schedules_for_current_view()
            self.schedules_changed.emit()

            QMessageBox.information(
                self,
                "Tersimpan",
                f"Seluruh jadwal hari {self.current_day} berhasil disimpan.",
            )
            return True
        except Exception as e:
            logger.exception("Gagal menyimpan jadwal: %s", e)
            QMessageBox.critical(
                self,
                "Kesalahan Penyimpanan",
                f"Gagal menyimpan jadwal:\n\n{e}",
            )
            return False

    def _on_copy_day(self):
        """Menyalin jadwal dari hari lain ke hari saat ini."""
        dlg = BatchCopyDayDialog(self.current_day, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        source_day = dlg.get_source_day()
        if source_day:
            count = self.schedule_repo.copy_day_schedules(
                self.current_profile_id,
                source_day,
                self.current_day,
                overwrite=True,
            )
            self.load_schedules_for_current_view()
            self.schedules_changed.emit()
            QMessageBox.information(
                self,
                "Berhasil",
                f"Berhasil menyalin {count} jadwal dari hari {source_day} ke hari {self.current_day}.",
            )
