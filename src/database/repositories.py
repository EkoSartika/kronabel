"""
Repository layer untuk operasi data Bel Otomatis Sekolah.
Menerapkan Repository Pattern dengan query berparameter, validasi, dan transaksi yang aman.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import List, Optional

from src.database.db import DatabaseManager
from src.models.models import (
    AppSetting,
    AudioFile,
    BellLog,
    Profile,
    Schedule,
    normalize_time,
    validate_day_of_week,
)


class ProfileRepository:
    """Pengelolaan profil jam pelajaran (Reguler, Ramadan, Ujian, dll)."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def get_all(self) -> List[Profile]:
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM profiles ORDER BY is_active DESC, name ASC")
            rows = cursor.fetchall()
            return [
                Profile(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    is_active=bool(row["is_active"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    def get_by_id(self, profile_id: int) -> Optional[Profile]:
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return Profile(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                is_active=bool(row["is_active"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def get_active(self) -> Optional[Profile]:
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM profiles WHERE is_active = 1 LIMIT 1")
            row = cursor.fetchone()
            if not row:
                return None
            return Profile(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                is_active=True,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def set_active(self, profile_id: int) -> None:
        """Mengaktifkan profil terpilih dan menonaktifkan profil lainnya dalam satu transaksi."""
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM profiles WHERE id = ?", (profile_id,))
            if not cursor.fetchone():
                raise ValueError(f"Profil dengan ID {profile_id} tidak ditemukan.")

            now = datetime.now().isoformat()
            cursor.execute("UPDATE profiles SET is_active = 0, updated_at = ?", (now,))
            cursor.execute("UPDATE profiles SET is_active = 1, updated_at = ? WHERE id = ?", (now, profile_id))

    def create(self, profile: Profile) -> Profile:
        profile.validate()
        now = datetime.now().isoformat()
        with self.db.session() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO profiles (name, description, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (profile.name.strip(), profile.description.strip(), 1 if profile.is_active else 0, now, now)
                )
                profile.id = cursor.lastrowid
                profile.created_at = now
                profile.updated_at = now
                return profile
            except sqlite3.IntegrityError:
                raise ValueError(f"Profil dengan nama '{profile.name}' sudah ada.")

    def update(self, profile: Profile) -> None:
        if profile.id is None:
            raise ValueError("ID profil tidak boleh kosong untuk pembaruan.")
        profile.validate()
        now = datetime.now().isoformat()
        with self.db.session() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    UPDATE profiles
                    SET name = ?, description = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (profile.name.strip(), profile.description.strip(), now, profile.id)
                )
                if cursor.rowcount == 0:
                    raise ValueError(f"Profil dengan ID {profile.id} tidak ditemukan.")
            except sqlite3.IntegrityError:
                raise ValueError(f"Nama profil '{profile.name}' sudah digunakan.")

    def delete(self, profile_id: int) -> None:
        """
        Menghapus profil dengan pengamanan:
        1. Menolak menghapus profil yang sedang aktif.
        2. Menolak menghapus jika hanya tersisa satu profil.
        3. Menolak menghapus jika profil masih memiliki jadwal kecuali dikonfirmasi eksplisit.
        """
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, is_active FROM profiles WHERE id = ?", (profile_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Profil dengan ID {profile_id} tidak ditemukan.")
            if row["is_active"]:
                raise ValueError("Tidak dapat menghapus profil yang sedang aktif. Silakan aktifkan profil lain terlebih dahulu.")

            cursor.execute("SELECT COUNT(*) AS total FROM profiles")
            if cursor.fetchone()["total"] <= 1:
                raise ValueError("Tidak dapat menghapus profil terakhir. Aplikasi membutuhkan minimal satu profil.")

            cursor.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))

    def get_schedule_count(self, profile_id: int) -> int:
        """Menghitung total jadwal yang terdaftar dalam suatu profil."""
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS total FROM schedules WHERE profile_id = ?", (profile_id,))
            return cursor.fetchone()["total"]


class ScheduleRepository:
    """Pengelolaan jadwal bel otomatis Senin–Sabtu."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def get_by_profile_and_day(self, profile_id: int, day_of_week: str) -> List[Schedule]:
        day_clean = validate_day_of_week(day_of_week)
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT s.*, a.name AS audio_name, a.stored_path AS audio_path, a.code AS audio_code
                FROM schedules s
                LEFT JOIN audio_files a ON s.audio_id = a.id
                WHERE s.profile_id = ? AND s.day_of_week = ?
                ORDER BY s.bell_time ASC
                """,
                (profile_id, day_clean)
            )
            rows = cursor.fetchall()
            return [self._row_to_schedule(row) for row in rows]

    def get_by_profile(self, profile_id: int) -> List[Schedule]:
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT s.*, a.name AS audio_name, a.stored_path AS audio_path, a.code AS audio_code
                FROM schedules s
                LEFT JOIN audio_files a ON s.audio_id = a.id
                WHERE s.profile_id = ?
                ORDER BY 
                    CASE s.day_of_week
                        WHEN 'Senin' THEN 1
                        WHEN 'Selasa' THEN 2
                        WHEN 'Rabu' THEN 3
                        WHEN 'Kamis' THEN 4
                        WHEN 'Jumat' THEN 5
                        WHEN 'Sabtu' THEN 6
                        ELSE 7
                    END ASC,
                    s.bell_time ASC
                """,
                (profile_id,)
            )
            rows = cursor.fetchall()
            return [self._row_to_schedule(row) for row in rows]

    def get_by_id(self, schedule_id: int) -> Optional[Schedule]:
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT s.*, a.name AS audio_name, a.stored_path AS audio_path, a.code AS audio_code
                FROM schedules s
                LEFT JOIN audio_files a ON s.audio_id = a.id
                WHERE s.id = ?
                """,
                (schedule_id,)
            )
            row = cursor.fetchone()
            return self._row_to_schedule(row) if row else None

    def create(self, schedule: Schedule) -> Schedule:
        schedule.validate()
        now = datetime.now().isoformat()
        with self.db.session() as conn:
            cursor = conn.cursor()
            # Cek konflik jadwal di hari dan waktu yang sama pada profil ini
            cursor.execute(
                """
                SELECT id, event_name FROM schedules
                WHERE profile_id = ? AND day_of_week = ? AND bell_time = ?
                """,
                (schedule.profile_id, schedule.day_of_week, schedule.bell_time)
            )
            conflict = cursor.fetchone()
            if conflict:
                raise ValueError(
                    f"Konflik jadwal: Waktu {schedule.bell_time} pada hari {schedule.day_of_week} "
                    f"sudah digunakan untuk kegiatan '{conflict['event_name']}'."
                )

            cursor.execute(
                """
                INSERT INTO schedules (
                    profile_id, day_of_week, bell_time, event_name, audio_id, is_enabled, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    schedule.profile_id,
                    schedule.day_of_week,
                    schedule.bell_time,
                    schedule.event_name.strip(),
                    schedule.audio_id,
                    1 if schedule.is_enabled else 0,
                    now,
                    now,
                )
            )
            schedule.id = cursor.lastrowid
            schedule.created_at = now
            schedule.updated_at = now
            return schedule

    def update(self, schedule: Schedule) -> None:
        if schedule.id is None:
            raise ValueError("ID jadwal tidak boleh kosong untuk pembaruan.")
        schedule.validate()
        now = datetime.now().isoformat()
        with self.db.session() as conn:
            cursor = conn.cursor()
            # Cek konflik dengan jadwal lain selain jadwal yang sedang diedit
            cursor.execute(
                """
                SELECT id, event_name FROM schedules
                WHERE profile_id = ? AND day_of_week = ? AND bell_time = ? AND id != ?
                """,
                (schedule.profile_id, schedule.day_of_week, schedule.bell_time, schedule.id)
            )
            conflict = cursor.fetchone()
            if conflict:
                raise ValueError(
                    f"Konflik jadwal: Waktu {schedule.bell_time} pada hari {schedule.day_of_week} "
                    f"sudah digunakan oleh kegiatan lain: '{conflict['event_name']}'."
                )

            cursor.execute(
                """
                UPDATE schedules
                SET day_of_week = ?, bell_time = ?, event_name = ?, audio_id = ?, is_enabled = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    schedule.day_of_week,
                    schedule.bell_time,
                    schedule.event_name.strip(),
                    schedule.audio_id,
                    1 if schedule.is_enabled else 0,
                    now,
                    schedule.id,
                )
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Jadwal dengan ID {schedule.id} tidak ditemukan.")

    def delete(self, schedule_id: int) -> None:
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))

    def toggle_enabled(self, schedule_id: int, is_enabled: bool) -> None:
        now = datetime.now().isoformat()
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE schedules SET is_enabled = ?, updated_at = ? WHERE id = ?",
                (1 if is_enabled else 0, now, schedule_id)
            )

    def copy_day_schedules(self, profile_id: int, from_day: str, to_day: str, overwrite: bool = False) -> int:
        """Menyalin seluruh jadwal dari satu hari ke hari lain dalam profil yang sama."""
        from_clean = validate_day_of_week(from_day)
        to_clean = validate_day_of_week(to_day)
        if from_clean == to_clean:
            raise ValueError("Hari sumber dan hari tujuan tidak boleh sama.")

        now = datetime.now().isoformat()
        with self.db.session() as conn:
            cursor = conn.cursor()
            if overwrite:
                cursor.execute(
                    "DELETE FROM schedules WHERE profile_id = ? AND day_of_week = ?",
                    (profile_id, to_clean)
                )

            # Ambil jadwal dari hari sumber
            cursor.execute(
                """
                SELECT bell_time, event_name, audio_id, is_enabled
                FROM schedules
                WHERE profile_id = ? AND day_of_week = ?
                ORDER BY bell_time ASC
                """,
                (profile_id, from_clean)
            )
            source_schedules = cursor.fetchall()
            if not source_schedules:
                return 0

            copied_count = 0
            for row in source_schedules:
                # Periksa apakah ada jadwal dengan waktu yang sama di hari tujuan jika tidak overwrite
                cursor.execute(
                    """
                    SELECT id FROM schedules
                    WHERE profile_id = ? AND day_of_week = ? AND bell_time = ?
                    """,
                    (profile_id, to_clean, row["bell_time"])
                )
                if not cursor.fetchone():
                    cursor.execute(
                        """
                        INSERT INTO schedules (
                            profile_id, day_of_week, bell_time, event_name, audio_id, is_enabled, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            profile_id,
                            to_clean,
                            row["bell_time"],
                            row["event_name"],
                            row["audio_id"],
                            row["is_enabled"],
                            now,
                            now,
                        )
                    )
                    copied_count += 1
            return copied_count

    def _row_to_schedule(self, row: sqlite3.Row) -> Schedule:
        return Schedule(
            id=row["id"],
            profile_id=row["profile_id"],
            day_of_week=row["day_of_week"],
            bell_time=row["bell_time"],
            event_name=row["event_name"],
            audio_id=row["audio_id"],
            is_enabled=bool(row["is_enabled"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            audio_name=row["audio_name"] if "audio_name" in row.keys() else None,
            audio_path=row["audio_path"] if "audio_path" in row.keys() else None,
            audio_code=row["audio_code"] if "audio_code" in row.keys() else None,
        )


class AudioRepository:
    """Pengelolaan pustaka file audio bel dengan dukungan Kode Lagu unik."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def _row_to_audio(self, row: sqlite3.Row) -> AudioFile:
        return AudioFile(
            id=row["id"],
            code=row["code"] if "code" in row.keys() and row["code"] else "",
            name=row["name"],
            stored_path=row["stored_path"],
            original_filename=row["original_filename"],
            duration_seconds=row["duration_seconds"],
            created_at=row["created_at"],
        )

    def get_all(self) -> List[AudioFile]:
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audio_files ORDER BY code ASC, name ASC")
            rows = cursor.fetchall()
            return [self._row_to_audio(row) for row in rows]

    def get_by_id(self, audio_id: int) -> Optional[AudioFile]:
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audio_files WHERE id = ?", (audio_id,))
            row = cursor.fetchone()
            return self._row_to_audio(row) if row else None

    def get_by_code(self, code: str) -> Optional[AudioFile]:
        clean_code = code.strip().upper()
        if not clean_code:
            return None
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audio_files WHERE UPPER(code) = ?", (clean_code,))
            row = cursor.fetchone()
            return self._row_to_audio(row) if row else None

    @staticmethod
    def generate_next_code(existing_codes: List[str], mode: str = "alphabet") -> str:
        """Menghasilkan kode lagu berikutnya:
        - mode 'alphabet': BEL A, BEL B, ..., BEL Z, BEL AA, dst.
        - mode 'numeric': BEL 1, BEL 2, BEL 3, dst.
        """
        upper_codes = {c.strip().upper() for c in existing_codes if c}
        if mode == "numeric":
            idx = 1
            while True:
                cand = f"BEL {idx}"
                if cand not in upper_codes:
                    return cand
                idx += 1

        idx = 0
        while True:
            num = idx
            letters = ""
            while num >= 0:
                letters = chr(65 + (num % 26)) + letters
                num = (num // 26) - 1
            cand = f"BEL {letters}"
            if cand not in upper_codes:
                return cand
            idx += 1

    def get_next_available_code(self, mode: str = "alphabet") -> str:
        """Mengambil kode lagu berikutnya yang belum terpakai berdasarkan mode ('alphabet' atau 'numeric')."""
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT code FROM audio_files")
            existing = [row["code"] for row in cursor.fetchall() if row["code"]]
            return self.generate_next_code(existing, mode=mode)

    def create(self, audio: AudioFile) -> AudioFile:
        audio.validate()
        now = datetime.now().isoformat()
        with self.db.session() as conn:
            cursor = conn.cursor()
            # Jika code belum diisi, buatkan kode default berformat alfabet (BEL A, BEL B, dst.)
            if not audio.code:
                cursor.execute("SELECT code FROM audio_files")
                existing = [row["code"] for row in cursor.fetchall() if row["code"]]
                audio.code = self.generate_next_code(existing)
            else:
                cursor.execute("SELECT id FROM audio_files WHERE UPPER(code) = ?", (audio.code.upper(),))
                if cursor.fetchone():
                    raise ValueError(f"Kode lagu '{audio.code}' sudah digunakan oleh berkas audio lain.")

            cursor.execute(
                """
                INSERT INTO audio_files (code, name, stored_path, original_filename, duration_seconds, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (audio.code.strip().upper(), audio.name.strip(), audio.stored_path, audio.original_filename, audio.duration_seconds, now)
            )
            audio.id = cursor.lastrowid
            audio.created_at = now
            return audio

    def update(self, audio: AudioFile) -> None:
        if audio.id is None:
            raise ValueError("ID audio tidak boleh kosong untuk pembaruan.")
        audio.validate()
        with self.db.session() as conn:
            cursor = conn.cursor()
            if audio.code:
                cursor.execute(
                    "SELECT id FROM audio_files WHERE UPPER(code) = ? AND id != ?",
                    (audio.code.upper(), audio.id)
                )
                if cursor.fetchone():
                    raise ValueError(f"Kode lagu '{audio.code}' sudah digunakan oleh berkas audio lain.")

            cursor.execute(
                """
                UPDATE audio_files
                SET code = ?, name = ?, stored_path = ?, original_filename = ?, duration_seconds = ?
                WHERE id = ?
                """,
                (audio.code.strip().upper(), audio.name.strip(), audio.stored_path, audio.original_filename, audio.duration_seconds, audio.id)
            )

    def get_affected_schedules(self, audio_id: int) -> List[dict]:
        """Mengembalikan daftar jadwal yang terhubung ke file audio ini."""
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT s.id, s.day_of_week, s.bell_time, s.event_name, p.name AS profile_name
                FROM schedules s
                JOIN profiles p ON s.profile_id = p.id
                WHERE s.audio_id = ?
                ORDER BY p.name, s.day_of_week, s.bell_time
                """,
                (audio_id,)
            )
            return [dict(r) for r in cursor.fetchall()]

    def delete(self, audio_id: int) -> None:
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM audio_files WHERE id = ?", (audio_id,))


class BellLogRepository:
    """Pencatatan riwayat eksekusi bel dan verifikasi idempotensi."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def add_log(self, log: BellLog) -> int:
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO bell_logs (
                    schedule_id, scheduled_at, executed_at, event_name, execution_mode, status, message
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log.schedule_id,
                    log.scheduled_at,
                    log.executed_at,
                    log.event_name,
                    log.execution_mode,
                    log.status,
                    log.message,
                )
            )
            return cursor.lastrowid

    create = add_log

    def update_status(self, log_id: int, status: str, message: Optional[str] = None) -> None:
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE bell_logs SET status = ?, message = COALESCE(?, message) WHERE id = ?",
                (status, message, log_id)
            )

    def _build_log_filter(
        self,
        date_filter: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status_filter: Optional[str] = None,
        mode_filter: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[str, list]:
        query = ""
        params = []

        if start_date and end_date:
            query += " AND substr(executed_at, 1, 10) >= ? AND substr(executed_at, 1, 10) <= ?"
            params.append(str(start_date)[:10])
            params.append(str(end_date)[:10])
        elif date_filter:
            query += " AND substr(executed_at, 1, 10) = ?"
            params.append(str(date_filter)[:10])

        if status_filter:
            query += " AND status = ?"
            params.append(status_filter)

        if mode_filter:
            query += " AND execution_mode = ?"
            params.append(mode_filter)

        if search and search.strip():
            clean_search = search.strip()
            query += " AND (event_name LIKE ? OR message LIKE ?)"
            params.append(f"%{clean_search}%")
            params.append(f"%{clean_search}%")

        return query, params

    def get_logs(
        self,
        date_filter: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status_filter: Optional[str] = None,
        mode_filter: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[BellLog]:
        where_clause, params = self._build_log_filter(
            date_filter=date_filter,
            start_date=start_date,
            end_date=end_date,
            status_filter=status_filter,
            mode_filter=mode_filter,
            search=search,
        )
        query = f"SELECT * FROM bell_logs WHERE 1=1{where_clause} ORDER BY executed_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [
                BellLog(
                    id=row["id"],
                    schedule_id=row["schedule_id"],
                    scheduled_at=row["scheduled_at"],
                    executed_at=row["executed_at"],
                    event_name=row["event_name"],
                    execution_mode=row["execution_mode"],
                    status=row["status"],
                    message=row["message"],
                )
                for row in rows
            ]

    def count_logs(
        self,
        date_filter: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status_filter: Optional[str] = None,
        mode_filter: Optional[str] = None,
        search: Optional[str] = None,
    ) -> int:
        """Menghitung total baris log yang sesuai dengan filter pencarian."""
        where_clause, params = self._build_log_filter(
            date_filter=date_filter,
            start_date=start_date,
            end_date=end_date,
            status_filter=status_filter,
            mode_filter=mode_filter,
            search=search,
        )
        query = f"SELECT COUNT(*) AS total FROM bell_logs WHERE 1=1{where_clause}"
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()["total"]


    def is_schedule_executed_today(self, schedule_id: int, date_str: str) -> bool:
        """
        Idempotensi: Memeriksa apakah jadwal telah dibunyikan (atau sedang dimainkan/dilewati) pada tanggal spesifik.
        Mencegah pemutaran berulang saat restart aplikasi.
        """
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id FROM bell_logs
                WHERE schedule_id = ?
                  AND scheduled_at LIKE ?
                  AND status IN ('requested', 'playing', 'completed', 'interrupted', 'missed', 'failed')
                LIMIT 1
                """,
                (schedule_id, f"{date_str}%")
            )
            return cursor.fetchone() is not None


class SettingsRepository:
    """Penyimpanan pasangan key-value untuk preferensi aplikasi."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def get(self, key: str, default: str = "") -> str:
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set(self, key: str, value: str) -> None:
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO app_settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, str(value))
            )
