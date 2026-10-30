"""
Model data Bel Otomatis Sekolah
Definisi dataclass dan validasi untuk entitas sistem.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.core.config import DAYS_OF_WEEK

# Regex untuk validasi format waktu HH:MM:SS atau HH:MM
TIME_PATTERN_HHMMSS = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d$")
TIME_PATTERN_HHMM = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def normalize_time(time_str: str) -> str:
    """
    Menormalkan format waktu menjadi HH:MM:SS.
    Menerima HH:MM atau HH:MM:SS.
    Menimbulkan ValueError jika format tidak valid.
    """
    time_str = time_str.strip()
    if TIME_PATTERN_HHMMSS.match(time_str):
        return time_str
    if TIME_PATTERN_HHMM.match(time_str):
        return f"{time_str}:00"
    raise ValueError(f"Format waktu tidak valid: '{time_str}'. Gunakan format HH:MM atau HH:MM:SS (contoh: 07:00:00).")


validate_time_format = normalize_time


def validate_day_of_week(day: str) -> str:
    """Memvalidasi dan mengembalikan nama hari yang dinormalisasi."""
    day_clean = day.strip().capitalize()
    for valid_day in DAYS_OF_WEEK:
        if valid_day.lower() == day_clean.lower():
            return valid_day
    raise ValueError(f"Hari tidak valid: '{day}'. Pilihan yang didukung: {', '.join(DAYS_OF_WEEK)}.")


@dataclass
class Profile:
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    is_active: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def validate(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Nama profil tidak boleh kosong.")


@dataclass
class Schedule:
    id: Optional[int] = None
    profile_id: int = 0
    day_of_week: str = "Senin"
    bell_time: str = "07:00"
    event_name: str = ""
    audio_id: Optional[int] = None
    is_enabled: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    # Data relasi untuk kemudahan presentasi
    audio_name: Optional[str] = None
    audio_path: Optional[str] = None
    audio_code: Optional[str] = None

    def validate(self) -> None:
        if not self.event_name or not self.event_name.strip():
            raise ValueError("Nama kegiatan bel tidak boleh kosong.")
        self.day_of_week = validate_day_of_week(self.day_of_week)
        self.bell_time = normalize_time(self.bell_time)


@dataclass
class AudioFile:
    id: Optional[int] = None
    name: str = ""
    stored_path: str = ""
    original_filename: str = ""
    duration_seconds: float = 0.0
    created_at: Optional[str] = None
    code: str = ""

    def validate(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Nama label audio tidak boleh kosong.")
        if not self.stored_path or not self.stored_path.strip():
            raise ValueError("Path penyimpanan audio tidak boleh kosong.")
        if self.code:
            self.code = self.code.strip().upper()


@dataclass
class BellLog:
    id: Optional[int] = None
    schedule_id: Optional[int] = None
    scheduled_at: Optional[str] = None
    executed_at: str = ""
    event_name: str = ""
    execution_mode: str = "OTOMATIS"  # "OTOMATIS" atau "MANUAL"
    status: str = "completed"         # "requested", "playing", "completed", "failed", "missed", "interrupted"
    message: Optional[str] = None


@dataclass
class AppSetting:
    key: str
    value: str
