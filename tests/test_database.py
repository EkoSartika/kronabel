"""
Pengujian Fondasi Database Bel Otomatis Sekolah.
Menguji inisialisasi tabel, foreign keys, persistensi, dan konfigurasi pragma.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.database.db import DatabaseManager


def test_database_initialization(temp_db: DatabaseManager):
    """Memastikan database dibuat dengan semua tabel yang dipersyaratkan dan pragma aktif."""
    with temp_db.session() as conn:
        cursor = conn.cursor()

        # 1. Cek PRAGMA foreign_keys
        cursor.execute("PRAGMA foreign_keys;")
        fk_status = cursor.fetchone()[0]
        assert fk_status == 1, "Foreign keys harus bernilai ON"

        # 2. Cek keberadaan tabel
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name;
            """
        )
        tables = [row["name"] for row in cursor.fetchall()]

        expected_tables = {"app_settings", "audio_files", "bell_logs", "profiles", "schedules"}
        assert expected_tables.issubset(set(tables)), f"Tabel yang ada: {tables}"


def test_default_profiles_seeded(temp_db: DatabaseManager):
    """Memastikan profil awal (Reguler, Ramadan, Ujian) terbuat otomatis."""
    with temp_db.session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, is_active FROM profiles ORDER BY name;")
        rows = cursor.fetchall()

        profile_map = {row["name"]: bool(row["is_active"]) for row in rows}
        assert "Reguler" in profile_map
        assert "Ramadan" in profile_map
        assert "Ujian" in profile_map

        # Profil Reguler harus aktif secara default
        assert profile_map["Reguler"] is True
        assert profile_map["Ramadan"] is False
        assert profile_map["Ujian"] is False


def test_data_persistence_across_connections(tmp_path: Path):
    """Memastikan data tersimpan persisten saat koneksi ditutup dan dibuka kembali."""
    db_file = tmp_path / "persist_test.db"
    db1 = DatabaseManager(db_path=db_file)
    db1.initialize_database()

    with db1.session() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO app_settings (key, value) VALUES ('sekolah_nama', 'SMA Negeri 1')")

    # Buka koneksi baru dengan instance DatabaseManager berbeda
    db2 = DatabaseManager(db_path=db_file)
    with db2.session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM app_settings WHERE key = 'sekolah_nama'")
        row = cursor.fetchone()
        assert row is not None
        assert row["value"] == "SMA Negeri 1"
