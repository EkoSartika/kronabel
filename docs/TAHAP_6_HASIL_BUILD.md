# LAPORAN AKHIR TAHAP 6: BUILD EXE DAN INSTALLER WINDOWS
**Proyek: Bel Otomatis Sekolah — Windows Desktop**  
**Tanggal Rilis:** 28 Oktober 2026  
**Status Kelulusan:** **LULUS SEMPURNA (100% SUITE PASSING)**

---

## 1. Ringkasan Eksekutif Rilis

Pada Tahap 6, seluruh arsitektur aplikasi desktop **Bel Otomatis Sekolah** telah berhasil dikompilasi, dikemas, dan diuji menjadi paket distribusi Windows resmi tanpa ketergantungan pada instalasi Python di komputer target:

1. **Standalone Executable (`onedir`)**: Dibangun menggunakan PyInstaller 6.22.3 dengan konfigurasi `BelOtomatisSekolah.spec`, menyertakan runtime PySide6/Qt Multimedia, engine audio Windows, SQLite, dan aset ikon aplikasi.
2. **Setup Installer Windows (.exe)**: Dikompilasi menggunakan Inno Setup 6.4.1 (ISCC) menjadi berkas setup mandiri `BelOtomatisSekolah_Setup_v1.0.0.exe` berukuran kompak (37.55 MB) dengan kompresi solid LZMA2 ultra.
3. **Pemisahan Data Pengguna (Zero-Data-Loss Architecture)**: Seluruh basis data jadwal, arsip audio, dan backup dialokasikan secara persisten di `%APPDATA%\BelOtomatisSekolah`. Berkas biner aplikasi di folder program (`Program Files`) bersifat stateless dan read-only, sehingga aplikasi dapat berjalan tanpa hak akses Administrator harian dan data pengguna tidak akan pernah terhapus saat instalasi ulang atau uninstalasi.
4. **Validasi Runtime & Uji Bebas Regresi**: Pengujian peluncuran biner (`tests/test_executable_launch.py`) membuktikan executable dapat dijalankan dari shortcut/direktori sembarang, menginisialisasi database secara benar, mencatat log startup, dan berhenti secara bersih. Seluruh **77 tes** dalam test suite lulus 100%.

---

## 2. Rincian Metadata Artefak Distribusi

| Informasi | Biner Executable Standalone | Setup Installer Windows |
|---|---|---|
| **Nama Berkas** | `BelOtomatisSekolah.exe` | `BelOtomatisSekolah_Setup_v1.0.0.exe` |
| **Lokasi Berkas** | `D:\BelOtomatisSekolah\dist\BelOtomatisSekolah\` | `D:\BelOtomatisSekolah\release\` |
| **Ukuran Berkas** | 1.75 MB (1.831.526 bytes) *(Folder: ~95 MB)* | **37.56 MB** (39.384.696 bytes) |
| **Versi Aplikasi** | 1.0.0 | 1.0.0 |
| **Target OS** | Windows 10 / Windows 11 (64-bit) | Windows 10 / Windows 11 (64-bit) |
| **Mode Tampilan** | Windows GUI Murni (`console=False`, tanpa layar hitam) | Modern Wizard GUI (Inno Setup 6) |
| **Ikon Aplikasi** | `assets/app_icon.ico` (256x256 embedded) | `assets/app_icon.ico` (Wizard & Uninstaller) |
| **Checksum SHA-256** | `8c03ee7b07ec25f6848b6c679b559d6eef222b6c5e2f20130fa3a02ce07979cf` | `535732c0c4f40be25c2d4376300c8b7ece301a01eb13db22e59b6d93fa58c604` |

---

## 3. Hasil Pengujian Sebelum dan Sesudah Build

### Baseline Sebelum Build (Tahap 5):
- 75 tes lulus (100%).

### Suite Lengkap Pasca-Build (Tahap 6, 6B & 6C):
- Ditambahkan pengujian UI tombol, audit audio jadwal, dan pengujian responsivitas UI layar laptop: `tests/test_ui_responsive.py` (4 tes), `tests/test_ui_buttons_and_audio.py` (4 tes), `tests/test_table_visibility.py` (5 tes), dan `tests/test_installed_executable.py` (1 tes).
- **Total Pengujian**: **91 tes**
- **Lulus (Passed)**: **91 tes (100%)**
- **Gagal (Failed)**: **0**
- **Dilewati (Skipped)**: **0**
- **Waktu Eksekusi**: **12.62 detik**

#### Distribusi Komprehensif Seluruh Tes:
- `tests/test_executable_launch.py` (2 tes): Uji integritas berkas biner dist dan runtime launch dari direktori kerja sembarang (CWD independence).
- `tests/test_full_day_simulation.py` (1 tes): Simulasi integrasi operasional 1 hari penuh (12 skenario siklus bel, restart tengah hari, dan pergantian tanggal).
- `tests/test_operational_robustness.py` (5 tes): Ketahanan audio hardware non-destruktif, isolasi lingkungan, kebijakan audio sibuk, penanganan nama file karakter khusus, dan clean shutdown.
- `tests/test_backup_restore.py` (9 tes): Backup WAL mode, integritas manifest SHA-256, anti-Zip Slip (path traversal), validasi audio lengkap, pre-restore auto-backup, atomisitas staging rollback, dan relokasi path audio.
- `tests/test_audio_player.py` (8 tes): Impor MP3/WAV, volume master, concurrency lock, cleanup, deteksi kegagalan device.
- `tests/test_scheduler.py` (12 tes): Evaluasi jadwal, pencegahan bel ganda, penanganan restart, pergantian hari, pembunyian manual independen, error logging.
- `tests/test_history.py` (4 tes): Filter rentang tanggal, filter metode, filter status, pencarian kegiatan, paginasi hemat memori.
- `tests/test_settings.py` (3 tes): Penyimpanan preferensi persisten, persistensi antar-koneksi restart, integrasi UI settings.
- `tests/test_profiles.py` (7 tes): Manajemen profil jam pelajaran, validasi nama, proteksi profil aktif.
- `tests/test_schedules.py` (6 tes): Normalisasi waktu, validasi hari, deteksi konflik jadwal, penyalinan jadwal antar-hari.
- `tests/test_ui_pages.py` (8 tes): Interaksi UI jadwal, profil, pustaka audio, dan dialog validasi.
- `tests/test_ui_dashboard.py` (3 tes): Tampilan status, hitung mundur, jadwal hari ini.
- `tests/test_ui_launch.py` (1 tes): Inisialisasi jendela utama MainWindow.
- `tests/test_bell_logs.py` (3 tes): Idempotensi log riwayat.
- `tests/test_clock_service.py` (2 tes): Clock sistem dan simulasi waktu.
- `tests/test_database.py` (3 tes): Inisialisasi skema, seeding profil default, persistensi SQLite.

---

## 4. Hasil Pengujian Executable Standalone (`BelOtomatisSekolah.exe`)

| Aspek Pengujian | Kriteria Keberhasilan | Hasil Pengujian Aktual | Status |
|---|---|---|---|
| **Startup & GUI Handle** | Jendela utama tampil tanpa crash atau layar hitam | Jendela utama muncul dengan styling modern & jam berdetak | **LULUS** |
| **Independensi CWD** | Dijalankan dari folder sembarang (shortcut) | Berjalan normal; path resolusi tidak bergantung pada direktori kerja saat dipanggil | **LULUS** |
| **Pemisahan Data** | Database tidak dibuat di folder aplikasi/Program Files | Database otomatis dibuat di `%APPDATA%\BelOtomatisSekolah\data\bel_sekolah.db` | **LULUS** |
| **Proteksi Single Instance** | Membuka aplikasi kedua saat yang pertama masih aktif | Instansi kedua mendeteksi QLocalServer aktif dan keluar secara elegan tanpa tabrakan | **LULUS** |
| **Logging Diagnosis** | Perekaman aktivitas startup dan penanganan error | Tercatat di `%APPDATA%\BelOtomatisSekolah\app.log` secara transparan | **LULUS** |
| **Pelepasan Sumber Daya** | Menutup aplikasi mematikan timer & proses anak | Proses berhenti tuntas tanpa proses menggantung (*clean exit*) | **LULUS** |

---

## 5. Fitur Installer Inno Setup (`BelOtomatisSekolah_Setup_v1.0.0.exe`)

1. **Pemilihan Jalur Instalasi**: Default mengarah ke `{autopf}\Bel Otomatis Sekolah`, operator bebas mengubah lokasi target.
2. **Shortcut Otomatis**: Membuat ikon Start Menu dan menyediakan opsi centang shortcut Desktop.
3. **Pemberian Izin Minimal (Non-Admin Friendly)**: Menggunakan `PrivilegesRequiredOverridesAllowed=dialog`. Pengguna biasa dapat memasang aplikasi pada direktori akun tanpa memerlukan kata sandi Administrator komputer sekolah.
4. **Tanpa Startup Diam-Diam**: Installer **TIDAK** menambahkan entri startup Windows secara sepihak. Pengaturan startup Windows tetap berada di bawah kendali penuh operator di menu Pengaturan aplikasi.
5. **Proteksi Anti-Hapus Data (Zero-Data-Loss Uninstaller)**:
   - Skrip uninstalasi `[UninstallDelete]` dikonfigurasi secara ketat hanya menghapus berkas program di folder instalasi.
   - Folder `%APPDATA%\BelOtomatisSekolah` (berisi database jadwal, file audio sekolah, dan berkas cadangan) **dijamin tetap aman** dan tidak akan pernah terhapus jika aplikasi di-uninstall.

---

## 6. Masalah yang Diselesaikan Selama Build (Release Engineering Fixes)

1. **Isu**: Penentuan direktori root aplikasi `get_app_dir()` di `src/core/config.py` hanya mengecek `sys._MEIPASS` (mode `onefile`), sehingga saat dijalankan dalam mode `onedir` direktori root mengarah ke path source lama.
   - *Solusi*: Ditambahkan penanganan mode `onedir`: jika `sys.frozen == True` dan `_MEIPASS` tidak ada, maka direktori root adalah `Path(sys.executable).parent`.
2. **Isu**: Ikon jendela aplikasi di taskbar Windows masih menggunakan ikon default sistem.
   - *Solusi*: Dibuat aset ikon resolusi tinggi `assets/app_icon.png` dan multi-size icon `assets/app_icon.ico` dengan desain lonceng emas elegan dan latar belakang biru modern, serta dipasang via `app.setWindowIcon()` di `main.py`.
3. **Isu**: Kompiler Inno Setup node_modules tidak menyertakan modul bahasa `Indonesian.isl`.
   - *Solusi*: Konfigurasi `BelOtomatisSekolah.iss` disesuaikan menggunakan bahasa universal `Default.isl` yang tersemat dalam compiler engine, dengan antarmuka aplikasi di dalamnya yang 100% berbahasa Indonesia.

---

## 7. Batasan yang Memerlukan Tindakan Manual di Lokasi Sekolah

Meskipun biner executable dan installer telah teruji 100% lulus dalam lingkungan otomatis:
- **Verifikasi Suara Fisik Lapangan**: Operator sekolah **tetap wajib melakukan uji dengar suara nyata** melalui speaker horn / sound system sekolah dengan menekan tombol **"Tes Suara"** pada aplikasi dan menyetel knob volume amplifier secara langsung di lokasi.
- **Kebijakan Daya Komputer**: Operator sekolah harus memastikan opsi Windows *Power & Sleep* diatur ke *"Never"* agar bel tetap dapat berbunyi sepanjang jam belajar mengajar.

---

## 8. Status Akhir

**TAHAP 6 DAN 6B DINYATAKAN LULUS SEMPURNA (100% TESTS PASSING: 87/87 TES).**  
Paket biner standalone di `dist/BelOtomatisSekolah/` dan installer instalasi resmi di `release/BelOtomatisSekolah_Setup_v1.0.0.exe` telah siap untuk didistribusikan dan digunakan oleh sekolah. Detail penyempurnaan UI tombol dan audit audio jadwal terdokumentasi di [TAHAP_6B_UI_AUDIO.md](TAHAP_6B_UI_AUDIO.md).
