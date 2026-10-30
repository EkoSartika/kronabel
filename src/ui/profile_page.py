"""
Halaman Manajemen Profil Jam Pelajaran Bel Otomatis Sekolah.
Menyediakan pengelolaan profil (Reguler, Ramadan, Ujian, Kustom), aktivasi,
penambahan, pengubahan status aktif/nonaktif, dan perlindungan profil aktif.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.database.db import DatabaseManager
from src.database.repositories import ProfileRepository
from src.models.models import Profile


class ProfileDialog(QDialog):
    """Dialog Tambah/Edit Profil Jam Pelajaran dengan Pengaturan Status Aktif/Nonaktif."""

    def __init__(self, profile: Optional[Profile] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.profile = profile
        self.setWindowTitle("Tambah Profil Baru" if profile is None else "Edit Profil")
        self.setFixedSize(450, 270)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                color: #0f172a;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #1e293b;
                font-size: 11.5px;
                font-weight: 700;
            }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #ffffff;
                color: #0f172a;
                border: 1.5px solid #94a3b8;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border: 2px solid #2563eb;
                background-color: #f8fafc;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #0f172a;
                selection-background-color: #e0f2fe;
                selection-color: #0369a1;
            }
        """)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(6)

        # 1. Nama Profil
        lbl_name = QLabel("Nama Profil:")
        layout.addWidget(lbl_name)

        self.name_edit = QLineEdit()
        self.name_edit.setFixedHeight(28)
        self.name_edit.setPlaceholderText("Contoh: Reguler, Ramadan, Ujian Semester")
        if self.profile:
            self.name_edit.setText(self.profile.name)
        layout.addWidget(self.name_edit)

        # 2. Deskripsi
        lbl_desc = QLabel("Deskripsi:")
        layout.addWidget(lbl_desc)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Keterangan singkat tentang penggunaan profil jadwal ini...")
        self.desc_edit.setFixedHeight(44)
        if self.profile:
            self.desc_edit.setText(self.profile.description)
        layout.addWidget(self.desc_edit)

        # 3. Status Profil (Aktif / Nonaktif)
        lbl_status = QLabel("Status Profil:")
        layout.addWidget(lbl_status)

        self.status_combo = QComboBox()
        self.status_combo.setFixedHeight(28)
        self.status_combo.addItem("Aktif (Jadwal Bel yang Sedang Digunakan)", True)
        self.status_combo.addItem("Nonaktif (Disimpan Sebagai Cadangan)", False)

        is_active_initial = self.profile.is_active if self.profile else False
        self.status_combo.setCurrentIndex(0 if is_active_initial else 1)
        layout.addWidget(self.status_combo)

        # Label Error
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #dc2626; font-size: 11px; font-weight: bold;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        # Baris Tombol Aksi
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        cancel_btn = QPushButton("Batal")
        cancel_btn.setFixedHeight(30)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #334155;
                border: 1.5px solid #cbd5e1;
                border-radius: 6px;
                padding: 0 18px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
                border-color: #94a3b8;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Simpan Profil")
        save_btn.setFixedHeight(30)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border: 1.5px solid #1d4ed8;
                border-radius: 6px;
                padding: 0 20px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        save_btn.clicked.connect(self._validate_and_accept)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _validate_and_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.error_label.setText("Nama profil tidak boleh kosong.")
            self.error_label.setVisible(True)
            self.name_edit.setFocus()
            return
        self.accept()

    def get_profile_data(self) -> Profile:
        is_active = bool(self.status_combo.currentData())
        return Profile(
            id=self.profile.id if self.profile else None,
            name=self.name_edit.text().strip(),
            description=self.desc_edit.toPlainText().strip(),
            is_active=is_active,
        )


class ProfilePage(QWidget):
    """Halaman Pengelolaan Profil Jam Pelajaran."""

    profile_changed = Signal()

    def __init__(self, db: DatabaseManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db
        self.profile_repo = ProfileRepository(db)

        self._setup_ui()
        self.refresh_profiles()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # 1. Baris Header & Tombol Tambah
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
        title = QLabel("Profil Jam Pelajaran")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #0f172a;")
        desc = QLabel(
            "Gunakan profil berbeda untuk skenario hari normal (Reguler), bulan Ramadan, "
            "atau periode ujian tanpa menghapus jadwal yang telah ada."
        )
        desc.setStyleSheet("color: #64748b; font-size: 12px;")
        desc.setWordWrap(True)
        info_layout.addWidget(title)
        info_layout.addWidget(desc)
        header_layout.addLayout(info_layout, 1)

        self.add_btn = QPushButton("Buat Profil Baru")
        self.add_btn.setMinimumHeight(32)
        self.add_btn.setStyleSheet(
            "background-color: #0284c7; color: #ffffff; border: none; "
            "border-radius: 6px; padding: 7px 16px; font-weight: 700; font-size: 12px;"
        )
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._on_add_profile)
        header_layout.addWidget(self.add_btn)

        main_layout.addWidget(header_card)

        # 2. Tabel Daftar Profil
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
            "Nama Profil", "Deskripsi", "Total Jadwal", "Status", "Aksi"
        ])
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.table.setColumnWidth(0, 160)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.table.setColumnWidth(2, 110)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self.table.setColumnWidth(3, 110)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Interactive)
        self.table.setColumnWidth(4, 240)
        self.table.horizontalHeader().setMinimumSectionSize(90)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
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
                outline: none;
            }
            QTableWidget::item {
                color: #0f172a;
                background-color: #ffffff;
                padding: 6px 8px;
                border: none;
                outline: none;
            }
            QTableWidget::item:focus {
                border: none;
                outline: none;
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

    def refresh_data(self) -> None:
        """Alias refresh_data untuk kompatibilitas switcher admin window."""
        self.refresh_profiles()

    def refresh_profiles(self) -> None:
        """Memuat daftar profil dari database."""
        profiles = self.profile_repo.get_all()
        self.table.setRowCount(len(profiles))

        for row, p in enumerate(profiles):
            # 0. Nama
            name_item = QTableWidgetItem(p.name)
            name_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            name_item.setForeground(QColor("#0f172a"))
            self.table.setItem(row, 0, name_item)

            # 1. Deskripsi
            desc_item = QTableWidgetItem(p.description if p.description else "-")
            desc_item.setForeground(QColor("#334155"))
            self.table.setItem(row, 1, desc_item)

            # 2. Total Jadwal
            sched_count = self.profile_repo.get_schedule_count(p.id)
            count_item = QTableWidgetItem(f"{sched_count} Jadwal")
            count_item.setTextAlignment(Qt.AlignCenter)
            count_item.setForeground(QColor("#0f172a"))
            self.table.setItem(row, 2, count_item)

            # 3. Status (Pill Badge Visual Bersih)
            status_text = "AKTIF" if p.is_active else "Nonaktif"
            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignCenter)
            if p.is_active:
                status_item.setForeground(QColor("#059669"))
                status_item.setBackground(QColor("#dcfce7"))
                status_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            else:
                status_item.setForeground(QColor("#64748b"))
                status_item.setBackground(QColor("#f8fafc"))
                status_item.setFont(QFont("Segoe UI", 9))
            self.table.setItem(row, 3, status_item)

            # 4. Tombol Aksi (Aktifkan, Edit, Hapus)
            action_widget = QWidget()
            action_widget.setStyleSheet("background-color: transparent;")
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(6, 4, 6, 4)
            action_layout.setSpacing(8)
            action_layout.setAlignment(Qt.AlignCenter)

            if not p.is_active:
                activate_btn = QPushButton("Aktifkan")
                activate_btn.setMinimumHeight(28)
                activate_btn.setMinimumWidth(70)
                activate_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #059669;
                        color: #ffffff;
                        border: 1px solid #047857;
                        border-radius: 6px;
                        padding: 4px 12px;
                        font-size: 11.5px;
                        font-weight: 700;
                        outline: none;
                    }
                    QPushButton:hover {
                        background-color: #047857;
                    }
                """)
                activate_btn.setCursor(Qt.PointingHandCursor)
                activate_btn.clicked.connect(lambda _=False, prof_id=p.id, prof_name=p.name: self._on_activate_profile(prof_id, prof_name))
                action_layout.addWidget(activate_btn)

            # Tombol Edit (Kini Proper, Elegan & Jelas)
            edit_btn = QPushButton("Edit")
            edit_btn.setMinimumHeight(28)
            edit_btn.setMinimumWidth(64)
            edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0284c7;
                    color: #ffffff;
                    border: 1px solid #0369a1;
                    border-radius: 6px;
                    padding: 4px 14px;
                    font-size: 11.5px;
                    font-weight: 700;
                    outline: none;
                }
                QPushButton:hover {
                    background-color: #0369a1;
                }
            """)
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.clicked.connect(lambda _=False, prof=p: self._on_edit_profile(prof))
            action_layout.addWidget(edit_btn)

            # Tombol hapus hanya jika bukan profil aktif
            if not p.is_active:
                del_btn = QPushButton("Hapus")
                del_btn.setMinimumHeight(28)
                del_btn.setMinimumWidth(60)
                del_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #fee2e2;
                        color: #dc2626;
                        border: 1px solid #fca5a5;
                        border-radius: 6px;
                        padding: 4px 10px;
                        font-size: 11.5px;
                        font-weight: 700;
                        outline: none;
                    }
                    QPushButton:hover {
                        background-color: #fecdd3;
                    }
                """)
                del_btn.setCursor(Qt.PointingHandCursor)
                del_btn.clicked.connect(lambda _=False, prof=p, count=sched_count: self._on_delete_profile(prof, count))
                action_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 4, action_widget)

    def _on_add_profile(self) -> None:
        dialog = ProfileDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            new_profile = dialog.get_profile_data()
            try:
                created = self.profile_repo.create(new_profile)
                if new_profile.is_active:
                    self.profile_repo.set_active(created.id)
                QMessageBox.information(self, "Berhasil", f"Profil '{new_profile.name}' berhasil dibuat.")
                self.refresh_profiles()
                self.profile_changed.emit()
            except ValueError as err:
                QMessageBox.warning(self, "Gagal Membuat Profil", str(err))

    def _on_edit_profile(self, profile: Profile) -> None:
        dialog = ProfileDialog(profile=profile, parent=self)
        if dialog.exec() == QDialog.Accepted:
            updated_profile = dialog.get_profile_data()
            try:
                self.profile_repo.update(updated_profile)
                if updated_profile.is_active and not profile.is_active:
                    self.profile_repo.set_active(profile.id)
                elif not updated_profile.is_active and profile.is_active:
                    # Alihkan ke profil lain yang tersedia
                    other_profiles = [p for p in self.profile_repo.get_all() if p.id != profile.id]
                    if other_profiles:
                        self.profile_repo.set_active(other_profiles[0].id)
                        QMessageBox.information(
                            self,
                            "Status Profil Diperbarui",
                            f"Profil '{profile.name}' dinonaktifkan.\nProfil '{other_profiles[0].name}' otomatis dijadikan profil aktif.",
                        )
                    else:
                        QMessageBox.warning(
                            self,
                            "Gagal Menonaktifkan",
                            "Harus ada minimal satu profil aktif dalam sistem.",
                        )
                        return
                QMessageBox.information(self, "Berhasil", f"Profil '{updated_profile.name}' berhasil diperbarui.")
                self.refresh_profiles()
                self.profile_changed.emit()
            except ValueError as err:
                QMessageBox.warning(self, "Gagal Memperbarui Profil", str(err))

    def _on_activate_profile(self, profile_id: int, profile_name: str) -> None:
        try:
            self.profile_repo.set_active(profile_id)
            QMessageBox.information(self, "Profil Diaktifkan", f"Profil '{profile_name}' sekarang aktif digunakan.")
            self.refresh_profiles()
            self.profile_changed.emit()
        except ValueError as err:
            QMessageBox.warning(self, "Gagal Mengaktifkan Profil", str(err))

    def _on_delete_profile(self, profile: Profile, schedule_count: int) -> None:
        extra_warning = ""
        if schedule_count > 0:
            extra_warning = f"\n\nPERHATIAN: Profil ini memiliki {schedule_count} jadwal yang juga akan terhapus."

        confirm = QMessageBox.question(
            self,
            "Konfirmasi Hapus Profil",
            f"Apakah Anda yakin ingin menghapus profil '{profile.name}'?{extra_warning}\n\n"
            "Tindakan ini tidak dapat dibatalkan.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            try:
                self.profile_repo.delete(profile.id)
                QMessageBox.information(self, "Berhasil", f"Profil '{profile.name}' berhasil dihapus.")
                self.refresh_profiles()
                self.profile_changed.emit()
            except ValueError as err:
                QMessageBox.warning(self, "Penolakan Penghapusan", str(err))
