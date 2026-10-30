"""
Pengujian Pencadangan dan Pemulihan (Backup & Restore Service)
Menguji:
6. Backup database yang valid
7. Backup file audio
8. Penolakan backup yang rusak
9. Penolakan restore dari arsip tidak valid
10. Restore backup yang valid
11. Backup otomatis sebelum restore
12. Kegagalan restore tidak merusak data aktif
"""

import json
import sqlite3
import zipfile
from pathlib import Path
import pytest

from src.database.db import DatabaseManager
from src.database.repositories import (
    AudioRepository,
    BellLogRepository,
    ProfileRepository,
    ScheduleRepository,
    SettingsRepository,
)
from src.models.models import AudioFile, BellLog, Profile, Schedule
from src.services.backup_service import BackupService


@pytest.fixture
def populated_db_and_audio(tmp_path):
    """Menyiapkan database dan file audio sampel dalam direktori sementara."""
    db_file = tmp_path / "test_active.db"
    db = DatabaseManager(db_file)
    db.initialize_database()

    # Buat file audio fisik tiruan
    audio_dir = tmp_path / "audio_storage"
    audio_dir.mkdir(parents=True, exist_ok=True)
    sample_wav = audio_dir / "bell_sample.wav"
    sample_wav.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00data\x00\x00\x00\x00")

    audio_repo = AudioRepository(db)
    audio_obj = audio_repo.create(
        AudioFile(
            name="Bel Nada Pagi",
            stored_path=str(sample_wav),
            original_filename="bell_sample.wav",
            duration_seconds=5,
        )
    )

    prof_repo = ProfileRepository(db)
    active_prof = prof_repo.get_active()

    sched_repo = ScheduleRepository(db)
    sched_repo.create(
        Schedule(
            profile_id=active_prof.id,
            day_of_week="Senin",
            bell_time="07:00",
            event_name="Bel Masuk Kelas",
            audio_id=audio_obj.id,
            is_enabled=True,
        )
    )

    log_repo = BellLogRepository(db)
    log_repo.create(
        BellLog(
            scheduled_at="2026-10-20T07:00:00",
            executed_at="2026-10-20T07:00:01",
            event_name="Bel Masuk Kelas",
            execution_mode="OTOMATIS",
            status="completed",
            message="Sukses diputar",
        )
    )

    settings_repo = SettingsRepository(db)
    settings_repo.set("volume", "90")
    settings_repo.set("confirm_manual_bell", "true")

    return {
        "db": db,
        "audio_dir": audio_dir,
        "sample_wav": sample_wav,
        "audio_obj": audio_obj,
        "profile": active_prof,
    }


def test_create_valid_backup_and_audio(tmp_path, populated_db_and_audio):
    """Uji 6 & 7: Backup database yang valid dan menyertakan file audio."""
    db = populated_db_and_audio["db"]
    backup_service = BackupService(db)

    target_zip = tmp_path / "backup_test.zip"
    result = backup_service.create_backup(target_zip)

    assert result["success"] is True
    assert target_zip.exists()
    assert result["schedules_count"] >= 1
    assert result["audio_files_count"] >= 1
    assert result["logs_count"] >= 1

    # Verifikasi isi zip
    with zipfile.ZipFile(target_zip, "r") as z:
        names = z.namelist()
        assert "manifest.json" in names
        assert "bel_sekolah.db" in names
        assert any(n.startswith("sounds/") for n in names)

        # Verifikasi manifest
        manifest = json.loads(z.read("manifest.json").decode("utf-8"))
        assert manifest["database_file"] == "bel_sekolah.db"
        assert len(manifest["database_sha256"]) == 64
        assert manifest["audio_files_count"] >= 1


def test_reject_corrupt_backup(tmp_path, populated_db_and_audio):
    """Uji 8: Penolakan backup yang rusak (arsip corrupt, checksum salah, file missing)."""
    db = populated_db_and_audio["db"]
    backup_service = BackupService(db)

    # 1. File bukan zip sama sekali
    corrupt_file = tmp_path / "not_a_zip.zip"
    corrupt_file.write_text("Ini bukan arsip zip!", encoding="utf-8")
    with pytest.raises(ValueError, match="bukan merupakan arsip ZIP"):
        backup_service.inspect_backup(corrupt_file)

    # 2. Arsip zip tanpa manifest.json
    no_manifest_zip = tmp_path / "no_manifest.zip"
    with zipfile.ZipFile(no_manifest_zip, "w") as z:
        z.writestr("test.txt", "data")
    with pytest.raises(ValueError, match="tidak memiliki manifest.json"):
        backup_service.inspect_backup(no_manifest_zip)

    # 3. Arsip zip dengan manifest tetapi checksum database telah dimanipulasi
    valid_zip = tmp_path / "original.zip"
    backup_service.create_backup(valid_zip)

    tampered_zip = tmp_path / "tampered.zip"
    with zipfile.ZipFile(valid_zip, "r") as z_in, zipfile.ZipFile(tampered_zip, "w") as z_out:
        for item in z_in.infolist():
            content = z_in.read(item.filename)
            if item.filename == "bel_sekolah.db":
                # Rusak isi database
                content = b"TAMPERED_HEADER_" + content[16:]
            z_out.writestr(item, content)

    with pytest.raises(ValueError, match="Checksum database tidak cocok"):
        backup_service.inspect_backup(tampered_zip)


def test_reject_restore_invalid_archive(tmp_path, populated_db_and_audio):
    """Uji 9: Penolakan pemulihan dari arsip tidak valid."""
    db = populated_db_and_audio["db"]
    backup_service = BackupService(db)

    invalid_zip = tmp_path / "fake_archive.zip"
    invalid_zip.write_bytes(b"PK\x05\x06" + b"\x00" * 18)  # Empty ZIP

    with pytest.raises(ValueError):
        backup_service.restore_backup(invalid_zip)


def test_restore_valid_backup_and_pre_restore_backup(tmp_path, populated_db_and_audio, monkeypatch):
    """Uji 10 & 11: Restore backup yang valid dan pembuatan cadangan otomatis pra-pemulihan."""
    db = populated_db_and_audio["db"]
    backup_service = BackupService(db)

    # Buat direktori user data palsu untuk menangkap pre-restore backup
    fake_user_dir = tmp_path / "fake_user_dir"
    fake_user_dir.mkdir()
    monkeypatch.setenv("BEL_APP_DATA_DIR", str(fake_user_dir))
    monkeypatch.setattr("src.services.backup_service.get_user_data_dir", lambda: fake_user_dir)
    monkeypatch.setattr("src.services.backup_service.get_audio_storage_dir", lambda: fake_user_dir / "sounds")

    target_zip = tmp_path / "state_one.zip"
    backup_service.create_backup(target_zip)

    # Ubah data di database aktif (hapus jadwal, ubah setting)
    sched_repo = ScheduleRepository(db)
    active_prof = populated_db_and_audio["profile"]
    schedules = sched_repo.get_by_profile_and_day(active_prof.id, "Senin")
    for s in schedules:
        sched_repo.delete(s.id)

    settings_repo = SettingsRepository(db)
    settings_repo.set("volume", "30")

    # Verifikasi data sekarang berkurang
    assert len(sched_repo.get_by_profile_and_day(active_prof.id, "Senin")) == 0
    assert settings_repo.get("volume") == "30"

    # Lakukan restore dari target_zip (state_one)
    restore_res = backup_service.restore_backup(target_zip, create_pre_restore_backup=True)

    assert restore_res["success"] is True
    assert restore_res["pre_restore_backup"] is not None
    assert Path(restore_res["pre_restore_backup"]).exists()

    # Periksa data setelah restore: Jadwal kembali dan volume kembali 90
    restored_schedules = sched_repo.get_by_profile_and_day(active_prof.id, "Senin")
    assert len(restored_schedules) == 1
    assert restored_schedules[0].event_name == "Bel Masuk Kelas"
    assert settings_repo.get("volume") == "90"


def test_failed_restore_preserves_active_data(tmp_path, populated_db_and_audio):
    """Uji 12: Kegagalan proses restore tidak merusak data aktif sistem."""
    db = populated_db_and_audio["db"]
    backup_service = BackupService(db)

    settings_repo = SettingsRepository(db)
    sched_repo = ScheduleRepository(db)
    active_prof = populated_db_and_audio["profile"]

    # Simpan snapshot state awal
    initial_volume = settings_repo.get("volume")
    initial_schedules_count = len(sched_repo.get_by_profile_and_day(active_prof.id, "Senin"))

    # Coba restore dari file yang rusak
    bad_zip = tmp_path / "bad.zip"
    bad_zip.write_text("corrupted content", encoding="utf-8")

    with pytest.raises(Exception):
        backup_service.restore_backup(bad_zip)

    # Verifikasi data aktif tetap utuh tanpa korupsi
    assert settings_repo.get("volume") == initial_volume
    assert len(sched_repo.get_by_profile_and_day(active_prof.id, "Senin")) == initial_schedules_count


def test_backup_rejects_incompatible_schema_version(tmp_path, populated_db_and_audio):
    """Pengujian penolakan arsip cadangan dengan versi skema yang lebih tinggi dari aplikasi."""
    db = populated_db_and_audio["db"]
    backup_service = BackupService(db)

    valid_zip = tmp_path / "valid.zip"
    backup_service.create_backup(valid_zip)

    # Modifikasi manifest dengan versi skema masa depan (misal: versi 99)
    future_zip = tmp_path / "future_version.zip"
    with zipfile.ZipFile(valid_zip, "r") as z_in, zipfile.ZipFile(future_zip, "w") as z_out:
        for item in z_in.infolist():
            content = z_in.read(item.filename)
            if item.filename == "manifest.json":
                manifest = json.loads(content.decode("utf-8"))
                manifest["schema_version"] = 99
                content = json.dumps(manifest).encode("utf-8")
            z_out.writestr(item, content)

    with pytest.raises(ValueError, match="lebih tinggi daripada versi aplikasi yang didukung"):
        backup_service.inspect_backup(future_zip)


def test_restore_audio_path_relocation(tmp_path, populated_db_and_audio, monkeypatch):
    """Pengujian penyesuaian stored_path file audio ke direktori sounds aktif saat di-restore."""
    db = populated_db_and_audio["db"]
    backup_service = BackupService(db)

    # Buat target sounds dir baru
    new_sounds_dir = tmp_path / "relocated_sounds"
    new_sounds_dir.mkdir()
    monkeypatch.setattr("src.services.backup_service.get_audio_storage_dir", lambda: new_sounds_dir)

    target_zip = tmp_path / "backup_relocate.zip"
    backup_service.create_backup(target_zip)

    # Jalankan restore
    restore_res = backup_service.restore_backup(target_zip, create_pre_restore_backup=False)
    assert restore_res["success"] is True

    # Periksa tabel audio_files di database aktif
    audio_repo = AudioRepository(db)
    audios = audio_repo.get_all()
    assert len(audios) >= 1
    for a in audios:
        p = Path(a.stored_path)
        assert p.parent.resolve() == new_sounds_dir.resolve()
        assert p.exists()


def test_backup_fails_if_audio_file_missing_on_disk(tmp_path, populated_db_and_audio):
    """Pengujian kegagalan backup jika ada file audio di database yang fisiknya hilang dari disk."""
    db = populated_db_and_audio["db"]
    backup_service = BackupService(db)

    # Hapus file audio fisik yang terdaftar
    sample_wav = populated_db_and_audio["sample_wav"]
    if sample_wav.exists():
        sample_wav.unlink()

    target_zip = tmp_path / "backup_missing_audio.zip"
    with pytest.raises(FileNotFoundError, match="file audio yang hilang di disk"):
        backup_service.create_backup(target_zip)


def test_restore_rejects_zip_slip_path_traversal(tmp_path, populated_db_and_audio):
    """Pengujian penolakan arsip ZIP berbahaya yang memuat nama berkas path traversal."""
    db = populated_db_and_audio["db"]
    backup_service = BackupService(db)

    # Buat arsip cadangan valid terlebih dahulu
    valid_zip = tmp_path / "valid_base.zip"
    backup_service.create_backup(valid_zip)

    # Sisipkan entri berbahaya dengan path traversal (Zip Slip)
    evil_zip = tmp_path / "evil_slip.zip"
    with zipfile.ZipFile(valid_zip, "r") as z_in, zipfile.ZipFile(evil_zip, "w") as z_out:
        for item in z_in.infolist():
            z_out.writestr(item, z_in.read(item.filename))
        # Tambah file dengan path traversal
        z_out.writestr("../../../evil_exploit.exe", b"MALICIOUS")

    with pytest.raises(ValueError, match="path traversal berbahaya"):
        backup_service.restore_backup(evil_zip)
