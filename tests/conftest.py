"""
Konfigurasi dan Fixture Pytest untuk Pengujian Bel Otomatis Sekolah.
Menyediakan database terisolasi untuk setiap pengujian dan mock dialog modal GUI.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

import pytest
from PySide6.QtWidgets import QMessageBox

from src.database.db import DatabaseManager
from src.database.repositories import (
    AudioRepository,
    BellLogRepository,
    ProfileRepository,
    ScheduleRepository,
    SettingsRepository,
)

# Set headless platform untuk pengujian Qt
os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(autouse=True)
def mock_qmessagebox(monkeypatch):
    """Mencegah QMessageBox memblokir atau memicu error GUI modal di sesi pengujian otomatis."""
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)


@pytest.fixture(scope="session")
def qapp():
    """Menyediakan instance QApplication untuk pengujian komponen UI."""
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
    app.processEvents()


@pytest.fixture
def temp_db(tmp_path: Path) -> Generator[DatabaseManager, None, None]:
    """Menyediakan instance DatabaseManager dengan file database terisolasi per sesi tes."""
    test_db_path = tmp_path / "test_bel_sekolah.db"
    db = DatabaseManager(db_path=test_db_path)
    db.initialize_database()
    yield db


@pytest.fixture
def db_manager(temp_db: DatabaseManager) -> DatabaseManager:
    """Alias untuk temp_db agar sesuai dengan penamaan db_manager."""
    return temp_db


@pytest.fixture
def profile_repo(temp_db: DatabaseManager) -> ProfileRepository:
    return ProfileRepository(temp_db)


@pytest.fixture
def schedule_repo(temp_db: DatabaseManager) -> ScheduleRepository:
    return ScheduleRepository(temp_db)


@pytest.fixture
def audio_repo(temp_db: DatabaseManager) -> AudioRepository:
    return AudioRepository(temp_db)


@pytest.fixture
def bell_log_repo(temp_db: DatabaseManager) -> BellLogRepository:
    return BellLogRepository(temp_db)


@pytest.fixture
def settings_repo(temp_db: DatabaseManager) -> SettingsRepository:
    return SettingsRepository(temp_db)
