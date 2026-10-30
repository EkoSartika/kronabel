# LAPORAN AKHIR TAHAP 6C: RESPONSIVE UI DAN PENYEMPURNAAN LAYOUT
**Proyek: Bel Otomatis Sekolah — Windows Desktop**  
**Tanggal:** 28 Oktober 2026  
**Status Kelulusan:** **LULUS SEMPURNA (100% SUITE PASSING: 91/91 TES)**

---

## 1. Latar Belakang dan Temuan Masalah

Berdasarkan pengujian visual pada ukuran jendela laptop non-maksimal (misalnya 1000×650 dan 1280×720) serta evaluasi scaling DPI Windows, ditemukan beberapa penyebab masalah tampilan:

1. **Qt Stylesheet Inheritance Trap pada QFrame & QLabel**:
   - Di PySide6/Qt, kelas `QLabel` merupakan turunan langsung dari `QFrame`.
   - Pada `src/ui/dashboard.py` dan `src/ui/settings_page.py`, penggunaan selektor CSS global `QFrame { padding: 16px; border: 1px solid #e2e8f0; }` menyebabkan seluruh widget teks `QLabel` di dalam kartu mewarisi padding 16px dan border abu-abu di sekeliling setiap kata/angka.
   - Akibatnya, angka jam digital berukuran besar terpotong secara horizontal, teks tanggal dan label status bertumpukan dengan batas kotak, serta muncul garis border tak diinginkan di sekeliling teks.

2. **Ukuran Minimum Jendela Terlalu Kaku**:
   - `MainWindow` sebelumnya menetapkan `setMinimumSize(1080, 680)`.
   - Ukuran ini memblokir pengguna laptop standar beresolusi 1366×768 dengan scaling DPI 125% (area kerja efektif ~1092×614) atau jendela berukuran 1000×650, sehingga jendela terpotong atau tidak dapat diperkecil secara wajar.

3. **Dashboard Tanpa Scroll Area Responsif**:
   - Pada ketinggian jendela terbatas (misal 650px dengan title bar dan taskbar Windows), tata letak vertikal Dashboard menjepit kartu dan memotong tabel "Jadwal Hari Ini" di bagian bawah.

4. **Kerapatan Kolom Aksi Tabel (Tabel Profil, Jadwal, Audio)**:
   - Kolom aksi tabel pada resolusi kecil terhimpit karena kolom tombol menggunakan mode resize otomatis yang tidak memberikan ruang interaktif tetap yang memadai.
   - Tombol "Aktifkan", "Edit", dan "Hapus" pada tabel Profil dan Jadwal tampak terlalu berdempetan jika lebar kolom tidak dijamin dengan batas minimal.
   - Tabel tidak memiliki kebijakan scroll horizontal eksplisit (`ScrollBarAsNeeded`), sehingga bila jendela diperkecil, tombol atau kolom akhir terpotong daripada dapat digeser secara nyaman.

5. **Kerapatan Kontrol Filter pada Halaman Jadwal & Riwayat**:
   - Dropdown pemilihan profil dan filter hari pada halaman Jadwal tidak memiliki pembatasan lebar maksimum yang teratur, sehingga dapat saling mendesak pada lebar jendela 1000px.

---

## 2. Rincian Perbaikan dan File yang Diubah

### A. [`src/ui/main_window.py`](file:///D:/BelOtomatisSekolah/src/ui/main_window.py)
- **Ukuran Jendela Ramah Laptop**: Mengubah ukuran minimum dari `(1080, 680)` menjadi `setMinimumSize(980, 620)` dan ukuran default awal menjadi `resize(1140, 700)`. Hal ini menjamin aplikasi dapat dibuka dan dioperasikan dengan nyaman pada resolusi 1000×650 maupun 1280×720.
- **Sidebar Proporsional**: Mengatur lebar sidebar menjadi tetap `220px` (`min-width: 220px; max-width: 220px;`) sehingga menyisakan ruang maksimal bagi konten utama.
- **Sinkronisasi Navigasi Otomatis**: Menghubungkan sinyal `stacked_widget.currentChanged` ke handler yang menyinkronkan status checked pada tombol navigasi sidebar dan judul header halaman, memastikan judul header selalu akurat bahkan saat perpindahan dipicu dari link cepat dashboard.
- **Reset Stylesheet Global**: Menambahkan aturan `QLabel { background-color: transparent; }` untuk mencegah latar belakang putih bawaan menimpa warna kontainer.

### B. [`src/ui/dashboard.py`](file:///D:/BelOtomatisSekolah/src/ui/dashboard.py)
- **Container QScrollArea Responsif**: Membungkus seluruh isi dashboard ke dalam `QScrollArea` dengan `setWidgetResizable(True)` dan `setFrameShape(QFrame.Shape.NoFrame)`. Pada layar laptop rendah, konten dapat digulir dengan mulus tanpa ada elemen yang terpotong.
- **Scoped Card Selector**: Memberikan object name spesifik (`#ClockCard`, `#StatusCard`, `#NextBellCard`, `#QuickActionsCard`, `#TodayScheduleCard`) dengan styling CSS yang mereset `QLabel` anak (`QLabel { border: none; background: transparent; padding: 0px; }`).
- **Margin Layout Terukur**: Menggantikan padding CSS dengan `setContentsMargins(18, 14, 18, 14)` pada layout kartu, memberikan ruang render penuh tanpa risiko terpotong.
- **Jam Digital Jernih**: Format jam digital ditampilkan dengan font tebal 36px monospace tanpa kotak artefak abu-abu.
- **Dimensi Tombol Ergonomis**: Tombol Mulai Otomatis, Hentikan, dan Bunyikan Bel Manual diberi padding dan tinggi minimum yang memadai (30–34px).
- **Tabel Jadwal Hari Ini Fleksibel**: Tabel jadwal hari ini diberi batas `minimumHeight(150)` dengan `QHeaderView.ResizeMode.Stretch` pada kolom kegiatan dan `ResizeToContents` pada kolom waktu/audio.

### C. [`src/ui/profile_page.py`](file:///D:/BelOtomatisSekolah/src/ui/profile_page.py)
- **Margin & Spacing Bersih**: Mengatur margin halaman `(20, 16, 20, 16)` dan spacing 12px.
- **Header Subtitle Word Wrap**: Menambahkan `setWordWrap(True)` pada deskripsi header agar tidak memicu pemanjangan horizontal yang kaku.
- **Kolom Aksi Lebar Tetap**: Menetapkan kolom 4 (Aksi) menjadi mode `Interactive` dengan lebar `220px`. Hal ini menjamin ketiga tombol (Aktifkan, Edit, Hapus) memiliki ruang horizontal yang cukup lebar (masing-masing min-width 56–68px) dengan jarak spacing 6px tanpa saling menumpuk.
- **Horizontal Scrollbar**: Mengaktifkan `setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)`.

### D. [`src/ui/schedule_page.py`](file:///D:/BelOtomatisSekolah/src/ui/schedule_page.py)
- **Kontrol Filter Proporsional**: Mengatur lebar combobox profil (`min-width: 150px; max-width: 190px`) dan filter hari (`min-width: 170px; max-width: 210px`) dengan layout spacing 8px.
- **Kolom Tabel Terproteksi**:
  - Kolom File Audio (Kolom 3) disetel ke lebar `190px`.
  - Kolom Aksi (Kolom 5) disetel ke mode `Interactive` dengan lebar `225px`.
  - Mengatur `table.horizontalHeader().setMinimumSectionSize(65)` dan `setHorizontalScrollBarPolicy(ScrollBarAsNeeded)`.

### E. [`src/ui/audio_page.py`](file:///D:/BelOtomatisSekolah/src/ui/audio_page.py)
- **Margin Bersih & Word Wrap**: Menambahkan word wrap pada deskripsi header dan mengatur margin container `(20, 16, 20, 16)`.
- **Kolom Aksi Audio**: Kolom Aksi (Kolom 4) diatur ke mode `Interactive` dengan lebar `160px` untuk menampung tombol Putar dan Hapus secara proporsional.
- **Horizontal Scrollbar**: Mengaktifkan `setHorizontalScrollBarPolicy(ScrollBarAsNeeded)`.

### F. [`src/ui/history_page.py`](file:///D:/BelOtomatisSekolah/src/ui/history_page.py)
- **Penyusunan Filter Dua Baris Teratur**:
  - Baris 1: Filter tanggal Mulai, Selesai, dan pencarian nama kegiatan (`min-width: 95–150px`).
  - Baris 2: Filter metode (Semua, Otomatis, Manual) dan filter status (Semua, Selesai, Gagal, dll.) dengan combobox berlebar teratur (`min-width: 100–130px`) serta tombol Reset.
- **Tabel Riwayat Fleksibel**: Kolom kegiatan diatur ke mode `Stretch`, tinggi baris konsisten 42px, dan mendukung scroll horizontal otomatis saat jendela diperkecil.

### G. [`src/ui/settings_page.py`](file:///D:/BelOtomatisSekolah/src/ui/settings_page.py)
- **Integrasi Judul Kartu**: Memindahkan judul kartu ke dalam layout internal kartu dengan styling `#CardTitle`, mencegah pergeseran vertikal.
- **Scoped `#SettingsCard` & `#WarnBox`**: Mengisolasi stylesheet kartu dan mereset `QLabel` child agar kotak peringatan dan label audio tidak menampilkan border ganda tak diinginkan.

---

## 3. Dokumentasi Verifikasi Visual (Screenshots)

Pengujian visual otomatis dan manual telah dijalankan pada dua target resolusi standar laptop Windows: **1000×650** (layar kompak / DPI 125%) dan **1280×720** (layar laptop standar HD).

Semua screenshot hasil render aktual tersimpan di direktori `scratch/screenshots_v6c/`:

| Halaman | Screenshot Resolusi 1000×650 | Screenshot Resolusi 1280×720 | Catatan Evaluasi Visual |
|---|---|---|---|
| **Dashboard** | `final_1000x650_dashboard.png` | `final_1280x720_dashboard.png` | Jam digital 36px terbaca utuh tanpa kotak border abu-abu; status mesin, jadwal berikutnya, countdown, dan tombol Mulai/Hentikan/Bel Manual berjarak rapi; tabel jadwal hari ini dapat diakses penuh via scroll responsif. |
| **Jadwal Bel** | `final_1000x650_schedule.png` | `final_1280x720_schedule.png` | Dropdown filter profil & hari tidak bertumpukan; kolom File Audio (190px) dan Aksi (225px) menampilkan tombol Aktif/Nonaktif, Edit, dan Hapus secara utuh dengan teks jelas. |
| **Profil Jam Pelajaran** | `final_1000x650_profile.png` | `final_1280x720_profile.png` | Kolom Aksi (220px) memberi ruang lega bagi 3 tombol (Aktifkan, Edit, Hapus); tombol memiliki lebar 56–68px tanpa tumpang tindih; teks status rata tengah. |
| **Audio Bel** | `final_1000x650_audio.png` | `final_1280x720_audio.png` | Slider volume master tampil proporsional; tombol Putar dan Hapus terpisah dengan jarak ergonomis. |
| **Riwayat Bel** | `final_1000x650_history.png` | `final_1280x720_history.png` | Kontrol filter dua baris tertata rapi; badge status (Selesai, Gagal, dll.) tampil bersih tanpa teks terpotong. |
| **Pengaturan & Backup** | `final_1000x650_settings.png` | `final_1280x720_settings.png` | Kartu pengaturan sekolah, audio, dan cadangan data berlatar putih bersih tanpa border ganda pada label; tombol Simpan dan Cadangkan Data mudah diakses. |

---

## 4. Hasil Pengujian Otomatis (Automated Tests)

Suite pengujian baru [`tests/test_ui_responsive.py`](file:///D:/BelOtomatisSekolah/tests/test_ui_responsive.py) ditambahkan untuk memvalidasi:
1. `test_window_supports_laptop_resolution`: Memverifikasi `minimumSize` jendela mendukung laptop 1000×650 dan dapat di-resize tanpa exception.
2. `test_dashboard_components_not_clipped_at_small_size`: Memverifikasi jam digital, tombol kontrol mesin, bel manual, dan countdown tampil utuh dan memiliki dimensi minimum memadai pada ukuran kecil.
3. `test_table_action_buttons_spacing_no_overlap`: Menguji geometri koordinat tombol aksi pada tabel Profil dan Jadwal, memastikan urutan tombol dari kiri ke kanan dengan spacing positif tanpa saling menimpa (`pos_x[0] + width <= pos_x[1] <= pos_x[2]`).
4. `test_navigation_and_header_synchronization`: Memverifikasi sinkronisasi judul header dan active state tombol navigasi sidebar saat navigasi internal atau link cepat dipicu.

### Ringkasan Eksekusi Pytest:
- **Total Pengujian**: **91 tes** (bertambah dari 87 tes di Tahap 6B)
- **Lulus (Passed)**: **91 tes (100%)**
- **Gagal (Failed)**: **0**
- **Dilewati (Skipped)**: **0**
- **Waktu Eksekusi**: **12.62 detik**

---

## 5. Hasil Build Executable dan Installer Windows

Kompilasi rilis ulang dijalankan menggunakan `build_release.py`:
- **PyInstaller**: Menghasilkan standalone binary `BelOtomatisSekolah.exe` versi 1.0.0.
- **Inno Setup 6 (ISCC)**: Menghasilkan paket setup installer resmi `BelOtomatisSekolah_Setup_v1.0.0.exe`.

### Ringkasan Metadata Artefak Rilis:
| Artefak Distribusi | Lokasi Berkas | Ukuran | Checksum SHA-256 | Status Validasi |
|---|---|---|---|---|
| **Standalone Binary** | `D:\BelOtomatisSekolah\dist\BelOtomatisSekolah\BelOtomatisSekolah.exe` | 1.75 MB *(1.831.526 bytes)* | `8c03ee7b07ec25f6848b6c679b559d6eef222b6c5e2f20130fa3a02ce07979cf` | **LULUS** (Diuji via `test_executable_launch.py`) |
| **Setup Installer** | `D:\BelOtomatisSekolah\release\BelOtomatisSekolah_Setup_v1.0.0.exe` | 37.56 MB *(39.384.696 bytes)* | `535732c0c4f40be25c2d4376300c8b7ece301a01eb13db22e59b6d93fa58c604` | **LULUS** (Diuji via `test_installed_executable.py`) |

### Verifikasi Perlindungan Data Pengguna:
- Database pengguna di `%APPDATA%\BelOtomatisSekolah\data\bel_sekolah.db` diverifikasi tetap **utuh 100%**:
  - `PROFILES`: 4 profil
  - `SCHEDULES`: 2 jadwal
  - `AUDIO_FILES`: 1 berkas audio
- Tidak ada data yang direset, dimodifikasi secara destruktif, atau dihapus selama proses perbaikan UI maupun build release.

---

## 6. Batasan Operasional yang Masih Ada

1. **Resolusi Minimal Fisik Layar**:
   - Batas minimum jendela aplikasi adalah **980×620 piksel**. Aplikasi tidak direkomendasikan dijalankan pada resolusi layar di bawah 1024×600 (netbook era lama), karena bilah tugas Windows akan memakan ruang vertikal. Pada layar laptop modern (1366×768 ke atas), aplikasi berjalan sangat ideal.
2. **Pengujian Suara Lapangan**:
   - Meskipun tata letak kontrol volume dan pemutar audio responsif, pengujian volume akhir pada sound system/amplifier sekolah tetap wajib divalidasi langsung oleh operator menggunakan tombol "Tes Suara".

---

## 7. Kesimpulan

Tahap 6C **RESPONSIVE UI DAN PENYEMPURNAAN LAYOUT** telah berhasil diselesaikan dengan predikat **LULUS SEMPURNA**. Aplikasi desktop Bel Otomatis Sekolah kini memiliki tampilan yang profesional, konsisten, ergonomis, dan fleksibel pada berbagai dimensi layar laptop Windows, baik saat jendela dimaksimalkan maupun dalam ukuran jendela bebas.
