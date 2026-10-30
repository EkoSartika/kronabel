"""
Layanan Cadangan (Backup) & Pemulihan (Restore) Bel Otomatis Sekolah.
Menerapkan SQLite Backup API yang aman terhadap WAL mode, arsip ZIP terkompresi,
manifest versi skema, pemeriksaan integritas, serta staging & rollback otomatis.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.config import APP_NAME, APP_VERSION, get_audio_storage_dir, get_db_path, get_user_data_dir
from src.database.db import DatabaseManager

logger = logging.getLogger(__name__)

BACKUP_SCHEMA_VERSION = 1


def calculate_sha256(file_path: Path) -> str:
    """Menghitung checksum SHA-256 dari sebuah file."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def _safe_extract(z: zipfile.ZipFile, target_dir: Path) -> None:
    """
    Mengekstrak seluruh berkas arsip ZIP dengan proteksi anti-Zip Slip (Path Traversal).
    Memastikan semua anggota arsip tetap berada dalam batas direktori target.
    """
    resolved_target = target_dir.resolve()
    for member in z.infolist():
        member_target = (resolved_target / member.filename).resolve()
        try:
            member_target.relative_to(resolved_target)
        except ValueError:
            raise ValueError(f"Deteksi potensi path traversal berbahaya pada arsip: {member.filename}")
    z.extractall(resolved_target)


class BackupService:
    """Layanan pencadangan dan pemulihan data sistem Bel Otomatis Sekolah."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def create_backup(self, target_zip_path: str | Path) -> Dict[str, Any]:
        """
        Membuat paket cadangan lengkap (Database + File Audio + Pengaturan + Manifest) dalam format ZIP.
        Menggunakan SQLite Backup API agar aman dari WAL concurrency lock.
        """
        target_path = Path(target_zip_path).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_dir_path = Path(tmp_dir)
            temp_db_copy = temp_dir_path / "bel_sekolah.db"

            # 1. Gunakan SQLite Backup API untuk menyalin database yang sedang aktif secara aman
            source_conn = self.db.get_connection()
            try:
                dest_conn = sqlite3.connect(str(temp_db_copy))
                try:
                    source_conn.backup(dest_conn)
                finally:
                    dest_conn.close()
            finally:
                source_conn.close()

            # 2. Periksa integritas database yang disalin
            check_conn = sqlite3.connect(str(temp_db_copy))
            try:
                cursor = check_conn.cursor()
                cursor.execute("PRAGMA integrity_check;")
                check_result = cursor.fetchone()[0]
                if check_result != "ok":
                    raise ValueError(f"Integritas database gagal: {check_result}")

                # Kumpulkan statistik data
                cursor.execute("SELECT COUNT(*) FROM profiles")
                profiles_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM schedules")
                schedules_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM bell_logs")
                logs_count = cursor.fetchone()[0]

                cursor.execute("SELECT id, name, original_filename, stored_path FROM audio_files")
                audio_records = cursor.fetchall()
            finally:
                check_conn.close()

            db_checksum = calculate_sha256(temp_db_copy)

            # 3. Kumpulkan file audio dan validasi keberadaannya di disk
            temp_sounds_dir = temp_dir_path / "sounds"
            temp_sounds_dir.mkdir(parents=True, exist_ok=True)

            audio_manifest_list = []
            missing_audios = []
            for a_id, a_name, a_orig, a_path in audio_records:
                src_audio = Path(a_path)
                stored_name = src_audio.name
                if src_audio.exists():
                    shutil.copy2(src_audio, temp_sounds_dir / stored_name)
                    audio_manifest_list.append({
                        "id": a_id,
                        "name": a_name,
                        "original_filename": a_orig,
                        "stored_filename": stored_name,
                        "sha256": calculate_sha256(src_audio),
                    })
                else:
                    missing_audios.append(f"'{a_name}' (ID: {a_id}, Path: {a_path})")

            # Jangan mengklaim backup lengkap jika ada file audio yang hilang di disk
            if missing_audios:
                raise FileNotFoundError(
                    f"Pencadangan ditolak karena terdapat {len(missing_audios)} file audio yang hilang di disk: "
                    + ", ".join(missing_audios)
                )

            # 4. Buat manifest.json
            now_iso = datetime.now().isoformat()
            manifest = {
                "app_name": APP_NAME,
                "app_version": APP_VERSION,
                "schema_version": BACKUP_SCHEMA_VERSION,
                "created_at": now_iso,
                "database_file": "bel_sekolah.db",
                "database_sha256": db_checksum,
                "profiles_count": profiles_count,
                "schedules_count": schedules_count,
                "logs_count": logs_count,
                "audio_files_count": len(audio_manifest_list),
                "audio_files": audio_manifest_list,
            }

            manifest_file = temp_dir_path / "manifest.json"
            manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


            # 5. Arsipkan seluruh file ke dalam ZIP
            with zipfile.ZipFile(target_path, "w", zipfile.ZIP_DEFLATED) as zip_out:
                zip_out.write(manifest_file, arcname="manifest.json")
                zip_out.write(temp_db_copy, arcname="bel_sekolah.db")

                for sound_file in temp_sounds_dir.glob("*"):
                    if sound_file.is_file():
                        zip_out.write(sound_file, arcname=f"sounds/{sound_file.name}")

        logger.info("Cadangan berhasil dibuat di: %s", target_path)
        return {
            "success": True,
            "path": str(target_path),
            "created_at": now_iso,
            "profiles_count": profiles_count,
            "schedules_count": schedules_count,
            "logs_count": logs_count,
            "audio_files_count": len(audio_manifest_list),
        }

    def inspect_backup(self, zip_path: str | Path) -> Dict[str, Any]:
        """
        Memeriksa validitas file arsip cadangan (format, integritas, dan manifest).
        Menimbulkan ValueError jika file rusak atau tidak kompatibel.
        """
        path = Path(zip_path)
        if not path.exists():
            raise FileNotFoundError(f"File cadangan tidak ditemukan: {path}")

        if not zipfile.is_zipfile(path):
            raise ValueError("File bukan merupakan arsip ZIP cadangan yang valid.")

        with zipfile.ZipFile(path, "r") as z:
            namelist = z.namelist()
            if "manifest.json" not in namelist:
                raise ValueError("Arsip tidak memiliki manifest.json yang valid.")

            if "bel_sekolah.db" not in namelist:
                raise ValueError("Arsip tidak memiliki file database bel_sekolah.db.")

            # Baca manifest
            try:
                manifest_data = json.loads(z.read("manifest.json").decode("utf-8"))
            except Exception as e:
                raise ValueError(f"Gagal membaca manifest cadangan: {e}")

            if manifest_data.get("app_name") != APP_NAME:
                raise ValueError(f"Cadangan ini bukan untuk aplikasi {APP_NAME}.")

            if manifest_data.get("schema_version") > BACKUP_SCHEMA_VERSION:
                raise ValueError(
                    f"Versi skema cadangan ({manifest_data.get('schema_version')}) "
                    f"lebih tinggi daripada versi aplikasi yang didukung ({BACKUP_SCHEMA_VERSION})."
                )

            # Uji integritas database dalam arsip
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_dir_path = Path(tmp_dir)
                _safe_extract(z, tmp_dir_path)
                test_db = tmp_dir_path / "bel_sekolah.db"

                test_checksum = calculate_sha256(test_db)
                if manifest_data.get("database_sha256") and test_checksum != manifest_data.get("database_sha256"):
                    raise ValueError("Checksum database tidak cocok. File cadangan terindikasi rusak atau dimodifikasi.")

                conn = sqlite3.connect(str(test_db))
                try:
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA integrity_check;")
                    result = cursor.fetchone()[0]
                    if result != "ok":
                        raise ValueError(f"Database dalam cadangan korup: {result}")
                finally:
                    conn.close()

            return {
                "valid": True,
                "created_at": manifest_data.get("created_at"),
                "app_version": manifest_data.get("app_version"),
                "profiles_count": manifest_data.get("profiles_count", 0),
                "schedules_count": manifest_data.get("schedules_count", 0),
                "logs_count": manifest_data.get("logs_count", 0),
                "audio_files_count": manifest_data.get("audio_files_count", 0),
            }

    def restore_backup(self, zip_path: str | Path, create_pre_restore_backup: bool = True) -> Dict[str, Any]:
        """
        Memulihkan database dan file audio dari file arsip cadangan.
        Menerapkan safety net: membuat cadangan darurat kondisi saat ini sebelum memulihkan.
        """
        # 1. Validasi arsip terlebih dahulu
        inspection = self.inspect_backup(zip_path)

        # 2. Buat backup darurat sebelum pemulihan jika diminta
        pre_backup_path = None
        if create_pre_restore_backup and self.db.db_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_folder = get_user_data_dir() / "backups"
            backup_folder.mkdir(parents=True, exist_ok=True)
            pre_backup_path = backup_folder / f"pre_restore_{timestamp}.zip"
            try:
                self.create_backup(pre_backup_path)
                logger.info("Backup otomatis sebelum restore tersimpan di: %s", pre_backup_path)
            except Exception as e:
                logger.warning("Gagal membuat backup otomatis pra-pemulihan: %s", e)

        # 3. Proses ekstraksi dan pemulihan via staging
        with tempfile.TemporaryDirectory() as staging_dir:
            staging_path = Path(staging_dir)
            with zipfile.ZipFile(zip_path, "r") as z:
                _safe_extract(z, staging_path)

            staged_db = staging_path / "bel_sekolah.db"
            if not staged_db.exists():
                raise ValueError("File database bel_sekolah.db tidak ditemukan dalam arsip cadangan.")

            # Uji koneksi pada staged_db
            staged_conn = sqlite3.connect(str(staged_db))
            try:
                staged_cursor = staged_conn.cursor()
                staged_cursor.execute("PRAGMA integrity_check;")
                if staged_cursor.fetchone()[0] != "ok":
                    raise ValueError("Database yang dipulihkan korup.")
            finally:
                staged_conn.close()

            # 4. Salin database yang dipulihkan ke target aktif menggunakan SQLite Backup API
            active_conn = self.db.get_connection()
            try:
                src_restore_conn = sqlite3.connect(str(staged_db))
                try:
                    src_restore_conn.backup(active_conn)
                finally:
                    src_restore_conn.close()
            finally:
                active_conn.close()

            # 5. Pulihkan file audio ke direktori sounds
            target_sounds_dir = get_audio_storage_dir()
            target_sounds_dir.mkdir(parents=True, exist_ok=True)

            staged_sounds = staging_path / "sounds"
            if staged_sounds.exists() and staged_sounds.is_dir():
                for sound_file in staged_sounds.glob("*"):
                    if sound_file.is_file():
                        shutil.copy2(sound_file, target_sounds_dir / sound_file.name)

            # 6. Perbarui stored_path pada database aktif agar konsisten dengan lokasi absolut terkini
            with self.db.session() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, stored_path FROM audio_files")
                audio_rows = cursor.fetchall()
                for row in audio_rows:
                    old_path = Path(row["stored_path"])
                    new_path = target_sounds_dir / old_path.name
                    if new_path.exists():
                        cursor.execute(
                            "UPDATE audio_files SET stored_path = ? WHERE id = ?",
                            (str(new_path), row["id"])
                        )

        logger.info("Pemulihan cadangan dari %s selesai.", zip_path)
        return {
            "success": True,
            "pre_restore_backup": str(pre_backup_path) if pre_backup_path else None,
            "summary": inspection,
        }

