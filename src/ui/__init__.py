"""Modul UI Bel Otomatis Sekolah"""
from src.ui.audio_page import AudioPage
from src.ui.dashboard import DashboardPage
from src.ui.history_page import HistoryPage
from src.ui.main_window import MainWindow
from src.ui.profile_page import ProfilePage
from src.ui.schedule_page import SchedulePage
from src.ui.settings_page import SettingsPage
from src.ui.background_page import BackgroundPage

__all__ = [
    "MainWindow",
    "DashboardPage",
    "SchedulePage",
    "ProfilePage",
    "AudioPage",
    "HistoryPage",
    "SettingsPage",
    "BackgroundPage",
]
