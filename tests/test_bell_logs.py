"""
Pengujian Riwayat Pembunyian Bel dan Idempotensi.
Memvalidasi foreign key schedule, logging bel manual, dan pemeriksaan idempotensi.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.database.repositories import BellLogRepository, ProfileRepository, ScheduleRepository
from src.models.models import BellLog, Schedule


def test_add_manual_bell_log(bell_log_repo: BellLogRepository):
    """Bel manual memiliki schedule_id = None dan scheduled_at = None."""
    now_str = datetime.now().isoformat()
    log = BellLog(
        id=None,
        schedule_id=None,
        scheduled_at=None,
        executed_at=now_str,
        event_name="Bel Manual Darurat",
        execution_mode="MANUAL",
        status="completed",
        message="Dibunyikan manual oleh operator.",
    )
    log_id = bell_log_repo.add_log(log)
    assert log_id > 0

    logs = bell_log_repo.get_logs()
    assert len(logs) == 1
    assert logs[0].event_name == "Bel Manual Darurat"
    assert logs[0].execution_mode == "MANUAL"
    assert logs[0].schedule_id is None


def test_add_scheduled_bell_log(
    profile_repo: ProfileRepository,
    schedule_repo: ScheduleRepository,
    bell_log_repo: BellLogRepository,
):
    """Bel otomatis terhubung dengan foreign key schedule yang valid."""
    active_profile = profile_repo.get_active()
    schedule = schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Senin",
            bell_time="07:00:00",
            event_name="Bel Masuk",
        )
    )

    now_str = datetime.now().isoformat()
    log = BellLog(
        id=None,
        schedule_id=schedule.id,
        scheduled_at="2026-10-28T07:00:00",
        executed_at=now_str,
        event_name="Bel Masuk",
        execution_mode="OTOMATIS",
        status="completed",
        message="Pemutaran otomatis berhasil.",
    )
    log_id = bell_log_repo.add_log(log)
    assert log_id > 0

    logs = bell_log_repo.get_logs()
    assert len(logs) >= 1
    target_log = [l for l in logs if l.id == log_id][0]
    assert target_log.schedule_id == schedule.id
    assert target_log.status == "completed"


def test_idempotency_verification(
    profile_repo: ProfileRepository,
    schedule_repo: ScheduleRepository,
    bell_log_repo: BellLogRepository,
):
    """Memastikan sistem dapat mendeteksi jadwal yang sudah dieksekusi pada hari ini."""
    today_date = "2026-10-28"
    active_profile = profile_repo.get_active()

    schedule = schedule_repo.create(
        Schedule(
            id=None,
            profile_id=active_profile.id,
            day_of_week="Rabu",
            bell_time="07:15:00",
            event_name="Tanda Masuk",
        )
    )

    # Belum dieksekusi
    assert bell_log_repo.is_schedule_executed_today(schedule.id, today_date) is False

    # Tambahkan log eksekusi
    bell_log_repo.add_log(
        BellLog(
            id=None,
            schedule_id=schedule.id,
            scheduled_at=f"{today_date}T07:15:00",
            executed_at=f"{today_date}T07:15:01",
            event_name="Tanda Masuk",
            execution_mode="OTOMATIS",
            status="completed",
            message=None,
        )
    )

    # Harus bernilai True setelah dieksekusi
    assert bell_log_repo.is_schedule_executed_today(schedule.id, today_date) is True
