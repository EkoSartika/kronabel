"""
Pengujian Fitur Windows Autostart dan Graceful Shutdown Komputer.
Memverifikasi:
1. get_recommended_autostart_command mengembalikan string path executable/script yang valid.
2. set_windows_autostart dan is_windows_autostart_enabled dapat memodifikasi dan membaca HKCU Run registry.
3. MainWindow.cleanup mematikan seluruh scheduler, timer, dan audio player tanpa exception.
4. MainWindow.nativeEvent merespons WM_QUERYENDSESSION dan WM_ENDSESSION dengan benar.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication

from src.core.autostart import (
    APP_REG_NAME,
    RUN_REG_KEY,
    get_recommended_autostart_command,
    is_windows_autostart_enabled,
    set_windows_autostart,
)
from src.database.db import DatabaseManager
from src.ui.main_window import MainWindow


@pytest.fixture
def test_db(tmp_path: Path) -> DatabaseManager:
    db_file = tmp_path / "test_autostart.db"
    db = DatabaseManager(db_file)
    db.initialize_database()
    return db


def test_autostart_recommended_command():
    cmd = get_recommended_autostart_command()
    assert isinstance(cmd, str)
    assert len(cmd) > 0
    # Memastikan perintah diawali kutip
    assert cmd.startswith('"')


@pytest.mark.skipif(sys.platform != "win32", reason="Hanya berlaku di lingkungan Windows")
def test_autostart_registry_toggle(monkeypatch):
    import winreg

    store = {}

    class DummyKey:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def fake_open_key(root, subkey, reserved=0, access=winreg.KEY_READ):
        return DummyKey()

    def fake_set_value_ex(key, name, reserved, reg_type, value):
        store[name] = (value, reg_type)

    def fake_delete_value(key, name):
        if name not in store:
            raise FileNotFoundError(name)
        del store[name]

    def fake_query_value_ex(key, name):
        if name not in store:
            raise FileNotFoundError(name)
        return store[name]

    monkeypatch.setattr(winreg, "OpenKey", fake_open_key)
    monkeypatch.setattr(winreg, "CreateKey", fake_open_key)
    monkeypatch.setattr(winreg, "CreateKeyEx", fake_open_key)
    monkeypatch.setattr(winreg, "SetValueEx", fake_set_value_ex)
    monkeypatch.setattr(winreg, "DeleteValue", fake_delete_value)
    monkeypatch.setattr(winreg, "QueryValueEx", fake_query_value_ex)

    # 1. Tes aktivasi
    success_enable = set_windows_autostart(True)
    assert success_enable is True
    assert is_windows_autostart_enabled() is True

    # 2. Tes deaktivasi
    success_disable = set_windows_autostart(False)
    assert success_disable is True
    assert is_windows_autostart_enabled() is False


def test_main_window_cleanup(qapp, test_db: DatabaseManager):
    window = MainWindow(test_db)

    # Pastikan scheduler dan clock berjalan
    assert window.scheduler.is_active is True
    assert window.clock_timer.isActive() is True

    # Panggil cleanup
    window.cleanup()

    # Pastikan scheduler dan clock berhenti
    assert window.scheduler.is_active is False
    assert window.clock_timer.isActive() is False
    assert window._cleaned_up is True

    # Panggilan cleanup kedua harus idempoten (tidak error)
    window.cleanup()
    window.close()
    window.deleteLater()


@pytest.mark.skipif(sys.platform != "win32", reason="Hanya berlaku di lingkungan Windows")
def test_main_window_native_event_shutdown(qapp, test_db: DatabaseManager):
    window = MainWindow(test_db)

    # Buat mock MSG untuk WM_QUERYENDSESSION (0x0011)
    class FakeMsg:
        message = 0x0011
        wParam = 0

    with patch("ctypes.wintypes.MSG.from_address", return_value=FakeMsg):
        handled, ret = window.nativeEvent("windows_generic_MSG", 12345)
        assert handled is True
        assert ret == 1

    # Buat mock MSG untuk WM_ENDSESSION (0x0016)
    class FakeEndMsg:
        message = 0x0016
        wParam = 1

    with patch("ctypes.wintypes.MSG.from_address", return_value=FakeEndMsg):
        with patch.object(QApplication, "quit") as mock_quit:
            handled, ret = window.nativeEvent("windows_generic_MSG", 12345)
            assert handled is True
            assert ret == 0
            assert window._cleaned_up is True
            mock_quit.assert_called_once()

    window.close()
    window.deleteLater()


def test_admin_logout_returns_to_main_window_without_quitting(qapp, test_db: DatabaseManager):
    from PySide6.QtWidgets import QMessageBox

    window = MainWindow(test_db)
    window.show()
    window._open_admin_window()

    assert window.admin_window is not None
    admin_win = window.admin_window
    assert admin_win.isVisible() is True

    with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes), \
         patch.object(QApplication, "quit") as mock_quit:
        admin_win._on_logout()

        # Pastikan aplikasi tidak quit, admin window tertutup, dan main window tetap tampil
        mock_quit.assert_not_called()
        assert window.admin_window is None
        assert window.isVisible() is True
        assert getattr(window, "_cleaned_up", False) is False

    window.close()
    window.deleteLater()


def test_windows_7_compatibility_helpers(qapp, test_db: DatabaseManager, tmp_path: Path):
    """Memverifikasi utilitas kompatibilitas Windows 7 (DWM check, environment setup, dan WinMM audio fallback)."""
    from src.core.win7_compat import (
        WinMMPlayer,
        configure_windows_7_environment,
        is_dwm_composition_enabled,
        is_windows_7_or_8,
    )

    assert isinstance(is_windows_7_or_8(), bool)
    assert isinstance(is_dwm_composition_enabled(), bool)

    configure_windows_7_environment()
    winmm = WinMMPlayer()
    winmm.set_volume(75)
    assert winmm._volume == 75
    assert winmm.is_playing() is False
    winmm.stop()


