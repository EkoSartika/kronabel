"""
Layanan Waktu (Clock Service) Bel Otomatis Sekolah.
Menyediakan abstraksi waktu lokal Windows dan clock simulasi untuk pengujian deterministik.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional

from src.core.config import DAYS_OF_WEEK

DAY_NAMES_MAP = {
    "Monday": "Senin",
    "Tuesday": "Selasa",
    "Wednesday": "Rabu",
    "Thursday": "Kamis",
    "Friday": "Jumat",
    "Saturday": "Sabtu",
    "Sunday": "Minggu",
}


class IClock(ABC):
    """Antarmuka penyedia waktu."""

    @abstractmethod
    def now(self) -> datetime:
        """Mengembalikan datetime saat ini."""
        pass

    def today_str(self) -> str:
        """Mengembalikan tanggal hari ini dalam format YYYY-MM-DD."""
        return self.now().strftime("%Y-%m-%d")

    def time_str(self) -> str:
        """Mengembalikan waktu saat ini dalam format HH:MM:SS."""
        return self.now().strftime("%H:%M:%S")

    def day_name(self) -> str:
        """Mengembalikan nama hari saat ini dalam bahasa Indonesia (Senin–Minggu)."""
        english_day = self.now().strftime("%A")
        return DAY_NAMES_MAP.get(english_day, english_day)

    def is_school_day(self) -> bool:
        """Memeriksa apakah hari saat ini adalah hari sekolah (Senin–Sabtu)."""
        return self.day_name() in DAYS_OF_WEEK


class SystemClock(IClock):
    """Penyedia waktu aktual sistem operasi Windows."""

    def now(self) -> datetime:
        return datetime.now()


class SimulatedClock(IClock):
    """Penyedia waktu simulasi untuk pengujian unit dan skenario waktu tertentu."""

    def __init__(self, initial_time: Optional[datetime] = None):
        self._current_time = initial_time if initial_time else datetime(2026, 10, 28, 7, 0, 0)

    def now(self) -> datetime:
        return self._current_time

    def set_time(self, new_time: datetime) -> None:
        """Mengatur waktu simulasi ke waktu tertentu."""
        self._current_time = new_time

    def advance(self, seconds: int = 1) -> None:
        """Memajukan waktu simulasi sebanyak n detik."""
        self._current_time += timedelta(seconds=seconds)

    def advance_minutes(self, minutes: int = 1) -> None:
        """Memajukan waktu simulasi sebanyak n menit."""
        self._current_time += timedelta(minutes=minutes)

    def advance_days(self, days: int = 1) -> None:
        """Memajukan waktu simulasi sebanyak n hari."""
        self._current_time += timedelta(days=days)
