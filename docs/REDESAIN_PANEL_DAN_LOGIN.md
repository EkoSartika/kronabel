# LAPORAN REDESAIN FINAL — PANEL KECIL, SETTING LOGIN, JADWAL BERKODE
**Proyek**: Bel Otomatis Sekolah (Windows Desktop)  
**Versi**: 1.0.0  
**Tanggal Rilis**: 28 Oktober 2026  
**Status**: Lulus Pengujian 100% (98/98 Pengujian)

---

## 1. RINGKASAN EKSEKUTIF

Proyek Bel Otomatis Sekolah telah disempurnakan secara menyeluruh sesuai kebutuhan operasional sekolah modern:
1. **Panel Utama Ringkas & Proporsional**: Menggantikan tampilan lama yang melebar/penuh dengan jendela panel desktop ringkas berukuran **740 × 380 piksel**. Aplikasi tidak lagi otomatis memenuhi layar (*non-maximized*), dapat digeser dan diubah ukurannya (*resizable*) secara bebas oleh operator.
2. **Keamanan Area Pengelola (Setting Wajib Login)**: Seluruh fungsi konfigurasi krusial (jadwal, profil, pustaka audio, pengaturan, riwayat, dan backup/restore) diproteksi di balik dialog otentikasi. Sistem menggunakan hashing kata sandi standar industri **PBKDF2-HMAC-SHA256 (100.000 iterasi)** dengan salt acak 16-byte cryptographically secure. Sistem tidak menyimpan password default dalam kode sumber (*zero hardcoded password*).
3. **Pustaka Lagu Berkode Unik**: Setiap rekaman audio memiliki kode identifikasi ringkas (seperti `BEL 1`, `BEL A`, `APL`, dsb.) yang unik dan langsung dipetakan ke tombol manual pada panel utama. Penghapusan lagu dilengkapi pengecekan dampak terhadap jadwal yang sedang aktif.
4. **Input Jadwal Terpadu Per Hari**: Halaman jadwal di Area Pengelola mengadopsi format tabel per hari (Senin–Sabtu) dengan penyuntingan langsung (*inline editing* tanpa popup bertumpuk), dilengkapi fitur salin jadwal antar-hari dan validasi format jam 24 jam (`HH:mm`).
5. **Perlindungan Data Lama Pengguna**: Migrasi skema SQLite dilakukan secara non-destruktif (*fail-safe migration*). Basis data asli pengguna di `%APPDATA%\BelOtomatisSekolah\data\bel_sekolah.db` tetap 100% utuh tanpa kehilangan riwayat, jadwal, atau profil yang sudah ada.

---

## 2. ARSITEKTUR & TATA LETAK PANEL UTAMA

### 2.1 Tata Letak Visual
Panel utama mengusung palet warna biru-putih modern dengan kontras tinggi yang sangat mudah dibaca dari jarak jauh:
- **Header Ringkas**: Menampilkan nama aplikasi "Bel Otomatis Sekolah", ikon status profil aktif (misal: `[Reguler]`), serta tombol **Setting ⚙** di pojok kanan atas.
- **Kolom Kiri (Kontrol & Jam)**:
  - **Jam Digital Besar**: Teks jam digital berukuran 38px dengan font monospace tebal berlatar gradien biru gelap (`#0f172a` ke `#1e293b`), dilengkapi detik dan indikator status hari/tanggal Indonesia.
  - **Status Scheduler & Countdown**: Indikator apakah scheduler otomatis sedang AKTIF / NONAKTIF serta hitung mundur ke bel berikutnya.
  - **Tombol Kontrol Utama**:
    - Tombol **ON** (Hijau `#10b981`): Mengaktifkan pemutaran otomatis terjadwal.
    - Tombol **OFF** (Merah `#ef4444`): Menghentikan pemutaran otomatis.
  - **Tombol Bel Manual Berkode**: Tombol-tombol berkode lagu (misal: `BEL 1`, `BEL A`, `APL`) yang di-generate dinamis dari pustaka lagu. Menekan tombol manual langsung membunyikan audio terkait dan mencatat ke riwayat dengan mode `MANUAL` tanpa mengganggu alur hitung mundur scheduler.
- **Kolom Kanan (Daftar Jam & Kode Lagu)**:
  - Panel vertikal berlatar belakang kontras gelap (`#0f172a`) dengan daftar jam (`HH:mm:ss`), kode lagu, dan nama kegiatan untuk hari ini.
  - Baris jadwal bel yang akan berbunyi berikutnya disorot (*highlight*) dengan warna emas/kuning berlatar terang.

### 2.2 Dimensi Jendela
- **Target Awal**: 740 × 380 piksel.
- **Ukuran Minimum**: 680 × 340 piksel.
- **Status Jendela**: `showNormal()` (tidak pernah otomatis dimaksimalkan).
- **Resizable**: Ya, operator dapat menyesuaikan skala jendela sesuai ruang desktop.

---

## 3. SISTEM KEAMANAN & PENGELOLA (SETTING LOGIN)

### 3.1 Spesifikasi Kriptografi Otentikasi
- **Algoritme**: PBKDF2-HMAC-SHA256.
- **Iterasi**: 100.000 iterasi hashing (standar OWASP).
- **Salt**: 16-byte acak dari `os.urandom(16)`, dikonversi ke format hex.
- **Penyimpanan**: Tabel `app_settings` lokal dengan kunci:
  - `admin_password_hash`
  - `admin_password_salt`
- **Keamanan Offline**: Bekerja 100% lokal tanpa dependensi cloud atau backend internet luar.

### 3.2 Alur Otentikasi & Inisialisasi
1. **Inisialisasi Pertama Kali**:
   - Jika aplikasi dijalankan dan belum ada kata sandi yang disetel, saat tombol **Setting** diklik, dialog **Inisialisasi Password Pengelola** akan muncul otomatis.
   - Operator memasukkan kata sandi pengelola baru (minimal 4 karakter) dan konfirmasi.
   - Hash dan salt langsung disimpan secara aman.
2. **Proses Login Rutin**:
   - Operator mengeklik tombol **Setting**.
   - Muncul modal **Login Pengelola**.
   - Jika kata sandi cocok, Area Pengelola (`AdminWindow`) terbuka secara independen.
   - Jika gagal, ditampilkan pesan kesalahan yang jelas tanpa membocorkan rincian sistem.
3. **Area Pengelola (Admin Window)**:
   - Dilengkapi menu tab sidebar modern:
     1. **Jadwal Bel**: Batch editor per hari.
     2. **Pustaka Lagu**: Manajemen audio berkode.
     3. **Profil Jadwal**: Pengaturan profil Reguler, Ramadan, Ujian, dll.
     4. **Riwayat Bel**: Pencatatan log putar otomatis & manual.
     5. **Pengaturan & Backup**: Pengaturan umum, backup `.belzip`, dan restore data.
   - **Tombol Ganti Password**: Memungkinkan pengelola memperbarui kata sandi dengan verifikasi kata sandi lama.
   - **Tombol Logout**: Mengunci kembali area pengelola dan menutup jendela admin secara bersih.

---

## 4. JADWAL TABEL PER HARI (BATCH INLINE EDITING)

Halaman Jadwal di Area Pengelola dirancang agar pengelola sekolah dapat mengisi jadwal satu minggu dengan cepat:
- **Pilihan Profil & Hari**: Dropdown profil jadwal aktif dan pilihan hari **Senin s/d Sabtu**.
- **Penyuntingan Langsung (*Inline*)**:
  - Kolom **Jam Bel**: Input jam format 24 jam dengan pemilih waktu (`QTimeEdit`).
  - Kolom **Kode Lagu**: Dropdown cerdas berisi daftar kode lagu aktif (misal: `BEL 1 - Jam Pelajaran 1`).
  - Kolom **Nama Kegiatan**: Text edit langsung di sel tabel (misal: "Upacara Bendera", "Masuk Kelas").
  - Kolom **Status Aktif**: Checkbox centang aktif/nonaktif di baris tabel.
  - Kolom **Aksi Hapus**: Tombol hapus baris dengan konfirmasi.
- **Tombol Tambah Baris**: Menambahkan baris kosong di akhir tabel secara instan.
- **Tombol Simpan Perubahan**: Memvalidasi seluruh baris, memastikan format jam valid, kode audio terdaftar, serta mendeteksi konflik duplikasi jam dalam satu hari sebelum menyimpan transaksi ke database.
- **Tombol Salin Hari Lain**: Memungkinkan penduplikasian susunan jam dan kode bel dari hari tertentu (misal Senin) ke hari lain (misal Selasa atau Kamis) dengan satu klik.

---

## 5. PUSTAKA LAGU BERKODE & VALIDASI DAMPAK JADWAL

- **Struktur Kolom**:
  - `Kode Lagu`: Kode unik alfanumerik (misal: `BEL 1`, `BEL A`, `APL`).
  - `Nama Lagu`: Deskripsi judul lagu / bel (misal: "Bel Masuk Kelas").
  - `Nama File`: Nama file asli (misal: `bel_sekolah.mp3`).
  - `Status File`: Indikator ketersediaan file fisik pada direktori `%APPDATA%\BelOtomatisSekolah\sounds\`.
  - `Putar Uji`: Tombol untuk menguji suara audio langsung ke speaker.
  - `Aksi`: Tombol Edit metadata dan Hapus lagu.
- **Import Lagu**:
  - Mendukung file audio `.mp3` dan `.wav`.
  - File disalin secara aman ke penyimpanan persisten terisolasi dengan nama berbasis UUID untuk menghindari konflik nama file.
- **Proteksi Hapus Lagu (Impact Verification)**:
  - Sebelum menghapus rekaman lagu, sistem memeriksa tabel `schedules`.
  - Jika lagu masih dipakai oleh jadwal tertentu, sistem menampilkan dialog peringatan daftar jadwal yang terdampak dan meminta konfirmasi tegas dari operator.

---

## 6. MIGRASI & INTEGRITAS DATABASE

### 6.1 Skema Kolom Baru
Pada tabel `audio_files`, ditambahkan kolom `code TEXT UNIQUE`.
Pada model `Schedule`, ditambahkan relasi `audio_code` yang ditarik via `LEFT JOIN` otomatis.

### 6.2 Prosedur Migrasi Aman
Fungsi migrasi `DatabaseManager._run_migrations_if_needed()` berjalan secara otomatis saat aplikasi dibuka:
1. Memeriksa keberadaan kolom `code` melalui `PRAGMA table_info(audio_files)`.
2. Jika belum ada:
   - Menjalankan `ALTER TABLE audio_files ADD COLUMN code TEXT`.
   - Mengisi otomatis kode default berurutan (`BEL 1`, `BEL 2`, dst.) untuk lagu-lagu lama agar tidak ada nilai `NULL`.
   - Membuat indeks unik `CREATE UNIQUE INDEX IF NOT EXISTS idx_audio_files_code ON audio_files(code)`.
3. Migrasi bersifat *idempotent* dan tidak menyentuh tabel lain (`profiles`, `schedules`, `bell_logs`, `app_settings`).

### 6.3 Backup Pra-Migrasi
Sebelum migrasi dieksekusi pada basis data nyata pengguna, backup instan telah disimpan pada:
`%APPDATA%\BelOtomatisSekolah\data\backups\bel_sekolah_pre_redesign.db`

---

## 7. HASIL PENGUJIAN KOMPREHENSIF

Seluruh rangkaian pengujian unit, integrasi, simulasi hari penuh, dan peluncuran executable biner telah dijalankan menggunakan `pytest`:

```text
============================= 98 passed in 16.02s =============================
```

### Rincian Modul Uji:
| Modul Pengujian | Jumlah Tes | Status | Keterangan |
|---|---|---|---|
| `test_panel_redesign_and_auth.py` | 7 | LULUS | Dimensi panel kecil, auth PBKDF2, tombol ON/OFF, bel manual berkode, batch schedule, audio code impact, admin window. |
| `test_executable_launch.py` | 2 | LULUS | Verifikasi startup biner `dist/BelOtomatisSekolah.exe` dari working dir sembarang. |
| `test_installed_executable.py` | 1 | LULUS | Verifikasi peluncuran hasil instalasi Inno Setup di folder terisolasi. |
| `test_scheduler.py` | 11 | LULUS | Pencegahan bel ganda, countdown, rollover hari, pengabaian jadwal nonaktif, penanganan crash audio. |
| `test_audio_player.py` | 6 | LULUS | Playback MP3/WAV, concurrency lock, volume control, device error resilience. |
| `test_backup_restore.py` | 9 | LULUS | Pembuatan zip backup, proteksi zip-slip, validasi integritas database & audio. |
| `test_full_day_simulation.py` | 1 | LULUS | Simulasi siklus 24 jam penuh jadwal sekolah. |
| `test_schedules.py` | 6 | LULUS | Normalisasi waktu, validasi hari, deteksi konflik jadwal, salin jadwal. |
| `test_profiles.py` | 7 | LULUS | Penggantian profil aktif, pencegahan hapus profil aktif, profil kustom. |
| `test_history.py` | 4 | LULUS | Filter tanggal, pencarian nama kegiatan, paginasi riwayat. |
| `test_settings.py` | 3 | LULUS | Persistensi setelan aplikasi & integrasi UI. |
| `test_table_visibility.py` | 5 | LULUS | Visibilitas teks dan tombol tabel pada styling Windows. |
| `test_ui_buttons_and_audio.py` | 4 | LULUS | Dimensi tombol aksi tabel, peringatan audio hilang. |
| `test_ui_responsive.py` | 4 | LULUS | Responsivitas jendela pada resolusi laptop standar. |
| `test_ui_pages.py` | 8 | LULUS | Interaksi dialog dan sinkronisasi halaman admin. |
| `test_bell_logs.py` | 3 | LULUS | Pencatatan otomatis dan manual idempotensi. |
| `test_clock_service.py` | 2 | LULUS | Akurasi jam sistem dan jam simulasi. |
| `test_database.py` | 3 | LULUS | Inisialisasi basis data dan seeding profil awal. |
| `test_operational_robustness.py` | 5 | LULUS | Pelepasan sumber daya saat aplikasi ditutup. |
| `test_ui_dashboard.py` | 3 | LULUS | Inisialisasi dashboard dan navigasi cepat. |
| `test_ui_launch.py` | 1 | LULUS | Peluncuran GUI dasar. |
| **TOTAL** | **98** | **100% LULUS** | **Semua fitur lulus verifikasi tanpa regresi** |

---

## 8. ARTEFAK RILIS & DISTRIBUSI

Proses build rilis otomatis melalui `build_release.py` telah menghasilkan berkas biner standalone dan setup installer resmi:

1. **Standalone Executable**:
   - Lokasi: `D:\BelOtomatisSekolah\dist\BelOtomatisSekolah\BelOtomatisSekolah.exe`
   - Ukuran: **1.79 MB**
   - SHA-256: `aeda87102ca2f7a29de776c5d9da986b392fc6659f38cf93973dc788969d96be`
   - Keterangan: Dapat dijalankan langsung secara mandiri tanpa memerlukan instalasi Python di komputer target.

2. **Windows Setup Installer (Inno Setup)**:
   - Lokasi: `D:\BelOtomatisSekolah\release\BelOtomatisSekolah_Setup_v1.0.0.exe`
   - Ukuran: **37.60 MB**
   - SHA-256: `6001ed41214c9e153998ed2cdcf146c4e0624bdd8641698cdf7c590ce250e5e1`
   - Keterangan: Installer lengkap berlisensi, shortcut Desktop & Start Menu, opsi uninstaller bersih, serta proteksi data pengguna di `%APPDATA%`.

---

## 9. DOKUMENTASI VISUAL (SCREENSHOT)

Tangkapan layar hasil redesain telah disimpan di direktori `docs/screenshots/`:
1. `panel_utama_normal.png`: Jendela panel desktop kecil (740 × 380 px) dengan jam besar, kontrol ON/OFF, tombol Setting, tombol kode manual, dan daftar jadwal di sebelah kanan.
2. `dialog_login.png`: Modal autentikasi kata sandi pengelola sebelum memasuki Area Pengelola.
3. `admin_area_jadwal.png`: Area pengelola dengan tabel penyuntingan jadwal inline per hari (Senin–Sabtu).
4. `admin_area_audio.png`: Area pengelola pustaka lagu dengan daftar kode unik, pemutar uji, dan validasi dampak jadwal.

---
*Dokumentasi ini disusun secara otomatis oleh Sistem Pemeliharaan Bel Otomatis Sekolah pada 28 Oktober 2026.*
