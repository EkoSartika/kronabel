"""
Entry Point Aplikasi Desktop Bel Otomatis Sekolah (Windows)
Menginisialisasi QApplication, koneksi database, single instance check, dan jendela utama.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox

# Pastikan root direktori proyek ada dalam sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.core.config import APP_DISPLAY_NAME, APP_NAME, get_assets_dir, get_user_data_dir
from src.core.win7_compat import configure_windows_7_environment
from src.database.db import DatabaseManager
from src.ui.dialog_helper import patch_qmessagebox
from src.ui.main_window import MainWindow

# Konfigurasi Logging
LOG_FILE = get_user_data_dir() / "app.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("main")


class SingleInstanceApp:
    """Mencegah dua instance aplikasi berjalan secara bersamaan menggunakan QLocalServer."""

    def __init__(self, app_id: str):
        self.app_id = app_id
        self.server: QLocalServer | None = None

    def is_running(self) -> bool:
        # Coba koneksi ke server yang mungkin sudah ada
        socket = QLocalSocket()
        socket.connectToServer(self.app_id)
        if socket.waitForConnected(500):
            socket.close()
            return True

        # Jika tidak ada instance aktif, buka server lokal
        self.server = QLocalServer()
        # Bersihkan server lama jika crash sebelumnya
        self.server.removeServer(self.app_id)
        self.server.listen(self.app_id)
        return False

    def cleanup(self) -> None:
        if self.server:
            self.server.close()
            self.server.removeServer(self.app_id)


def main() -> int:
    logger.info("Memulai aplikasi %s", APP_DISPLAY_NAME)

    # Konfigurasi kompatibilitas grafis & DPI untuk Windows 7 / 8 / 10 / 11
    configure_windows_7_environment()

    # Inisialisasi QApplication
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    # Jangan keluar otomatis saat dialog/jendela anak ditutup karena aplikasi memiliki System Tray
    # dan MainWindow menggunakan Qt.Tool; keluar aplikasi dikontrol eksplisit saat MainWindow ditutup / Quit
    app.setQuitOnLastWindowClosed(False)
    patch_qmessagebox()

    icon_path = get_assets_dir() / "app_icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Global Stylesheet untuk QMessageBox dan QDialog agar kontras tinggi & terbaca jelas di segala tema Windows
    app.setStyleSheet("""
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
        QMessageBox QPushButton:hover {
            background-color: #1d4ed8;
            border-color: #1e40af;
            color: #ffffff;
        }
        QMessageBox QPushButton:focus {
            background-color: #2563eb;
            color: #ffffff;
            border: 2px solid #60a5fa;
            outline: none;
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
            background-color: #e2e8f0;
            color: #0f172a;
            border: 2px solid #2563eb;
        }
        QDialog {
            background-color: #ffffff;
            color: #0f172a;
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
    """)

    # Proteksi Single Instance
    lock_name = f"{APP_NAME}_SingleInstanceLock"
    custom_data_dir = os.environ.get("BEL_APP_DATA_DIR")
    if custom_data_dir:
        import hashlib
        h = hashlib.md5(custom_data_dir.encode("utf-8")).hexdigest()[:8]
        lock_name = f"{lock_name}_{h}"

    instance_guard = SingleInstanceApp(lock_name)
    if instance_guard.is_running():
        logger.warning("Upaya membuka instance kedua dibatalkan.")
        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            QMessageBox.warning(
                None,
                "Aplikasi Sedang Berjalan",
                f"Aplikasi {APP_DISPLAY_NAME} sudah berjalan di sistem ini.",
            )
        return 0

    try:
        # Inisialisasi Database
        db = DatabaseManager()
        db.initialize_database()
        db.seed_default_audio_templates_if_needed()
        logger.info("Database berhasil diinisialisasi pada: %s", db.db_path)

        # Buka Jendela Utama
        window = MainWindow(db)

        # Integrasi Manajemen Sesi & Shutdown Windows (Mematikan aplikasi saat komputer dimatikan)
        def handle_commit_data(manager):
            logger.info("Windows commitDataRequest diterima (komputer sedang dimatikan/logoff)...")
            try:
                if hasattr(manager, "allowsInteraction") and manager.allowsInteraction():
                    manager.release()
            except Exception:
                pass
            window.cleanup()
            app.quit()

        def handle_save_state(manager):
            logger.info("Windows saveStateRequest diterima...")
            window.cleanup()

        def handle_about_to_quit():
            logger.info("Aplikasi sedang ditutup (aboutToQuit)...")
            window.cleanup()

        app.commitDataRequest.connect(handle_commit_data)
        app.saveStateRequest.connect(handle_save_state)
        app.aboutToQuit.connect(handle_about_to_quit)

        window.show()

        exit_code = app.exec()
        logger.info("Aplikasi ditutup dengan kode: %d", exit_code)
        return exit_code
    except Exception as e:
        logger.exception("Terjadi kesalahan fatal saat menjalankan aplikasi: %s", e)
        QMessageBox.critical(
            None,
            "Kesalahan Fatal",
            f"Terjadi kesalahan saat memulai aplikasi:\n\n{e}",
        )
        return 1
    finally:
        instance_guard.cleanup()


if __name__ == "__main__":
    sys.exit(main())
