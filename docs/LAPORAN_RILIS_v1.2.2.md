# LAPORAN RILIS RESMI: BEL OTOMATIS SEKOLAH v1.2.2

**Tanggal Rilis:** 29 Oktober 2026  
**Target Sistem Operasi:** Windows 10 & Windows 11 (64-bit)  
**Lingkungan Runtime:** Python 3.11.9 + PySide6 6.12.0 (Qt 6 Native)  
**Status Pengujian:** 135 Pengujian Lulus (100% PASS, 0 Fail, 0 Skip)

---

## 1. Ringkasan Pembaruan (Update v1.2.2)

Pembaruan **v1.2.2** berfokus pada **Penyempurnaan Operasional Aplikasi**, khususnya sistem notifikasi non-intrusif ketika jadwal otomatis terlewat (*missed schedule notification*), pencegahan duplikasi pencatatan kejadian jadwal, perlindungan idempotensi terhadap restart aplikasi, dan penegasan aturan prioritas audio bel sekolah.

### Penyempurnaan Utama:
1. **Notifikasi Jadwal Otomatis yang Terlewat (`missed`):**
   - Ketika waktu jadwal otomatis tiba saat operator sedang memutar bel manual, pemutaran audio manual tetap dipertahankan tanpa gangguan.
   - Sinyal `schedule_missed` dipancarkan oleh `SchedulerService` dengan informasi nama kegiatan, jam jadwal, dan keterangan alasan konflik secara jelas dalam bahasa Indonesia (misal: *"Jadwal bel 'Bel Masuk' pukul 07:00 dilewati karena audio manual masih berlangsung"*).
   - Antarmuka utama (`MainWindow`) menampilkan banner notifikasi khusus berwarna oranye-emas (`missed_notif_banner`) yang informatif dan otomatis menghilang setelah 7 detik tanpa memblokir operator (non-modal).
   - Sistem tray Windows (`QSystemTrayIcon.showMessage`) secara otomatis mengirimkan notifikasi balon/toast ketika jendela aplikasi diminimalkan atau berjalan di latar belakang (background tray).
   - Dashboard (`DashboardPage`) menyinkronkan label status jadwal berikutnya agar operator mengetahui status keterlewatan bel.
   - Tidak ada notifikasi yang menyatakan bel otomatis berhasil berbunyi jika statusnya `missed`.

2. **Perlindungan Idempotensi & Anti-Duplikasi Log:**
   - Satu kejadian jadwal otomatis yang terlewat hanya dicatat tepat 1 kali pada tabel `bell_logs` dengan status `missed` dan mode `OTOMATIS`.
   - Jadwal yang telah berstatus `missed`, `completed`, `interrupted`, atau `failed` tidak akan dieksekusi ulang pada hari yang sama.
   - Restart aplikasi (atau pembukaan instans baru `SchedulerService`) membaca log database persisten hari ini dan tidak akan memicu pemutaran ulang jadwal yang sudah terlewat atau selesai.
   - Pada pergantian hari berikutnya (*midnight rollover*), memori cache eksekusi direset secara otomatis sehingga jadwal hari berikutnya tetap dapat berjalan normal dan tepat waktu.

3. **Integritas Prioritas Audio & Pembersihan Status:**
   - Bel manual tetap dapat menginterupsi audio bel otomatis maupun audio manual lainnya.
   - Tombol `Stop` menghentikan audio yang sedang aktif (baik otomatis maupun manual) tanpa menonaktifkan scheduler.
   - Selesai normal, gagal, atau dihentikan selalu membersihkan metadata pemutar (`current_title`, `current_file_path`, `current_mode`, `current_audio_id`, `active_session_id`) secara bersih.
   - Callback usang (*stale callback*) dari audio lama yang sudah digantikan tetap diabaikan menggunakan token sesi pemutaran (`active_session_id`).

---

## 2. Berkas yang Diubah / Ditambahkan

| No | Berkas | Deskripsi Perubahan |
|---|---|---|
| 1 | [`src/services/scheduler.py`](file:///d:/BelOtomatisSekolah/src/services/scheduler.py) | Menambahkan sinyal `schedule_missed = Signal(str, str, str)`, memformat pesan konflik dalam bahasa Indonesia yang jelas, dan memancarkan sinyal notifikasi saat jadwal otomatis terlewat karena audio manual aktif (`MANUAL` / `PREVIEW`). |
| 2 | [`src/database/repositories.py`](file:///d:/BelOtomatisSekolah/src/database/repositories.py) | Memperbarui `is_schedule_executed_today` pada `BellLogRepository` agar mengecek status `'requested', 'playing', 'completed', 'interrupted', 'missed', 'failed'`, mencegah eksekusi ulang setelah restart aplikasi. |
| 3 | [`src/ui/main_window.py`](file:///d:/BelOtomatisSekolah/src/ui/main_window.py) | Menambahkan `missed_notif_banner` pada panel kanan, menghubungkan sinyal `scheduler.schedule_missed`, mengimplementasikan `_on_schedule_missed` dengan notifikasi banner UI dan balon system tray Windows (`tray.showMessage`). |
| 4 | [`src/ui/dashboard.py`](file:///d:/BelOtomatisSekolah/src/ui/dashboard.py) | Menghubungkan sinyal `scheduler.schedule_missed` dan menampilkan keterangan jadwal yang terlewat pada label dashboard. |
| 5 | [`src/__init__.py`](file:///d:/BelOtomatisSekolah/src/__init__.py) | Menaikkan versi paket menjadi `1.2.2`. |
| 6 | [`src/core/config.py`](file:///d:/BelOtomatisSekolah/src/core/config.py) | Menetapkan konstanta `APP_VERSION = "1.2.2"`. |
| 7 | [`installer/BelOtomatisSekolah.iss`](file:///d:/BelOtomatisSekolah/installer/BelOtomatisSekolah.iss) | Memperbarui versi installer Inno Setup menjadi `1.2.2`. |
| 8 | [`build_release.py`](file:///d:/BelOtomatisSekolah/build_release.py) | Memperbarui skrip otomatisasi build ke versi `1.2.2`. |
| 9 | [`tests/test_installed_executable.py`](file:///d:/BelOtomatisSekolah/tests/test_installed_executable.py) | Menyesuaikan verifikasi paket target instalasi ke `v1.2.2`. |
| 10 | [`tests/test_missed_schedule_and_notifications.py`](file:///d:/BelOtomatisSekolah/tests/test_missed_schedule_and_notifications.py) | **Berkas Pengujian Baru**: Pengujian khusus untuk notifikasi jadwal terlewat, pencatatan tunggal tanpa duplikasi, pencegahan eksekusi ulang pasca-restart aplikasi, dan rollover hari berikutnya. |

---

## 3. Hasil Pengujian Otomatis (Test Suite)

Seluruh test suite dijalankan menggunakan Python 3.11.9:
```text
pytest tests/ -v
============================ 135 passed in 37.70s =============================
```

### Rincian Verifikasi Fitur dan Regresi:
1. **Bel manual menginterupsi bel otomatis:** Audio otomatis berhenti seketika, dicatat `interrupted`, audio manual langsung berbunyi. (**LULUS**)
2. **Bel manual kedua menggantikan bel manual pertama:** Audio pertama berhenti, audio kedua berbunyi dari awal. (**LULUS**)
3. **Jadwal otomatis tiba saat audio manual masih berlangsung:** Audio manual tidak dipotong, jadwal otomatis dilewati dan dicatat sebagai `missed`. (**LULUS**)
4. **Notifikasi jadwal terlewat muncul tanpa memotong audio manual:** Sinyal `schedule_missed` terverifikasi memuat nama jadwal dan jam, banner antarmuka muncul, dan audio manual tetap bermain utuh. (**LULUS**)
5. **Satu jadwal `missed` hanya dicatat satu kali:** Idempotensi memori sesi menjamin tidak ada duplikasi entri pada tabel `bell_logs`. (**LULUS**)
6. **Jadwal `missed` tidak diulang pada hari yang sama:** Setelah audio manual selesai atau dihentikan, jam jadwal yang telah terlewat tidak dieksekusi lagi. (**LULUS**)
7. **Jadwal berikutnya tetap berjalan:** Jadwal jam berikutnya (misal 07:40 setelah 07:00 terlewat) dieksekusi secara normal dan tepat waktu. (**LULUS**)
8. **Scheduler tetap ON setelah interupsi dan Stop:** Status ON/OFF dan timer `SchedulerService` tidak terpengaruh oleh interupsi atau tombol Stop audio. (**LULUS**)
9. **Scheduler OFF tetap memungkinkan pemutaran manual:** Operator tetap dapat membunyikan bel manual saat scheduler berstatus OFF. (**LULUS**)
10. **Callback audio lama tidak merusak status audio baru:** Token sesi inkremental menolak sinyal callback dari audio yang telah dihentikan. (**LULUS**)
11. **Audio gagal atau file hilang ditangani tanpa crash:** Penanganan kesalahan aman, dicatat `failed`, dan aplikasi tetap berjalan stabil. (**LULUS**)
12. **Aplikasi restart tidak memutar ulang jadwal lama secara keliru:** Instansiasi baru `SchedulerService` memverifikasi database log dan tidak mengeksekusi ulang jadwal yang berstatus `completed`, `interrupted`, `missed`, atau `failed`. (**LULUS**)
13. **Profil Reguler, Ramadan, Ujian, dan Kustom:** Seluruh pengujian penggantian profil, pembuatan profil baru, dan penjadwalan per profil lulus 100%. (**LULUS**)
14. **Backup/restore dan database SQLite:** Pengujian backup ZIP persisten, pemulihan data, validasi hash, dan pencegahan path traversal lulus 100%. (**LULUS**)
15. **Penanganan shutdown Windows:** Penanganan event native Windows (`WM_QUERYENDSESSION`, `WM_ENDSESSION`), pembersihan timer, pelepasan lock audio, dan penguncian jendela di tengah monitor lulus 100%. (**LULUS**)

---

## 4. Artefak Distribusi Rilis v1.2.2

Seluruh artefak rilis resmi telah dikompilasi ulang secara bersih untuk Windows 10 & Windows 11 (64-bit) dan disimpan di folder `release/` dan `dist/`:

| Tipe Artefak | Lokasi Berkas | Ukuran | Checksum SHA-256 |
|---|---|---|---|
| **Installer Setup EXE** | [`release/BelOtomatisSekolah_Setup_v1.2.2.exe`](file:///d:/BelOtomatisSekolah/release/BelOtomatisSekolah_Setup_v1.2.2.exe) | 45.63 MB (47.842.113 bytes) | `c1a6275c94533f54b8fca069de453a34b2c10a3aedb8f63450acbeda4dc72ae0` |
| **Paket Portable ZIP** | [`release/BelOtomatisSekolah_Portable_v1.2.2.zip`](file:///d:/BelOtomatisSekolah/release/BelOtomatisSekolah_Portable_v1.2.2.zip) | 79.80 MB (83.673.779 bytes) | `a8f693c6ab2dd5c28a55c05231758be749050b2aae9c8ccd221761868d0f8004` |
| **Standalone Binary EXE** | [`dist/BelOtomatisSekolah/BelOtomatisSekolah.exe`](file:///d:/BelOtomatisSekolah/dist/BelOtomatisSekolah/BelOtomatisSekolah.exe) | 1.87 MB (1.965.768 bytes) | `ec253605ccc2b46483806570602286ed41582d6b7aabca703b7f3993ecff4bb0` |

### Pengujian Peluncuran Paket Hasil Build:
- Paket Portable ZIP v1.2.2 diekstrak ke lingkungan terisolasi temporer dan diverifikasi meluncurkan proses utama, membuat database pengguna di `%APPDATA%\BelOtomatisSekolah`, menyalin seluruh file audio bawaan, dan membaca log sistem secara 100% mandiri.
- Executable hasil instalasi Inno Setup terverifikasi dapat diluncurkan dan dimatikan secara bersih tanpa ketergantungan luar.

---

## 5. Catatan Keterbatasan

> [!NOTE]
> **Pengujian Output Fisik Sound System:**
> Pengujian otomatis memvalidasi seluruh alur kode, API audio PySide6 / WinMM, antarmuka grafis, database, dan paket rilis. Pengujian kenyaringan suara fisik, pengaturan equalizer/amplifier sekolah, dan koneksi kabel speaker lorong sekolah tetap disarankan untuk diperiksa saat pertama kali dihubungkan ke komputer operator sekolah.

