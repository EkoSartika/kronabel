"""
Pengujian Kerangka Antarmuka Jendela Utama (PySide6).
Menguji inisialisasi MainWindow dan pembaruan label profil aktif.
"""

from __future__ import annotations

import os
import sys

import pytest
from PySide6.QtWidgets import QApplication

from src.database.db import DatabaseManager
from src.ui.main_window import MainWindow

# Gunakan platform offscreen untuk eksekusi tanpa layar fisik
os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def test_main_window_initialization(qapp, temp_db: DatabaseManager):
    """Memastikan jendela utama dapat dibuat sebagai panel kompak dengan komponen lengkap."""
    window = MainWindow(temp_db)
    assert window is not None
    assert "KRONABEL" in window.windowTitle()
    assert window.width() <= 750
    assert window.height() <= 400
    assert window.clock_label is not None
    assert window.btn_on is not None
    assert window.btn_off is not None
    assert window.btn_setting is not None
    assert window.schedule_table is not None
    assert window.stacked_widget.count() >= 5
    assert "Reguler" in window.profile_badge.text()
    window.close()
