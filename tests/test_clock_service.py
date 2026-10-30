"""
Pengujian Unit Layanan Waktu (Clock Service).
Menguji IClock, SystemClock, dan SimulatedClock.
"""

from __future__ import annotations

from datetime import datetime

from src.services.clock_service import SimulatedClock, SystemClock


def test_system_clock():
    clock = SystemClock()
    now = clock.now()
    assert isinstance(now, datetime)
    assert len(clock.today_str().split("-")) == 3
    assert len(clock.time_str().split(":")) == 3
    assert clock.day_name() in ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def test_simulated_clock_advancement():
    # Mulai pada Rabu, 28 Oktober 2026 pukul 07:00:00
    base_dt = datetime(2026, 10, 28, 7, 0, 0)
    clock = SimulatedClock(base_dt)

    assert clock.day_name() == "Rabu"
    assert clock.time_str() == "07:00:00"
    assert clock.is_school_day() is True

    # Majukan 30 detik
    clock.advance(30)
    assert clock.time_str() == "07:00:30"

    # Majukan 45 menit
    clock.advance_minutes(45)
    assert clock.time_str() == "07:45:30"

    # Majukan 4 hari (Rabu -> Kamis -> Jumat -> Sabtu -> Minggu)
    clock.advance_days(4)
    assert clock.day_name() == "Minggu"
    assert clock.is_school_day() is False
