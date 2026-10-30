"""
Halaman Pustaka Lagu Berkode
Menangani penambahan, pemutaran uji, pengeditan kode unik, dan penghapusan lagu bel dengan verifikasi jadwal terdampak.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QDialog,
    QLineEdit,
    QMessageBox,
    QHeaderView,
    QAbstractItemView,
)

from src.core.config import get_audio_storage_dir
from src.database.db import DatabaseManager
from src.database.repositories import AudioRepository
from src.models.models import AudioFile
from src.services.audio_player import AudioPlayer

logger = logging.getLogger(__name__)


class AudioEditDialog(QDialog):
    """Dialog untuk menambah atau mengedit Kode Lagu dan Nama Lagu dengan fitur auto-urut abjad/angka."""

    def __init__(
        self,
        audio: Optional[AudioFile] = None,
        file_path: Optional[str] = None,
        suggested_code: str = "",
        repo: Optional[AudioRepository] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.audio = audio
        self.file_path = file_path
        self.suggested_code = suggested_code
        self.repo = repo
        self.setWindowTitle("Tambah Lagu Baru" if audio is None else "Edit Kode & Nama Lagu")
        self.setFixedSize(460, 310)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                color: #0f172a;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #1e293b;
                font-size: 12px;
                font-weight: 600;
            }
            QLineEdit {
                background-color: #ffffff;
                color: #0f172a;
                border: 1.5px solid #94a3b8;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
                font-weight: 600;
            }
            QLineEdit:focus {
                border: 2px solid #2563eb;
                background-color: #f8fafc;
            }
        """)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(11)

        # Kode Lagu & Tombol Auto Urut
        lbl_code = QLabel("Kode Lagu (misal: BEL A, BEL 1, APL):")
        layout.addWidget(lbl_code)

        code_box = QHBoxLayout()
        code_box.setSpacing(8)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("BEL A / BEL 1...")
        self.code_input.setMaxLength(10)
        self.code_input.setFixedHeight(34)
        if self.audio and self.audio.code:
            self.code_input.setText(self.audio.code)
        elif self.suggested_code:
            self.code_input.setText(self.suggested_code)
        code_box.addWidget(self.code_input, 1)

        btn_auto_alpha = QPushButton("Urut Abjad")
        btn_auto_alpha.setFixedHeight(34)
        btn_auto_alpha.setToolTip("Otomatis isi kode alfabet berikutnya (misal: BEL A, BEL B)")
        btn_auto_alpha.setStyleSheet("""
            QPushButton {
                background-color: #eff6ff;
                color: #1d4ed8;
                border: 1.5px solid #bfdbfe;
                border-radius: 6px;
                padding: 0 12px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #dbeafe;
                border-color: #93c5fd;
            }
        """)
        btn_auto_alpha.clicked.connect(lambda: self._set_auto_code("alphabet"))
        code_box.addWidget(btn_auto_alpha)

        btn_auto_num = QPushButton("Urut Angka")
        btn_auto_num.setFixedHeight(34)
        btn_auto_num.setToolTip("Otomatis isi kode angka berikutnya (misal: BEL 1, BEL 2)")
        btn_auto_num.setStyleSheet("""
            QPushButton {
                background-color: #eff6ff;
                color: #1d4ed8;
                border: 1.5px solid #bfdbfe;
                border-radius: 6px;
                padding: 0 12px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #dbeafe;
                border-color: #93c5fd;
            }
        """)
        btn_auto_num.clicked.connect(lambda: self._set_auto_code("numeric"))
        code_box.addWidget(btn_auto_num)

        layout.addLayout(code_box)

        # Nama Lagu
        lbl_name = QLabel("Nama / Label Lagu:")
        layout.addWidget(lbl_name)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nama lagu / kegiatan...")
        self.name_input.setFixedHeight(34)
        if self.audio and self.audio.name:
            self.name_input.setText(self.audio.name)
        elif self.file_path:
            self.name_input.setText(Path(self.file_path).stem)
        layout.addWidget(self.name_input)

        # Pilih/Ganti Berkas Audio
        file_box = QHBoxLayout()
        self.btn_browse = QPushButton("Pilih File Audio...")
        self.btn_browse.setFixedHeight(30)
        self.btn_browse.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #0f172a;
                border: 1.5px solid #94a3b8;
                border-radius: 6px;
                padding: 0 12px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        self.btn_browse.clicked.connect(self._on_browse_file)
        file_box.addWidget(self.btn_browse)

        current_fn = self.file_path
        if not current_fn and self.audio:
            current_fn = self.audio.original_filename or Path(self.audio.stored_path).name
        self.lbl_selected_file = QLabel(Path(current_fn).name if current_fn else "(Belum ada file)")
        self.lbl_selected_file.setStyleSheet("color: #475569; font-size: 11px; font-weight: normal;")
        file_box.addWidget(self.lbl_selected_file)
        file_box.addStretch()
        layout.addLayout(file_box)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #dc2626; font-size: 11px; font-weight: bold;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        cancel_btn = QPushButton("Batal")
        cancel_btn.setFixedHeight(34)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #334155;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 0 18px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Simpan")
        save_btn.setFixedHeight(34)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border: 1px solid #1d4ed8;
                border-radius: 6px;
                padding: 0 20px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _set_auto_code(self, mode: str):
        if self.repo:
            new_code = self.repo.get_next_available_code(mode=mode)
            self.code_input.setText(new_code)
            self.error_label.setVisible(False)

    def _on_save(self):
        code = self.code_input.text().strip().upper()
        name = self.name_input.text().strip()

        if not code:
            self.error_label.setText("Kode lagu tidak boleh kosong.")
            self.error_label.setVisible(True)
            self.code_input.setFocus()
            return

        if not name:
            self.error_label.setText("Nama lagu tidak boleh kosong.")
            self.error_label.setVisible(True)
            self.name_input.setFocus()
            return

        self.result_code = code
        self.result_name = name
        self.accept()

    def _on_browse_file(self):
        f, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih Berkas Audio MP3/WAV",
            "",
            "Audio Files (*.mp3 *.wav);;All Files (*.*)",
        )
        if f:
            self.file_path = f
            self.lbl_selected_file.setText(Path(f).name)
            if not self.name_input.text().strip():
                self.name_input.setText(Path(f).stem)


class AudioCodePage(QWidget):
    """Pengelolaan pustaka berkas audio bel dengan kode unik."""

    audio_list_changed = Signal()

    def __init__(self, db: DatabaseManager, audio_player: AudioPlayer, parent=None):
        super().__init__(parent)
        self.db = db
        self.repo = AudioRepository(db)
        self.player = audio_player
        self.playing_audio_id: Optional[int] = None
        self.player.status_changed.connect(self._on_player_status_changed)

        self._setup_ui()
        self.refresh_table()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        top_bar = QHBoxLayout()
        title = QLabel("Daftar Lagu Bel Berkode")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #1e3a8a;")
        top_bar.addWidget(title)

        top_bar.addStretch()

        self.add_btn = QPushButton("Tambah Lagu MP3/WAV")
        self.add_btn.setFixedHeight(34)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 0 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        self.add_btn.clicked.connect(self._on_add_audio)
        top_bar.addWidget(self.add_btn)
        layout.addLayout(top_bar)

        desc = QLabel("Setiap lagu memiliki Kode Unik alfabet (misal: BEL A, BEL B, BEL C, APL) yang digunakan pada jadwal dan tombol manual.")
        desc.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(desc)

        # Tabel Audio
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Kode Lagu",
            "Nama Lagu",
            "Nama File",
            "Status File",
            "Putar Uji",
            "Aksi",
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                background-color: #ffffff;
                gridline-color: #e2e8f0;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                color: #1e293b;
                font-weight: bold;
                padding: 8px 6px;
                border: none;
                border-bottom: 2px solid #cbd5e1;
            }
        """)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(0, 110)
        self.table.setColumnWidth(1, 160)
        self.table.setColumnWidth(3, 110)
        self.table.setColumnWidth(4, 90)
        self.table.setColumnWidth(5, 130)

        layout.addWidget(self.table)

    def refresh_table(self):
        audios = self.repo.get_all()
        self.table.setRowCount(0)

        for row, a in enumerate(audios):
            self.table.insertRow(row)
            self.table.setRowHeight(row, 40)

            # 1. Kode Lagu
            code_item = QTableWidgetItem(a.code if a.code else f"BEL {a.id}")
            code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            code_item.setForeground(Qt.GlobalColor.darkBlue)
            font = code_item.font()
            font.setBold(True)
            code_item.setFont(font)
            self.table.setItem(row, 0, code_item)

            # 2. Nama Lagu
            name_item = QTableWidgetItem(a.name)
            name_item.setForeground(QColor("#0f172a"))
            font_name = name_item.font()
            font_name.setBold(True)
            name_item.setFont(font_name)
            self.table.setItem(row, 1, name_item)

            # 3. Nama File
            fn_text = a.original_filename if a.original_filename else Path(a.stored_path).name
            fn_item = QTableWidgetItem(fn_text)
            fn_item.setForeground(QColor("#334155"))
            self.table.setItem(row, 2, fn_item)

            # 4. Status File Fisik
            exists = Path(a.stored_path).exists()
            status_item = QTableWidgetItem("✔ Tersedia" if exists else "✖ Hilang")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if not exists:
                status_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 3, status_item)

            # 5. Putar Uji Button
            play_btn = QPushButton("Putar" if self.playing_audio_id != a.id else "Stop")
            play_btn.setFixedHeight(28)
            play_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e0f2fe;
                    color: #0369a1;
                    border: 1px solid #bae6fd;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QPushButton:hover { background-color: #bae6fd; }
            """)
            play_btn.clicked.connect(lambda _=False, item=a: self._toggle_play(item))
            self.table.setCellWidget(row, 4, play_btn)

            # 6. Aksi (Edit & Hapus)
            action_box = QWidget()
            action_layout = QHBoxLayout(action_box)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(6)

            edit_btn = QPushButton("Edit")
            edit_btn.setFixedHeight(28)
            edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f1f5f9;
                    color: #334155;
                    border: 1px solid #cbd5e1;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover { background-color: #e2e8f0; }
            """)
            edit_btn.clicked.connect(lambda _=False, item=a: self._on_edit_audio(item))
            action_layout.addWidget(edit_btn)

            del_btn = QPushButton("Hapus")
            del_btn.setFixedHeight(28)
            del_btn.setStyleSheet("""
                QPushButton {
                    background-color: #fee2e2;
                    color: #b91c1c;
                    border: 1px solid #fca5a5;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover { background-color: #fecaca; }
            """)
            del_btn.clicked.connect(lambda _=False, item=a: self._on_delete_audio(item))
            action_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 5, action_box)

    def _on_player_status_changed(self, status: str):
        from src.services.audio_player import AudioStatus
        if status in (AudioStatus.PLAYING.value, AudioStatus.LOADING.value):
            new_id = getattr(self.player, "current_audio_id", None)
            if self.playing_audio_id != new_id:
                self.playing_audio_id = new_id
                self.refresh_table()
        else:
            if self.playing_audio_id is not None:
                self.playing_audio_id = None
                self.refresh_table()

    def _toggle_play(self, audio: AudioFile):
        if self.playing_audio_id == audio.id and self.player.is_playing():
            self.player.stop(reason="Dihentikan dari Pustaka Lagu")
            self.playing_audio_id = None
            self.refresh_table()
        else:
            if not Path(audio.stored_path).exists():
                QMessageBox.warning(self, "Berkas Tidak Ditemukan", f"Berkas fisik audio tidak ada di: {audio.stored_path}")
                return
            success = self.player.play_file(
                audio.stored_path,
                title=f"Uji {audio.name}",
                interrupt=True,
                mode="PREVIEW",
                audio_id=audio.id,
            )
            self.playing_audio_id = audio.id if success else None
            self.refresh_table()

    def _on_add_audio(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih Berkas Audio Bel",
            "",
            "Audio Files (*.mp3 *.wav);;All Files (*.*)",
        )
        if not file_path:
            return

        suggested_code = self.repo.get_next_available_code(mode="alphabet")
        dialog = AudioEditDialog(
            audio=None,
            file_path=file_path,
            suggested_code=suggested_code,
            repo=self.repo,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            code = dialog.result_code
            name = dialog.result_name

            # Cek apakah kode sudah terdaftar
            existing = self.repo.get_by_code(code)
            if existing:
                QMessageBox.warning(self, "Kode Duplikat", f"Kode '{code}' sudah digunakan oleh lagu '{existing.name}'.")
                return

            try:
                # Salin ke penyimpanan audio persisten
                storage_dir = get_audio_storage_dir()
                dest_file = storage_dir / Path(file_path).name
                # Jika nama sudah ada, tambahkan suffix
                if dest_file.exists():
                    dest_file = storage_dir / f"{Path(file_path).stem}_{code.replace(' ', '_')}{Path(file_path).suffix}"
                shutil.copy2(file_path, dest_file)

                # Simpan ke database
                new_audio = AudioFile(
                    code=code,
                    name=name,
                    stored_path=str(dest_file),
                    original_filename=Path(file_path).name,
                )
                self.repo.create(new_audio)
                self.refresh_table()
                self.audio_list_changed.emit()
                QMessageBox.information(self, "Berhasil", f"Lagu '{name}' dengan kode '{code}' berhasil ditambahkan.")
            except Exception as e:
                logger.exception("Gagal menambahkan lagu: %s", e)
                QMessageBox.critical(self, "Kesalahan", f"Gagal menambahkan berkas audio:\n\n{e}")

    def _on_edit_audio(self, audio: AudioFile):
        dialog = AudioEditDialog(
            audio=audio,
            repo=self.repo,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            code = dialog.result_code
            name = dialog.result_name

            # Cek konflik kode pada record lain
            existing = self.repo.get_by_code(code)
            if existing and existing.id != audio.id:
                QMessageBox.warning(self, "Kode Duplikat", f"Kode '{code}' sudah digunakan oleh lagu '{existing.name}'.")
                return

            try:
                audio.code = code
                audio.name = name

                # Jika pengguna memilih file audio baru
                if dialog.file_path and str(dialog.file_path) != str(audio.stored_path):
                    storage_dir = get_audio_storage_dir()
                    dest_file = storage_dir / Path(dialog.file_path).name
                    if dest_file.exists() and str(dest_file) != str(dialog.file_path):
                        dest_file = storage_dir / f"{Path(dialog.file_path).stem}_{code.replace(' ', '_')}{Path(dialog.file_path).suffix}"
                    if str(dest_file) != str(dialog.file_path):
                        shutil.copy2(dialog.file_path, dest_file)
                    audio.stored_path = str(dest_file)
                    audio.original_filename = Path(dialog.file_path).name

                self.repo.update(audio)
                self.refresh_table()
                self.audio_list_changed.emit()
                QMessageBox.information(self, "Berhasil", "Kode dan nama lagu berhasil diperbarui.")
            except Exception as e:
                logger.exception("Gagal mengupdate lagu: %s", e)
                QMessageBox.critical(self, "Kesalahan", f"Gagal memperbarui lagu:\n\n{e}")

    def _on_delete_audio(self, audio: AudioFile):
        # 1. Periksa jadwal yang terdampak
        affected = self.repo.get_affected_schedules(audio.id)
        if affected:
            detail_lines = [f"• Profil {r['profile_name']} — {r['day_of_week']} {r['bell_time'][:5]} ({r['event_name']})" for r in affected[:8]]
            if len(affected) > 8:
                detail_lines.append(f"... dan {len(affected) - 8} jadwal lainnya.")
            details_str = "\n".join(detail_lines)

            ans = QMessageBox.warning(
                self,
                "Lagu Sedang Digunakan Jadwal",
                f"Lagu '{audio.name}' (Kode: {audio.code}) sedang digunakan oleh {len(affected)} jadwal berikut:\n\n"
                f"{details_str}\n\n"
                "Jika dihapus, jadwal-jadwal tersebut tidak akan memiliki file audio bel.\n"
                "Apakah Anda yakin ingin tetap menghapus lagu ini?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                return
        else:
            ans = QMessageBox.question(
                self,
                "Konfirmasi Hapus",
                f"Hapus lagu '{audio.name}' (Kode: {audio.code}) dari pustaka bel?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                return

        try:
            if self.playing_audio_id == audio.id:
                self.player.stop()
                self.playing_audio_id = None

            self.repo.delete(audio.id)
            self.refresh_table()
            self.audio_list_changed.emit()
            QMessageBox.information(self, "Berhasil", f"Lagu '{audio.name}' berhasil dihapus.")
        except Exception as e:
            logger.exception("Gagal menghapus audio: %s", e)
            QMessageBox.critical(self, "Kesalahan", f"Gagal menghapus lagu:\n\n{e}")
