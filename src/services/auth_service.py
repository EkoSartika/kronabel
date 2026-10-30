"""
Layanan Autentikasi Pengelola Bel Otomatis Sekolah
Menangani hashing password aman (PBKDF2-HMAC-SHA256), verifikasi login, dan inisialisasi akun pengelola.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Optional

from src.database.repositories import SettingsRepository


class AuthService:
    """Mengelola autentikasi pengelola aplikasi secara lokal dan aman."""

    KEY_PASSWORD_HASH = "admin_password_hash"
    KEY_PASSWORD_SALT = "admin_password_salt"
    ITERATIONS = 100_000

    def __init__(self, settings_repo: SettingsRepository):
        self.settings = settings_repo

    def is_password_set(self) -> bool:
        """Memeriksa apakah password pengelola sudah pernah diinisialisasi."""
        pw_hash = self.settings.get(self.KEY_PASSWORD_HASH, "")
        pw_salt = self.settings.get(self.KEY_PASSWORD_SALT, "")
        return bool(pw_hash.strip() and pw_salt.strip())

    def _hash_password(self, password: str, salt: str) -> str:
        """Menghasilkan hash aman menggunakan PBKDF2-HMAC-SHA256."""
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            self.ITERATIONS
        )
        return derived.hex()

    def set_password(self, new_password: str) -> None:
        """Mengatur atau memperbarui password pengelola."""
        if not new_password or len(new_password) < 4:
            raise ValueError("Password pengelola minimal terdiri dari 4 karakter.")
        
        salt = secrets.token_hex(16)
        pw_hash = self._hash_password(new_password, salt)
        self.settings.set(self.KEY_PASSWORD_SALT, salt)
        self.settings.set(self.KEY_PASSWORD_HASH, pw_hash)

    def verify_password(self, password: str) -> bool:
        """Memvalidasi password masukan terhadap hash tersimpan."""
        if not self.is_password_set():
            return False
        
        salt = self.settings.get(self.KEY_PASSWORD_SALT, "")
        stored_hash = self.settings.get(self.KEY_PASSWORD_HASH, "")
        calculated_hash = self._hash_password(password, salt)
        return hmac.compare_digest(stored_hash, calculated_hash)

    def change_password(self, old_password: str, new_password: str) -> bool:
        """Mengganti password lama dengan password baru setelah verifikasi."""
        if not self.verify_password(old_password):
            return False
        self.set_password(new_password)
        return True
