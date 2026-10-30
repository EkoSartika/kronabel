"""
Pengujian Pengelolaan Profil Bel Otomatis Sekolah.
Menguji penambahan, pengaktifan, perubahan, dan proteksi penghapusan profil.
"""

from __future__ import annotations

import pytest

from src.database.repositories import ProfileRepository
from src.models.models import Profile


def test_get_all_profiles(profile_repo: ProfileRepository):
    profiles = profile_repo.get_all()
    assert len(profiles) >= 3
    names = [p.name for p in profiles]
    assert "Reguler" in names


def test_get_active_profile(profile_repo: ProfileRepository):
    active = profile_repo.get_active()
    assert active is not None
    assert active.name == "Reguler"
    assert active.is_active is True


def test_switch_active_profile(profile_repo: ProfileRepository):
    """Memastikan perpindahan profil aktif menonaktifkan profil sebelumnya."""
    profiles = {p.name: p for p in profile_repo.get_all()}
    ramadan_profile = profiles["Ramadan"]

    # Aktifkan Ramadan
    profile_repo.set_active(ramadan_profile.id)

    new_active = profile_repo.get_active()
    assert new_active is not None
    assert new_active.name == "Ramadan"

    # Pastikan profil Reguler sekarang non-aktif
    reguler = profile_repo.get_by_id(profiles["Reguler"].id)
    assert reguler.is_active is False


def test_create_custom_profile(profile_repo: ProfileRepository):
    custom = Profile(
        id=None,
        name="Semester Genap",
        description="Jadwal semester genap khusus",
        is_active=False,
    )
    saved = profile_repo.create(custom)
    assert saved.id is not None
    assert saved.name == "Semester Genap"

    # Tidak boleh ada nama duplikat
    duplicate = Profile(id=None, name="Semester Genap")
    with pytest.raises(ValueError, match="sudah ada"):
        profile_repo.create(duplicate)


def test_profile_empty_name_validation(profile_repo: ProfileRepository):
    invalid = Profile(id=None, name="   ")
    with pytest.raises(ValueError, match="tidak boleh kosong"):
        profile_repo.create(invalid)


def test_cannot_delete_active_profile(profile_repo: ProfileRepository):
    active = profile_repo.get_active()
    with pytest.raises(ValueError, match="sedang aktif"):
        profile_repo.delete(active.id)


def test_delete_inactive_profile(profile_repo: ProfileRepository):
    # Buat profil baru
    extra = profile_repo.create(Profile(id=None, name="Profil Sementara"))
    profile_repo.delete(extra.id)

    assert profile_repo.get_by_id(extra.id) is None
