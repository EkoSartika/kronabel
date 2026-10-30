# LAPORAN AKHIR UPDATE RILIS v1.2.0 — BEL OTOMATIS SEKOLAH

**Tanggal Rilis**: 29 Oktober 2026  
**Versi Aplikasi**: `1.2.0`  
**Target Sistem Operasi**: Windows 10 & Windows 11 (64-bit)  
**Konfigurasi Runtime**: Python `3.11.9` + PySide6 `6.12.0` (Qt 6 Native) + SQLite `3.x`  
**Status Rilis**: **STABIL & SIAP DISTRIBUSI (115/115 Tes Regresi Lulus)**

---

## 1. Ringkasan Pembaruan Utama (Changelog v1.2.0)

1. **Pemulihan Penuh Konfigurasi Windows 10 & Windows 11 (Python 3.11 + PySide6)**:
   - Menghentikan seluruh pengembangan dan konfigurasi kompatibilitas khusus Windows 7 (`Python 3.8`, `PySide2`, `shiboken2`, dan skrip diagnostik `DiagWin7.exe`).
   - Memulihkan alur impor `PySide6` secara langsung dan native pada [`main.py`](../main.py), [`src/__init__.py`](../src/__init__.py), dan [`tests/conftest.py`](../tests/conftest.py).
   - Membersihkan [`src/core/qt_compat.py`](../src/core/qt_compat.py) dari seluruh patch `sys.modules`, manipulasi `PATH` / `QT_PLUGIN_PATH`, serta shim `PySide2`/`shiboken2`.
   - Memastikan proses build di [`build_release.py`](../build_release.py) dan [`BelOtomatisSekolah.spec`](../BelOtomatisSekolah.spec) terisolasi 100% dari lingkungan `build_env_py38` dan tidak menyertakan DLL eksternal ClickToRun/Windows 7.

2. **Perbaikan Antarmuka (UI) Jendela Utama**:
   - Menghapus aset gambar lencana (`bell_badge.png`) yang berada di sebelah kiri judul **"BEL SEKOLAH OTOMATIS"** pada header panel kiri di [`src/ui/main_window.py`](../src/ui/main_window.py) sehingga tampilan header lebih bersih dan rapi.

3. **Pemisahan Alur Logout Pengelola vs Shutdown Komputer**:
   - **Logout Pengelola** pada [`src/ui/admin_window.py`](../src/ui/admin_window.py) hanya menutup jendela Pengaturan/Admin dan mengembalikan tampilan ke halaman utama (`MainWindow`) tanpa menghentikan aplikasi maupun jadwal bel.
   - **Mematikan/Restart Komputer (Windows Shutdown)** ditangani secara terpisah melalui sinyal sesi Windows (`WM_QUERYENDSESSION` / `WM_ENDSESSION` dan `commitDataRequest`) untuk menghentikan audio dan menutup aplikasi dengan aman saat PC dimatikan.

4. **Paket Instalasi & Portable Mandiri (100% Offline Standalone)**:
   - Menyertakan seluruh runtime Python 3.11 (`python311.dll`), pustaka GUI & Multimedia `PySide6`, serta 19 berkas suara bel bawaan di dalam paket installer dan portable tanpa memerlukan instalasi Python di komputer sekolah tujuan.

---

## 2. Daftar File yang Diubah, Dipulihkan, dan Diarsipkan

### A. File Kode Sumber & Konfigurasi Aktif yang Diperbarui
| File | Keterangan Perubahan |
|---|---|
| [`main.py`](../main.py) | Dipulihkan ke impor langsung `PySide6` tanpa hook kompatibilitas Windows 7. |
| [`src/__init__.py`](../src/__init__.py) | Diperbarui ke `__version__ = "1.2.0"` tanpa pemanggilan `install_qt_compat()`. |
| [`src/core/config.py`](../src/core/config.py) | Diperbarui ke `APP_VERSION = "1.2.0"`. |
| [`src/core/qt_compat.py`](../src/core/qt_compat.py) | Dibersihkan menjadi modul verifikasi `PySide6` murni tanpa patch Windows 7. |
| [`src/ui/main_window.py`](../src/ui/main_window.py) | Menghapus elemen gambar `bell_badge.png` di sebelah kiri tulisan `"BEL SEKOLAH OTOMATIS"`. |
| [`BelOtomatisSekolah.spec`](../BelOtomatisSekolah.spec) | Konfigurasi tunggal PyInstaller `onedir` (Python 3.11 + PySide6) dengan blokir eksplisit terhadap `PySide2` & `shiboken2`. |
| [`installer/BelOtomatisSekolah.iss`](../installer/BelOtomatisSekolah.iss) | Konfigurasi Inno Setup 6 (`MinVersion=10.0`, `MyAppVersion="1.2.0"`). |
| [`build_release.py`](../build_release.py) | Skrip build otomatis tunggal Windows 10/11 dengan verifikasi kemurnian biner `python311.dll` + `PySide6`. |
| [`requirements.txt`](../requirements.txt) | Dependensi murni Windows 10/11 (`PySide6>=6.6.0`, `pytest>=8.0.0`, `pyinstaller>=6.0.0`). |
| [`tests/conftest.py`](../tests/conftest.py) | Dipulihkan ke impor langsung `PySide6`. |
| [`tests/test_executable_launch.py`](../tests/test_executable_launch.py) | Pengujian peluncuran executable dan pemeriksaan kemurnian dependensi Windows 10/11. |
| [`tests/test_installed_executable.py`](../tests/test_installed_executable.py) | Pengujian paket `BelOtomatisSekolah_Setup_v1.2.0.exe`, `BelOtomatisSekolah_Portable_v1.2.0.zip`, dan instalasi terisolasi. |
| [`docs/BUILD_DAN_INSTALASI.md`](BUILD_DAN_INSTALASI.md) | Pembaruan dokumentasi build dan instalasi ke versi `1.2.0`. |

### B. Cadangan & Arsip yang Disimpan Aman
- **Cadangan Kode Sumber**:
  - `backups_source/source_backup_v1.0.0.zip` (`150,289 bytes`)
  - `backups_source/source_backup_v1.0.1_pre_dual_variant.zip` (`158,117 bytes`)
  - `backups_source/source_backup_v1.1.0_pre_win10_11_restore.zip` (`406,726 bytes`)
- **Arsip Konfigurasi Historis (`backups_source/archive_win7_configs/`)**:
  - `BelOtomatisSekolah_Win7.spec`, `BelOtomatisSekolah_DiagWin7.spec`, `BelOtomatisSekolah_Win10_11.spec`
  - `BelOtomatisSekolah_Win7.iss`, `BelOtomatisSekolah_Win10_11.iss`
  - `diag_win7.py`, `build_win7_compatible.bat`, `requirements-win7.txt`
  - `win7_binary_audit.py`, `test_win7_binary_audit.py`, `qt_compat_win7.py`, `bell_badge.png`

---

## 3. Hasil Pengujian Regresi & Verifikasi Fitur

Seluruh pengujian otomatis dijalankan menggunakan `pytest` pada Python `3.11.9`:
- **Total Tes**: `115 passed, 0 failed, 0 skipped`
- **Cakupan Verifikasi**:
  1. **Peluncuran & Kemurnian Biner (`test_executable_launch.py`, `test_installed_executable.py`)**:
     - Memastikan `_internal/python311.dll` dan `_internal/PySide6` tersedia lengkap.
     - Memastikan **tidak ada** berkas `python38.dll`, `PySide2`, `shiboken2`, atau `Qt5*.dll`.
  2. **Penjadwalan Bel & Simulasi Sehari Penuh (`test_scheduler.py`, `test_full_day_simulation.py`)**:
     - Eksekusi jadwal otomatis tepat waktu, pencegahan duplikasi bel setelah restart, dan pergantian profil jadwal (`Reguler`, `Ramadan`, `Ujian`, `Kustom`).
  3. **Pemutar Audio & Tombol Manual (`test_audio_player.py`, `test_ui_buttons_and_audio.py`)**:
     - Pemutaran MP3/WAV, tombol bel manual (`BEL A`–`BEL N`, `TES 1`–`TES 5`), tombol `Stop`, dan pengaturan volume.
  4. **Kontrol ON/OFF, Login Pengelola, & Logout (`test_panel_redesign_and_auth.py`, `test_autostart_and_shutdown.py`)**:
     - Tombol `ON` / `OFF` scheduler, autentikasi password pengelola, logout kembali ke halaman utama tanpa menutup aplikasi, serta penanganan shutdown Windows.
  5. **Database & Backup/Restore (`test_database.py`, `test_backup_restore.py`)**:
     - Inisialisasi SQLite di `%APPDATA%\BelOtomatisSekolah\data\bel_sekolah.db`, penyalinan 19 audio bawaan ke `%APPDATA%\BelOtomatisSekolah\sounds\`, serta pencadangan dan pemulihan arsip `.zip`.

---

## 4. Artefak Distribusi Resmi v1.2.0

| Paket Distribusi | Lokasi Berkas | Ukuran | Checksum SHA-256 |
|---|---|---|---|
| **Windows Setup Installer (`.exe`)** | `release/BelOtomatisSekolah_Setup_v1.2.0.exe` | `45,62 MB` (`47.834.629 bytes`) | `55ec5b658b39aadfbefab47d2b18ad866f7067ecd8ddd698641a5eed0658d187` |
| **Paket Portable (`.zip`)** | `release/BelOtomatisSekolah_Portable_v1.2.0.zip` | `79,79 MB` (`83.666.198 bytes`) | `4dca928468b936588f2e4ca9cdb463c0d1f848e45cedf30d257ca44bffc07bd0` |
| **Standalone Executable (`onedir`)** | `dist/BelOtomatisSekolah/BelOtomatisSekolah.exe` | `1,87 MB` (`1.957.117 bytes`) | `06fa0a2707a6dbe9e409d8f114556f03d4989593a21ee8187cae9217574cd4da` |
| **Informasi Rilis Resmi** | `release/RELEASE_INFO_v1.2.0.txt` | `1,6 KB` | - |

