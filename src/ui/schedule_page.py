"""
Halaman Manajemen Jadwal Bel Otomatis Sekolah (Senin–Sabtu).
Menyediakan tabel jadwal, filter hari & profil, CRUD lengkap, validasi benturan,
penyalinan jadwal antarahari, dan konfirmasi penghapusan.
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.config import DAYS_OF_WEEK
from src.database.db import DatabaseManager
from src.database.repositories import AudioRepository, ProfileRepository, ScheduleRepository
from src.models.models import Schedule, normalize_time


class ScheduleDialog(QDialog):
    """Dialog Tambah/Edit Jadwal Bel."""

    def __init__(
        self,
        profile_id: int,
        schedule: Optional[Schedule] = None,
        audio_repo: Optional[AudioRepository] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.profile_id = profile_id
        self.schedule = schedule
        self.audio_repo = audio_repo

        self.setWindowTitle("Tambah Jadwal Bel" if schedule is None else "Edit Jadwal Bel")
        self.setMinimumWidth(440)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        # 1. Hari
        self.day_combo = QComboBox()
        self.day_combo.addItems(list(DAYS_OF_WEEK))
        if self.schedule:
            idx = self.day_combo.findText(self.schedule.day_of_week)
            if idx >= 0:
                self.day_combo.setCurrentIndex(idx)
        form_layout.addRow("Hari Operasional:", self.day_combo)

        # 2. Waktu Bel (Format HH:MM:SS)
        self.time_edit = QLineEdit()
        self.time_edit.setPlaceholderText("HH:MM:SS (contoh: 07:00:00 atau 07:00)")
        if self.schedule:
            self.time_edit.setText(self.schedule.bell_time)
        else:
            self.time_edit.setText("07:00:00")
        form_layout.addRow("Waktu Bel:", self.time_edit)

        # 3. Nama Kegiatan
        self.event_edit = QLineEdit()
        self.event_edit.setPlaceholderText("Contoh: Masuk Sekolah, Istirahat 1, Pulang")
        if self.schedule:
            self.event_edit.setText(self.schedule.event_name)
        form_layout.addRow("Nama Kegiatan:", self.event_edit)

        # 4. Pilihan Audio
        self.audio_combo = QComboBox()
        self.audio_combo.addItem("(Belum Dipilih / Default)", None)
        if self.audio_repo:
            audio_files = self.audio_repo.get_all()
            for af in audio_files:
                self.audio_combo.addItem(f"{af.name} ({af.original_filename})", af.id)

        if self.schedule and self.schedule.audio_id:
            for i in range(self.audio_combo.count()):
                if self.audio_combo.itemData(i) == self.schedule.audio_id:
                    self.audio_combo.setCurrentIndex(i)
                    break
        form_layout.addRow("File Suara Bel:", self.audio_combo)

        # 5. Status Aktif
        self.enabled_check = QCheckBox("Aktifkan jadwal ini")
        self.enabled_check.setChecked(self.schedule.is_enabled if self.schedule else True)
        form_layout.addRow("Status:", self.enabled_check)

        layout.addLayout(form_layout)

        # Tombol Batal & Simpan
        btn_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Save).setText("Simpan Jadwal")
        btn_box.button(QDialogButtonBox.Cancel).setText("Batal")
        btn_box.accepted.connect(self._validate_and_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _validate_and_accept(self) -> None:
        event_name = self.event_edit.text().strip()
        if not event_name:
            QMessageBox.warning(self, "Validasi Gagal", "Nama kegiatan bel tidak boleh kosong.")
            self.event_edit.setFocus()
            return

        time_str = self.time_edit.text().strip()
        try:
            normalized_time = normalize_time(time_str)
        except ValueError as err:
            QMessageBox.warning(self, "Format Waktu Salah", str(err))
            self.time_edit.setFocus()
            return

        self.time_edit.setText(normalized_time)
        self.accept()

    def get_schedule_data(self) -> Schedule:
        audio_id = self.audio_combo.currentData()
        return Schedule(
            id=self.schedule.id if self.schedule else None,
            profile_id=self.profile_id,
            day_of_week=self.day_combo.currentText(),
            bell_time=self.time_edit.text().strip(),
            event_name=self.event_edit.text().strip(),
            audio_id=audio_id,
            is_enabled=self.enabled_check.isChecked(),
        )


class CopyScheduleDialog(QDialog):
    """Dialog untuk menyalin seluruh jadwal dari satu hari ke hari lain."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Salin Jadwal Antarhari")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        form_layout = QFormLayout()

        self.from_combo = QComboBox()
        self.from_combo.addItems(list(DAYS_OF_WEEK))
        form_layout.addRow("Dari Hari (Sumber):", self.from_combo)

        self.to_combo = QComboBox()
        self.to_combo.addItems(list(DAYS_OF_WEEK))
        self.to_combo.setCurrentIndex(1)  # Default Selasa
        form_layout.addRow("Ke Hari (Tujuan):", self.to_combo)

        self.overwrite_check = QCheckBox("Timpa jadwal yang ada di hari tujuan")
        form_layout.addRow("", self.overwrite_check)

        layout.addLayout(form_layout)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Ok).setText("Mulai Salin")
        btn_box.button(QDialogButtonBox.Cancel).setText("Batal")
        btn_box.accepted.connect(self._validate_and_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _validate_and_accept(self) -> None:
        if self.from_combo.currentText() == self.to_combo.currentText():
            QMessageBox.warning(self, "Pilihan Hari Sama", "Hari sumber dan hari tujuan tidak boleh sama.")
            return
        self.accept()

    def get_copy_params(self) -> tuple[str, str, bool]:
        return (
            self.from_combo.currentText(),
            self.to_combo.currentText(),
            self.overwrite_check.isChecked(),
        )


class SchedulePage(QWidget):
    """Halaman Pengelolaan Jadwal Bel Otomatis."""

    schedules_changed = Signal()

    def __init__(self, db: DatabaseManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db
        self.schedule_repo = ScheduleRepository(db)
        self.profile_repo = ProfileRepository(db)
        self.audio_repo = AudioRepository(db)

        self.current_profile_id: Optional[int] = None
        self._setup_ui()
        self.refresh_profiles()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # 1. Baris Kontrol Atas (Pilih Profil, Filter Hari, Tombol Tambah, Tombol Salin)
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
        controls_layout.setContentsMargins(14, 10, 14, 10)
        controls_layout.setSpacing(12)

        # Pemilihan Profil
        prof_label = QLabel("Profil:")
        prof_label.setStyleSheet("font-weight: 600; color: #334155;")
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(150)
        self.profile_combo.setMaximumWidth(190)
        self.profile_combo.currentIndexChanged.connect(self._on_profile_selected)
        controls_layout.addWidget(prof_label)
        controls_layout.addWidget(self.profile_combo)

        # Filter Hari
        day_label = QLabel("Hari:")
        day_label.setStyleSheet("font-weight: 600; color: #334155;")
        self.day_filter_combo = QComboBox()
        self.day_filter_combo.setMinimumWidth(170)
        self.day_filter_combo.setMaximumWidth(210)
        self.day_filter_combo.addItem("Semua Hari (Senin–Sabtu)", None)
        for d in DAYS_OF_WEEK:
            self.day_filter_combo.addItem(d, d)
        self.day_filter_combo.currentIndexChanged.connect(self._on_day_filter_changed)
        controls_layout.addWidget(day_label)
        controls_layout.addWidget(self.day_filter_combo)

        controls_layout.addStretch()

        # Tombol Salin Jadwal
        self.copy_btn = QPushButton("Salin Antarhari")
        self.copy_btn.setMinimumHeight(32)
        self.copy_btn.setStyleSheet(
            "background-color: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; "
            "border-radius: 6px; padding: 7px 14px; font-weight: 600; font-size: 12px;"
        )
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.clicked.connect(self._on_copy_schedules)
        controls_layout.addWidget(self.copy_btn)

        # Tombol Tambah Jadwal
        self.add_btn = QPushButton("Tambah Jadwal")
        self.add_btn.setMinimumHeight(32)
        self.add_btn.setStyleSheet(
            "background-color: #0284c7; color: #ffffff; border: none; "
            "border-radius: 6px; padding: 7px 16px; font-weight: 600; font-size: 12px;"
        )
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._on_add_schedule)
        controls_layout.addWidget(self.add_btn)

        main_layout.addWidget(controls_card)

        # 2. Tabel Jadwal Bel
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
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Hari", "Waktu", "Nama Kegiatan", "File Audio", "Status", "Aksi"
        ])
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self.table.setColumnWidth(3, 190)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Interactive)
        self.table.setColumnWidth(5, 225)
        self.table.horizontalHeader().setMinimumSectionSize(65)
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

    def refresh_profiles(self) -> None:
        """Memuat daftar profil ke dalam dropdown."""
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()

        profiles = self.profile_repo.get_all()
        active_idx = 0
        for i, p in enumerate(profiles):
            label = f"{p.name} (Aktif)" if p.is_active else p.name
            self.profile_combo.addItem(label, p.id)
            if p.is_active:
                active_idx = i

        if self.profile_combo.count() > 0:
            self.profile_combo.setCurrentIndex(active_idx)
            self.current_profile_id = self.profile_combo.currentData()

        self.profile_combo.blockSignals(False)
        self.refresh_schedules()

    def _on_profile_selected(self, index: int) -> None:
        self.current_profile_id = self.profile_combo.currentData()
        self.refresh_schedules()

    def _on_day_filter_changed(self, index: int) -> None:
        self.refresh_schedules()

    def refresh_schedules(self) -> None:
        """Memuat jadwal sesuai filter profil dan hari."""
        if self.current_profile_id is None:
            self.table.setRowCount(0)
            return

        selected_day = self.day_filter_combo.currentData()
        if selected_day:
            schedules = self.schedule_repo.get_by_profile_and_day(self.current_profile_id, selected_day)
        else:
            schedules = self.schedule_repo.get_by_profile(self.current_profile_id)

        self.table.setRowCount(len(schedules))
        for row, s in enumerate(schedules):
            # 0. Hari
            day_item = QTableWidgetItem(s.day_of_week)
            day_item.setTextAlignment(Qt.AlignCenter)
            day_item.setForeground(QColor("#0f172a"))
            self.table.setItem(row, 0, day_item)

            # 1. Waktu
            time_item = QTableWidgetItem(s.bell_time)
            time_item.setTextAlignment(Qt.AlignCenter)
            time_item.setFont(QFont("Monospace", 9, QFont.Bold))
            time_item.setForeground(QColor("#0f172a"))
            self.table.setItem(row, 1, time_item)

            # 2. Nama Kegiatan
            event_item = QTableWidgetItem(s.event_name)
            event_item.setForeground(QColor("#0f172a"))
            self.table.setItem(row, 2, event_item)

            # 3. Audio (Peringatan eksplisit jika belum dipilih)
            if s.audio_name:
                audio_text = s.audio_name
                audio_item = QTableWidgetItem(audio_text)
                audio_item.setForeground(QColor("#0f172a"))
                audio_item.setToolTip(f"File audio yang digunakan: {s.audio_name}")
            else:
                audio_text = "⚠️ Belum Dipilih (Edit Jadwal)"
                audio_item = QTableWidgetItem(audio_text)
                audio_item.setForeground(QColor("#b45309"))
                audio_item.setToolTip(
                    "File suara bel belum dikaitkan dengan jadwal ini.\n"
                    "Silakan klik tombol Edit untuk memilih file suara bel."
                )
            self.table.setItem(row, 3, audio_item)

            # 4. Status Aktif / Toggle Checkbox
            status_item = QTableWidgetItem("Aktif" if s.is_enabled else "Nonaktif")
            status_item.setTextAlignment(Qt.AlignCenter)
            if s.is_enabled:
                status_item.setForeground(Qt.darkGreen)
            else:
                status_item.setForeground(Qt.gray)
            self.table.setItem(row, 4, status_item)

            # 5. Tombol Aksi (Toggle, Edit, Hapus)
            action_widget = QWidget()
            action_widget.setStyleSheet("background-color: transparent;")
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(6, 4, 6, 4)
            action_layout.setSpacing(8)
            action_layout.setAlignment(Qt.AlignCenter)

            toggle_btn = QPushButton("Matikan" if s.is_enabled else "Aktifkan")
            toggle_btn.setMinimumHeight(28)
            toggle_btn.setMinimumWidth(68)
            toggle_btn.setStyleSheet(
                "min-height: 28px; padding: 4px 10px; font-size: 11px; font-weight: 600; border-radius: 5px; "
                f"background-color: {'#fee2e2' if s.is_enabled else '#dcfce7'}; "
                f"color: {'#991b1b' if s.is_enabled else '#166534'}; "
                f"border: 1px solid {'#fca5a5' if s.is_enabled else '#86efac'};"
            )
            toggle_btn.setCursor(Qt.PointingHandCursor)
            toggle_btn.clicked.connect(lambda _=False, sched_id=s.id, current_state=s.is_enabled: self._toggle_schedule(sched_id, current_state))
            action_layout.addWidget(toggle_btn)

            edit_btn = QPushButton("Edit")
            edit_btn.setMinimumHeight(28)
            edit_btn.setMinimumWidth(50)
            edit_btn.setStyleSheet(
                "min-height: 28px; padding: 4px 12px; font-size: 11px; font-weight: 600; border-radius: 5px; "
                "background-color: #f1f5f9; color: #0f172a; border: 1px solid #cbd5e1;"
            )
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.clicked.connect(lambda _=False, sched=s: self._on_edit_schedule(sched))
            action_layout.addWidget(edit_btn)

            del_btn = QPushButton("Hapus")
            del_btn.setMinimumHeight(28)
            del_btn.setMinimumWidth(56)
            del_btn.setStyleSheet(
                "min-height: 28px; padding: 4px 12px; font-size: 11px; font-weight: 600; border-radius: 5px; "
                "background-color: #fff1f2; color: #be123c; border: 1px solid #fecdd3;"
            )
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.clicked.connect(lambda _=False, sched=s: self._on_delete_schedule(sched))
            action_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 5, action_widget)

    def _on_add_schedule(self) -> None:
        if self.current_profile_id is None:
            QMessageBox.warning(self, "Peringatan", "Pilih profil terlebih dahulu.")
            return

        dialog = ScheduleDialog(self.current_profile_id, audio_repo=self.audio_repo, parent=self)
        if dialog.exec() == QDialog.Accepted:
            new_sched = dialog.get_schedule_data()
            try:
                self.schedule_repo.create(new_sched)
                QMessageBox.information(self, "Berhasil", f"Jadwal '{new_sched.event_name}' berhasil ditambahkan.")
                self.refresh_schedules()
                self.schedules_changed.emit()
            except ValueError as err:
                QMessageBox.warning(self, "Gagal Menyimpan", str(err))

    def _on_edit_schedule(self, schedule: Schedule) -> None:
        dialog = ScheduleDialog(schedule.profile_id, schedule=schedule, audio_repo=self.audio_repo, parent=self)
        if dialog.exec() == QDialog.Accepted:
            updated_sched = dialog.get_schedule_data()
            try:
                self.schedule_repo.update(updated_sched)
                QMessageBox.information(self, "Berhasil", f"Jadwal '{updated_sched.event_name}' berhasil diperbarui.")
                self.refresh_schedules()
                self.schedules_changed.emit()
            except ValueError as err:
                QMessageBox.warning(self, "Gagal Memperbarui", str(err))

    def _on_delete_schedule(self, schedule: Schedule) -> None:
        confirm = QMessageBox.question(
            self,
            "Konfirmasi Hapus",
            f"Apakah Anda yakin ingin menghapus jadwal:\n\n"
            f"Hari: {schedule.day_of_week}\n"
            f"Waktu: {schedule.bell_time}\n"
            f"Kegiatan: {schedule.event_name}\n\n"
            "Tindakan ini tidak dapat dibatalkan.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            self.schedule_repo.delete(schedule.id)
            self.refresh_schedules()
            self.schedules_changed.emit()

    def _toggle_schedule(self, schedule_id: int, current_state: bool) -> None:
        new_state = not current_state
        self.schedule_repo.toggle_enabled(schedule_id, new_state)
        self.refresh_schedules()
        self.schedules_changed.emit()

    def _on_copy_schedules(self) -> None:
        if self.current_profile_id is None:
            return

        dialog = CopyScheduleDialog(self)
        if dialog.exec() == QDialog.Accepted:
            from_day, to_day, overwrite = dialog.get_copy_params()
            try:
                copied = self.schedule_repo.copy_day_schedules(
                    self.current_profile_id, from_day, to_day, overwrite=overwrite
                )
                QMessageBox.information(
                    self,
                    "Salin Jadwal Selesai",
                    f"Berhasil menyalin {copied} jadwal dari hari {from_day} ke hari {to_day}.",
                )
                self.refresh_schedules()
                self.schedules_changed.emit()
            except ValueError as err:
                QMessageBox.warning(self, "Gagal Menyalin", str(err))
