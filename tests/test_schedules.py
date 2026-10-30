"""
Pengujian Pengelolaan Jadwal Bel Sekolah (Senin–Sabtu).
Menguji penambahan, normalisasi waktu, pencegahan benturan jadwal, dan penyalinan antarahari.
"""

from __future__ import annotations

import pytest

from src.database.repositories import ProfileRepository, ScheduleRepository
from src.models.models import Schedule, normalize_time, validate_day_of_week


def test_time_normalization():
    assert normalize_time("07:00") == "07:00:00"
    assert normalize_time("07:00:00") == "07:00:00"
    assert normalize_time("12:30") == "12:30:00"

    with pytest.raises(ValueError, match="Format waktu tidak valid"):
        normalize_time("25:00")

    with pytest.raises(ValueError, match="Format waktu tidak valid"):
        normalize_time("07:65")

    with pytest.raises(ValueError, match="Format waktu tidak valid"):
        normalize_time("pagi")


def test_day_of_week_validation():
    valid_days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"]
    for day in valid_days:
        assert validate_day_of_week(day) == day
        assert validate_day_of_week(day.lower()) == day

    with pytest.raises(ValueError, match="Hari tidak valid"):
        validate_day_of_week("Minggu")

    with pytest.raises(ValueError, match="Hari tidak valid"):
        validate_day_of_week("Sunday")


def test_create_and_query_schedules(profile_repo: ProfileRepository, schedule_repo: ScheduleRepository):
    active_profile = profile_repo.get_active()

    schedule1 = Schedule(
        id=None,
        profile_id=active_profile.id,
        day_of_week="Senin",
        bell_time="07:00",
        event_name="Upacara Bendera",
    )
    saved = schedule_repo.create(schedule1)
    assert saved.id is not None
    assert saved.bell_time == "07:00:00"

    schedule2 = Schedule(
        id=None,
        profile_id=active_profile.id,
        day_of_week="Senin",
        bell_time="09:30:00",
        event_name="Istirahat Pertama",
    )
    schedule_repo.create(schedule2)

    # Query per hari
    senin_list = schedule_repo.get_by_profile_and_day(active_profile.id, "Senin")
    assert len(senin_list) == 2
    assert senin_list[0].event_name == "Upacara Bendera"
    assert senin_list[1].event_name == "Istirahat Pertama"

    # Query hari lain (kosong)
    selasa_list = schedule_repo.get_by_profile_and_day(active_profile.id, "Selasa")
    assert len(selasa_list) == 0


def test_schedule_conflict_detection(profile_repo: ProfileRepository, schedule_repo: ScheduleRepository):
    """Memastikan dua jadwal dengan waktu sama di hari dan profil sama ditolak sebagai konflik."""
    active_profile = profile_repo.get_active()

    s1 = Schedule(
        id=None,
        profile_id=active_profile.id,
        day_of_week="Senin",
        bell_time="07:00:00",
        event_name="Masuk Kelas",
    )
    schedule_repo.create(s1)

    s2_conflict = Schedule(
        id=None,
        profile_id=active_profile.id,
        day_of_week="Senin",
        bell_time="07:00:00",
        event_name="Doa Pagi",
    )
    with pytest.raises(ValueError, match="Konflik jadwal"):
        schedule_repo.create(s2_conflict)


def test_copy_day_schedules(profile_repo: ProfileRepository, schedule_repo: ScheduleRepository):
    """Menguji penyalinan jadwal dari Senin ke Selasa."""
    active_profile = profile_repo.get_active()

    schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Senin",
            bell_time="07:00:00",
            event_name="Masuk Pagi",
        )
    )
    schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Senin",
            bell_time="09:45:00",
            event_name="Istirahat",
        )
    )

    copied = schedule_repo.copy_day_schedules(active_profile.id, "Senin", "Selasa", overwrite=False)
    assert copied == 2

    selasa_schedules = schedule_repo.get_by_profile_and_day(active_profile.id, "Selasa")
    assert len(selasa_schedules) == 2
    assert selasa_schedules[0].bell_time == "07:00:00"
    assert selasa_schedules[1].bell_time == "09:45:00"


def test_toggle_schedule_enabled(profile_repo: ProfileRepository, schedule_repo: ScheduleRepository):
    active_profile = profile_repo.get_active()
    s = schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Rabu",
            bell_time="08:00:00",
            event_name="Pelajaran 1",
            is_enabled=True,
        )
    )
    assert s.is_enabled is True

    schedule_repo.toggle_enabled(s.id, False)
    reloaded = schedule_repo.get_by_id(s.id)
    assert reloaded.is_enabled is False
