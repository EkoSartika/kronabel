# LAPORAN BUGFIX PRIORITAS — VISIBILITAS DATA TABEL
## Aplikasi: Bel Otomatis Sekolah v1.0.0 (Windows Desktop)
**Tanggal Verifikasi**: 28 Oktober 2026  
**Status**: SELESAI & TERVERIFIKASI PENUH (83/83 Pengujian Lulus)

---

## 1. Ringkasan Eksekutif

Setelah aplikasi dipasang menggunakan installer Windows, dilaporkan bahwa data tabel pada halaman **Jadwal Bel**, **Profil Jam Pelajaran**, dan **Audio Bel** terlihat memiliki baris dan tombol aksi, namun informasi teksnya tidak terbaca.

Investigasi mendalam dan visual membuktikan bahwa **data pada database pengguna 100% utuh dan tidak hilang**. Akar masalah berada pada benturan stylesheet antarmuka (UI) Qt di mana teks sel tidak memiliki definisi warna gelap eksplisit (`color: #0f172a`), serta adanya efek cascading CSS dari kartu pembungkus (`QFrame`) yang tidak menggunakan selektor ID sehingga merusak pewarnaan dan tata letak header tabel (`QHeaderView::section`).

Perbaikan telah diterapkan secara non-destruktif, didukung 5 tes regresi visibilitas baru, seluruh 83/83 unit & integration test lulus, serta executable mandiri dan installer Windows Inno Setup telah dibuild ulang dan diverifikasi secara nyata.

---

## 2. Akar Masalah yang Terbukti (Proven Root Cause)

Melalui pemeriksaan visual dan inspeksi runtime terhadap instance antarmuka, ditemukan 2 penyebab utama yang terjadi secara bersamaan:

### A. Ketiadaan Warna Foreground Gelap pada Sel Tabel (White-on-White Text)
1. Pada `schedule_page.py`, `profile_page.py`, dan `audio_page.py`, stylesheet lokal `QTableWidget` hanya menyetel `background-color: #ffffff;` tanpa menyetel `color: #0f172a;` atau `QTableWidget::item { color: #0f172a; }`.
2. Saat item sel dibuat (`QTableWidgetItem`), kolom non-status (hari, jam, nama kegiatan, audio, nama profil, deskripsi, total jadwal, file audio, path) tidak diberikan pemanggilan `setForeground(...)`.
3. Pada sistem operasi Windows dengan style bawaan (seperti WindowsVista style), teks sel mewarisi warna default yang berbenturan dengan latar belakang putih murni (`#ffffff`), sehingga teks menjadi tidak kontras/tak terbaca.
4. Sebaliknya, item status ("★ AKTIF", "Tersedia", "Aktif") secara sengaja diberi `setForeground(Qt.blue)` atau `Qt.darkGreen`, dan tombol aksi memiliki stylesheet tersendiri, sehingga hanya status dan tombol aksi yang terlihat oleh pengguna.

### B. Cascading Stylesheet QFrame Merusak Header Tabel (Header View Section)
1. Tabel pada ketiga halaman tersebut dibungkus di dalam kartu `table_card = QFrame()`.
2. Kartu tersebut diberi stylesheet dengan selektor tipe umum:
   ```css
   QFrame {
       background-color: #ffffff;
       border: 1px solid #e2e8f0;
       border-radius: 10px;
       padding: 12px;
   }
   ```
3. Dalam hierarki kelas Qt: `QTableWidget` mewarisi `QFrame`, dan `QHeaderView` mewarisi `QAbstractItemView` yang juga mewarisi `QFrame`.
4. Akibat selektor tidak dibatasi ID spesifik (`#TableCard`), aturan `padding: 12px; border-radius: 10px; background-color: #ffffff;` mengalir (cascade) ke `QHeaderView`, merusak tata letak section header dan menimpa teks header kolom menjadi putih/tak terlihat.
5. Pada Halaman Riwayat (`history_page.py`), tabel tidak dibungkus dengan selektor generic `QFrame` dan memiliki styling warna `#1e293b` lengkap, sehingga teks header dan teks sel riwayat selalu tampil dengan jelas.

---

## 3. Berkas yang Diubah

| Berkas | Perubahan yang Dilakukan |
| :--- | :--- |
| `src/ui/main_window.py` | Menambahkan stylesheet global untuk `QTableWidget`, `QTableView`, `QTableWidget::item`, `QHeaderView::section`, `QComboBox`, dan `QLineEdit` dengan latar belakang `#ffffff` dan teks gelap `#0f172a` / `#334155`. |
| `src/ui/schedule_page.py` | 1. Mengubah selektor kartu menjadi ID spesifik `QFrame#ControlsCard` dan `QFrame#TableCard`.<br>2. Menambahkan `color: #0f172a;` dan styling section header tabel.<br>3. Menetapkan `setForeground(QColor("#0f172a"))` secara eksplisit pada item hari, waktu, nama kegiatan, dan audio. |
| `src/ui/profile_page.py` | 1. Mengubah selektor kartu menjadi `QFrame#HeaderCard` dan `QFrame#TableCard`.<br>2. Menambahkan `color: #0f172a;` dan styling section header tabel.<br>3. Menetapkan `setForeground(QColor("#0f172a"))` secara eksplisit pada nama profil, deskripsi, dan total jadwal. |
| `src/ui/audio_page.py` | 1. Mengubah selektor kartu menjadi `QFrame#HeaderCard`, `QFrame#ControlsCard`, dan `QFrame#TableCard`.<br>2. Menambahkan `color: #0f172a;` dan styling section header tabel.<br>3. Menetapkan `setForeground(QColor("#0f172a"))` secara eksplisit pada nama label audio, file asli, dan path penyimpanan. |
| `src/ui/dashboard.py` | Mengubah selektor kartu tabel jadwal hari ini menjadi `QFrame#TodayScheduleCard` dan menetapkan foreground warna gelap pada item tabel dashboard. |
| `installer/BelOtomatisSekolah.iss` | Menambahkan `PrivilegesRequired=lowest` dan `PrivilegesRequiredOverridesAllowed=dialog commandline` untuk fleksibilitas instalasi pengguna biasa/admin. |
| `tests/test_table_visibility.py` | Berkas pengujian regresi baru yang memeriksa secara ketat isi teks, header, dan luminansi warna teks pada seluruh tabel. |
| `tests/test_installed_executable.py` | Berkas pengujian runtime untuk executable hasil instalasi Inno Setup. |

---

## 4. Hasil Pengujian Sebelum dan Sesudah Perbaikan

### Sebelum Perbaikan
- **Total Test**: 75 test (Tahap 5).
- **Pengujian Tampilan**: Hanya memeriksa `rowCount()` atau keberadaan baris, tidak memverifikasi apakah teks sel memiliki luminansi kontras dan apakah judul kolom header tampil di layar.

### Sesudah Perbaikan
- **Total Test**: **83 test** (Seluruhnya **LULUS / PASSED 100%**, waktu eksekusi: 9.32 detik).
  ```text
  ============================= test session starts =============================
  platform win32 -- Python 3.11.9, pytest-9.2.0, pluggy-1.7.0
  rootdir: D:\BelOtomatisSekolah
  collected 83 items

  tests/test_audio_player.py (8 test) ................................. PASSED
  tests/test_backup_restore.py (9 test) ............................... PASSED
  tests/test_bell_logs.py (3 test) .................................... PASSED
  tests/test_clock_service.py (2 test) ................................ PASSED
  tests/test_database.py (3 test) ..................................... PASSED
  tests/test_executable_launch.py (2 test) ............................ PASSED
  tests/test_full_day_simulation.py (1 test) .......................... PASSED
  tests/test_history.py (4 test) ...................................... PASSED
  tests/test_installed_executable.py (1 test) ......................... PASSED
  tests/test_operational_robustness.py (5 test) ....................... PASSED
  tests/test_profiles.py (7 test) ..................................... PASSED
  tests/test_scheduler.py (12 test) ................................... PASSED
  tests/test_schedules.py (6 test) .................................... PASSED
  tests/test_settings.py (3 test) ..................................... PASSED
  tests/test_table_visibility.py (5 test) ............................. PASSED
  tests/test_ui_dashboard.py (3 test) ................................. PASSED
  tests/test_ui_launch.py (1 test) .................................... PASSED
  tests/test_ui_pages.py (8 test) ..................................... PASSED

  ============================= 83 passed in 9.32s ==============================
  ```

---

## 5. Hasil Pemeriksaan Visual Antarmuka

| Halaman | Hasil Verifikasi Visual | Status |
| :--- | :--- | :---: |
| **Jadwal Bel** | Judul header ("Hari", "Waktu", "Nama Kegiatan", "File Audio", "Status", "Aksi") terlihat tebal dan jelas. Baris "Senin", "07:00:00", "Jam Ke 1", "(Default/Belum Dipilih)", status "Aktif", dan tombol Matikan/Edit/Hapus terbaca sempurna dengan latar belakang putih. | **OK** |
| **Profil Jam Pelajaran** | Judul header ("Nama Profil", "Deskripsi", "Total Jadwal", "Status", "Aksi") tampil jelas. Baris profil "Reguler", "Ramadan", "Senin", "Ujian", deskripsi, total jadwal ("1 Jadwal", "0 Jadwal"), status "★ AKTIF", serta tombol aksi terlihat tajam. | **OK** |
| **Audio Bel** | Judul header ("Nama Label Audio", "File Asli", "Path Penyimpanan Persisten", "Status Berkas", "Aksi") tampil jelas. Kolom nama label "Jam Pelajaran 1", file asli "Jam Pelajaran 1.mp3", path penyimpanan, badge status "Tersedia", dan tombol Putar/Hapus terlihat jelas. | **OK** |
| **Riwayat Bel** | Header dan baris data riwayat tanggal, waktu, nama kegiatan, status, dan mode tetap tampil kontras dan tajam. | **OK** |
| **Dashboard** | Header "Jadwal Hari Ini" ("Waktu", "Kegiatan Bel", "File Audio", "Status") dan isi jadwal hari aktif tampil jelas tanpa terpotong. | **OK** |

---

## 6. Perlindungan Data Pengguna

Pemeriksaan integritas terhadap database aktual pengguna pada `%APPDATA%\BelOtomatisSekolah\data\bel_sekolah.db` sebelum dan sesudah perbaikan:

- **Tabel `profiles`**: 4 record (`Reguler`, `Ramadan`, `Ujian`, `Senin`) — **Utuh 100%**.
- **Tabel `schedules`**: 1 record (`Senin`, `07:00:00`, `Jam Ke 1`, status aktif) — **Utuh 100%**.
- **Tabel `audio_files`**: 1 record (`Jam Pelajaran 1`, `Jam Pelajaran 1.mp3`) — **Utuh 100%**.
- **Tabel `bell_logs`**: 1 record riwayat bel — **Utuh 100%**.
- **Tabel `app_settings`**: 3 konfigurasi aplikasi — **Utuh 100%**.
- **Folder audio**: `%APPDATA%\BelOtomatisSekolah\sounds\Jam Pelajaran 1.mp3` — **Ada & Utuh**.

> **Konfirmasi Keamanan**: Tidak ada reset database, tidak ada pembersihan tabel (TRUNCATE/DROP), dan seluruh pengujian menggunakan database sementara (`temp_db`) yang terisolasi.

---

## 7. Hasil Build & Lokasi Artefak Rilis Baru

Build ulang telah berhasil dijalankan menggunakan `build_release.py` dan Inno Setup Compiler (`ISCC.exe`):

1. **Standalone Executable Binary**:
   - **Lokasi**: `D:\BelOtomatisSekolah\dist\BelOtomatisSekolah\BelOtomatisSekolah.exe`
   - **Ukuran**: 1.827.654 bytes (1,74 MB)
   - **Waktu Build**: 28 Oktober 2026, 12:27:10
   - **SHA-256**: `9310818f8e7128b733cddf73e54eac05271025c6560571044d43d00217457b42`
   - **Verifikasi**: Lulus peluncuran mandiri, single-instance lock, dan koneksi database.

2. **Windows Setup Installer**:
   - **Lokasi**: `D:\BelOtomatisSekolah\release\BelOtomatisSekolah_Setup_v1.0.0.exe`
   - **Ukuran**: 39.370.437 bytes (37,55 MB)
   - **Waktu Build**: 28 Oktober 2026, 12:31:13
   - **SHA-256**: `c71610353183ced76e1769ed0ae8c8408572b6d8ec258fc7693dfb7f304bf95d`
   - **Verifikasi**: Berhasil diuji instalasi silent pada direktori terisolasi, menghasilkan biner executable lengkap beserta dependensi runtime dan uninstaller.
