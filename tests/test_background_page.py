import pytest
from pathlib import Path
from PySide6.QtGui import QImage, QColor

from src.database.db import DatabaseManager
from src.database.repositories import SettingsRepository
from src.ui.background_page import BackgroundPage
from src.ui.main_window import MainWindow


def test_background_page_load_and_reset(qapp, temp_db, tmp_path):
    """Menguji inisialisasi BackgroundPage, upload gambar, dan reset default."""
    page = BackgroundPage(temp_db)
    page.show()
    qapp.processEvents()

    settings_repo = SettingsRepository(temp_db)
    # Awalnya belum ada kustomisasi
    assert settings_repo.get("clock_background_path", "") == ""
    assert settings_repo.get("main_background_path", "") == ""

    # Buat file gambar contoh
    dummy_img = tmp_path / "test_clock_bg.png"
    img = QImage(440, 126, QImage.Format.Format_RGB32)
    img.fill(QColor(10, 50, 40))
    img.save(str(dummy_img))

    # Simpan sebagai background jam
    settings_repo.set("clock_background_path", str(dummy_img))
    page.refresh_data()
    qapp.processEvents()

    assert "kustom" in page.lbl_clock_status.text().lower()

    # Reset ke bawaan jam
    page._reset_clock_bg()
    assert settings_repo.get("clock_background_path", "") == ""
    assert "bawaan" in page.lbl_clock_status.text().lower()

    page.close()


def test_main_window_apply_custom_background(qapp, temp_db, tmp_path):
    """Menguji bahwa MainWindow memperbarui style saat custom background diterapkan."""
    main_win = MainWindow(temp_db)
    main_win.show()
    qapp.processEvents()

    # Buat dummy background
    clock_file = tmp_path / "custom_clock.png"
    main_file = tmp_path / "custom_main.png"
    img1 = QImage(440, 126, QImage.Format.Format_RGB32)
    img1.fill(QColor(20, 20, 20))
    img1.save(str(clock_file))

    img2 = QImage(740, 380, QImage.Format.Format_RGB32)
    img2.fill(QColor(30, 30, 30))
    img2.save(str(main_file))

    # Terapkan
    main_win.settings_repo.set("clock_background_path", str(clock_file))
    main_win.settings_repo.set("main_background_path", str(main_file))

    main_win.apply_backgrounds()
    qapp.processEvents()

    assert clock_file.as_posix() in main_win.clock_box.styleSheet()
    assert main_file.as_posix() in main_win.central_widget_ref.styleSheet()

    # Reset dengan mengosongkan path
    main_win.settings_repo.set("clock_background_path", "")
    main_win.settings_repo.set("main_background_path", "")
    main_win.apply_backgrounds()
    qapp.processEvents()

    assert clock_file.as_posix() not in main_win.clock_box.styleSheet()
    assert main_file.as_posix() not in main_win.central_widget_ref.styleSheet()

    main_win.close()
