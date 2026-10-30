"""
Dialog Login dan Inisialisasi Akun Pengelola Bel Otomatis Sekolah
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QFrame,
)

from src.core.win7_compat import is_dwm_composition_enabled
from src.services.auth_service import AuthService


class LoginDialog(QDialog):
    """Dialog login untuk mengakses area pengelola (Setting)."""

    def __init__(self, auth_service: AuthService, parent=None):
        super().__init__(parent)
        self.auth = auth_service
        self.setWindowTitle("Login Pengelola Bel")
        self.setFixedSize(380, 260)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, is_dwm_composition_enabled())
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self._drag_pos = None

        self._setup_ui()
        self._center_dialog()

    def _center_dialog(self):
        parent = self.parent()
        if parent and hasattr(parent, "geometry") and parent.isVisible():
            parent_geo = parent.geometry()
            geo = self.frameGeometry()
            geo.moveCenter(parent_geo.center())
            self.move(geo.topLeft())
        else:
            screen = QApplication.primaryScreen()
            if screen:
                geo = self.frameGeometry()
                geo.moveCenter(screen.availableGeometry().center())
                self.move(geo.topLeft())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("LoginCard")
        card.setStyleSheet("""
            QFrame#LoginCard {
                background-color: #ffffff;
                color: #0f172a;
                border: 2px solid #cbd5e1;
                border-radius: 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Autentikasi Pengelola")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e3a8a;")
        layout.addWidget(title)

        desc = QLabel("Masukkan password pengelola untuk membuka menu pengaturan, jadwal, dan pustaka lagu.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #475569; font-size: 12px; line-height: 1.4;")
        layout.addWidget(desc)

        # Input Password dengan warna teks dan bullet hitam pekat
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Masukkan password pengelola...")
        self.password_input.setFixedHeight(38)
        self.password_input.setStyleSheet("""
            QLineEdit {
                background-color: #ffffff;
                color: #0f172a;
                border: 1.5px solid #94a3b8;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 15px;
                font-weight: bold;
            }
            QLineEdit:focus {
                border: 2px solid #2563eb;
                background-color: #f8fafc;
            }
        """)
        self.password_input.returnPressed.connect(self._on_login)
        layout.addWidget(self.password_input)

        # Tombol Tampilkan Password tanpa icon di sebelah kiri
        self.show_pw_cb = QPushButton("Tampilkan Password")
        self.show_pw_cb.setCheckable(True)
        self.show_pw_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_pw_cb.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #475569;
                font-size: 11px;
                text-align: left;
                padding: 2px 0;
            }
            QPushButton:hover {
                color: #1d4ed8;
            }
            QPushButton:checked {
                color: #2563eb;
                font-weight: bold;
            }
        """)
        self.show_pw_cb.toggled.connect(self._toggle_show_password)
        layout.addWidget(self.show_pw_cb)

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
                font-weight: 600;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self.login_btn = QPushButton("Masuk")
        self.login_btn.setFixedHeight(34)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        self.login_btn.clicked.connect(self._on_login)
        btn_layout.addWidget(self.login_btn)

        layout.addLayout(btn_layout)
        root_layout.addWidget(card)

    def _toggle_show_password(self, checked: bool):
        if checked:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_pw_cb.setText("Sembunyikan Password")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_pw_cb.setText("Tampilkan Password")

    def _on_login(self):
        password = self.password_input.text()
        if not password:
            self.error_label.setText("Harap masukkan password.")
            self.error_label.setVisible(True)
            self.password_input.setFocus()
            return

        if self.auth.verify_password(password):
            self.accept()
        else:
            self.error_label.setText("Password salah. Silakan coba lagi.")
            self.error_label.setVisible(True)
            self.password_input.selectAll()
            self.password_input.setFocus()


class SetupPasswordDialog(QDialog):
    """Dialog pembuatan atau penggantian password pengelola."""

    def __init__(self, auth_service: AuthService, is_initial: bool = True, parent=None):
        super().__init__(parent)
        self.auth = auth_service
        self.is_initial = is_initial
        self.setWindowTitle("Buat Password Pengelola" if is_initial else "Ganti Password Pengelola")
        self.setFixedSize(390, 360 if not is_initial else 310)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, is_dwm_composition_enabled())
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self._drag_pos = None

        self._setup_ui()
        self._center_dialog()

    def _center_dialog(self):
        parent = self.parent()
        if parent and hasattr(parent, "geometry") and parent.isVisible():
            parent_geo = parent.geometry()
            geo = self.frameGeometry()
            geo.moveCenter(parent_geo.center())
            self.move(geo.topLeft())
        else:
            screen = QApplication.primaryScreen()
            if screen:
                geo = self.frameGeometry()
                geo.moveCenter(screen.availableGeometry().center())
                self.move(geo.topLeft())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("SetupCard")
        card.setStyleSheet("""
            QFrame#SetupCard {
                background-color: #ffffff;
                color: #0f172a;
                border: 2px solid #cbd5e1;
                border-radius: 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #1e293b;
                font-size: 12px;
                font-weight: 600;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        title_text = "Inisialisasi Akun Pengelola" if self.is_initial else "Ganti Password Pengelola"
        title = QLabel(title_text)
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #1e3a8a;")
        layout.addWidget(title)

        desc_text = (
            "Silakan buat password pengelola baru untuk melindungi menu jadwal, pustaka lagu, dan pengaturan aplikasi."
            if self.is_initial else
            "Masukkan password lama dan password baru pengelola."
        )
        desc = QLabel(desc_text)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #475569; font-size: 11px; font-weight: normal; line-height: 1.3;")
        layout.addWidget(desc)

        input_style = """
            QLineEdit {
                background-color: #ffffff;
                color: #0f172a;
                border: 1.5px solid #94a3b8;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QLineEdit:focus {
                border: 2px solid #2563eb;
                background-color: #f8fafc;
            }
        """

        if not self.is_initial:
            layout.addWidget(QLabel("Password Lama:"))
            self.old_pw_input = QLineEdit()
            self.old_pw_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.old_pw_input.setPlaceholderText("Password saat ini...")
            self.old_pw_input.setFixedHeight(34)
            self.old_pw_input.setStyleSheet(input_style)
            layout.addWidget(self.old_pw_input)

        layout.addWidget(QLabel("Password Baru (minimal 4 karakter):"))
        self.new_pw_input = QLineEdit()
        self.new_pw_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pw_input.setPlaceholderText("Password baru...")
        self.new_pw_input.setFixedHeight(34)
        self.new_pw_input.setStyleSheet(input_style)
        layout.addWidget(self.new_pw_input)

        layout.addWidget(QLabel("Konfirmasi Password Baru:"))
        self.confirm_pw_input = QLineEdit()
        self.confirm_pw_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pw_input.setPlaceholderText("Ulangi password baru...")
        self.confirm_pw_input.setFixedHeight(34)
        self.confirm_pw_input.setStyleSheet(input_style)
        layout.addWidget(self.confirm_pw_input)

        # Tombol toggle lihat password tanpa ikon
        self.show_pw_btn = QPushButton("Tampilkan Password")
        self.show_pw_btn.setCheckable(True)
        self.show_pw_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_pw_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #475569;
                font-size: 11px;
                text-align: left;
                padding: 2px 0;
            }
            QPushButton:hover {
                color: #1d4ed8;
            }
            QPushButton:checked {
                color: #2563eb;
                font-weight: bold;
            }
        """)
        self.show_pw_btn.toggled.connect(self._toggle_show_password)
        layout.addWidget(self.show_pw_btn)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #dc2626; font-size: 11px; font-weight: bold;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Batal")
        cancel_btn.setFixedHeight(34)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #334155;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                font-weight: 600;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Simpan Password")
        save_btn.setFixedHeight(34)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)
        root_layout.addWidget(card)

    def _toggle_show_password(self, checked: bool):
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        if hasattr(self, "old_pw_input"):
            self.old_pw_input.setEchoMode(mode)
        self.new_pw_input.setEchoMode(mode)
        self.confirm_pw_input.setEchoMode(mode)
        self.show_pw_btn.setText("Sembunyikan Password" if checked else "Tampilkan Password")

    def _on_save(self):
        new_pw = self.new_pw_input.text()
        confirm_pw = self.confirm_pw_input.text()

        if len(new_pw) < 4:
            self.error_label.setText("Password baru minimal 4 karakter.")
            self.error_label.setVisible(True)
            return

        if new_pw != confirm_pw:
            self.error_label.setText("Konfirmasi password baru tidak cocok.")
            self.error_label.setVisible(True)
            return

        if not self.is_initial:
            old_pw = self.old_pw_input.text()
            if not self.auth.verify_password(old_pw):
                self.error_label.setText("Password lama tidak sesuai.")
                self.error_label.setVisible(True)
                return

        try:
            self.auth.set_password(new_pw)
            QMessageBox.information(
                self,
                "Berhasil",
                "Password pengelola berhasil disimpan.",
            )
            self.accept()
        except Exception as e:
            self.error_label.setText(str(e))
            self.error_label.setVisible(True)
