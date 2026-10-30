"""
Manajer Database SQLite Bel Otomatis Sekolah
Menangani inisialisasi schema, koneksi, migrasi, transaksi, dan penanganan database rusak.
"""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

from src.core.config import get_assets_dir, get_audio_storage_dir, get_db_path

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
-- Aktifkan Foreign Keys
PRAGMA foreign_keys = ON;

-- Tabel Profil Jam Pelajaran
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Tabel File Audio Bel
CREATE TABLE IF NOT EXISTS audio_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    name TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    duration_seconds REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL
);

-- Tabel Jadwal Bel
CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    day_of_week TEXT NOT NULL,
    bell_time TEXT NOT NULL,
    event_name TEXT NOT NULL,
    audio_id INTEGER,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (audio_id) REFERENCES audio_files(id) ON DELETE SET NULL,
    CONSTRAINT uq_schedule_time UNIQUE (profile_id, day_of_week, bell_time)
);

-- Indeks untuk pencarian cepat jadwal aktif per hari dan waktu
CREATE INDEX IF NOT EXISTS idx_schedules_day_time ON schedules(profile_id, day_of_week, bell_time);

-- Tabel Riwayat Pembunyian Bel
CREATE TABLE IF NOT EXISTS bell_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id INTEGER,
    scheduled_at TEXT,
    executed_at TEXT NOT NULL,
    event_name TEXT NOT NULL,
    execution_mode TEXT NOT NULL, -- 'OTOMATIS' atau 'MANUAL'
    status TEXT NOT NULL,         -- 'requested', 'playing', 'completed', 'failed', 'missed', 'interrupted'
    message TEXT,
    FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE SET NULL
);

-- Indeks untuk riwayat
CREATE INDEX IF NOT EXISTS idx_bell_logs_executed_at ON bell_logs(executed_at);
CREATE INDEX IF NOT EXISTS idx_bell_logs_schedule ON bell_logs(schedule_id, scheduled_at);

-- Tabel Pengaturan Aplikasi
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class DatabaseManager:
    """Manajer koneksi SQLite yang thread-safe dengan isolasi transaksi."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else get_db_path()

    def get_connection(self) -> sqlite3.Connection:
        """Membuka koneksi ke database SQLite dengan konfigurasi optimal."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=20.0,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            return conn
        except sqlite3.DatabaseError as e:
            logger.error("Gagal membuka database %s: %s", self.db_path, e)
            self._handle_corrupt_database(e)
            # Coba kembali setelah rekoveri
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=20.0,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            return conn

    def _handle_corrupt_database(self, error: Exception) -> None:
        """Menyelamatkan database rusak dengan membuat cadangan sebelum membuat baru."""
        if self.db_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.db_path.with_name(f"{self.db_path.stem}_corrupt_{timestamp}.bak")
            logger.warning("Membuat backup database rusak ke: %s", backup_path)
            shutil.copy2(self.db_path, backup_path)

    @contextmanager
    def session(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager untuk transaksi database."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize_database(self) -> None:
        """Membuat tabel dan indeks jika belum ada, serta mengisi default awal."""
        with self.session() as conn:
            conn.executescript(SCHEMA_SQL)
            self._run_migrations_if_needed(conn)
            self._seed_default_profiles_if_empty(conn)

    def _run_migrations_if_needed(self, conn: sqlite3.Connection) -> None:
        """Migrasi skema database yang aman dan idempotensial."""
        cursor = conn.cursor()
        # Periksa kolom 'code' di audio_files
        cursor.execute("PRAGMA table_info(audio_files)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "code" not in columns:
            logger.info("Migrasi skema: Menambahkan kolom 'code' ke tabel audio_files")
            cursor.execute("ALTER TABLE audio_files ADD COLUMN code TEXT")

        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_audio_files_code ON audio_files(code)")

        # Konversi kode lagu yang berformat numerik 'BEL 1', 'BEL 2', ... ke alfabet 'BEL A', 'BEL B', ...
        cursor.execute("SELECT id, code FROM audio_files ORDER BY id ASC")
        rows = cursor.fetchall()
        for idx, row in enumerate(rows):
            current_code = row["code"]
            num = idx
            letters = ""
            while num >= 0:
                letters = chr(65 + (num % 26)) + letters
                num = (num // 26) - 1
            target_code = f"BEL {letters}"

            # Jika kode kosong atau berformat 'BEL <angka>'
            if not current_code or (current_code.startswith("BEL ") and current_code[4:].isdigit()):
                # Periksa apakah target_code sudah dipakai baris lain
                existing = cursor.execute("SELECT id FROM audio_files WHERE UPPER(code) = ? AND id != ?", (target_code.upper(), row["id"])).fetchone()
                if not existing:
                    cursor.execute("UPDATE audio_files SET code = ? WHERE id = ?", (target_code, row["id"]))

    def seed_default_audio_templates_if_needed(self) -> None:
        """Menyiapkan template audio bawaan BEL A - BEL N serta Tes 1 - Tes 5 jika belum ada."""
        with self.session() as conn:
            self._seed_default_audio_templates(conn)

    def _ensure_default_chime_file(self) -> Path:
        """Menghasilkan berkas audio chime bawaan jika belum ada di folder penyimpanan audio."""
        import math
        import struct
        import wave

        storage_dir = get_audio_storage_dir()
        storage_dir.mkdir(parents=True, exist_ok=True)
        chime_file = storage_dir / "chime_default.wav"
        if not chime_file.exists():
            sample_rate = 22050
            duration = 1.2
            num_samples = int(sample_rate * duration)
            with wave.open(str(chime_file), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                frames = bytearray()
                for i in range(num_samples):
                    t = i / sample_rate
                    if t < 0.5:
                        freq = 523.25
                        decay = math.exp(-t * 4.0)
                    else:
                        freq = 659.25
                        decay = math.exp(-(t - 0.5) * 3.5)
                    sample = int(32767.0 * 0.7 * decay * math.sin(2.0 * math.pi * freq * t))
                    sample = max(-32768, min(32767, sample))
                    frames.extend(struct.pack("<h", sample))
                wf.writeframes(frames)
        return chime_file

    def _seed_default_audio_templates(self, conn: sqlite3.Connection) -> None:
        """
        Menyiapkan template audio bawaan BEL A - BEL N serta Tes 1 - Tes 5.
        Jika di folder assets/sounds tersedia file MP3 bawaan aplikasi, salin otomatis
        ke folder penyimpanan pengguna (%APPDATA%/BelOtomatisSekolah/sounds) agar langsung
        siap digunakan saat diinstal di komputer baru.
        """
        cursor = conn.cursor()
        chime_path = self._ensure_default_chime_file()
        storage_dir = get_audio_storage_dir()
        storage_dir.mkdir(parents=True, exist_ok=True)
        bundled_sounds_dir = get_assets_dir() / "sounds"
        now = datetime.now().isoformat()

        # Pemetaan kode template ke nama lagu dan kandidat file MP3 bawaan di assets/sounds
        bel_templates = [
            ("BEL A", "Upacara Senin", "Upacara Senin.mp3"),
            ("BEL B", "Jam Pelajaran 1", "Jam Pelajaran 1.mp3"),
            ("BEL C", "Jam Pelajaran 2", "Jam Pelajaran 2.mp3"),
            ("BEL D", "Jam Pelajaran 3", "Jam Pelajaran 3.mp3"),
            ("BEL E", "Jam Pelajaran 4", "Jam Pelajaran 4.mp3"),
            ("BEL F", "Jam Pelajaran 5", "Jam Pelajaran 5.mp3"),
            ("BEL G", "Jam Pelajaran 6", "Jam Pelajaran 6.mp3"),
            ("BEL H", "Jam Pelajaran 7", "Jam Pelajaran 7.mp3"),
            ("BEL I", "Jam Pelajaran 8", "Jam Pelajaran 8.mp3"),
            ("BEL J", "Jam Pelajaran 9", "Jam Pelajaran 9.mp3"),
            ("BEL K", "Istirahat", "Istirahat.mp3"),
            ("BEL L", "Sholat Dhuha", "Sholat Dhuha.mp3"),
            ("BEL M", "Sholat Dzuhur", "Sholat Dzuhur.mp3"),
            ("BEL N", "Akhir Pelajaran", "Akhir Pelajaran.mp3"),
        ]

        tes_templates = [
            ("Tes 1", "Akhir Pekan", "Akhir Pekan.mp3"),
            ("Tes 2", "Tes Audio 2", ""),
            ("Tes 3", "Tes Audio 3", ""),
            ("Tes 4", "Tes Audio 4", ""),
            ("Tes 5", "Tes Audio 5", ""),
        ]

        for code, name, mp3_filename in (bel_templates + tes_templates):
            target_file = chime_path
            if mp3_filename and (bundled_sounds_dir / mp3_filename).exists():
                src_mp3 = bundled_sounds_dir / mp3_filename
                dst_mp3 = storage_dir / mp3_filename
                if not dst_mp3.exists():
                    try:
                        shutil.copy2(src_mp3, dst_mp3)
                    except Exception as e:
                        logger.warning("Gagal menyalin MP3 bawaan %s: %s", mp3_filename, e)
                if dst_mp3.exists():
                    target_file = dst_mp3

            existing = cursor.execute(
                "SELECT id, stored_path FROM audio_files WHERE UPPER(code) = ?",
                (code.upper(),),
            ).fetchone()
            if not existing:
                cursor.execute(
                    """
                    INSERT INTO audio_files (code, name, stored_path, original_filename, duration_seconds, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (code, name, str(target_file), Path(target_file).name, 1.2, now),
                )
            else:
                # Jika path lama tidak ditemukan di komputer ini (misal hasil pindah DB), perbaiki otomatis
                old_stored = Path(existing["stored_path"]) if existing["stored_path"] else None
                if not old_stored or not old_stored.exists():
                    candidate_in_storage = storage_dir / old_stored.name if old_stored else None
                    resolved_file = (
                        candidate_in_storage
                        if (candidate_in_storage and candidate_in_storage.exists())
                        else target_file
                    )
                    cursor.execute(
                        "UPDATE audio_files SET stored_path = ?, original_filename = ? WHERE id = ?",
                        (str(resolved_file), Path(resolved_file).name, existing["id"]),
                    )

    def _seed_default_profiles_if_empty(self, conn: sqlite3.Connection) -> None:
        """Inisialisasi profil dasar tanpa mengisi jadwal palsu."""
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM profiles")
        count = cursor.fetchone()["total"]
        if count == 0:
            now = datetime.now().isoformat()
            default_profiles = [
                ("Reguler", "Profil jadwal kegiatan belajar mengajar harian reguler", 1, now, now),
                ("Ramadan", "Profil jadwal khusus bulan suci Ramadan", 0, now, now),
                ("Ujian", "Profil jadwal khusus periode ujian sekolah / asesmen", 0, now, now),
            ]
            cursor.executemany(
                """
                INSERT INTO profiles (name, description, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                default_profiles
            )
            # Default pengaturan
            cursor.execute(
                """
                INSERT OR IGNORE INTO app_settings (key, value)
                VALUES ('auto_scheduler_enabled', '1'),
                       ('volume', '80')
                """
            )
